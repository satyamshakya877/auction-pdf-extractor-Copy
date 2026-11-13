    records, rejected, issues = [], [], []
    try:
        for page_num, page in enumerate(doc, 1):
            lines = [unicodedata.normalize('NFKC', x.strip()) for x in page.get_text(sort=False).splitlines() if x.strip()]
            # A record starts with date/time, followed shortly by an auction and a lot.
            # This avoids treating cancellation timestamps as new vehicle records.
            starts = []
            for i, line in enumerate(lines):
                if not DATE.fullmatch(line):
                    continue
                lookahead = lines[i+1:i+5]
                if any(LOT.fullmatch(s) for s in lookahead) and any(KNOWN.search(s) for s in lookahead):
                    starts.append(i)
            if not starts:
                issues.append(f'{filename}: page {page_num} has no recognized vehicle records (possibly scanned or different format).')
            for j, start in enumerate(starts):
                section = lines[start:starts[j+1] if j+1 < len(starts) else len(lines)]
                lot = next((m.group(1) for s in section[:8] if (m := LOT.fullmatch(s))), None)
                auction = next((s for s in section[1:5] if KNOWN.search(s)), None)
                price = next((float(m.group(1).replace(',', '')) for s in section if (m := PRICE.search(s))), None)
                if not lot:
                    continue
                if any(CANCEL.search(s) for s in section):
                    rejected.append({'File':filename, 'Page':page_num, 'Lot':lot, 'Reason':'Raku POS cancelled'})
                    continue
                if price is None or not auction:
                    issues.append(f'{filename}: page {page_num}, lot {lot}: missing auction or Raku POS price.')
                    continue
                remark = ('WON' if any(WON.search(s) for s in section)
                          else 'LOST' if any(LOST.search(s) for s in section)
                          else 'UNSOLD' if any(UNSOLD.search(s) for s in section)
                          else 'PENDING' if any(PENDING.search(s) for s in section)
                          else 'UNKNOWN')
                records.append({'Remark':remark, 'Auction':auction_english(auction), 'Lot':lot,
                                'Bid Price (Man Yen)':price, 'Bid Price JPY':round(price*10000),
                                'Source File':filename, 'Page':page_num})
    finally:
        doc.close()
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
        for col, width in {'A':24, 'B':14, 'C':25, 'D':17}.items():
            ws.column_dimensions[col].width = width
        for cell in ws['B'][1:]:
            cell.number_format = '@'
        for cell in ws['C'][1:]:
            cell.number_format = '0.0'
    return out.getvalue()
