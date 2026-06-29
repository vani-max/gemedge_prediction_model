"""
Component A of the GemEdge engine.
Responsibility: Document and validate the data collection pipeline.

In production, this would contain scrapers and API clients.
For this prototype, it validates that required data files exist
and provides metadata about what was collected and from where.
"""

import os
import json
import pandas as pd
import pdfplumber
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DATA MANIFEST

TENDER_MANIFEST = [
    {
        "bid_number": "GEM/2026/B/7553726",
        "filename": "laptop_1.pdf",
        "category": "laptop",
        "item": "Entry and Mid Level Laptop - Notebook",
        "quantity": 7,
        "buyer": "Indian Army, Ministry of Defence",
        "source": "bidplus.gem.gov.in",
        "collected_date": "2026-06-25"
    },
    {
        "bid_number": "GEM/2026/B/7704471",
        "filename": "laptop_2.pdf",
        "category": "laptop",
        "item": "High End Laptop - Notebook (Q2)",
        "quantity": None,
        "buyer": "Unknown",
        "source": "bidplus.gem.gov.in",
        "collected_date": "2026-06-25"
    },
    {
        "bid_number": "GEM/2026/B/7708073",
        "filename": "laptop_3.pdf",
        "category": "laptop",
        "item": "Rental Laptop",
        "quantity": None,
        "buyer": "Unknown",
        "source": "bidplus.gem.gov.in",
        "collected_date": "2026-06-25"
    },
    {
        "bid_number": "GEM/2026/B/7706864",
        "filename": "laptop_4.pdf",
        "category": "laptop",
        "item": "Laptop with Express Card Slot",
        "quantity": None,
        "buyer": "Unknown",
        "source": "bidplus.gem.gov.in",
        "collected_date": "2026-06-25"
    },
    {
        "bid_number": "GEM/2025/B/5902895",
        "filename": "bollard_1.pdf",
        "category": "bollard",
        "item": "K-4 Crash Rated Blocking Bollard (Q3)",
        "quantity": 3,
        "buyer": "Indian Army, Ministry of Defence",
        "source": "bidplus.gem.gov.in",
        "collected_date": "2026-06-25"
    }
]


def validate_tender_files(tender_dir: str = "data/raw_tenders") -> dict:
    """
    Verifies all expected tender PDFs exist and are readable.
    Returns a validation report.
    """
    results = {"valid": [], "missing": [], "unreadable": []}

    for tender in TENDER_MANIFEST:
        path = os.path.join(tender_dir, tender["filename"])

        if not os.path.exists(path):
            results["missing"].append(tender["filename"])
            logger.warning(f"MISSING: {tender['filename']}")
            continue

        try:
            with pdfplumber.open(path) as pdf:
                page_count = len(pdf.pages)
            results["valid"].append({
                "filename": tender["filename"],
                "bid_number": tender["bid_number"],
                "pages": page_count
            })
            logger.info(f"VALID: {tender['filename']} ({page_count} pages)")
        except Exception as e:
            results["unreadable"].append(tender["filename"])
            logger.error(f"UNREADABLE: {tender['filename']} — {e}")

    return results


def validate_historical_data(csv_path: str = "data/historical_awards.csv") -> dict:
    """
    Validates the historical awards CSV is present and well-formed.
    """
    if not os.path.exists(csv_path):
        logger.error(f"Historical data not found: {csv_path}")
        return {"valid": False, "error": "File not found"}

    df = pd.read_csv(csv_path)

    required_columns = [
        "gem_ref_number", "product_name", "category",
        "l1_price", "num_bidders", "award_date"
    ]
    missing_cols = [c for c in required_columns if c not in df.columns]

    if missing_cols:
        return {"valid": False, "error": f"Missing columns: {missing_cols}"}

    report = {
        "valid": True,
        "total_records": len(df),
        "price_range": {
            "min": float(df["l1_price"].min()),
            "max": float(df["l1_price"].max()),
            "mean": round(float(df["l1_price"].mean()), 2)
        },
        "date_range": {
            "earliest": str(df["award_date"].min()),
            "latest": str(df["award_date"].max())
        },
        "categories": df["category"].value_counts().to_dict(),
        "data_note": (
            "25 synthetic records generated to be statistically consistent "
            "with publicly known GeM laptop procurement price ranges. "
            "GeM public order data requires authenticated login for "
            "individual order details."
        )
    }

    logger.info(f"Historical data valid: {len(df)} records")
    return report


def validate_vendor_profiles(
    profiles_path: str = "data/vendor_profiles.json"
) -> dict:
    """Validates vendor profiles are present and well-formed."""
    if not os.path.exists(profiles_path):
        return {"valid": False, "error": "File not found"}

    with open(profiles_path) as f:
        vendors = json.load(f)

    required_fields = [
        "vendor_id", "name", "annual_turnover_lakhs",
        "is_msme", "certifications"
    ]

    issues = []
    for v in vendors:
        missing = [f for f in required_fields if f not in v]
        if missing:
            issues.append(f"{v.get('name', 'Unknown')}: missing {missing}")

    return {
        "valid": len(issues) == 0,
        "vendor_count": len(vendors),
        "vendors": [v["name"] for v in vendors],
        "issues": issues
    }


def run_data_pipeline_validation() -> dict:
    """
    Master validation function — checks all data sources.
    Run this before starting the main pipeline to catch missing files early.
    """
    logger.info("Running Data Pipeline Validation")

    report = {
        "timestamp": datetime.now().isoformat(),
        "tender_files": validate_tender_files(),
        "historical_data": validate_historical_data(),
        "vendor_profiles": validate_vendor_profiles()
    }

    all_valid = (
        len(report["tender_files"]["missing"]) == 0 and
        len(report["tender_files"]["unreadable"]) == 0 and
        report["historical_data"]["valid"] and
        report["vendor_profiles"]["valid"]
    )

    report["pipeline_ready"] = all_valid

    if all_valid:
        logger.info("ALL DATA SOURCES VALID — pipeline ready to run")
    else:
        logger.error("DATA VALIDATION FAILED — check report for details")

    return report

if __name__ == "__main__":
    report = run_data_pipeline_validation()
    print("\n DATA PIPELINE VALIDATION")
    print(f"Pipeline Ready: {report['pipeline_ready']}")
    print(f"\nTender Files:")
    print(f"  Valid: {len(report['tender_files']['valid'])}")
    print(f"  Missing: {report['tender_files']['missing']}")
    print(f"\nHistorical Data:")
    hd = report['historical_data']
    if hd['valid']:
        print(f"  Records: {hd['total_records']}")
        print(f"  Price range: ₹{hd['price_range']['min']:,} – ₹{hd['price_range']['max']:,}")
    print(f"\nVendor Profiles:")
    print(f"  Count: {report['vendor_profiles']['vendor_count']}")
    print(f"  Vendors: {report['vendor_profiles']['vendors']}")