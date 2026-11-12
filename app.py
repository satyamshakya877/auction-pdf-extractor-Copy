import streamlit as st
import pandas as pd
from extractor import parse_pdf,excel_bytes,csv_bytes

st.set_page_config(page_title='Auction PDF Extractor',page_icon='🚘',layout='wide')
st.markdown('''<style>
.block-container{max-width:1180px;padding-top:2rem}
h1{letter-spacing:-.035em}
[data-testid="stMetric"]{background:#f0f5ff;border:1px solid #dbe5f7;border-radius:12px;padding:15px}
</style>''',unsafe_allow_html=True)
st.title('🚘 Auction PDF Extractor')
st.caption('Japanese Raku POS PDFs → clean bid list with WON/LOST remarks. Cancelled lots are automatically excluded.')
files=st.file_uploader('Upload auction PDFs',type=['pdf'],accept_multiple_files=True)
st.info('Bid Price is taken from らくPOS申込価格 (万円), not the vehicle price. 1 万円 = ¥10,000.')
if files:
    active=[];cancelled=[];issues=[]
    with st.spinner('Extracting lots and checking cancellations...'):
        for f in files:
            try:
                a,c,e=parse_pdf(f.getvalue(),f.name)
                active.extend(a);cancelled.extend(c);issues.extend(e)
            except Exception as exc:
                issues.append(f'{f.name}: {exc}')
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Active lots',len(active));c2.metric('Cancelled skipped',len(cancelled));c3.metric('WON lots',sum(r['Remark']=='WON' for r in active));c4.metric('Files processed',len(files))
    if issues:
        st.warning('Some records may require manual review:')
        for issue in issues:st.write('• '+issue)
    if active:
        df=pd.DataFrame(active)[['Auction','Lot','Bid Price (Man Yen)','Remark']]
        st.subheader('Extracted bids with auction remarks')
        st.dataframe(df,hide_index=True,use_container_width=True,column_config={'Lot':st.column_config.TextColumn('Lot')})
        d1,d2=st.columns(2)
        d1.download_button('⬇ Download Excel (.xlsx)',excel_bytes(df),'auction_active_bids.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
        d2.download_button('⬇ Download CSV',csv_bytes(df),'auction_active_bids.csv',mime='text/csv',use_container_width=True)
    else:st.error('No active records found. This PDF may be scanned or use a different auction layout.')
    with st.expander(f'Cancelled lots ({len(cancelled)})'):
        if cancelled:st.dataframe(pd.DataFrame(cancelled),hide_index=True,use_container_width=True)
else:
    st.write('Upload one or more PDF files to get started.')
st.caption('Supported/tested: text-based KCAA Raku POS layout. Other layouts and scanned PDFs need additional parsing/OCR support. Review results before using for live bidding.')
