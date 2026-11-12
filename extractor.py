import re
import unicodedata
from io import BytesIO
import fitz
import pandas as pd

DATE = re.compile(r'^\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}$')
LOT = re.compile(r'^(\d{4,6})\s*\[[A-Z]\]$')
PRICE = re.compile(r'らく\s*POS\s*申込価格\s*[:：]\s*([\d,.]+)\s*万円', re.I)
CANCEL = re.compile(r'らく\s*POS\s*取消|取消車両', re.I)
WON = re.compile(r'自社落札')
LOST = re.compile(r'他社落札')
UNSOLD = re.compile(r'流れ')
PENDING = re.compile(r'未セリ')
NAMES = {'福岡':'Fukuoka','大阪':'Osaka','東京':'Tokyo','北海道':'Hokkaido','名古屋':'Nagoya','中部':'Chubu','九州':'Kyushu','神戸':'Kobe','札幌':'Sapporo','広島':'Hiroshima','四国':'Shikoku','関東':'Kanto','東北':'Tohoku'}

def auction_english(raw):
    name = raw.strip()
    for jp,en in NAMES.items():
        name=name.replace(jp,' '+en)
    return re.sub(r'\s+',' ',name).strip()

def parse_pdf(content, filename='file.pdf'):
    doc=fitz.open(stream=content,filetype='pdf')
    records=[]; rejected=[]; issues=[]
    for page_num,page in enumerate(doc,1):
        lines=[unicodedata.normalize('NFKC',x.strip()) for x in page.get_text(sort=False).splitlines() if x.strip()]
        starts=[i for i,x in enumerate(lines) if DATE.fullmatch(x)]
        if not starts:
            issues.append(f'{filename}: page {page_num} has no recognized vehicle records (possibly scanned or different format).')
        for j,start in enumerate(starts):
            section=lines[start:starts[j+1] if j+1<len(starts) else len(lines)]
            lot=next((m.group(1) for s in section if (m:=LOT.fullmatch(s))),None)
            price=next((float(m.group(1).replace(',','')) for s in section if (m:=PRICE.search(s))),None)
            auction=next((s for s in section[1:5] if re.search(r'KCAA|TAA|CAA|USS|MIRIVE|JU|HAA|ARAI|AUCNET|NAA|LAA|JAA',s,re.I)),None)
            if not lot: continue
            if any(CANCEL.search(s) for s in section):
                rejected.append({'File':filename,'Page':page_num,'Lot':lot,'Reason':'Raku POS cancelled'})
                continue
            if price is None or not auction:
                issues.append(f'{filename}: page {page_num}, lot {lot}: missing auction or Raku POS price.')
                continue
            remark = ('WON' if any(WON.search(s) for s in section) else 'LOST' if any(LOST.search(s) for s in section) else 'UNSOLD' if any(UNSOLD.search(s) for s in section) else 'PENDING' if any(PENDING.search(s) for s in section) else 'UNKNOWN')
            records.append({'Remark':remark,'Auction':auction_english(auction),'Lot':lot,'Bid Price (Man Yen)':price,'Bid Price JPY':round(price*10000),'Source File':filename,'Page':page_num})
    doc.close()
    return records,rejected,issues

def csv_bytes(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

def excel_bytes(df):
    out=BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl') as writer:
        df.to_excel(writer,index=False,sheet_name='Active Bids')
        ws=writer.sheets['Active Bids'];ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for col,width in {'A':24,'B':14,'C':25,'D':17}.items():ws.column_dimensions[col].width=width
        for cell in ws['B'][1:]:cell.number_format='0'
        for cell in ws['C'][1:]:cell.number_format='0.0'
    return out.getvalue()
