
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
# WHITE + GREEN + BLACK THEME
# ==========================================
st.markdown("""
<style>
/* Main background */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background-color: #ffffff !important;
    color: #171717 !important;
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* General typography */
h1, h2, h3, h4, p, label {
    color: #171717;
}

h1 {
    font-weight: 800;
    letter-spacing: -0.04em;
}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    color: #647064 !important;
}

/* Main brand header */
.brand-header {
    background: #ffffff;
    border: 1px solid #e2e8e2;
    border-radius: 16px;
    padding: 22px 26px;
    margin-bottom: 24px;
}

.brand-header h1 {
    color: #141414 !important;
    font-size: 30px;
    margin: 15px 0 5px;
}

.brand-header p {
    color: #647064 !important;
    margin: 0;
}

.brand-line {
    height: 4px;
    background: linear-gradient(
        90deg, #27a329, #71d94d, #ffffff
    );
    border-radius: 4px;
    margin-top: 18px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #f2f9f0 !important;
    border: 1px solid #d6e8d1 !important;
    border-radius: 14px !important;
    padding: 20px !important;
    min-height: 125px;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    color: #384638 !important;
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

/* File uploader */
[data-testid="stFileUploader"] {
    background-color: #f8fbf7 !important;
    border: 1px solid #dce9d8 !important;
    border-radius: 14px;
    padding: 12px;
}

[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small {
    color: #222222 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background-color: #ffffff !important;
    border: 2px dashed #90c68a !important;
    border-radius: 10px;
}

[data-testid="stFileUploaderDropzone"] button {
    color: #ffffff !important;
    background-color: #202820 !important;
    border: 1px solid #202820 !important;
}

/* Download buttons */
div.stDownloadButton > button {
    background-color: #23932c !important;
    color: #ffffff !important;
    border: 1px solid #23932c !important;
    border-radius: 10px !important;
    padding: 12px !important;
    font-weight: 700 !important;
}

div.stDownloadButton > button:hover {
    background-color: #176d20 !important;
    border-color: #176d20 !important;
    color: #ffffff !important;
}

div.stDownloadButton > button p {
    color: #ffffff !important;
}

/* Table */
[data-testid="stDataFrame"] {
    border: 1px solid #e1e8e0;
    border-radius: 12px;
    overflow: hidden;
}

/* Info and warning messages */
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
    margin-top: 32px;
    color: #647064;
    font-size: 13px;
}

.biz-footer strong {
    color: #21852b;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# BIZUPON LOGO + HEADER
# ==========================================
st.markdown(
    '<div class="brand-header">',
    unsafe_allow_html=True
)

st.image(LOGO_URL, width=220)

st.markdown("""
<h1>🚘 Auction PDF Extractor</h1>
<p>
Extract Japanese Auction Raku POS bid prices,
lot numbers and auction remarks automatically.
</p>
<div class="brand-line"></div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

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
        st.metric(
            "Active Lots",
            len(active)
        )

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
        # DOWNLOAD BUTTONS
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
    <p>
        Japanese Auction Data Processing System
    </p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Supported/tested: text-based KCAA Raku POS "
    "layout. Other layouts and scanned PDFs "
    "may need additional parsing/OCR support. "
    "Review results before using for live bidding."
)
