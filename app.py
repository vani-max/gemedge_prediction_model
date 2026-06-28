"""
app.py

GemEdge Procurement Intelligence — Streamlit Dashboard
Ties together all 4 components into a single interactive UI.

A user can:
1. Select a tender PDF
2. Select a vendor profile  
3. Enter a target bid price
4. See compliance result, predicted L1 price, and win probability
"""

import streamlit as st
import json
import pandas as pd
import numpy as np
import sys
import os

from data_pipeline import run_data_pipeline_validation
from compliance_engine import (
    extract_tender_text,
    extract_requirements_with_llm,
    parse_and_validate_llm_output,
    check_vendor_compliance
)
from pricing_model import predict_l1_price
from win_probability import calculate_win_probability

# PAGE CONFIG
st.set_page_config(
    page_title="GemEdge Intelligence",
    page_icon="🏛️",
    layout="wide"
)

# HEADER
st.title("GemEdge Procurement Intelligence")
st.caption("AI-powered tender analysis for the Government e-Marketplace (GeM)")
st.divider()


# SIDEBAR — ALL INPUTS
st.sidebar.title("Analysis Parameters")

# --- Tender Selection ---
st.sidebar.header("Step 1 — Select Tender")

TENDER_OPTIONS = {
    "Laptop (Entry/Mid Level) — GEM/2026/B/7553726": {
        "path": "data/raw_tenders/laptop_1.pdf",
        "category": "laptop",
        "bid_number": "GEM/2026/B/7553726"
    },
    "High End Laptop — GEM/2026/B/7704471": {
        "path": "data/raw_tenders/laptop_2.pdf",
        "category": "laptop",
        "bid_number": "GEM/2026/B/7704471"
    },
    "Rental Laptop — GEM/2026/B/7708073": {
        "path": "data/raw_tenders/laptop_3.pdf",
        "category": "laptop",
        "bid_number": "GEM/2026/B/7708073"
    },
    "Laptop Express Card — GEM/2026/B/7706864": {
        "path": "data/raw_tenders/laptop_4.pdf",
        "category": "laptop",
        "bid_number": "GEM/2026/B/7706864"
    },
    "Crash Bollard — GEM/2025/B/5902895": {
        "path": "data/raw_tenders/bollard_1.pdf",
        "category": "bollard",
        "bid_number": "GEM/2025/B/5902895"
    }
}

selected_tender_name = st.sidebar.selectbox(
    "Choose a tender",
    list(TENDER_OPTIONS.keys())
)
selected_tender = TENDER_OPTIONS[selected_tender_name]

# --- Vendor Selection ---
st.sidebar.header("Step 2 — Select Vendor")

with open("data/vendor_profiles.json") as f:
    vendors = json.load(f)

vendor_names = [v["name"] for v in vendors]
selected_vendor_name = st.sidebar.selectbox("Choose a vendor", vendor_names)
selected_vendor = next(v for v in vendors if v["name"] == selected_vendor_name)

# Show vendor summary
with st.sidebar.expander("Vendor Profile"):
    st.write(f"**Turnover:** ₹{selected_vendor['annual_turnover_lakhs']}L")
    st.write(f"**MSME:** {selected_vendor['is_msme']}")
    st.write(f"**MSME Type:** {selected_vendor.get('msme_type') or 'N/A'}")
    st.write(f"**OEM:** {selected_vendor.get('is_oem')}")
    st.write(f"**Certifications:** {', '.join(selected_vendor['certifications'])}")
    st.write(f"**Local Supplier Class:** {selected_vendor.get('is_local_supplier_class')}")
    st.write(f"**Local Content:** {selected_vendor.get('local_content_percent')}%")

# --- Bid Price Input ---
st.sidebar.header("Step 3 — Enter Bid Price")

bid_price = st.sidebar.number_input(
    "Your proposed bid price (₹)",
    min_value=10000,
    max_value=500000,
    value=47000,
    step=500,
    help="Enter the price you want to quote for this tender"
)

expected_bidders = st.sidebar.slider(
    "Expected number of competitors",
    min_value=1,
    max_value=25,
    value=8,
    help="How many other vendors do you expect to bid?"
)

# --- Run Button ---
st.sidebar.divider()
run_clicked = st.sidebar.button(
    "Run Full Analysis",
    type="primary",
    use_container_width=True
)

