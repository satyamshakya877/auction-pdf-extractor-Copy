"""Extract auction, lot and winning price from AUCNEO '落札車一覧' PDFs.

Input PDF prices are in 万円 (10,000 JPY). This is a *winning-price*
report, not the Raku POS bid-application report.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

import fitz


DATE = re.compile(r"^\d{1,2}/\d{1,2}$")
ISSUE_LOT = re.compile(r"^\d+回\s+(\d{1,6})$")
WIN_PRICE = re.compile(r"^([\d,]+(?:\.\d+)?)万円$")
LANE_SUFFIX = re.compile(r"\s+[A-Z]{2}$")

# More specific names must precede their shared substrings.
PLACE_NAMES = [
    ("南九州", "South Kyushu"), ("北九州", "North Kyushu"),
    ("福岡・鹿児島", "Fukuoka"), ("北海道", "Hokkaido"),
    ("ベイサイド", "Bayside"), ("名古屋", "Nagoya"),
    ("鹿児島", "Kagoshima"), ("岡山", "Okayama"),
    ("福岡", "Fukuoka"), ("愛知", "Aichi"),
    ("横浜", "Yokohama"), ("中部", "Chubu"),
    ("埼玉", "Saitama"), ("京都", "Kyoto"),
    ("大阪", "Osaka"), ("東京", "Tokyo"),
    ("岐阜", "Gifu"), ("九州", "Kyushu"),
    ("四国", "Shikoku"), ("近畿", "Kinki"),
    ("関西", "Kansai"), ("広島", "Hiroshima"),
    ("兵庫", "Hyogo"), ("関東", "Kanto"),
    ("東北", "Tohoku"), ("山口", "Yamaguchi"),
    ("静岡", "Shizuoka"), ("新潟", "Niigata"),
    ("宮城・秋田", "Miyagi Akita"),
    ("宮城", "Miyagi"), ("秋田", "Akita"),
    ("石川", "Ishikawa"), ("仙台", "Sendai"),
    ("小山", "Oyama"), ("札幌", "Sapporo"),
    ("富山", "Toyama"), ("福島", "Fukushima"),
    ("茨城", "Ibaraki"), ("三重", "Mie"),
]


def normalize_auction(raw):
    """Merge only lane suffixes; preserve distinct auction houses/venues."""
    value = unicodedata.normalize("NFKC", raw).strip()
    value = LANE_SUFFIX.sub("", value)  # e.g. CAA中部 EF -> CAA中部
    value = value.replace("アライAA", "ARAI ").replace("アライ", "ARAI ")
    value = value.replace("ベイオーク", "Bay Auction")
    value = value.replace("ホンダ", "Honda ")
    value = value.replace("オークネット", "AUCNET")
    value = value.replace("日産", "Nissan ")
    value = value.replace("オーサカ", "Osaka")
    value = value.replace("ヒーロー", "Hero")
    value = value.replace("大阪AA", "大阪 AA")
    value = value.replace("小山VT", "小山 VT")
    for japanese, english in PLACE_NAMES:
        value = value.replace(japanese, " " + english)
    value = re.sub(r"^(NAA|SAA|KCAA|CAA|TAA|MIRIVE)(?=[A-Z][a-z])", r"\1 ", value)
    return " ".join(value.split())


def parse_won_pdf(pdf_bytes, filename="WON.pdf"):
    """Return (rows, warnings), without dropping duplicate lots across dates.

    Rows contain Auction, Lot, Win Price (Man Yen), Auction Date and Page.
    The display/export uses the first three fields; date/page aid review.
    """
    rows, warnings = [], []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        for page_number, page in enumerate(document, 1):
            # JasperReports PDF has a useful natural text order with sort=False.
            lines = [unicodedata.normalize("NFKC", x).strip()
                     for x in page.get_text("text", sort=False).splitlines()]
            lines = [line for line in lines if line]

            starts = []
            for i in range(len(lines) - 2):
                if DATE.fullmatch(lines[i]) and ISSUE_LOT.fullmatch(lines[i + 2]):
                    starts.append(i)

            if not starts:
                warnings.append(f"{filename}: page {page_number} - no win records recognized")
                continue

            for index, start in enumerate(starts):
                end = starts[index + 1] if index + 1 < len(starts) else len(lines)
                record_lines = lines[start:end]
                lot_match = ISSUE_LOT.fullmatch(lines[start + 2])
                lot = lot_match.group(1)
                candidate_prices = [m.group(1) for item in record_lines[3:]
                                    if (m := WIN_PRICE.fullmatch(item))]
                if len(candidate_prices) != 1:
                    warnings.append(
                        f"{filename}: page {page_number}, lot {lot} - "
                        f"expected one win price, found {len(candidate_prices)}"
                    )
                    continue
                try:
                    price = Decimal(candidate_prices[0].replace(",", ""))
                except InvalidOperation:
                    warnings.append(f"{filename}: page {page_number}, lot {lot} - invalid price")
                    continue
                if price < 0:
                    warnings.append(f"{filename}: page {page_number}, lot {lot} - negative price")
                    continue
                rows.append({
                    "Auction": normalize_auction(lines[start + 1]),
                    "Lot": lot,  # text: keep leading zeroes
                    "Win Price (Man Yen)": float(price),
                    "Auction Date": lines[start],
                    "Page": page_number,
                })
    return rows, warnings
