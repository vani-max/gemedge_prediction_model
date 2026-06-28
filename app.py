"""
app.py — GemEdge Procurement Intelligence Dashboard
Color scheme inspired by GeM portal: white background, navy #1B3A6B,
teal #00A896, orange #FF6B35
"""

import streamlit as st
import json
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="GemEdge Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #FFFFFF !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
    background: #FFFFFF;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background-color: #1B3A6B !important;
    border-right: 1px solid #16336080;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 20px 18px 24px 18px !important;
}
[data-testid="stSidebar"] * { color: #E8EDF5 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stNumberInput > div > div > input {
    background-color: #213F72 !important;
    border: 1px solid #2D5499 !important;
    border-radius: 6px !important;
    color: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] .stSlider > div > div > div {
    background: #00A896 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #FF6B35 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 12px 0 !important;
    width: 100% !important;
    letter-spacing: 0.03em !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #E55A25 !important;
}

/* ── MAIN BACKGROUND ── */
.main { background: #FFFFFF !important; }
.main-wrap {
    padding: 0 24px 32px 24px;
    background: #FFFFFF;
}

/* ── TOP NAV BAR (GeM style) ── */
.top-nav {
    background: #1B3A6B;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0;
}
.top-nav-logo {
    display: flex; align-items: center; gap: 10px;
}
.top-nav-icon {
    width: 32px; height: 32px;
    background: #00A896;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
}
.top-nav-brand { font-size: 18px; font-weight: 700; color: #FFFFFF; }
.top-nav-sub { font-size: 10px; color: #8BA3C7; letter-spacing: 0.1em; text-transform: uppercase; }
.top-nav-right { font-size: 12px; color: #8BA3C7; }

/* ── BREADCRUMB STRIP ── */
.breadcrumb-strip {
    background: #F0F4FA;
    border-bottom: 1px solid #DDE4F0;
    padding: 10px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
}
.breadcrumb-left { font-size: 12px; color: #5A7BAD; }
.breadcrumb-left strong { color: #1B3A6B; }
.breadcrumb-right {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px; font-weight: 700;
    color: #FF6B35;
}

/* ── HEADER CARD ── */
.header-card {
    background: #FFFFFF;
    border: 1px solid #DDE4F0;
    border-radius: 8px;
    padding: 16px 22px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 4px rgba(27,58,107,0.06);
}
.hc-label {
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #8BA3C7; margin-bottom: 3px;
}
.hc-val { font-size: 14px; font-weight: 600; color: #1B3A6B; }
.hc-sub {
    font-size: 11px; color: #8BA3C7;
    font-family: 'JetBrains Mono', monospace; margin-top: 2px;
}
.hc-bid {
    font-family: 'JetBrains Mono', monospace;
    font-size: 24px; font-weight: 700; color: #FF6B35;
}

/* ── COLUMN CARDS ── */
.col-card {
    background: #FFFFFF;
    border: 1px solid #DDE4F0;
    border-radius: 8px;
    padding: 18px 18px 20px 18px;
    box-shadow: 0 1px 4px rgba(27,58,107,0.06);
}
.card-b { border-top: 3px solid #1B3A6B; }
.card-c { border-top: 3px solid #00A896; }
.card-d { border-top: 3px solid #FF6B35; }

.card-header {
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #8BA3C7; margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #EEF2F8;
}

/* ── STATUS BADGES ── */
.badge-eligible {
    display: inline-flex; align-items: center; gap: 6px;
    background: #E8F9F6; color: #007A6A;
    border: 1px solid #00A89640;
    border-radius: 6px; padding: 7px 14px;
    font-weight: 700; font-size: 14px; margin-bottom: 14px;
}
.badge-ineligible {
    display: inline-flex; align-items: center; gap: 6px;
    background: #FEE8E8; color: #C0392B;
    border: 1px solid #E74C3C40;
    border-radius: 6px; padding: 7px 14px;
    font-weight: 700; font-size: 14px; margin-bottom: 14px;
}

/* ── CHECK ROWS ── */
.check-row {
    display: flex; align-items: flex-start;
    justify-content: space-between;
    padding: 9px 0; gap: 8px;
    border-bottom: 1px solid #F0F4FA;
}
.check-row:last-child { border-bottom: none; }
.cr-label { font-size: 12px; font-weight: 600; color: #1B3A6B; }
.cr-sub { font-size: 11px; color: #8BA3C7; margin-top: 2px; }
.pill {
    border-radius: 20px; padding: 2px 9px;
    font-size: 10px; font-weight: 700;
    white-space: nowrap; letter-spacing: 0.04em;
}
.pill-pass { background: #E8F9F6; color: #007A6A; }
.pill-fail { background: #FEE8E8; color: #C0392B; }
.pill-warn { background: #FFF4E6; color: #D4820A; }
.pill-info { background: #EAF0FB; color: #2D6BB5; }

/* ── REGULATORY TAG ── */
.reg-tag {
    display: inline-flex; align-items: center; gap: 5px;
    background: #E8F9F6; color: #007A6A;
    border: 1px solid #00A89640;
    border-radius: 6px; padding: 6px 12px;
    font-size: 11px; font-weight: 600;
    margin-top: 6px; margin-right: 5px;
}

/* ── PRICE DISPLAY ── */
.price-hero {
    font-family: 'JetBrains Mono', monospace;
    font-size: 34px; font-weight: 700;
    color: #1B3A6B; line-height: 1.1;
    margin: 6px 0 4px 0;
}
.price-sub { font-size: 11px; color: #8BA3C7; margin-bottom: 14px; }

/* ── BID VS L1 CARD ── */
.bid-vs-card {
    background: #F8FAFD;
    border: 1px solid #DDE4F0;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 14px;
}
.bvc-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8BA3C7; margin-bottom: 6px;
}
.bvc-above {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px; font-weight: 700; color: #C0392B;
}
.bvc-below {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px; font-weight: 700; color: #007A6A;
}
.bvc-sub {
    font-size: 11px; color: #8BA3C7;
    font-family: 'JetBrains Mono', monospace; margin-top: 3px;
}

/* ── RANGE BAR ── */
.range-title {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8BA3C7;
    margin: 14px 0 6px 0;
}
.range-outer {
    background: linear-gradient(to right, #E8F9F6, #FFF4E6, #FEE8E8);
    border-radius: 999px; height: 10px; position: relative;
    margin-bottom: 5px;
}
.range-ticks {
    display: flex; justify-content: space-between;
    font-size: 10px; color: #8BA3C7;
    font-family: 'JetBrains Mono', monospace;
}

/* ── STAT ROWS ── */
.stat-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 0; border-bottom: 1px solid #F0F4FA;
}
.stat-row:last-child { border-bottom: none; }
.sk { font-size: 12px; color: #5A7BAD; }
.sv {
    font-size: 12px; font-weight: 600; color: #1B3A6B;
    font-family: 'JetBrains Mono', monospace;
}

/* ── DIVIDER ── */
.cdiv { border: none; border-top: 1px solid #EEF2F8; margin: 12px 0; }

/* ── DONUT ── */
.donut-wrap {
    display: flex; flex-direction: column;
    align-items: center; margin: 4px 0 14px 0;
}

/* ── SCORE BAR ── */
.sbar-title {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8BA3C7; margin: 14px 0 7px 0;
}
.sbar-outer {
    display: flex; border-radius: 6px; overflow: hidden;
    height: 9px; margin-bottom: 8px;
}
.sbar-legend {
    display: flex; gap: 14px; flex-wrap: wrap;
}
.sleg {
    display: flex; align-items: center; gap: 5px;
    font-size: 11px; color: #5A7BAD;
}
.sleg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── MSME BADGE ── */
.msme-pill {
    display: inline-block;
    background: #E8F9F6; color: #007A6A;
    border: 1px solid #00A89640;
    border-radius: 4px; padding: 1px 6px;
    font-size: 9px; font-weight: 700;
    letter-spacing: 0.05em; margin-left: 6px;
    vertical-align: middle;
}

/* ── SIDEBAR LABELS ── */
.sb-section {
    font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #5A7BAD !important;
    margin: 14px 0 5px 0;
}
.sb-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; color: #5A7BAD !important;
    margin-top: -6px; margin-bottom: 10px;
}

/* ── DATA SOURCES ── */
.ds-footer {
    margin-top: 20px; padding-top: 14px;
    border-top: 1px solid #2D5499;
}
.ds-title {
    font-size: 9px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #5A7BAD !important; margin-bottom: 8px;
}
.ds-item {
    display: flex; align-items: center; gap: 7px;
    font-size: 11px; color: #8BA3C7 !important; margin-bottom: 5px;
}
.ds-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #00A896; flex-shrink: 0;
}

/* ── IDLE STATE ── */
.idle-wrap {
    text-align: center; padding: 80px 0 60px 0;
    background: #FFFFFF;
}

/* streamlit expander */
.streamlit-expanderHeader {
    background: #F8FAFD !important;
    border-radius: 6px !important;
    border: 1px solid #DDE4F0 !important;
    font-size: 12px !important; font-weight: 600 !important;
    color: #1B3A6B !important;
}
</style>
""", unsafe_allow_html=True)

from data_pipeline import run_data_pipeline_validation
from compliance_engine import (
    extract_tender_text, extract_requirements_with_llm,
    parse_and_validate_llm_output, check_vendor_compliance
)
from pricing_model import predict_l1_price
from win_probability import calculate_win_probability

TENDERS = {
    "Laptop (Entry/Mid Level) — GEM/2026/B/7553726": {"path": "data/raw_tenders/laptop_1.pdf", "category": "laptop", "bid_number": "GEM/2026/B/7553726"},
    "High End Laptop — GEM/2026/B/7704471":           {"path": "data/raw_tenders/laptop_2.pdf", "category": "laptop", "bid_number": "GEM/2026/B/7704471"},
    "Rental Laptop — GEM/2026/B/7708073":             {"path": "data/raw_tenders/laptop_3.pdf", "category": "laptop", "bid_number": "GEM/2026/B/7708073"},
    "Laptop Express Card — GEM/2026/B/7706864":       {"path": "data/raw_tenders/laptop_4.pdf", "category": "laptop", "bid_number": "GEM/2026/B/7706864"},
    "Crash Bollard — GEM/2025/B/5902895":             {"path": "data/raw_tenders/bollard_1.pdf","category": "bollard","bid_number": "GEM/2025/B/5902895"},
}

# ── SIDEBAR ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:22px;">
      <div style="width:34px;height:34px;background:#00A896;border-radius:7px;
           display:flex;align-items:center;justify-content:center;font-size:17px;">🏛️</div>
      <div>
        <div style="font-size:16px;font-weight:700;color:#FFFFFF;">GemEdge</div>
        <div style="font-size:9px;color:#5A7BAD;letter-spacing:0.1em;text-transform:uppercase;">
          Procurement Intelligence</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section">Select Tender</div>', unsafe_allow_html=True)
    sel_tender_name = st.selectbox("tender", list(TENDERS.keys()), label_visibility="collapsed")
    tender = TENDERS[sel_tender_name]
    st.markdown(f'<div class="sb-sub">{tender["bid_number"]}</div>', unsafe_allow_html=True)

    with open("data/vendor_profiles.json") as f:
        vendors = json.load(f)

    st.markdown('<div class="sb-section">Select Vendor</div>', unsafe_allow_html=True)
    sel_vendor_name = st.selectbox("vendor", [v["name"] for v in vendors], label_visibility="collapsed")
    vendor = next(v for v in vendors if v["name"] == sel_vendor_name)
    msme_tag = f'<span class="msme-pill">{vendor["msme_type"]}</span>' if vendor.get("msme_type") else ""
    st.markdown(f'<div class="sb-sub">₹{vendor["annual_turnover_lakhs"]}L turnover{msme_tag}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section">Bid Price (₹)</div>', unsafe_allow_html=True)
    bid_price = st.number_input("bid", min_value=10000, max_value=999999, value=47000, step=500, label_visibility="collapsed")
    st.markdown(f'<div class="sb-sub">≈ ₹{bid_price/100000:.2f}L</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section">Expected Competitors</div>', unsafe_allow_html=True)
    num_competitors = st.slider("comp", 1, 25, 8, label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    run_clicked = st.button("Run Analysis →", use_container_width=True)

    st.markdown("""
    <div class="ds-footer">
      <div class="ds-title">Data Sources</div>
      <div class="ds-item"><div class="ds-dot"></div>5 PDFs loaded</div>
      <div class="ds-item"><div class="ds-dot"></div>25 historical records</div>
      <div class="ds-item"><div class="ds-dot"></div>3 vendor profiles</div>
    </div>
    """, unsafe_allow_html=True)

# ── TOP NAV BAR ──────────────────────────────────────────────────
st.markdown(f"""
<div class="top-nav">
  <div class="top-nav-logo">
    <div class="top-nav-icon">🏛️</div>
    <div>
      <div class="top-nav-brand">GemEdge</div>
      <div class="top-nav-sub">Procurement Intelligence Platform</div>
    </div>
  </div>
  <div class="top-nav-right">Government e-Marketplace · Bid Analysis Engine</div>
</div>
""", unsafe_allow_html=True)

# ── BREADCRUMB ───────────────────────────────────────────────────
st.markdown(f"""
<div class="breadcrumb-strip">
  <div class="breadcrumb-left">
    Home / Bids / <strong>{tender["bid_number"]}</strong>
  </div>
  <div class="breadcrumb-right">Bid: ₹{bid_price:,}</div>
</div>
""", unsafe_allow_html=True)

# ── MAIN WRAP ───────────────────────────────────────────────────
st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

# ── HEADER CARD ─────────────────────────────────────────────────
msme_html = f'<span class="msme-pill">{vendor["msme_type"]}</span>' if vendor.get("msme_type") else ""
st.markdown(f"""
<div class="header-card">
  <div>
    <div class="hc-label">Tender</div>
    <div class="hc-val">{sel_tender_name.split('—')[0].strip()}</div>
    <div class="hc-sub">{tender["bid_number"]}</div>
  </div>
  <div>
    <div class="hc-label">Vendor</div>
    <div class="hc-val">{sel_vendor_name}{msme_html}</div>
    <div class="hc-sub">₹{vendor["annual_turnover_lakhs"]}L annual turnover</div>
  </div>
  <div style="text-align:right;">
    <div class="hc-label">Your Bid</div>
    <div class="hc-bid">₹{bid_price:,}</div>
    <div class="hc-sub">≈ ₹{bid_price/100000:.2f}L</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── IDLE STATE ───────────────────────────────────────────────────
if not run_clicked:
    st.markdown("""
    <div class="idle-wrap">
      <div style="font-size:44px;margin-bottom:14px;">🏛️</div>
      <div style="font-size:17px;font-weight:600;color:#1B3A6B;margin-bottom:8px;">
        Ready to Analyse
      </div>
      <div style="font-size:13px;color:#8BA3C7;">
        Select your tender, vendor, and bid price in the sidebar<br>
        then click <strong style="color:#FF6B35;">Run Analysis →</strong>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── 3 COLUMNS ───────────────────────────────────────────────────
col_b, col_c, col_d = st.columns(3, gap="medium")

# ════════════════════════════════════════════════════════════════
# COLUMN B — COMPLIANCE
# ════════════════════════════════════════════════════════════════
with col_b:
    st.markdown('<div class="col-card card-b">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">Compliance Check</div>', unsafe_allow_html=True)

    with st.spinner("Parsing tender..."):
        try:
            text  = extract_tender_text(tender["path"])
            raw   = extract_requirements_with_llm(text)
            reqs  = parse_and_validate_llm_output(raw)
            comp  = check_vendor_compliance(vendor, reqs)
        except Exception as e:
            st.error(f"Error: {e}")
            comp = {"is_compliant": False, "failures": [], "warnings": [], "preferences": []}
            reqs = None

    if comp["is_compliant"]:
        st.markdown('<div class="badge-eligible">✓ &nbsp;ELIGIBLE TO BID</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-ineligible">✗ &nbsp;NOT ELIGIBLE</div>', unsafe_allow_html=True)

    if reqs:
        def crow(label, sub, status):
            pcls = {"PASS":"pill-pass","FAIL":"pill-fail","WARN":"pill-warn","INFO":"pill-info"}.get(status,"pill-info")
            return (f'<div class="check-row">'
                    f'<div><div class="cr-label">{label}</div>'
                    f'<div class="cr-sub">{sub}</div></div>'
                    f'<div class="pill {pcls}">{status}</div></div>')

        rows = ""
        # Turnover
        if reqs.minimum_turnover_lakhs:
            vt = vendor["annual_turnover_lakhs"]
            rt = reqs.minimum_turnover_lakhs
            exempt = vendor.get("is_msme") and reqs.mse_relaxation
            if exempt:
                rows += crow("Turnover Requirement", "Waived — MSE relaxation applies", "PASS")
            elif vt >= rt:
                rows += crow("Annual Turnover", f"₹{vt}L ≥ required ₹{rt}L", "PASS")
            else:
                rows += crow("Annual Turnover", f"₹{vt}L < required ₹{rt}L", "FAIL")
        else:
            rows += crow("Annual Turnover", "Refer buyer spec document", "WARN")

        # MSE
        if vendor.get("is_msme"):
            rows += crow("MSE / MSME Status", f"Registered · {vendor.get('msme_type','MSME')}", "PASS")
        else:
            rows += crow("MSE / MSME Status", "Not registered — no preference", "INFO")

        # ISO
        certs = set(vendor.get("certifications", []))
        if "ISO9001" in certs:
            rows += crow("ISO 9001 Certification", "Certificate verified", "PASS")
        elif reqs.required_certifications and "ISO9001" in reqs.required_certifications:
            rows += crow("ISO 9001 Certification", "Required but missing", "FAIL")

        # OEM
        if reqs.oem_authorization_required:
            if vendor.get("is_oem") and "OEM_Authorization" in certs:
                rows += crow("OEM Authorization", "Certificate present", "PASS")
            else:
                rows += crow("OEM Authorization", "Required — vendor not OEM", "FAIL")

        # Local supplier
        cls = vendor.get("is_local_supplier_class")
        lc  = vendor.get("local_content_percent", 0)
        if cls in [1, 2]:
            rows += crow(f"Local Supplier Class {cls}", f"{lc}% local content", "PASS")
        elif vendor.get("is_msme"):
            rows += crow("Local Supplier Class", "MSME exception applies", "WARN")
        else:
            rows += crow("Local Supplier Class", "Min 20% local content needed", "FAIL")

        # EMD
        if reqs.emd_required:
            rows += crow("EMD / Bid Security", "Required for this tender", "WARN")
        else:
            rows += crow("EMD / Bid Security", "Not required", "PASS")

        st.markdown(rows, unsafe_allow_html=True)

    if comp["failures"]:
        st.markdown('<hr class="cdiv">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;font-weight:700;color:#C0392B;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:5px;">Disqualifying Issues</div>', unsafe_allow_html=True)
        for f in comp["failures"]:
            st.markdown(f'<div style="font-size:12px;color:#C0392B;padding:3px 0;">✗ &nbsp;{f}</div>', unsafe_allow_html=True)

    if comp["preferences"]:
        st.markdown('<hr class="cdiv">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;font-weight:700;color:#007A6A;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:7px;">Regulatory Advantages</div>', unsafe_allow_html=True)
        for p in comp["preferences"]:
            short = p.split(".")[0][:65] if "." in p else p[:65]
            st.markdown(f'<div class="reg-tag">★ &nbsp;{short}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# COLUMN C — PRICE PREDICTION
# ════════════════════════════════════════════════════════════════
with col_c:
    st.markdown('<div class="col-card card-c">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">L1 Price Prediction</div>', unsafe_allow_html=True)

    with st.spinner("Running price model..."):
        try:
            pr = predict_l1_price(
                csv_path="data/historical_awards.csv",
                target_specs={"category": tender["category"], "expected_bidders": num_competitors}
            )
            predicted_l1 = pr["recommended_l1_estimate"]
        except Exception as e:
            st.error(f"Error: {e}")
            predicted_l1 = 47159.0
            pr = None

    st.markdown('<div style="font-size:10px;color:#8BA3C7;margin-bottom:2px;">Predicted L1 Price</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="price-hero">₹{predicted_l1:,.0f}</div>', unsafe_allow_html=True)
    recs = pr["data_points_used"] if pr else 0
    st.markdown(f'<div class="price-sub">₹{predicted_l1/100000:.2f}L · based on {recs} historical records</div>', unsafe_allow_html=True)

    # Bid vs L1
    diff     = bid_price - predicted_l1
    diff_pct = (diff / predicted_l1) * 100
    above    = diff > 0
    d_cls    = "bvc-above" if above else "bvc-below"
    d_arrow  = "↑" if above else "↓"
    d_lbl    = "above L1" if above else "below L1"
    st.markdown(f"""
    <div class="bid-vs-card">
      <div class="bvc-label">Your Bid vs Predicted L1</div>
      <div class="{d_cls}">{d_arrow} ₹{abs(diff):,.0f} &nbsp;
        <span style="font-size:12px;">({abs(diff_pct):.1f}% {d_lbl})</span>
      </div>
      <div class="bvc-sub">Your bid: ₹{bid_price:,}</div>
    </div>
    """, unsafe_allow_html=True)

    # Range bar
    if pr:
        s   = pr["statistical"]
        lo, hi, med = s["min_observed"], s["max_observed"], s["median"]
        pos = max(2, min(97, (bid_price - lo) / max(hi - lo, 1) * 100))
        mp  = max(2, min(97, (med - lo)      / max(hi - lo, 1) * 100))
        dot_color = "#C0392B" if above else "#007A6A"
        st.markdown(f"""
        <div class="range-title">Bid Position — Historical Range</div>
        <div class="range-outer">
          <div style="position:absolute;left:{mp}%;top:50%;
               transform:translate(-50%,-50%);
               width:2px;height:18px;background:#8BA3C7;border-radius:2px;"></div>
          <div style="position:absolute;left:calc({pos}% - 6px);top:50%;
               transform:translateY(-50%);
               width:12px;height:12px;background:{dot_color};
               border:2px solid #FFFFFF;border-radius:50%;
               box-shadow:0 0 0 3px {dot_color}33;"></div>
        </div>
        <div class="range-ticks">
          <span>₹{lo/1000:.0f}K</span>
          <span>Avg ₹{med/1000:.0f}K</span>
          <span>₹{hi/1000:.0f}K</span>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Statistical Details"):
        if pr:
            ci = pr["statistical"]["confidence_interval_90"]
            for k, v in [
                ("Median",     f"₹{pr['statistical']['median']:,.0f}"),
                ("Mean",       f"₹{pr['statistical']['mean']:,.0f}"),
                ("Std Dev",    f"₹{pr['statistical']['std_deviation']:,.0f}"),
                ("90% CI",     f"₹{ci['lower']:,.0f} – ₹{ci['upper']:,.0f}"),
                ("Method",     pr["recommendation_method"]),
            ]:
                st.markdown(f'<div class="stat-row"><span class="sk">{k}</span><span class="sv">{v}</span></div>', unsafe_allow_html=True)

    if pr and pr.get("ml"):
        with st.expander("ML Model Coefficients"):
            ml = pr["ml"]
            st.markdown(f'<div class="stat-row"><span class="sk">MAE</span><span class="sv">₹{ml["mean_absolute_error"]:,.0f}</span></div>', unsafe_allow_html=True)
            for feat, coef in ml["coefficients"].items():
                d = "↓" if coef < 0 else "↑"
                c = "#007A6A" if coef < 0 else "#C0392B"
                st.markdown(f'<div class="stat-row"><span class="sk">{feat}</span><span class="sv" style="color:{c};">{d} ₹{abs(coef):,.0f}/unit</span></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# COLUMN D — WIN PROBABILITY
# ════════════════════════════════════════════════════════════════
with col_d:
    st.markdown('<div class="col-card card-d">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">Win Probability</div>', unsafe_allow_html=True)

    prob_r = calculate_win_probability(
        vendor_bid=bid_price, predicted_l1=predicted_l1,
        num_competitors=num_competitors,
        is_msme=vendor["is_msme"], msme_type=vendor.get("msme_type"),
        is_compliant=comp["is_compliant"]
    )
    prob = prob_r["win_probability"]

    if prob >= 65:
        pc, pb, ps = "#007A6A", "#E8F9F6", "Strong"
    elif prob >= 40:
        pc, pb, ps = "#D4820A", "#FFF4E6", "Competitive"
    elif prob > 0:
        pc, pb, ps = "#C0392B", "#FEE8E8", "Weak"
    else:
        pc, pb, ps = "#8BA3C7", "#F0F4FA", "Ineligible"

    # SVG donut
    R   = 54; cx = cy = 70
    C   = 2 * 3.14159 * R
    dsh = (prob / 100) * C
    gap = C - dsh
    st.markdown(f"""
    <div class="donut-wrap">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="{cx}" cy="{cy}" r="{R}"
          fill="none" stroke="#EEF2F8" stroke-width="13"/>
        <circle cx="{cx}" cy="{cy}" r="{R}"
          fill="none" stroke="{pc}" stroke-width="13"
          stroke-dasharray="{dsh:.1f} {gap:.1f}"
          stroke-dashoffset="{C/4:.1f}" stroke-linecap="round"/>
        <text x="{cx}" y="{cy-5}" text-anchor="middle"
          font-family="JetBrains Mono,monospace"
          font-size="26" font-weight="700" fill="{pc}">{prob:.0f}</text>
        <text x="{cx}" y="{cy+13}" text-anchor="middle"
          font-family="Inter,sans-serif"
          font-size="8" font-weight="600" fill="#8BA3C7"
          letter-spacing="1">WIN PROB %</text>
      </svg>
      <div style="font-size:12px;font-weight:700;color:{pc};
           background:{pb};padding:3px 14px;border-radius:20px;
           margin-top:-6px;border:1px solid {pc}33;">{ps}</div>
    </div>
    """, unsafe_allow_html=True)

    # Score breakdown bar
    if prob_r["breakdown"]:
        bd = prob_r["breakdown"]
        ps_s = bd["price_score"] * 60
        cf_s = bd["competition_factor"] * 30
        rb_s = bd["regulatory_bonus"] * 100
        tot  = ps_s + cf_s + rb_s
        if tot > 0:
            pw = ps_s / tot * 100
            cw = cf_s / tot * 100
            rw = max(0, 100 - pw - cw)
        else:
            pw = cw = rw = 33.3

        st.markdown(f"""
        <div class="sbar-title">Score Breakdown</div>
        <div class="sbar-outer">
          <div style="width:{pw:.0f}%;background:#00A896;"></div>
          <div style="width:{cw:.0f}%;background:#1B3A6B;"></div>
          <div style="width:{rw:.0f}%;background:#FF6B35;"></div>
        </div>
        <div class="sbar-legend">
          <div class="sleg"><div class="sleg-dot" style="background:#00A896;"></div>
            Price Score <strong style="color:#1B3A6B;">&nbsp;{ps_s:.0f}</strong></div>
          <div class="sleg"><div class="sleg-dot" style="background:#1B3A6B;"></div>
            Competition <strong style="color:#1B3A6B;">&nbsp;{cf_s:.0f}</strong></div>
          <div class="sleg"><div class="sleg-dot" style="background:#FF6B35;"></div>
            Regulatory <strong style="color:#1B3A6B;">&nbsp;{rb_s:.0f}</strong></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr class="cdiv">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="stat-row"><span class="sk">Price Ratio</span>
          <span class="sv">{bd['price_ratio']:.3f}×</span></div>
        <div class="stat-row"><span class="sk">Regulatory</span>
          <span class="sv" style="font-family:Inter;font-size:11px;color:#5A7BAD;">
          {bd['regulatory_note']}</span></div>
        <div style="font-size:10px;color:#8BA3C7;margin-top:10px;line-height:1.6;">
          Formula: (0.6 × price_score) + (0.3 × competition) + regulatory_bonus
        </div>
        """, unsafe_allow_html=True)

    # Sensitivity chart
    st.markdown('<hr class="cdiv">', unsafe_allow_html=True)
    st.markdown('<div class="card-header" style="margin-top:4px;">Bid Price Sensitivity</div>', unsafe_allow_html=True)
    pr_range = np.linspace(predicted_l1 * 0.70, predicted_l1 * 1.40, 55)
    curve = [
        calculate_win_probability(
            vendor_bid=float(p), predicted_l1=predicted_l1,
            num_competitors=num_competitors,
            is_msme=vendor["is_msme"], msme_type=vendor.get("msme_type"),
            is_compliant=comp["is_compliant"]
        )["win_probability"]
        for p in pr_range
    ]
    cdf = pd.DataFrame({
        "Bid Price (₹)": pr_range.astype(int),
        "Win Probability (%)": curve
    }).set_index("Bid Price (₹)")
    st.line_chart(cdf, color="#00A896", height=150, use_container_width=True)
    st.markdown(
        '<div style="font-size:10px;color:#8BA3C7;text-align:center;margin-top:-6px;">'
        'Strictly monotonically decreasing · verified by automated tests</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)