# DEFAULT STATE — show instructions before run
if not run_clicked:
    st.info(
        "Select a tender, vendor, and bid price in the sidebar, "
        "then click **Run Full Analysis**."
    )

    # Show data pipeline status
    st.subheader("Data Pipeline Status")
    with st.spinner("Validating data sources..."):
        validation = run_data_pipeline_validation()

    col1, col2, col3 = st.columns(3)
    with col1:
        valid_count = len(validation['tender_files']['valid'])
        st.metric("Tender PDFs Loaded", f"{valid_count}/5")
    with col2:
        records = validation['historical_data'].get('total_records', 0)
        st.metric("Historical Records", records)
    with col3:
        vendor_count = validation['vendor_profiles']['vendor_count']
        st.metric("Vendor Profiles", vendor_count)

    if validation['pipeline_ready']:
        st.success("All data sources valid — ready to run analysis")
    else:
        st.error("Data validation failed — check file paths")
    st.stop()

# MAIN ANALYSIS — runs when button clicked
st.subheader(f"Analysis: {selected_tender_name}")
st.caption(f"Vendor: {selected_vendor_name} | Bid: ₹{bid_price:,}")
st.divider()

# Three columns for three components
col_b, col_c, col_d = st.columns(3)

# COLUMN 1: COMPONENT B — COMPLIANCE
with col_b:
    st.markdown("### Component B\nCompliance Check")

    with st.spinner("Parsing tender document..."):
        try:
            tender_text = extract_tender_text(selected_tender["path"])
            raw_llm_output = extract_requirements_with_llm(tender_text)
            requirements = parse_and_validate_llm_output(raw_llm_output)
            compliance = check_vendor_compliance(
                selected_vendor, requirements
            )

            # Pass/Fail badge
            if compliance["is_compliant"]:
                st.success("## ✓ ELIGIBLE TO BID")
            else:
                st.error("## ✗ NOT ELIGIBLE")

            # Extracted requirements
            with st.expander("Extracted Tender Requirements", expanded=True):
                st.write(f"**Bid Number:** {requirements.bid_number}")
                st.write(f"**Category:** {requirements.item_category}")
                st.write(
                    f"**Min Turnover:** "
                    f"{'₹' + str(requirements.minimum_turnover_lakhs) + 'L' if requirements.minimum_turnover_lakhs else 'See spec doc'}"
                )
                st.write(f"**MSE Relaxation:** {requirements.mse_relaxation}")
                st.write(f"**MII Preference:** {requirements.mii_purchase_preference}")
                st.write(
                    f"**MII Band:** "
                    f"L1+{requirements.mii_price_band_percent}%" if requirements.mii_price_band_percent else "N/A"
                )
                st.write(f"**MSE Preference:** {requirements.mse_purchase_preference}")
                st.write(
                    f"**MSE Band:** "
                    f"L1+{requirements.mse_price_band_percent}%" if requirements.mse_price_band_percent else "N/A"
                )
                st.write(f"**EMD Required:** {requirements.emd_required}")
                st.write(
                    f"**Certifications Required:** "
                    f"{', '.join(requirements.required_certifications) or 'None specified'}"
                )

            # Failures
            if compliance["failures"]:
                st.markdown("**Disqualifying Issues:**")
                for f in compliance["failures"]:
                    st.error(f"✗ {f}")

            # Warnings
            if compliance["warnings"]:
                for w in compliance["warnings"]:
                    st.warning(f"⚠ {w}")

            # Preferences
            if compliance["preferences"]:
                st.markdown("**Regulatory Advantages:**")
                for p in compliance["preferences"]:
                    st.info(f"★ {p}")

        except Exception as e:
            st.error(f"Compliance check failed: {e}")
            compliance = {"is_compliant": False}
            requirements = None

