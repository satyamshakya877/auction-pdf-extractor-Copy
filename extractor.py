"""Raku POS auction PDF extractor. Text-based PDFs (PyMuPDF)."""
import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO

import fitz
import pandas as pd

DATE = re.compile(r'^\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}$')
LOT = re.compile(r'^(\d{1,6})\s*\[([A-Z])\]$', re.I)
PRICE = re.compile(r'らく\s*POS\s*申込価格\s*[:：]\s*([\d,.]+)\s*万円', re.I)
CANCEL = re.compile(r'らく\s*POS\s*(?:取消|キャンセル)|取消車両|出品取消|入札取消', re.I)
WON = re.compile(r'自社落札')
LOST = re.compile(r'他社落札')
UNSOLD = re.compile(r'流れ|流札')
PENDING = re.compile(r'未セリ')
AUCTION_KEYS = re.compile(r'KCAA|TAA|CAA|USS|MIRIVE|JU|HAA|ARAI|AUCNET|オークネット|NAA|LAA|JAA|HONDA|ホンダ|ホンタ゛|ホンタ|ホンダ|KAA', re.I)
NAMES = {'福岡': 'Fukuoka', '大阪': 'Osaka', '東京': 'Tokyo', '北海道': 'Hokkaido', '名古屋': 'Nagoya', '中部': 'Chubu', '九州': 'Kyushu', '神戸': 'Kobe', '札幌': 'Sapporo', '広島': 'Hiroshima', '四国': 'Shikoku', '関東': 'Kanto', '東北': 'Tohoku'}


def normalize(value):
    return unicodedata.normalize('NFKC', value).strip()


def auction_english(raw):
    name = normalize(raw)
    # AUCNET appears as オークネット in Japanese Raku POS PDFs.
    if name == 'オークネット':
        return 'AUCNET'
    # NFKC converts half-width ﾎﾝﾀﾞ to ホンダ.
    name = re.sub(r'ホンダ', 'Honda', name, flags=re.I)
    for jp, en in NAMES.items():
        name = name.replace(jp, ' ' + en)
    return re.sub(r'\s+', ' ', name).strip()


def parse_pdf(content, filename='file.pdf'):
    records, rejected, issues = [], [], []
    with fitz.open(stream=content, filetype='pdf') as doc:
        for page_num, page in enumerate(doc, 1):
            # sort=False is essential: it preserves the logical order of Raku POS rows.
            lines = [normalize(s) for s in page.get_text('text', sort=False).splitlines()]
            lines = [s for s in lines if s]
            # A cancellation row contains a second date/time on its own line.
            # Only treat a date as a vehicle start when an auction name and lot
            # appear before the next date; otherwise it belongs to cancellation.
            candidate_starts = [i for i, s in enumerate(lines) if DATE.fullmatch(s)]
            starts = []
            for idx, pos in enumerate(candidate_starts):
                next_pos = candidate_starts[idx + 1] if idx + 1 < len(candidate_starts) else len(lines)
                chunk = lines[pos:next_pos]
                if any(LOT.fullmatch(s) for s in chunk) and any(AUCTION_KEYS.search(s) for s in chunk[1:7]):
                    starts.append(pos)
            if not starts:
                issues.append(f'{filename}: page {page_num} has no recognized vehicle records (scanned or different layout).')
                continue
            for j, start in enumerate(starts):
                end = starts[j + 1] if j + 1 < len(starts) else len(lines)
                section = lines[start:end]
                lot_match = next((m for s in section if (m := LOT.fullmatch(s))), None)
                if not lot_match:
                    issues.append(f'{filename}: page {page_num}, record at {section[0]}: lot not recognized.')
                    continue
                lot = lot_match.group(1)
                if any(CANCEL.search(s) for s in section):
                    rejected.append({'File': filename, 'Page': page_num, 'Lot': lot, 'Reason': 'Raku POS cancelled'})
                    continue
                price_match = next((m for s in section if (m := PRICE.search(s))), None)
                auction_raw = next((s for s in section[1:7] if AUCTION_KEYS.search(s)), None)
                if not price_match or not auction_raw:
                    missing = 'auction and price' if not price_match and not auction_raw else 'price' if not price_match else 'auction'
                    issues.append(f'{filename}: page {page_num}, lot {lot}: missing {missing}.')
                    continue
                try:
                    price = Decimal(price_match.group(1).replace(',', ''))
                except InvalidOperation:
                    issues.append(f'{filename}: page {page_num}, lot {lot}: invalid price.')
                    continue
                if price < 0:
                    issues.append(f'{filename}: page {page_num}, lot {lot}: negative price.')
                    continue
                remark = ('WON' if any(WON.search(s) for s in section)
                          else 'LOST' if any(LOST.search(s) for s in section)
                          else 'UNSOLD' if any(UNSOLD.search(s) for s in section)
                          else 'PENDING' if any(PENDING.search(s) for s in section)
                          else 'UNKNOWN')
                records.append({
                    'Remark': remark, 'Auction': auction_english(auction_raw),
                    'Lot': lot, 'Bid Price (Man Yen)': float(price),
                    'Bid Price JPY': int((price * 10000).quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
                    'Source File': filename, 'Page': page_num,
                })
    return records, rejected, issues


def csv_bytes(df):
    return df.to_csv(index=False).encode('utf-8-sig')


def excel_bytes(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Active Bids')
        ws = writer.sheets['Active Bids']
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        for col, width in {'A': 24, 'B': 14, 'C': 25, 'D': 17}.items():
            ws.column_dimensions[col].width = width
        for cell in ws['B'][1:]:
            cell.number_format = '@'  # preserve leading zeroes if any
        for cell in ws['C'][1:]:
            cell.number_format = '0.0'
    return out.getvalue()
