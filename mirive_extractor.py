"""MIRIVE member-site PDF snapshots: own bids only, latest snapshot wins.

Returns (records, skipped, issues). PDF must contain selectable text.
"""
import re
import unicodedata
from datetime import datetime
from decimal import Decimal
import fitz

VENUES = {'埼玉': 'MIRIVE Saitama', '大阪': 'MIRIVE Osaka', '愛知': 'MIRIVE Aichi', '兵庫': 'MIRIVE Hyogo'}
# Header on each printed table row: venue, auction date, lane + lot (digits may be spaced).
ROW = re.compile(r'(?m)^(埼玉|大阪|愛知|兵庫)\s*\n(\d{1,2}/\d{1,2})\s*\n([A-Z](?:\s*\d){1,6})\s*\n')
BID_YEN = re.compile(r'(?<!\d)(\d[\d, ]{0,14})\s*\n\s*,?\s*000円')
EXPLICIT_BID = re.compile(r'入札\s*[:：]\s*([\d,.]+)\s*万円')
STATUS = [('自社落札', 'WON'), ('他社落札', 'LOST'), ('流れ', 'UNSOLD'), ('流札', 'UNSOLD'), ('未セリ', 'PENDING')]
PDF_TIME = re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4})\s*,?\s*(\d{1,2}:\d{2})\s*(AM|PM)?', re.I)


def _norm(s):
    return unicodedata.normalize('NFKC', s)


def _timestamp(doc, filename):
    for p in doc:
        s = p.get_text('text', sort=False)
        m = PDF_TIME.search(s[:500]) or PDF_TIME.search(s[-600:])
        if m:
            try:
                stamp = f'{m.group(1)} {m.group(2)} {m.group(3) or ""}'.strip()
                fmt = '%m/%d/%y %I:%M %p' if len(m.group(1).split('/')[-1]) == 2 and m.group(3) else '%m/%d/%Y %I:%M %p' if m.group(3) else '%m/%d/%Y %H:%M'
                return datetime.strptime(stamp, fmt)
            except ValueError:
                pass
    return None


def _parse_chunk(chunk, auction, lot, auction_date, filename, page):
    """A blank own bid is a cancellation even when a final hammer price exists."""
    text = _norm(chunk)
    result = next((value for jp, value in STATUS if jp in text), 'UNKNOWN')
    # Negotiation application explicitly states user's offer. Never use 503,000円
    # (negotiation application amount) when 入札:10.4万円 is present.
    explicit = EXPLICIT_BID.search(text)
    if explicit:
        own_bid = Decimal(explicit.group(1).replace(',', ''))
        source = '入札:万円'
    else:
        # Locate the OWN bid input area. Ignore start price, final sale price,
        # and auction hammer values (all in different columns).
        bid_area = re.search(r'(?:不在\s*入札|不在入札|商談\s*申込|商談申込)', text)
        candidate = text[bid_area.end():] if bid_area else ''
        m = BID_YEN.search(candidate)
        if m:
            thousands = int(re.sub(r'\D', '', m.group(1)))
            own_bid = Decimal(thousands) / Decimal('10')
            source = 'own bid 円'
        else:
            own_bid = None
            source = 'blank'
    base = {'Auction': auction, 'Lot': lot, 'Remark': result,
            'Source File': filename, 'Page': page, 'Price Source': source, '_auction_date': auction_date}
    if own_bid is None:
        return None, {**base, 'Reason': 'Own bid blank in this PDF (skip)'}, None
    if own_bid < 0:
        return None, None, f'{filename} page {page} lot {lot}: negative bid'
    return {**base, 'Bid Price (Man Yen)': float(own_bid)}, None, None


def parse_mirive_pdf(content, filename='MIRIVE.pdf'):
    """Return (records, skipped, issues) for one PDF."""
    records, skipped, issues = [], [], []
    with fitz.open(stream=content, filetype='pdf') as doc:
        timestamp = _timestamp(doc, filename)
        for page_num, page in enumerate(doc, 1):
            text = page.get_text('text', sort=False)
            matches = list(ROW.finditer(text))
            if not matches:
                issues.append(f'{filename}: page {page_num} has no MIRIVE table rows (or is image-only).')
                continue
            for idx, m in enumerate(matches):
                lot = ''.join(re.findall(r'\d', m.group(3)))
                auction = VENUES.get(m.group(1), 'MIRIVE ' + m.group(1))
                chunk = text[m.end(): matches[idx+1].start() if idx+1 < len(matches) else len(text)]
                record, skipped_row, issue = _parse_chunk(chunk, auction, lot, m.group(2), filename, page_num)
                if record:
                    record['_snapshot'] = timestamp
                    records.append(record)
                if skipped_row:
                    skipped_row['_snapshot'] = timestamp
                    skipped.append(skipped_row)
                if issue:
                    issues.append(issue)
    return records, skipped, issues


def combine_mirive_snapshots(uploaded):
    """uploaded: iterable of (filename, bytes). Latest PDF state wins per auction+lot.

    If latest snapshot has blank own bid, it overrides an earlier valid bid.
    """
    entries, issues = [], []
    for upload_index, (name, content) in enumerate(uploaded):
        rows, skipped, warnings = parse_mirive_pdf(content, name)
        issues.extend(warnings)
        for row in rows:
            entries.append((row, False, upload_index))
        for row in skipped:
            entries.append((row, True, upload_index))
    def order(entry):
        row, _, index = entry
        # Undated files are ordered by upload sequence.
        return (row.get('_snapshot') or datetime.min, index)
    latest = {}
    for entry in sorted(entries, key=order):
        row = entry[0]
        latest[(row['Auction'], row['_auction_date'], row['Lot'])] = entry
    records, skipped = [], []
    for row, is_skipped, _ in latest.values():
        row = {k:v for k,v in row.items() if not k.startswith('_')}
        (skipped if is_skipped else records).append(row)
    records.sort(key=lambda r: (r['Auction'], int(r['Lot'])))
    skipped.sort(key=lambda r: (r['Auction'], int(r['Lot'])))
    return records, skipped, issues
