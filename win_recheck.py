import re, unicodedata, io
from decimal import Decimal, InvalidOperation
import pandas as pd
import streamlit as st
import pdfplumber

def base(s):
    s=unicodedata.normalize('NFKC',str(s)).upper().strip()
    s=re.sub(r'[・･／]','/',s)
    s=re.sub(r'\s+',' ',s)
    s=re.sub(r'\s+[RH]\d{1,2}年.*$', '', s)
    return re.sub(r'\s+(AB|CD|EF|GH|IJ|KL|MN|OP|QR|ST|UV|WX|YZ)$','',s)

ALIASES = {}
ALIASES.update({base(a):base(b) for a,b in [('ARAI AA Sendai', 'ARAI Sendai'), ('ｱﾗｲAA仙台', 'ARAI Sendai'), ('アライAA仙台', 'ARAI Sendai'), ('ARAI AA Sendai', 'ARAI Sendai'), ('ｱﾗｲAAﾍﾞｲｻｲﾄﾞ', 'ARAI Bayside'), ('アライAAベイサイド', 'ARAI Bayside'), ('ARAI AA Bayside', 'ARAI Bayside'), ('ｱﾗｲ小山VT', 'ARAI Oyama VT'), ('アライ小山VT', 'ARAI Oyama VT'), ('JU福岡・鹿児島', 'JU Fukuoka'), ('JU Fukuoka/Kagoshima', 'JU Fukuoka'), ('JU Fukuoka / Kagoshima', 'JU Fukuoka'), ('JU宮城・秋田', 'JU Miyagi'), ('JU Miyagi/Akita', 'JU Miyagi'), ('ﾍﾞｲｵｰｸ', 'BAYAUC'), ('ベイオーク', 'BAYAUC'), ('BAY OAK', 'BAYAUC'), ('BAYOAK', 'BAYAUC'), ('オークネット', 'AUCNET'), ('ｵｰｸﾈｯﾄ', 'AUCNET'), ('AUC', 'AUCNET'), ('ﾋｰﾛｰ', 'HERO'), ('ヒーロー', 'HERO'), ('日産大阪AA', 'NISSAN Osaka'), ('NAAｵｰｻｶ', 'NAA Osaka'), ('NAA大阪', 'NAA Osaka'), ('SAA浜松', 'SUZUKI AA Hamamatsu'), ('LAA岡山', 'LAA Okayama'), ('LAA四国', 'LAA Shikoku'), ('KCAA福岡', 'KCAA Fukuoka'), ('KCAA京都', 'KCAA Kyoto'), ('KCAA山口', 'KCAA Yamaguchi'), ('KCAA南九州', 'KCAA Minami Kyushu'), ('MIRIVE愛知', 'MIRIVE Aichi'), ('MIRIVE埼玉', 'MIRIVE Saitama'), ('MIRIVE大阪', 'MIRIVE Osaka'), ('CAA中部', 'CAA Chubu'), ('CAA東京', 'CAA Tokyo'), ('CAA岐阜', 'CAA Gifu'), ('CAA東北', 'CAA Tohoku'), ('IAA大阪', 'IAA Osaka'), ('TAA北海道', 'TAA Hokkaido'), ('TAA東北', 'TAA Tohoku'), ('TAA関東', 'TAA Kanto'), ('TAA中部', 'TAA Chubu'), ('TAA横浜', 'TAA Yokohama'), ('TAA近畿', 'TAA Kinki'), ('TAA兵庫', 'TAA Hyogo'), ('TAA広島', 'TAA Hiroshima'), ('TAA九州', 'TAA Kyushu'), ('TAA南九州', 'TAA Minami Kyushu'), ('TAA四国', 'TAA Shikoku'), ('NAA名古屋', 'NAA Nagoya'), ('NAA福岡', 'NAA Fukuoka'), ('NAA東京', 'NAA Tokyo'), ('ZIP東京', 'ZIP Tokyo'), ('ZIP大阪', 'ZIP Osaka'), ('ﾎﾝﾀﾞ東京', 'Honda Tokyo'), ('ホンダ東京', 'Honda Tokyo'), ('ﾎﾝﾀﾞ名古屋', 'Honda Nagoya'), ('ホンダ名古屋', 'Honda Nagoya'), ('ﾎﾝﾀﾞ関西', 'Honda Kansai'), ('ホンダ関西', 'Honda Kansai'), ('ﾎﾝﾀﾞ仙台', 'Honda Sendai'), ('ホンダ仙台', 'Honda Sendai'), ('ﾎﾝﾀﾞ北海道', 'Honda Hokkaido'), ('ホンダ北海道', 'Honda Hokkaido'), ('ﾎﾝﾀﾞ九州', 'Honda Kyushu'), ('ホンダ九州', 'Honda Kyushu'), ('JU東京', 'JU Tokyo'), ('JU静岡', 'JU Shizuoka'), ('JU石川', 'JU Ishikawa'), ('JU福島', 'JU Fukushima'), ('JU新潟', 'JU Niigata'), ('JU富山', 'JU Toyama'), ('JU北海道', 'JU Hokkaido'), ('JU岐阜', 'JU Gifu'), ('JU愛知', 'JU Aichi'), ('JU茨城', 'JU Ibaraki'), ('JU三重', 'JU Mie'), ('JU Tochigi', 'JU Tochigi'), ('ARAI Oyama', 'ARAI Oyama')]})
MASTER_AUCTIONS = ['Honda Tokyo', 'Honda Nagoya', 'Honda Kansai', 'Honda Sendai', 'Honda Hokkaido', 'Honda Kyushu', 'JU Tokyo', 'JU Mie', 'JU Saitama', 'JU Shizuoka', 'JU Fukui', 'JU Nagano', 'JU Yamaguchi', 'JU Ishikawa', 'JU Ibaraki', 'JU Nagasaki', 'JU Kumamoto', 'JU Aomori', 'JU Fukushima', 'JU Toyama', 'JU Hiroshima', 'JU Gunma', 'JU Aichi', 'JU Kanagawa', 'JU Miyagi', 'JU Niigata', 'JU Fukuoka', 'JU Tochigi', 'JU Hokkaido', 'JU Chiba', 'JU Okinawa', 'JU Shimane', 'JU Gifu', 'JU Nara', 'JU Yamagata', 'JU Yamanashi', 'USS Sapporo', 'USS Kobe', 'USS Niigata', 'USS JAA', 'USS Fukuoka', 'USS Tohoku', 'USS Tokyo', 'USS Nagoya', 'USS Osaka', 'USS Saitama', 'USS Okayama', 'USS Kyushu', 'USS Gunma', 'USS Shizuoka', 'USS Hokuriku', 'USS Yokohama', 'USS R-Nagoya', 'USS HAA Kobe', 'CAA Chubu', 'CAA Gifu', 'CAA Tohoku', 'CAA Tokyo', 'TAA Hiroshima', 'TAA Kinki', 'TAA Kyushu', 'TAA Minami Kyushu', 'TAA Shikoku', 'TAA Chubu', 'TAA Kanto', 'TAA Tohoku', 'TAA Hokkaido', 'TAA Yokohama', 'TAA Hyogo', 'NAA Fukuoka', 'NAA Osaka', 'NAA Nagoya', 'NAA Tokyo', 'SAA Sapporo', 'JBA Kobe', 'JBA Yokohama', 'LAA Okayama', 'LAA Shikoku', 'KCAA Kyoto', 'KCAA Minami Kyushu', 'KCAA Fukuoka', 'KCAA Yamaguchi', 'IAA Osaka', 'MIRIVE Saitama', 'MIRIVE Osaka', 'MIRIVE Aichi', 'ZIP Osaka', 'ZIP Tokyo', 'ZERO Chiba', 'ZERO Osaka', 'ZERO Hokkaido', 'ZERO Shonan', 'ZERO Hakata', 'ZERO Sendai', 'ARAI Oyama', 'ARAI Oyama VT', 'ARAI Bayside', 'ARAI Sendai', 'BDS Kantou', 'BDS Kyushu', 'BDS Kansai', 'ORIX Atsugi Nyusatsu', 'ORIX Fukuoka Nyusatsu', 'ORIX Kobe Nyusatsu', 'ORIX Sendai Nyusatsu', 'LUM Tokyo Nyusatsu', 'LUM Fukuoka Nyusatsu', 'LUM Nagoya Nyusatsu', 'LUM Hokkaido Nyusatsu', 'LUM Kobe Nyusatsu', 'NPS Chubu Nyusatsu', 'NPS Osaka Nyusatsu', 'NPS Sendai Nyusatsu', 'NPS Tochigi Nyusatsu', 'NPS Tokyo Nyusatsu', 'NPS Tomakomai Nyusatsu', 'NISSAN Osaka', 'SUZUKI AA Hamamatsu', 'ISUZU Kyushu', 'AUCNET', 'BAYAUC', 'HERO']
EXTRA_ALIASES = {'ホンダ東京': 'Honda Tokyo', 'ホンダ名古屋': 'Honda Nagoya', 'ホンダ関西': 'Honda Kansai', 'ホンダ仙台': 'Honda Sendai', 'ホンダ北海道': 'Honda Hokkaido', 'ホンダ九州': 'Honda Kyushu', 'JU東京': 'JU Tokyo', 'JU三重': 'JU Mie', 'JU埼玉': 'JU Saitama', 'JU静岡': 'JU Shizuoka', 'JU福井': 'JU Fukui', 'JU長野': 'JU Nagano', 'JU山口': 'JU Yamaguchi', 'JU石川': 'JU Ishikawa', 'JU茨城': 'JU Ibaraki', 'JU長崎': 'JU Nagasaki', 'JU熊本': 'JU Kumamoto', 'JU青森': 'JU Aomori', 'JU福島': 'JU Fukushima', 'JU富山': 'JU Toyama', 'JU広島': 'JU Hiroshima', 'JU群馬': 'JU Gunma', 'JU愛知': 'JU Aichi', 'JU神奈川': 'JU Kanagawa', 'JU宮城': 'JU Miyagi', 'JU新潟': 'JU Niigata', 'JU福岡': 'JU Fukuoka', 'JU栃木': 'JU Tochigi', 'JU北海道': 'JU Hokkaido', 'JU千葉': 'JU Chiba', 'JU沖縄': 'JU Okinawa', 'JU島根': 'JU Shimane', 'JU岐阜': 'JU Gifu', 'JU奈良': 'JU Nara', 'JU山形': 'JU Yamagata', 'JU山梨': 'JU Yamanashi', 'USS札幌': 'USS Sapporo', 'USS神戸': 'USS Kobe', 'USS新潟': 'USS Niigata', 'USS福岡': 'USS Fukuoka', 'USS東北': 'USS Tohoku', 'USS東京': 'USS Tokyo', 'USS名古屋': 'USS Nagoya', 'USS大阪': 'USS Osaka', 'USS埼玉': 'USS Saitama', 'USS岡山': 'USS Okayama', 'USS九州': 'USS Kyushu', 'USS群馬': 'USS Gunma', 'USS静岡': 'USS Shizuoka', 'USS北陸': 'USS Hokuriku', 'USS横浜': 'USS Yokohama', 'CAA中部': 'CAA Chubu', 'CAA岐阜': 'CAA Gifu', 'CAA東北': 'CAA Tohoku', 'CAA東京': 'CAA Tokyo', 'TAA広島': 'TAA Hiroshima', 'TAA近畿': 'TAA Kinki', 'TAA九州': 'TAA Kyushu', 'TAA南九州': 'TAA Minami Kyushu', 'TAA四国': 'TAA Shikoku', 'TAA中部': 'TAA Chubu', 'TAA関東': 'TAA Kanto', 'TAA東北': 'TAA Tohoku', 'TAA北海道': 'TAA Hokkaido', 'TAA横浜': 'TAA Yokohama', 'TAA兵庫': 'TAA Hyogo', 'NAA福岡': 'NAA Fukuoka', 'NAA大阪': 'NAA Osaka', 'NAA名古屋': 'NAA Nagoya', 'NAA東京': 'NAA Tokyo', 'SAA札幌': 'SAA Sapporo', 'JBA神戸': 'JBA Kobe', 'JBA横浜': 'JBA Yokohama', 'LAA岡山': 'LAA Okayama', 'LAA四国': 'LAA Shikoku', 'KCAA京都': 'KCAA Kyoto', 'KCAA南九州': 'KCAA Minami Kyushu', 'KCAA福岡': 'KCAA Fukuoka', 'KCAA山口': 'KCAA Yamaguchi', 'IAA大阪': 'IAA Osaka', 'MIRIVE埼玉': 'MIRIVE Saitama', 'MIRIVE大阪': 'MIRIVE Osaka', 'MIRIVE愛知': 'MIRIVE Aichi', 'ZIP大阪': 'ZIP Osaka', 'ZIP東京': 'ZIP Tokyo', 'ZERO千葉': 'ZERO Chiba', 'ZERO大阪': 'ZERO Osaka', 'ZERO北海道': 'ZERO Hokkaido', 'ZERO湘南': 'ZERO Shonan', 'ZERO博多': 'ZERO Hakata', 'ZERO仙台': 'ZERO Sendai', 'アライ小山': 'ARAI Oyama', 'アライ小山VT': 'ARAI Oyama VT', 'アライベイサイド': 'ARAI Bayside', 'アライ仙台': 'ARAI Sendai', 'BDS関東': 'BDS Kantou', 'BDS九州': 'BDS Kyushu', 'BDS関西': 'BDS Kansai', 'ORIX厚木入札': 'ORIX Atsugi Nyusatsu', 'ORIX福岡入札': 'ORIX Fukuoka Nyusatsu', 'ORIX神戸入札': 'ORIX Kobe Nyusatsu', 'ORIX仙台入札': 'ORIX Sendai Nyusatsu', 'LUM東京入札': 'LUM Tokyo Nyusatsu', 'LUM福岡入札': 'LUM Fukuoka Nyusatsu', 'LUM名古屋入札': 'LUM Nagoya Nyusatsu', 'LUM北海道入札': 'LUM Hokkaido Nyusatsu', 'LUM神戸入札': 'LUM Kobe Nyusatsu', 'NPS中部入札': 'NPS Chubu Nyusatsu', 'NPS大阪入札': 'NPS Osaka Nyusatsu', 'NPS仙台入札': 'NPS Sendai Nyusatsu', 'NPS栃木入札': 'NPS Tochigi Nyusatsu', 'NPS東京入札': 'NPS Tokyo Nyusatsu', 'NPS苫小牧入札': 'NPS Tomakomai Nyusatsu', '日産大阪': 'NISSAN Osaka', 'スズキAA浜松': 'SUZUKI AA Hamamatsu', 'いすゞ九州': 'ISUZU Kyushu', 'BAY AUC': 'BAYAUC', 'ARAI AA Oyama': 'ARAI Oyama', 'アライAA小山': 'ARAI Oyama', 'アライAA小山VT': 'ARAI Oyama VT', 'USS HAA KOBE': 'USS HAA Kobe', 'JU Fukuoka Kagoshima': 'JU Fukuoka', 'JU Miyagi Akita': 'JU Miyagi'}

