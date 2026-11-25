import re, unicodedata, io
from decimal import Decimal, InvalidOperation
import pandas as pd
import streamlit as st
import pdfplumber

def base(s):
    s=unicodedata.normalize('NFKC',str(s)).upper().strip()
    s=re.sub(r'[・･／]','/',s)
    s=re.sub(r'\s+',' ',s)
    return re.sub(r'\s+(AB|CD|EF|GH|IJ|KL|MN|OP|QR|ST|UV|WX|YZ)$','',s)

ALIASES = {}
ALIASES.update({base(a):base(b) for a,b in [('ARAI AA Sendai', 'ARAI Sendai'), ('ｱﾗｲAA仙台', 'ARAI Sendai'), ('アライAA仙台', 'ARAI Sendai'), ('ARAI AA Sendai', 'ARAI Sendai'), ('ｱﾗｲAAﾍﾞｲｻｲﾄﾞ', 'ARAI Bayside'), ('アライAAベイサイド', 'ARAI Bayside'), ('ARAI AA Bayside', 'ARAI Bayside'), ('ｱﾗｲ小山VT', 'ARAI Oyama VT'), ('アライ小山VT', 'ARAI Oyama VT'), ('JU福岡・鹿児島', 'JU Fukuoka'), ('JU Fukuoka/Kagoshima', 'JU Fukuoka'), ('JU Fukuoka / Kagoshima', 'JU Fukuoka'), ('JU宮城・秋田', 'JU Miyagi'), ('JU Miyagi/Akita', 'JU Miyagi'), ('ﾍﾞｲｵｰｸ', 'BAYAUC'), ('ベイオーク', 'BAYAUC'), ('BAY OAK', 'BAYAUC'), ('BAYOAK', 'BAYAUC'), ('オークネット', 'AUCNET'), ('ｵｰｸﾈｯﾄ', 'AUCNET'), ('AUC', 'AUCNET'), ('ﾋｰﾛｰ', 'HERO'), ('ヒーロー', 'HERO'), ('日産大阪AA', 'NISSAN Osaka'), ('NAAｵｰｻｶ', 'NAA Osaka'), ('NAA大阪', 'NAA Osaka'), ('SAA浜松', 'SUZUKI AA Hamamatsu'), ('LAA岡山', 'LAA Okayama'), ('LAA四国', 'LAA Shikoku'), ('KCAA福岡', 'KCAA Fukuoka'), ('KCAA京都', 'KCAA Kyoto'), ('KCAA山口', 'KCAA Yamaguchi'), ('KCAA南九州', 'KCAA Minami Kyushu'), ('MIRIVE愛知', 'MIRIVE Aichi'), ('MIRIVE埼玉', 'MIRIVE Saitama'), ('MIRIVE大阪', 'MIRIVE Osaka'), ('CAA中部', 'CAA Chubu'), ('CAA東京', 'CAA Tokyo'), ('CAA岐阜', 'CAA Gifu'), ('CAA東北', 'CAA Tohoku'), ('IAA大阪', 'IAA Osaka'), ('TAA北海道', 'TAA Hokkaido'), ('TAA東北', 'TAA Tohoku'), ('TAA関東', 'TAA Kanto'), ('TAA中部', 'TAA Chubu'), ('TAA横浜', 'TAA Yokohama'), ('TAA近畿', 'TAA Kinki'), ('TAA兵庫', 'TAA Hyogo'), ('TAA広島', 'TAA Hiroshima'), ('TAA九州', 'TAA Kyushu'), ('TAA南九州', 'TAA Minami Kyushu'), ('TAA四国', 'TAA Shikoku'), ('NAA名古屋', 'NAA Nagoya'), ('NAA福岡', 'NAA Fukuoka'), ('NAA東京', 'NAA Tokyo'), ('ZIP東京', 'ZIP Tokyo'), ('ZIP大阪', 'ZIP Osaka'), ('ﾎﾝﾀﾞ東京', 'Honda Tokyo'), ('ホンダ東京', 'Honda Tokyo'), ('ﾎﾝﾀﾞ名古屋', 'Honda Nagoya'), ('ホンダ名古屋', 'Honda Nagoya'), ('ﾎﾝﾀﾞ関西', 'Honda Kansai'), ('ホンダ関西', 'Honda Kansai'), ('ﾎﾝﾀﾞ仙台', 'Honda Sendai'), ('ホンダ仙台', 'Honda Sendai'), ('ﾎﾝﾀﾞ北海道', 'Honda Hokkaido'), ('ホンダ北海道', 'Honda Hokkaido'), ('ﾎﾝﾀﾞ九州', 'Honda Kyushu'), ('ホンダ九州', 'Honda Kyushu'), ('JU東京', 'JU Tokyo'), ('JU静岡', 'JU Shizuoka'), ('JU石川', 'JU Ishikawa'), ('JU福島', 'JU Fukushima'), ('JU新潟', 'JU Niigata'), ('JU富山', 'JU Toyama'), ('JU北海道', 'JU Hokkaido'), ('JU岐阜', 'JU Gifu'), ('JU愛知', 'JU Aichi'), ('JU茨城', 'JU Ibaraki'), ('JU三重', 'JU Mie'), ('JU Tochigi', 'JU Tochigi'), ('ARAI Oyama', 'ARAI Oyama')]})
def auction(s):
    s=base(s)
    s=ALIASES.get(s,s)
    s=re.sub(r'^ARAI\s+AA\s+','ARAI ',s)
    s=re.sub(r'^(MIRIVE|KCAA|CAA|IAA|ARAI|HONDA|USS|LAA|NAA|TAA|JU|ZIP)(?=[A-Z])',r'\1 ',s)
    return ALIASES.get(s,s)

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
                m=re.match(r'^\s*(\d{1,2}/\d{1,2})\s{2,}(.+?)\s{2,}\S',line)
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
        p=re.search(r'\bsuccess\s*[|\t\n ]+\s*([\d,]+(?:\.\d+)?)',block,re.I)
        if p: rows.append(record(m[1],m[2],price(p[1],10),'TAA/CAA'))
        else: warnings.append(f'{m[1]} {m[2]}: success price not found')
    return rows,warnings