# COLUMN 2: COMPONENT C — PRICE PREDICTION
with col_c:
    st.markdown("### Component C\nL1 Price Prediction")

    with st.spinner("Running price model..."):
        try:
            price_result = predict_l1_price(
                csv_path="data/historical_awards.csv",
                target_specs={
                    "category": selected_tender["category"],
                    "expected_bidders": expected_bidders
                }
            )

            predicted_l1 = price_result["recommended_l1_estimate"]

            st.metric(
                "Predicted L1 Price",
                f"₹{predicted_l1:,.0f}",
                help="Our predicted winning bid price based on historical data"
            )

            # Bid vs L1 comparison
            diff = bid_price - predicted_l1
            diff_pct = (diff / predicted_l1) * 100
            diff_label = f"+{diff_pct:.1f}%" if diff > 0 else f"{diff_pct:.1f}%"
            st.metric(
                "Your Bid vs Predicted L1",
                f"₹{bid_price:,}",
                delta=diff_label,
                delta_color="inverse"
            )

            with st.expander("Statistical Details", expanded=True):
                st.write(
                    f"**Median (historical):** "
                    f"₹{price_result['statistical']['median']:,.0f}"
                )
                st.write(
                    f"**Mean (historical):** "
                    f"₹{price_result['statistical']['mean']:,.0f}"
                )
                st.write(
                    f"**Std Deviation:** "
                    f"₹{price_result['statistical']['std_deviation']:,.0f}"
                )
                ci = price_result['statistical']['confidence_interval_90']
                st.write(
                    f"**90% Confidence Interval:** "
                    f"₹{ci['lower']:,.0f} – ₹{ci['upper']:,.0f}"
                )
                st.write(
                    f"**Data Points Used:** "
                    f"{price_result['data_points_used']} (after outlier removal)"
                )
                st.write(
                    f"**Method:** {price_result['recommendation_method']}"
                )

            if price_result.get("ml"):
                with st.expander("ML Model Details"):
                    ml = price_result["ml"]
                    st.write(
                        f"**ML Predicted Price:** ₹{ml['predicted_price']:,.0f}"
                    )
                    st.write(f"**Mean Absolute Error:** ₹{ml['mean_absolute_error']:,.0f}")
                    st.write(f"**Features:** {', '.join(ml['features_used'])}")
                    st.write("**Coefficients:**")
                    for feat, coef in ml['coefficients'].items():
                        direction = "↓" if coef < 0 else "↑"
                        st.write(
                            f"  • {feat}: {direction} ₹{abs(coef):,.0f} per unit"
                        )

        except Exception as e:
            st.error(f"Price prediction failed: {e}")
            predicted_l1 = 47159.0
            st.warning(f"Using fallback estimate: ₹{predicted_l1:,}")

# COLUMN 3: COMPONENT D — WIN PROBABILITY
with col_d:
    st.markdown("### Component D\nWin Probability")

    try:
        prob_result = calculate_win_probability(
            vendor_bid=bid_price,
            predicted_l1=predicted_l1,
            num_competitors=expected_bidders,
            is_msme=selected_vendor["is_msme"],
            msme_type=selected_vendor.get("msme_type"),
            is_compliant=compliance["is_compliant"]
        )

        prob = prob_result["win_probability"]

        # Color-coded probability display
        if prob >= 65:
            st.success(f"## {prob}%")
            st.caption("Strong chance of winning")
        elif prob >= 40:
            st.warning(f"## {prob}%")
            st.caption("Moderate chance — consider lowering bid")
        elif prob > 0:
            st.error(f"## {prob}%")
            st.caption("Low chance — bid price too high or strong competition")
        else:
            st.error("## 0%")
            st.caption("No chance — vendor failed compliance")

        # Progress bar
        st.progress(prob / 100)

        # Score breakdown
        if prob_result["breakdown"]:
            with st.expander("Score Breakdown", expanded=True):
                bd = prob_result["breakdown"]
                st.write(
                    f"**Price Ratio:** {bd['price_ratio']} "
                    f"({'below' if bd['price_ratio'] < 1 else 'above'} predicted L1)"
                )
                st.write(
                    f"**Price Score:** {bd['price_score']} × 60% weight"
                )
                st.write(
                    f"**Competition Factor:** {bd['competition_factor']} × 30% weight"
                )
                st.write(
                    f"**Regulatory Bonus:** +{bd['regulatory_bonus']} (additive)"
                )
                st.write(f"**Note:** {bd['regulatory_note']}")
                st.divider()
                st.caption(
                    "Formula: (0.6 × price_score) + "
                    "(0.3 × competition_factor) + regulatory_bonus"
                )

        # Monotonicity chart — show how probability changes with price
        with st.expander("Bid Price Sensitivity"):
            st.caption(
                "How your win probability changes as you adjust your bid price"
            )
            price_range = np.linspace(
                predicted_l1 * 0.7,
                predicted_l1 * 1.4,
                50
            )
            probs = []
            for p in price_range:
                r = calculate_win_probability(
                    vendor_bid=float(p),
                    predicted_l1=predicted_l1,
                    num_competitors=expected_bidders,
                    is_msme=selected_vendor["is_msme"],
                    msme_type=selected_vendor.get("msme_type"),
                    is_compliant=compliance["is_compliant"]
                )
                probs.append(r["win_probability"])

            chart_data = pd.DataFrame({
                "Bid Price (₹)": price_range.astype(int),
                "Win Probability (%)": probs
            }).set_index("Bid Price (₹)")

            st.line_chart(chart_data)
            st.caption(
                "This curve is strictly monotonically decreasing — "
                "verified by automated tests."
            )

    except Exception as e:
        st.error(f"Win probability calculation failed: {e}")

# FOOTER
st.divider()
st.caption(
    "GemEdge Procurement Intelligence Engine | "
    "Components: Data Pipeline → Compliance → Price Prediction → Win Probability"
)