def auction_key(s):
    return re.sub(r"[\s/_.・-]+", "", base(s))

MASTER_LOOKUP = {auction_key(n): n for n in MASTER_AUCTIONS}
for a,b in list(ALIASES.items()) + list(EXTRA_ALIASES.items()):
    canonical = MASTER_LOOKUP.get(auction_key(b))
    if canonical:
        MASTER_LOOKUP[auction_key(a)] = canonical

def auction(s):
    return MASTER_LOOKUP.get(auction_key(s), base(s))

def known_auction(s):
    return auction(s) in MASTER_AUCTIONS

def lot(s):
    s=base(s)
    return re.sub(r'^0+(?=\d)','',re.sub(r'\.0+$','',s)) if re.fullmatch(r'\d+(?:\.0+)?',s) else s

def price(s, divisor=1):
    try:
        n=Decimal(re.sub(r'[,，\s¥￥]','',str(s)))/Decimal(divisor)
        return n if n.is_finite() else None
    except (InvalidOperation, ValueError): return None

def record(a,l,p,source,date=''):
    return dict(Auction=str(a).strip(),Lot=str(l).strip(),Price=p,Source=source,Date=date)

def pdf_rows(data):
    rows=[]; warnings=[]
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i,page in enumerate(pdf.pages,1):
            text=page.extract_text(layout=True) or ''
            current=None
            for line in text.splitlines():
                m=re.match(r'^\s*(\d{1,2}/\d{1,2})\s+(.+?)\s+[RHS]\d{1,2}年(?:\s|$)',line) or re.match(r'^\s*(\d{1,2}/\d{1,2})\s{2,}(.+?)\s{2,}\S',line)
                if m: current=m.groups()
                m=re.search(r'\d+回\s+(\d+[A-Z]?)\b.*?([\d,.]+)\s*万円',line)
                if m and current:
                    rows.append(record(current[1],m[1],price(m[2]),'AUCNEO',current[0])); current=None
            expected=len(re.findall(r'\d+回\s+\d+',text))
            if expected!=sum(1 for _ in re.finditer(r'\d+回\s+\d+.*?万円',text)): warnings.append(f'Page {i}: review missing prices')
    return rows,warnings