def compare(jp,external,tolerance):
    merged={}; conflicts=[]; buckets={}; out=[]
    for r in external:
        k=(auction(r['Auction']),lot(r['Lot']))
        if 'SHARED' in k[0]: continue
        if k in merged:
            old=merged[k]
            if old['Price'] is not None and r['Price'] is not None and old['Price']!=r['Price']: conflicts.append((k,old['Price'],r['Price']))
            if old['Price'] is None: merged[k]=r
        else: merged[k]=r
    for r in jp: buckets.setdefault((auction(r['Auction']),lot(r['Lot'])),[]).append(r)
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
    for label,index in zip(['Auction','Lot','Winning price'],defaults):
        selected.append(st.selectbox(f'{source}: {label}',cols,index=min(index,len(cols)-1),key=f'{source}-{label}-{f.name}'))
    return [record(r[selected[0]],r[selected[1]],price(r[selected[2]],divisor),source) for _,r in df.iterrows() if str(r[selected[0]]).strip() and str(r[selected[1]]).strip()]

def render_win_recheck():
    st.subheader('BIZUPON WIN RECHECK')
    jpfile=st.file_uploader('BIZUPON WIN Excel / CSV',type=['xlsx','xls','csv'],key='wr_jp')
    files=st.file_uploader('AUCNEO WON PDF / Excel / CSV',type=['pdf','xlsx','xls','csv'],accept_multiple_files=True,key='wr_auc')
    pasted=st.text_area('TAA / CAA WIN data — paste full table',height=150,key='wr_taa')
    tolerance=Decimal(str(st.number_input('Price tolerance (万円)',min_value=0.0,value=0.0,step=0.1,key='wr_tol')))
    try:
        jp=table_rows(jpfile,'BIZUPON',(3,4,15),10000) if jpfile else []
        ext=[]; warnings=[]
        for f in files:
            if f.name.lower().endswith('.pdf'):
                r,w=pdf_rows(f.getvalue()); dates=sorted({x['Date'] for x in r}); chosen=st.multiselect(f'{f.name}: select auction dates for recheck',dates,key='wr_dates_'+f.name); ext.extend(x for x in r if x['Date'] in chosen); warnings.extend(w)
            else: ext.extend(table_rows(f,'AUCNEO',(0,1,2),1))
        r,w=taa_rows(pasted); ext.extend(r); warnings.extend(w)
        st.caption(f'BIZUPON: {len(jp)} | Auction records: {len(ext)}')
        for w in warnings: st.warning(w)
        if jp and ext:
            df,conflicts=compare(jp,ext,tolerance)
            if conflicts: st.warning(f'{len(conflicts)} duplicate price conflicts — AUCNEO/first valid price retained'); st.write(conflicts)
            if df.empty: return
            st.write(df['Status'].value_counts().to_dict())
            statuses=st.multiselect('Status',list(df.Status.unique()),default=list(df.Status.unique()),key='wr_status')
            auctions=st.multiselect('Auction',sorted(df.Auction.unique()),key='wr_auction')
            view=df[df.Status.isin(statuses)]
            if auctions: view=view[view.Auction.isin(auctions)]
            st.dataframe(view,use_container_width=True,hide_index=True)
            st.download_button('Download CSV',view.to_csv(index=False).encode('utf-8-sig'),'win_recheck.csv','text/csv')
            buf=io.BytesIO(); view.to_excel(buf,index=False,engine='openpyxl'); st.download_button('Download Excel',buf.getvalue(),'win_recheck.xlsx')
        else: st.info('Upload BIZUPON and auction records; select relevant PDF dates.')
    except Exception as e: st.error(f'Input could not be processed: {e}')
