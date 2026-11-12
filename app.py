
import streamlit as st
import pandas as pd
from extractor import parse_pdf, excel_bytes, csv_bytes

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="BIZUPON | Auction PDF Extractor",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_URL = "https://www.bizupon.com/images/logo.png"

# ==========================================
# WHITE + GREEN + BLACK DESIGN
# ==========================================
st.markdown("""
<style>

/* Main page */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background-color: #ffffff !important;
    color: #171717 !important;
}

.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Headings */
h1, h2, h3 {
    color: #171717 !important;
    font-weight: 750;
}

h1 {
    letter-spacing: -0.035em;
}

/* Brand divider */
.brand-line {
    height: 4px;
    background: linear-gradient(
        90deg, #23932c, #8fda76, #ffffff
    );
    border-radius: 4px;
    margin: 20px 0 25px;
}

/* Normal text */
.stApp p,
.stApp label {
    color: #222222;
}

/* Caption */
[data-testid="stCaptionContainer"] p {
    color: #647064 !important;
}

/* Statistics cards */
[data-testid="stMetric"] {
    background-color: #f0f8ee !important;
    border: 1px solid #d6e8d1 !important;
    border-radius: 14px !important;
    padding: 20px !important;
    min-height: 125px;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    color: #354535 !important;
    opacity: 1 !important;
    font-weight: 600 !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
    color: #168322 !important;
    opacity: 1 !important;
    font-size: 32px !important;
    font-weight: 800 !important;
}

/* PDF uploader container */
[data-testid="stFileUploader"] {
    background: #f8fcf7 !important;
    border: 1px solid #dcebd8 !important;
    border-radius: 12px !important;
    padding: 12px !important;
}

/* Upload drop area */
[data-testid="stFileUploaderDropzone"] {
    background-color: #ffffff !important;
    border: 2px dashed #8acb82 !important;
    border-radius: 10px !important;
}

/* Upload text */
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzoneInstructions"] * {
    color: #222222 !important;
    opacity: 1 !important;
}

/* Upload button - green background + white text */
[data-testid="stFileUploaderDropzone"] button {
    background-color: #23932c !important;
    border: 1px solid #23932c !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] button *,
[data-testid="stFileUploaderDropzone"] button p,
[data-testid="stFileUploaderDropzone"] button span {
    color: #ffffff !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] button:hover {
    background-color: #176d20 !important;
    border-color: #176d20 !important;
}

/* Download buttons */
div.stDownloadButton > button {
    background-color: #23932c !important;
    border: 1px solid #23932c !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    min-height: 48px;
}

div.stDownloadButton > button *,
div.stDownloadButton > button p {
    color: #ffffff !important;
}

div.stDownloadButton > button:hover {
    background-color: #176d20 !important;
    border-color: #176d20 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #e1e8e0;
    border-radius: 12px;
    overflow: hidden;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 12px;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #dce8da !important;
    border-radius: 12px !important;
}

/* Footer */
.biz-footer {
    text-align: center;
    padding: 22px;
    border-top: 1px solid #e1e8e0;
    margin-top: 35px;
    color: #647064;
    font-size: 13px;
}

.biz-footer strong {
    color: #23932c;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# BIZUPON BRAND HEADER
# ==========================================
# No empty HTML wrapper - fixes blank box.

st.image(LOGO_URL, width=200)

st.title("🚘 Auction PDF Extractor")

st.caption(
    "Extract Japanese Auction Raku POS bid prices, "
    "lot numbers and auction remarks automatically."
)

st.markdown(
    '<div class="brand-line"></div>',
    unsafe_allow_html=True
)

# ==========================================
# PDF UPLOAD
# ==========================================
st.subheader("Upload Auction PDFs")

files = st.file_uploader(
    "Choose one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

st.info(
    "Bid Price is extracted from "
    "らくPOS申込価格 (万円). "
    "1 万円 = ¥10,000. "
    "Cancelled lots are excluded."
)

# ==========================================
# PDF EXTRACTION
# ==========================================
if files:

    active = []
    cancelled = []
    issues = []

    with st.spinner(
        "Extracting lots and checking cancellations..."
    ):
        for f in files:
            try:
                a, c, e = parse_pdf(
                    f.getvalue(),
                    f.name
                )

                active.extend(a)
                cancelled.extend(c)
                issues.extend(e)

            except Exception as exc:
                issues.append(
                    f"{f.name}: {exc}"
                )

    # ======================================
    # STATISTICS
    # ======================================
    st.markdown("### Extraction Summary")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Active Lots", len(active))

    with c2:
        st.metric(
            "Cancelled Skipped",
            len(cancelled)
        )

    with c3:
        st.metric(
            "WON Lots",
            sum(
                r["Remark"] == "WON"
                for r in active
            )
        )

    with c4:
        st.metric(
            "Files Processed",
            len(files)
        )

    # ======================================
    # WARNINGS
    # ======================================
    if issues:
        st.warning(
            "Some records may require manual review:"
        )

        for issue in issues:
            st.write("• " + issue)

    # ======================================
    # EXTRACTED RESULTS
    # ======================================
    if active:

        df = pd.DataFrame(active)[
            [
                "Auction",
                "Lot",
                "Bid Price (Man Yen)",
                "Remark"
            ]
        ]

        st.markdown(
            "### Extracted Auction Bids"
        )

        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Lot": st.column_config.TextColumn(
                    "Lot"
                )
            }
        )

        # ==================================
        # DOWNLOAD
        # ==================================
        st.markdown("### Download Results")

        d1, d2 = st.columns(2)

        with d1:
            st.download_button(
                "⬇ Download Excel (.xlsx)",
                data=excel_bytes(df),
                file_name="auction_active_bids.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True
            )

        with d2:
            st.download_button(
                "⬇ Download CSV",
                data=csv_bytes(df),
                file_name="auction_active_bids.csv",
                mime="text/csv",
                use_container_width=True
            )

    else:
        st.error(
            "No active records found. "
            "The PDF may be scanned or use "
            "a different auction layout."
        )

    # ======================================
    # CANCELLED LOTS
    # ======================================
    with st.expander(
        f"View Cancelled Lots ({len(cancelled)})"
    ):
        if cancelled:
            st.dataframe(
                pd.DataFrame(cancelled),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.write("No cancelled lots found.")

else:
    st.write(
        "Upload one or more PDF files to get started."
    )

# ==========================================
# FOOTER
# ==========================================
st.markdown("""
<div class="biz-footer">
    <strong>BIZUPON</strong> | Auction PDF Extractor
    <p>Japanese Auction Data Processing System</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Supported/tested: text-based KCAA Raku POS "
    "layout. Other layouts and scanned PDFs "
    "may need additional parsing/OCR support. "
    "Review results before using for live bidding."
)
