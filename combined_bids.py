from decimal import Decimal, InvalidOperation
import unicodedata


def merge_bids(groups, normalize_auction, normalize_lot):
    merged = {}
    for source, records in groups:
        for row in records:
            remark = unicodedata.normalize('NFKC', str(row.get('Remark', ''))).strip().upper()
            if 'CANCEL' in remark or '取消' in remark:
                continue
            a = normalize_auction(row['Auction'])
            l = normalize_lot(row['Lot'])
            try:
                p = Decimal(str(row['Bid Price (Man Yen)']).replace(',', ''))
            except (InvalidOperation, KeyError):
                continue
            if not a or not l or not p.is_finite() or p < 0:
                continue
            key = (a, l)
            won = remark in ('WON', 'YOUR SUCCESS', 'SUCCESS FOR REAL', '自社落札')
            if key not in merged:
                merged[key] = [p, won, str(row['Lot'])]
            else:
                old = merged[key]
                old[1] = old[1] or won
                if p > old[0]:
                    old[0] = p
    return [{'Auction': a, 'Lot': v[2], 'Bid Price (Man Yen)': float(v[0]), 'Remark': 'WON' if v[1] else ''} for (a,l),v in sorted(merged.items(), key=lambda x: (x[0][0], int(x[0][1]) if x[0][1].isdigit() else float('inf'), x[0][1]))]


def render_combined(raku, taa, mirive):
    import streamlit as st
    import pandas as pd
    from win_recheck import auction, lot
    from extractor import excel_bytes, csv_bytes
    st.subheader('COMBINED BID EXTRACTOR')
    st.caption('Upload or paste in the existing Raku POS, TAA/CAA and MIRIVE tabs. Use records from the same auction date only.')
    st.write(f'Raku POS: {len(raku)} | TAA/CAA: {len(taa)} | MIRIVE: {len(mirive)}')
    result = merge_bids([('Raku POS',raku),('TAA/CAA',taa),('MIRIVE',mirive)], auction, lot)
    if not result:
        st.info('Add bid data in any of the three extractor tabs first.')
        return
    df = pd.DataFrame(result)
    selected = st.multiselect('Auction', sorted(df.Auction.unique()), key='combined_auction')
    if selected:
        df = df[df.Auction.isin(selected)]
    if st.checkbox('WON only', key='combined_won'):
        df = df[df.Remark == 'WON']
    st.caption(f'{len(df)} lots | Prices in Man Yen | Highest own bid, not hammer price')
    st.dataframe(df, hide_index=True, use_container_width=True)
    a,b = st.columns(2)
    a.download_button('Download Excel', excel_bytes(df), 'combined_bids.xlsx', key='combined_xlsx')
    b.download_button('Download CSV', csv_bytes(df), 'combined_bids.csv', key='combined_csv')
