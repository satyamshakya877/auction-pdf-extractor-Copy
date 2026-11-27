"""Extract all lots from TAA/CAA Successful Bid website clipboard text.

Supports native Ctrl+C tab/newline text and Markdown tables. No Streamlit dependency.
Public API remains: HEADERS, clean, site_name, remark, parse_taa(text).
"""
import re
import unicodedata
from decimal import Decimal

HEADERS = ['Auction', 'Lot', 'Bid Price (Man Yen)', 'Remark']

# The copied site/lot cell contains a line break between auction and lot.
# Restrict the auction token so that we do not swallow other table columns.
SITE_LOT = re.compile(
    r'(?<![A-Z0-9])((?:TAA|CAA)[A-Z0-9_-]{0,35})[ \t]*\n[ \t]*(\d{4,6})(?!\d)',
    re.IGNORECASE,
)
BID = re.compile(r'\bDirect\s*(?:\|\s*)?([\d,]+(?:\.\d+)?)\b', re.IGNORECASE)
STATUS = re.compile(
    r'Your\s+success|Another\s+success|UNSOLD|Cancelled|Canceled|Pending|Success',
    re.IGNORECASE,
)


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
    if 'your success' in s:
        return 'WON'
    if 'another success' in s:
        return 'LOST'
    if 'unsold' in s:
        return 'UNSOLD'
    if 'cancel' in s:
        return 'CANCELLED'
    if 'pending' in s:
        return 'PENDING'
    # Preserve unfamiliar statuses instead of silently discarding a lot.
    return clean(raw).split('\n')[0].strip() or 'UNKNOWN'


def parse_taa(text):
    """Return (records, issues) for all recognized lots in pasted order.

    Bid Price is the number after 'Direct' (thousands of yen), not the
    auction result amount after 'Your success' / 'Another success'.
    """
    records, issues = [], []
    if not text or not text.strip():
        return records, issues

    normalized = clean(text).replace('\r\n', '\n').replace('\r', '\n')
    # Markdown table cells use pipes, but copied HTML cells contain tabs.
    # Neither is needed to locate the site+lot / Direct+bid markers.
    matches = list(SITE_LOT.finditer(normalized))
    if not matches:
        return [], ['No auction rows recognized. Copy the website table (Ctrl+C, Ctrl+V).']

    for i, match in enumerate(matches):
        auction = site_name(match.group(1))
        lot = match.group(2)
        segment = normalized[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(normalized)]
        bid_match = BID.search(segment)
        if not bid_match:
            issues.append(f'{auction} {lot}: bid price after Direct not found')
            continue
        amount = Decimal(bid_match.group(1).replace(',', ''))
        # Only inspect status after the bid; the earlier fields can contain arbitrary text.
        status_match = STATUS.search(segment, bid_match.end())
        if status_match:
            status = remark(status_match.group())
        else:
            status = 'UNKNOWN'
            issues.append(f'{auction} {lot}: status not recognized; lot included as UNKNOWN')
        records.append({
            'Auction': auction,
            'Lot': lot,
            'Bid Price (Man Yen)': float(amount / Decimal('10')),
            'Remark': status,
        })
    return records, issues

# Keep the existing TAA/CAA parser intact; route ARAI clipboard rows separately.
_parse_original_taa = parse_taa
ARAI_ROW = re.compile(r'(?im)\b(4W[ \t]+BAYSIDE)\s*\n[ \t]*No\.[ \t]*(\d{1,6})\b')
ARAI_BID = re.compile(r'(?:\\|¥)\s*([\d,]+)\s*\n[ \t]*バイヤー席')

def parse_taa(text):
    normalized = clean(text or '').replace('\r\n','\n').replace('\r','\n')
    arai = list(ARAI_ROW.finditer(normalized))
    if not arai:
        return _parse_original_taa(text)
    markers = sorted([(m.start(), 'arai', m) for m in arai] + [(m.start(), 'taa', m) for m in SITE_LOT.finditer(normalized)])
    rows, issues = [], []
    for i, (start, kind, m) in enumerate(markers):
        end = markers[i+1][0] if i+1 < len(markers) else len(normalized)
        segment = normalized[start:end]
        if kind == 'taa':
            r, e = _parse_original_taa(segment); rows.extend(r); issues.extend(e); continue
        lot = m.group(2)
        bid = ARAI_BID.search(segment)
        if not bid:
            issues.append(f'ARAI Bayside {lot}: buyer bid price not found'); continue
        if re.search(r'取消|\bCancel(?:led|ed)?\b', segment, re.I):
            continue
        rows.append({'Auction':'ARAI Bayside','Lot':lot,'Bid Price (Man Yen)':float(Decimal(bid.group(1).replace(',',''))/Decimal(10000)), 'Remark':''})
    return rows, issues
