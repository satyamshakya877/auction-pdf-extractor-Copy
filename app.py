import streamlit as st
import pandas as pd
import re
from extractor import parse_pdf, excel_bytes, csv_bytes
from taa_extractor import parse_taa
from mirive_extractor import combine_mirive_snapshots
from aucneo_won_extractor import parse_won_pdf

st.set_page_config(page_title='BIZUPON | Auction Extractor', page_icon='🚘', layout='wide')
st.markdown('''<style>
.stApp {background:#fff;color:#171717}
.block-container {max-width:1180px;padding-top:2rem}
h1,h2,h3 {color:#171717!important}
[data-testid="stMetric"] {background:#f2f9f0;border:1px solid #d6e8d1;border-radius:12px;padding:16px}
[data-testid="stMetricValue"] * {color:#18852a!important}
div.stDownloadButton button {background:#23932c!important;color:white!important;border:0;border-radius:9px}
div.stDownloadButton button * {color:white!important}
</style>''', unsafe_allow_html=True)
st.image('https://www.bizupon.com/images/logo.png', width=300)
st.title('🚘 Auction Data Extractor')
st.caption('BIZUPON | Auction PDF bids, won vehicles and TAA/CAA copied tables')

pdf_tab, taa_tab, mirive_tab, won_tab, recheck_tab, combined_tab = st.tabs([
    '📄 Raku POS PDF Extractor',
    '📋 TAA / CAA Paste Extractor',
    '🚗 MIRIVE PDF Extractor',
    '🏆 AUCNEO WON Extractor',
    '✅ BIZUPON WIN RECHECK',
    '📊 COMBINED BID EXTRACTOR',
])

