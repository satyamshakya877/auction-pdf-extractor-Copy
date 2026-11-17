"""Parse copied TAA/CAA successful-bid tables (tab-separated or Markdown)."""
import re
import unicodedata
from decimal import Decimal

HEADERS = ['Auction', 'Lot', 'Bid Price (Man Yen)', 'Remark']
SITE_LOT = re.compile(r'\b((?:TAA|CAA)[A-Z0-9 _-]*?)\s*(?:<br\s*/?>|\n|\s+)\s*(\d{4,6})\b', re.I)
AMOUNT = re.compile(r'^\s*([\d,]+)(?:\.\d+)?\s*(?:[+＋]\s*\d+)?\s*$', re.I)
STATUS = re.compile(r'Your\s+success|Another\s+success|UNSOLD|Cancelled|Canceled|Pending|Success', re.I)

def clean(value):
    value = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', str(value))
    value = re.sub(r'<br\s*/?>', '\n', value, flags=re.I)
    value = re.sub(r'<[^>]*>', ' ', value)
    return unicodedata.normalize('NFKC', value).strip()

def site_name(raw):
    name = re.sub(r'[^A-Z0-9]', '', raw.upper())
    prefix = 'TAA' if name.startswith('TAA') else 'CAA'
    region = name[len(prefix):]
    return prefix + (' ' + region.title() if region else '')

def remark(raw):
    s = clean(raw).lower()
    if 'your success' in s: return 'WON'
    if 'another success' in s: return 'LOST'
    if 'unsold' in s: return 'UNSOLD'
    if 'cancel' in s: return 'CANCELLED'
    if 'pending' in s: return 'PENDING'
    return 'UNKNOWN'

def parse_taa(text):
    """Return (records, issues). Never silently discard a recognized lot."""
    records, issues = [], []
    if not text.strip(): return records, issues
    for line_no, raw in enumerate(text.splitlines(), 1):
        if not raw.strip(): continue
        if raw.lstrip().startswith('|'):
            cells = [clean(x) for x in raw.strip().strip('|').split('|')]
        elif '\t' in raw:
            cells = [clean(x) for x in raw.split('\t')]
        else:
            continue
        found = None
        for idx, cell in enumerate(cells):
            match = SITE_LOT.search(cell)
            if match:
                found = (idx, match)
                break
        if not found: continue
        idx, match = found
        auction, lot = site_name(match.group(1)), match.group(2)
        # Website has one site/lot column, then year, model, grade, start price,
        # method, bid price, status. The copied markdown sample includes a blank
        # leading column; using offsets relative to site/lot avoids that issue.
        # Bid price is 6 columns after site/lot (site,year,model,grade,start,method,bid).
        bid_idx = idx + 6
        status_idx = idx + 7
        if bid_idx >= len(cells):
            issues.append(f'Line {line_no}: {auction} {lot} - bid price column missing')
            continue
        bid_cell = cells[bid_idx].split('\n')[0].strip()
        price_match = AMOUNT.match(bid_cell)
        if not price_match:
            issues.append(f'Line {line_no}: {auction} {lot} - cannot read bid price: {bid_cell!r}')
            continue
        amount_thousand = Decimal(price_match.group(1).replace(',', ''))
        status_cell = cells[status_idx] if status_idx < len(cells) else ''
        records.append({
            'Auction': auction, 'Lot': lot,
            'Bid Price (Man Yen)': float(amount_thousand / Decimal(10)),
            'Remark': remark(status_cell)
        })
    if not records and not issues:
        issues.append('No auction rows recognized. Copy the website table into the paste box (Ctrl+C, Ctrl+V).')
    return records, issues