def taa_rows(text):
    text=unicodedata.normalize('NFKC',text)
    text=re.sub(r'<br\s*/?>','\n',text,flags=re.I)
    pattern=r'\b((?:TAA|CAA)[A-Z]+(?:[ ]+[A-Z]+)?)\s*[|\t\n ]+\s*(\d{3,7})\b'
    matches=list(re.finditer(pattern,text,re.I)); rows=[]; warnings=[]
    for i,m in enumerate(matches):
        block=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        p=re.search(r'\bsuccess(?:\s+for\s+REAL)?\s*[|\t\n ]+\s*([\d,]+(?:\.\d+)?)',block,re.I)
        if p: rows.append(record(m[1],m[2],price(p[1],10),'TAA/CAA'))
        else: warnings.append(f'{m[1]} {m[2]}: success price not found')
    return rows,warnings

def compare(jp,external,tolerance):
    merged={}; conflicts=[]; buckets={}; out=[]
    for r in external:
        k=(auction(r['Auction']),lot(r['Lot']))
        if 'SHARED' in k[0]: continue
        if not known_auction(r['Auction']):
            out.append({'Source':r['Source'],'Auction':r['Auction'],'Lot':r['Lot'],'Site WIN':r['Price'],'BIZUPON WIN':None,'Difference':None,'Status':'Unknown Auction'}); continue
        if k in merged:
            old=merged[k]
            if old['Price'] is not None and r['Price'] is not None and old['Price']!=r['Price']: conflicts.append((k,old['Price'],r['Price']))
            if old['Price'] is None: merged[k]=r
        else: merged[k]=r
    for r in jp:
        if not known_auction(r['Auction']):
            out.append({'Source':'BIZUPON','Auction':r['Auction'],'Lot':r['Lot'],'Site WIN':None,'BIZUPON WIN':r['Price'],'Difference':None,'Status':'Unknown Auction'}); continue
        buckets.setdefault((auction(r['Auction']),lot(r['Lot'])),[]).append(r)
    def emit(a,b,status):
        r=a or b; x=a['Price'] if a else None; y=b['Price'] if b else None
        out.append({'Source':a['Source'] if a else 'BIZUPON','Auction':auction(r['Auction']),'Lot':r['Lot'],'Site WIN':x,'BIZUPON WIN':y,'Difference':abs(x-y) if x is not None and y is not None else None,'Status':status})
    for k,a in merged.items():
        b=buckets.get(k,[])
        if not b: emit(a,None,'Missing in BIZUPON'); continue
        b.sort(key=lambda r:abs(r['Price']-a['Price']) if r['Price'] is not None and a['Price'] is not None else Decimal('Infinity'))
        r=b.pop(0); x,y=a['Price'],r['Price']
        emit(a,r,'Price Missing' if x is None or y is None else 'Matched' if abs(x-y)<=tolerance else 'Price Diff')
    for b in buckets.values():
        for r in b: emit(None,r,'Missing in Auction')
    return pd.DataFrame(out),conflicts

