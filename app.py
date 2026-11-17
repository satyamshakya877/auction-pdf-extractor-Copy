import streamlit as st
import pandas as pd
from extractor import parse_pdf, excel_bytes, csv_bytes
from taa_extractor import parse_taa

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
st.caption('BIZUPON | Japanese auction PDFs and TAA/CAA copied bid tables')

pdf_tab, taa_tab = st.tabs(['📄 Raku POS PDF Extractor', '📋 TAA / CAA Paste Extractor'])

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