with pdf_tab:
    files = st.file_uploader('Upload auction PDFs', type=['pdf'], accept_multiple_files=True)
    st.info('PDF bid price: らくPOS申込価格 (万円). Cancelled lots are excluded.')
    if files:
        active, cancelled, issues = [], [], []
        with st.spinner('Extracting PDF records...'):
            for f in files:
                try:
                    a, c, e = parse_pdf(f.getvalue(), f.name)
                    active.extend(a); cancelled.extend(c); issues.extend(e)
                except Exception as exc:
                    issues.append(f'{f.name}: {exc}')
        c1,c2,c3,c4=st.columns(4)
        c1.metric('Active lots',len(active));c2.metric('Cancelled skipped',len(cancelled))
        c3.metric('WON lots',sum(r.get('Remark')=='WON' for r in active));c4.metric('Files processed',len(files))
        if issues:
            with st.expander(f'Review warnings ({len(issues)})'):
                for issue in issues: st.write('• '+str(issue))
        if active:
            df=pd.DataFrame(active)[['Auction','Lot','Bid Price (Man Yen)','Remark']]
            df['Lot']=df['Lot'].astype(str)
            st.dataframe(df,hide_index=True,use_container_width=True)
            a,b=st.columns(2)
            a.download_button('⬇ Download Excel',excel_bytes(df),'auction_active_bids.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
            b.download_button('⬇ Download CSV',csv_bytes(df),'auction_active_bids.csv',mime='text/csv',use_container_width=True)
        else: st.warning('No active lots recognized.')
        with st.expander(f'Cancelled lots ({len(cancelled)})'):
            if cancelled: st.dataframe(pd.DataFrame(cancelled),hide_index=True,use_container_width=True)

with taa_tab:
    st.subheader('Paste complete TAA / CAA table')
    st.caption('On the TAA/CAA website, select the entire table, Ctrl+C, then paste here with Ctrl+V. No Excel Special Paste needed.')
    pasted = st.text_area('Copied auction table',height=220,placeholder='Paste TAAKINKI / TAASHIKOKU / CAATOKYO ... rows here')
    if pasted.strip():
        rows, issues = parse_taa(pasted)
        combined_taa_rows = rows
        if issues:
            with st.expander(f'Rows needing review ({len(issues)})',expanded=True):
                for issue in issues[:100]: st.write('• '+issue)
        if rows:
            all_df=pd.DataFrame(rows,columns=['Auction','Lot','Bid Price (Man Yen)','Remark'])
            auctions=sorted(all_df['Auction'].unique().tolist())
            selected=st.selectbox('Select auction for download',['All Auctions']+auctions)
            df=all_df if selected=='All Auctions' else all_df[all_df['Auction']==selected]
            c1,c2,c3=st.columns(3)
            c1.metric('All extracted lots',len(all_df));c2.metric('Auctions',len(auctions));c3.metric('Selected lots',len(df))
            st.dataframe(df,hide_index=True,use_container_width=True,column_config={'Lot':st.column_config.TextColumn('Lot')})
            safe_name='all_auctions' if selected=='All Auctions' else selected.lower().replace(' ','_')
            a,b=st.columns(2)
            a.download_button('⬇ Download selected Excel',excel_bytes(df),f'{safe_name}_bids.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
            b.download_button('⬇ Download selected CSV',csv_bytes(df),f'{safe_name}_bids.csv',mime='text/csv',use_container_width=True)
        else: st.warning('No auction lots found. Check copied table format.')
    else: st.info('Paste the website table to begin. All statuses, including UNSOLD, are included.')


with mirive_tab:
    st.subheader('MIRIVE PDF Extractor')
    st.caption('Upload one or more MIRIVE member-site PDFs. For matching lots, the latest PDF snapshot takes priority. Blank own bids are skipped even if an earlier PDF had a bid.')
    mirive_files = st.file_uploader('Upload MIRIVE PDFs', type=['pdf'], accept_multiple_files=True, key='mirive_files')
    if mirive_files:
        with st.spinner('Comparing MIRIVE PDF snapshots...'):
            mirive_rows, mirive_skipped, mirive_issues = combine_mirive_snapshots(
                [(f.name, f.getvalue()) for f in mirive_files]
            )
        a,b,c,d=st.columns(4)
        a.metric('Active lots',len(mirive_rows))
        b.metric('Blank bid skipped',len(mirive_skipped))
        c.metric('WON',sum(r['Remark']=='WON' for r in mirive_rows))
        d.metric('PDFs uploaded',len(mirive_files))
        if mirive_issues:
            with st.expander(f'Extraction warnings ({len(mirive_issues)})'):
                for issue in mirive_issues[:150]: st.write('• '+issue)
        if mirive_rows:
            mirive_df = pd.DataFrame(mirive_rows)[['Auction','Lot','Bid Price (Man Yen)','Remark']]
            st.dataframe(mirive_df,hide_index=True,use_container_width=True,column_config={'Lot':st.column_config.TextColumn('Lot')})
            left,right=st.columns(2)
            left.download_button('⬇ Download MIRIVE Excel',excel_bytes(mirive_df),'mirive_active_bids.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
            right.download_button('⬇ Download MIRIVE CSV',csv_bytes(mirive_df),'mirive_active_bids.csv',mime='text/csv',use_container_width=True)
        else:
            st.warning('No valid MIRIVE own bids found in the uploaded PDF(s).')
        with st.expander(f'Blank-price lots skipped ({len(mirive_skipped)})'):
            if mirive_skipped:
                st.dataframe(pd.DataFrame(mirive_skipped)[['Auction','Lot','Reason','Source File']],hide_index=True,use_container_width=True)
    else:
        st.info('Upload MIRIVE PDFs to extract your own bids. Final selling prices are never substituted for missing bids.')


with won_tab:
    st.subheader('AUCNEO Won Vehicles Extractor')
    st.caption(
        'Upload the AUCNEO 落札車一覧 (Won Vehicles List) PDF. '
        'WIN PRICE comes from 価格(万) and is in Man Yen (10,000 JPY).'
    )
    won_files = st.file_uploader(
        'Upload AUCNEO WON PDF(s)', type=['pdf'],
        accept_multiple_files=True, key='aucneo_won_files',
    )
    if won_files:
        won_rows, won_issues = [], []
        with st.spinner('Extracting winning prices and auction names...'):
            for file in won_files:
                try:
                    rows, issues = parse_won_pdf(file.getvalue(), file.name)
                    won_rows.extend(rows)
                    won_issues.extend(issues)
                except Exception as exc:
                    won_issues.append(f'{file.name}: {exc}')

        if won_issues:
            with st.expander(f'Records to review ({len(won_issues)})', expanded=True):
                for issue in won_issues[:200]:
                    st.write('• ' + issue)

        if won_rows:
            full_df = pd.DataFrame(won_rows)
            auction_options = sorted(full_df['Auction'].unique().tolist())
            selected_auction = st.selectbox(
                'Select auction', ['All Auctions'] + auction_options,
                key='aucneo_won_auction',
            )
            selected_df = (full_df if selected_auction == 'All Auctions'
                           else full_df.loc[full_df['Auction'] == selected_auction])
            output_df = selected_df[
                ['Auction', 'Lot', 'Win Price (Man Yen)']
            ].copy()
            output_df['Lot'] = output_df['Lot'].astype(str)

            total_col, groups_col, selected_col = st.columns(3)
            total_col.metric('Total won lots', len(full_df))
            groups_col.metric('Auction groups', len(auction_options))
            selected_col.metric('Selected auction lots', len(output_df))

            st.dataframe(
                output_df, hide_index=True, use_container_width=True,
                column_config={
                    'Lot': st.column_config.TextColumn('Lot'),
                    'Win Price (Man Yen)': st.column_config.NumberColumn(
                        'Win Price (Man Yen)', format='%.1f'
                    ),
                },
            )
            safe_name = ('all_auctions' if selected_auction == 'All Auctions'
                         else re.sub(r'[^a-z0-9_-]+', '_', selected_auction.lower()).strip('_'))
            excel_col, csv_col = st.columns(2)
            excel_col.download_button(
                '⬇ Download selected Excel', excel_bytes(output_df),
                f'{safe_name}_won.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True, key='aucneo_won_excel',
            )
            csv_col.download_button(
                '⬇ Download selected CSV', csv_bytes(output_df),
                f'{safe_name}_won.csv', mime='text/csv',
                use_container_width=True, key='aucneo_won_csv',
            )
            with st.expander('View auction dates (for repeated lots across 3 months)'):
                st.dataframe(
                    selected_df[['Auction Date', 'Auction', 'Lot',
                                 'Win Price (Man Yen)', 'Page']],
                    hide_index=True, use_container_width=True,
                )
        else:
            st.warning('No winning vehicle records found. Please upload an AUCNEO 落札車一覧 report.')
    else:
        st.info('Upload WON.pdf to extract all auction wins and select one auction or All Auctions.')


with recheck_tab:
    from win_recheck import render_win_recheck
    render_win_recheck()


with combined_tab:
    from combined_bids import render_combined
    render_combined(active if files else [], combined_taa_rows if pasted.strip() else [], mirive_rows if mirive_files else [])