def read_table(f):
    return pd.read_csv(f,dtype=str,keep_default_na=False) if f.name.lower().endswith('.csv') else pd.read_excel(f,dtype=str).fillna('')

def table_rows(f,source,defaults,divisor):
    df=read_table(f); cols=list(df.columns)
    st.caption(f'{f.name}: {len(df)} rows')
    selected=[]
    expected=['Auction','Lot number','Sold for'] if source=='BIZUPON' else ['Auction','Lot','Win Price (Man Yen)']
    if all(c in cols for c in expected):
        return [record(r[expected[0]],r[expected[1]],price(r[expected[2]],divisor),source) for _,r in df.iterrows() if str(r[expected[0]]).strip() and str(r[expected[1]]).strip()]
    for label,index in zip(['Auction','Lot','Winning price'],defaults):
        selected.append(st.selectbox(f'{source}: {label}',cols,index=min(index,len(cols)-1),key=f'{source}-{label}-{f.name}'))
    return [record(r[selected[0]],r[selected[1]],price(r[selected[2]],divisor),source) for _,r in df.iterrows() if str(r[selected[0]]).strip() and str(r[selected[1]]).strip()]

def uss_rows(data):
    for encoding in ('utf-8-sig', 'cp932', 'cp1252'):
        try:
            df=pd.read_csv(io.BytesIO(data),encoding=encoding,dtype=str,keep_default_na=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('USS CSV encoding not recognized')
    required={'Date','Bid No.','Site','Result','Final Price'}
    if not required.issubset(df.columns):
        raise ValueError('USS CSV missing columns: '+', '.join(sorted(required-set(df.columns))))
    short={auction_key(n[4:]):n for n in MASTER_AUCTIONS if n.startswith('USS ')}
    # Combined USS site label is Nagoya in BIZUPON's auction master.
    short[auction_key('Nagoya&Hokuriku')] = 'USS Nagoya'
    short[auction_key('USS Nagoya&Hokuriku')] = 'USS Nagoya'
    rows=[]; warnings=[]
    for _,r in df.iterrows():
        if base(r['Result']) not in ('SOLD','NEGOTIATE SOLD'): continue
        a=short.get(auction_key(r['Site']),auction(r['Site']))
        p=price(r['Final Price'],10)
        if not known_auction(a): warnings.append(f"USS: unknown site {r['Site']}")
        if p is None: warnings.append(f"USS {a} {r['Bid No.']}: final price missing")
        d=pd.to_datetime(r['Date'],format='%b %d.%y',errors='coerce')
        if pd.isna(d):
            warnings.append(f"USS {a} {r['Bid No.']}: invalid date {r['Date']}")
            continue
        rows.append(record(a,r['Bid No.'],p,'USS',d.strftime('%Y-%m-%d')))
    return rows,warnings

@st.cache_data(show_spinner=False)
def cached_pdf_rows(data):
    return pdf_rows(data)

def render_win_recheck():
    st.markdown('### BIZUPON WIN RECHECK')
    st.caption('Upload or paste your data → select auction date → review differences.')
    with st.expander('1. Upload / paste winning data', expanded=True):
        a,b,c,d=st.columns(4)
        with a:
            jpfile=st.file_uploader('BIZUPON WIN',type=['xlsx','xls','csv'],key='wr_jp')
        with b:
            files=st.file_uploader('AUCNEO WON',type=['pdf','xlsx','xls','csv'],accept_multiple_files=True,key='wr_auc')
        with c:
            pasted=st.text_area('TAA / CAA WIN — paste table',height=100,key='wr_taa')
        with d:
            ussfiles=st.file_uploader("USS WIN CSV",type=["csv"],accept_multiple_files=True,key="wr_uss")
        try:
            jp=table_rows(jpfile,'BIZUPON',(3,4,15),10000) if jpfile else []
            ext=[]; warnings=[]; pending=False
            for i,f in enumerate(files):
                if f.name.lower().endswith('.pdf'):
                    r,w=cached_pdf_rows(f.getvalue()); dates=sorted({x['Date'] for x in r},key=lambda d:tuple(map(int,d.split('/'))))
                    chosen=st.selectbox(f'{f.name}: auction date',dates,index=0 if len(dates)==1 else None,placeholder='Select date',key=f'wr_v4_date_{i}_{f.name}')
                    if chosen is None: pending=True
                    ext.extend(x for x in r if x['Date']==chosen); warnings.extend(w)
                else: ext.extend(table_rows(f,'AUCNEO',(0,1,2),1))
            r,w=taa_rows(pasted); ext.extend(r); warnings.extend(w)
            ur=[]
            for f in ussfiles:
                r,w=uss_rows(f.getvalue()); ur.extend(r); warnings.extend(w)
            if ur:
                dates=sorted({r['Date'] for r in ur})
                chosen=st.selectbox('USS auction date',dates,index=0 if len(dates)==1 else None,key='wr_uss_date')
                if chosen is None: pending=True
                else:
                    pdf_dates={r['Date'] for r in ext if r['Source']=='AUCNEO' and r['Date']}
                    if pdf_dates and pdf_dates!={f'{int(chosen[5:7])}/{int(chosen[8:10])}'}:
                        # Compare numeric month/day to allow leading zeros in PDF.
                        if {tuple(map(int,x.split('/'))) for x in pdf_dates}!={(int(chosen[5:7]),int(chosen[8:10]))}:
                            st.error('USS and AUCNEO PDF auction dates differ. Select matching dates.'); return
                    ext.extend(r for r in ur if r['Date']==chosen)
            st.caption(f'BIZUPON: {len(jp)} rows | Auction: {len(ext)} rows')
        except Exception as e:
            st.error(f'Input could not be processed: {e}'); return
    if warnings:
        with st.expander(f'Extraction warnings ({len(warnings)})'):
            for w in warnings: st.warning(w)
    if pending:
        st.info('Select the auction date for each dated source before reviewing.'); return
    if not jp or not ext:
        st.info('Add BIZUPON WIN and at least one auction source to start.'); return
    df,conflicts=compare(jp,ext,Decimal('0'))
    if conflicts:
        st.warning(f'{len(conflicts)} duplicate price conflicts — review before accepting results.')
        with st.expander('View conflicting prices'):
            st.write(conflicts)
    if df.empty: return
    counts=df.Status.value_counts(); matched=int(counts.get('Matched',0))
    st.markdown(f'**WIN REVERSE** · Total: {len(df)} | Matched: {matched} | Needs review: {len(df)-matched}')
    a,b,c=st.columns([2,2,1])
    with a:
        statuses=st.multiselect('Status filter',sorted(df.Status.unique()),default=[x for x in sorted(df.Status.unique()) if x!='Matched'],key='wr_v4_status')
    with b:
        auctions=st.multiselect('Auction filter',sorted(df.Auction.unique()),key='wr_v4_auction',placeholder='All auctions')
    with c:
        search=st.text_input('Find lot',key='wr_v4_search').strip()
    view=df[df.Status.isin(statuses)]
    if auctions: view=view[view.Auction.isin(auctions)]
    if search: view=view[view.Lot.map(lot).str.contains(lot(search),regex=False)]
    view=view.rename(columns={'Source':'SOURCE / TYPE','Auction':'AUCTION','Lot':'LOT NUMBER','Site WIN':'AUCTION WIN','BIZUPON WIN':'BIZUPON WIN','Difference':'DIFFERENCE','Status':'STATUS'}).copy()
    for col in ['AUCTION WIN','BIZUPON WIN','DIFFERENCE']:
        view[col]=pd.to_numeric(view[col],errors='coerce')
    def status_color(v):
        return 'color: #137333' if v=='Matched' else 'color: #b3261e'
    styled=view.style.map(status_color,subset=['STATUS']).format({c:'{:.1f}' for c in ['AUCTION WIN','BIZUPON WIN','DIFFERENCE']},na_rep='')
    st.dataframe(styled,use_container_width=True,hide_index=True,height=550,column_config={c:st.column_config.NumberColumn(format='%.1f') for c in ['AUCTION WIN','BIZUPON WIN','DIFFERENCE']})
    st.caption(f'Showing {len(view)} of {len(df)} records · Prices in 万円 · Exact comparison')
    a,b=st.columns(2)
    a.download_button('Download filtered CSV',view.to_csv(index=False).encode('utf-8-sig'),'win_recheck.csv','text/csv')
    buf=io.BytesIO(); view.to_excel(buf,index=False,engine='openpyxl'); b.download_button('Download filtered Excel',buf.getvalue(),'win_recheck.xlsx')
