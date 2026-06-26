# Component B
import json
import logging
import re
import os
from typing import Optional
from dotenv import load_dotenv
import pdfplumber
from pydantic import BaseModel, ValidationError, field_validator
from groq import Groq

# Load environment variables from .env file
load_dotenv()

# Set up logging — this is how we trace what happened at each step
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# SECTION 1: PDF TEXT EXTRACTION

def extract_tender_text(pdf_path: str) -> str:
    """
    Reads a PDF page by page and returns all text as one string.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")
    
    full_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        logger.info(f"Opened PDF: {pdf_path} ({len(pdf.pages)} pages)")
        
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            
            if page_text:
                full_text += f"\n--- PAGE {page_num} ---\n"
                full_text += page_text
            else:
                # Some pages are scanned images — pdfplumber returns None
                logger.warning(f"Page {page_num} returned no text (may be scanned image)")
    
    logger.info(f"Extracted {len(full_text)} characters from PDF")
    return full_text



# SECTION 2: PYDANTIC SCHEMA

class TenderRequirements(BaseModel):
    """
    Structured representation of a tender's compliance requirements.
    Every field has a type — Pydantic enforces this at runtime.
    Optional fields handle cases where the PDF doesn't mention something.
    """
    bid_number: str
    item_category: str
    
    # Turnover — Optional because some tenders reference external spec docs
    minimum_turnover_lakhs: Optional[float] = None
    
    # Relaxations — who gets exemptions
    mse_relaxation: bool = False
    startup_relaxation: bool = False
    
    # Purchase preferences — regulatory bonuses for local/MSME suppliers
    mii_purchase_preference: bool = False
    mii_price_band_percent: Optional[float] = None   # e.g. 20.0 means L1+20%
    mii_max_quantity_percent: Optional[float] = None  # e.g. 50.0 means up to 50% of order
    
    mse_purchase_preference: bool = False
    mse_price_band_percent: Optional[float] = None   # e.g. 15.0 means L1+15%
    mse_max_quantity_percent: Optional[float] = None
    
    # Documents and certifications required
    required_certifications: list[str] = []
    oem_authorization_required: bool = False
    emd_required: bool = False
    
    # Other terms
    warranty_years: Optional[int] = None
    delivery_days: Optional[int] = None

    @field_validator('minimum_turnover_lakhs')
    @classmethod
    def turnover_must_be_positive(cls, v):
        """
        Business rule validation.
        If LLM returns a negative number, Pydantic calls this and raises an error.
        We catch that error in the hardening layer below.
        """
        if v is not None and v < 0:
            raise ValueError(f"Turnover cannot be negative, got: {v}")
        return v

    @field_validator('mii_price_band_percent', 'mse_price_band_percent')
    @classmethod
    def price_band_must_be_reasonable(cls, v):
        """
        GeM price bands are legally defined: MII=20%, MSE=15%.
        If LLM hallucinates 200%, something went wrong.
        """
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"Price band percent must be 0-100, got: {v}")
        return v



# SECTION 3: LLM EXTRACTION

def extract_requirements_with_llm(tender_text: str) -> str:
    """
    Sends tender text to Groq LLM and asks for structured JSON extraction.
    Returns raw string — validation happens separately in the hardening layer.
    
    Why return raw string instead of parsed JSON here?
    So the hardening layer can handle malformed JSON gracefully.
    """
    client = Groq()  # automatically reads GROQ_API_KEY from environment
    
    # Government PDFs are long but the eligibility info is usually in first few pages
    truncated_text = tender_text[:8000]
    
    prompt = f"""You are a government procurement document parser for India's GeM portal.

Extract the compliance requirements from this tender document and return ONLY a valid JSON object.
No explanation, no markdown code blocks, no extra text — just the raw JSON.

Required JSON structure:
{{
  "bid_number": "string (e.g. GEM/2026/B/7553726)",
  "item_category": "string",
  "minimum_turnover_lakhs": number or null,
  "mse_relaxation": true or false,
  "startup_relaxation": true or false,
  "mii_purchase_preference": true or false,
  "mii_price_band_percent": number or null,
  "mii_max_quantity_percent": number or null,
  "mse_purchase_preference": true or false,
  "mse_price_band_percent": number or null,
  "mse_max_quantity_percent": number or null,
  "required_certifications": ["list", "of", "strings"],
  "oem_authorization_required": true or false,
  "emd_required": true or false,
  "warranty_years": number or null,
  "delivery_days": number or null
}}

Rules:
- For mse_relaxation: true means MSEs are EXEMPT from turnover/experience criteria
- For mii_price_band_percent: extract the X from "L1+X%" for MII preference
- For mse_price_band_percent: extract the X from "L1+X%" for MSE preference  
- For required_certifications: include ISO9001, OEM_Authorization, etc if mentioned
- If a value is not mentioned anywhere in the document, use null for numbers and false for booleans

TENDER DOCUMENT:
{truncated_text}"""

    logger.info("Sending tender text to LLM for extraction...")
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0  # deterministic — same input always gives same output
    )
    
    raw_output = response.choices[0].message.content
    logger.info(f"LLM returned {len(raw_output)} characters")
    return raw_output



# SECTION 4: THE HARDENING LAYER

def parse_and_validate_llm_output(
    raw_output: str,
    fallback_bid_number: str = "UNKNOWN",
    fallback_category: str = "UNKNOWN"
) -> TenderRequirements:
    """
    Attempts to parse LLM output into a validated TenderRequirements object.
    Falls through multiple recovery attempts before using hardcoded defaults.
    
    Recovery hierarchy:
    1. Direct JSON parse (LLM behaved perfectly)
    2. Strip markdown fences and retry
    3. Regex extract JSON block from surrounding text
    4. Conservative fallback defaults (never crash)
    """
    
    # --- Attempt 1: Direct parse ---
    # Best case: LLM returned clean JSON exactly as asked
    try:
        data = json.loads(raw_output.strip())
        requirements = TenderRequirements(**data)
        logger.info("SUCCESS: LLM output parsed and validated directly")
        return requirements
    except json.JSONDecodeError:
        logger.warning("Attempt 1 failed: not valid JSON. Trying markdown strip...")
    except ValidationError as e:
        logger.warning(f"Attempt 1 failed: Pydantic validation error: {e}")
    
    # --- Attempt 2: Strip markdown code fences ---
    # LLMs often return: ```json\n{...}\n```
    # We strip the fences and retry
    try:
        cleaned = re.sub(r'```(?:json)?\s*', '', raw_output)
        cleaned = cleaned.replace('```', '').strip()
        data = json.loads(cleaned)
        requirements = TenderRequirements(**data)
        logger.info("SUCCESS: Parsed after stripping markdown fences")
        return requirements
    except (json.JSONDecodeError, ValidationError):
        logger.warning("Attempt 2 failed. Trying regex JSON extraction...")
    
    # --- Attempt 3: Regex extract JSON block ---
    # LLM may have said "Here is the JSON: {...} Hope this helps!"
    # We find the {...} block using regex
    try:
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw_output, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            requirements = TenderRequirements(**data)
            logger.info("SUCCESS: Extracted JSON block via regex")
            return requirements
    except (json.JSONDecodeError, ValidationError):
        logger.warning("Attempt 3 failed. Using fallback defaults.")
    
    # --- Attempt 4: Conservative fallback ---
    # All recovery failed. Log clearly and return safe defaults.
    # Better to be conservative (stricter requirements) than to pass bad vendors.
    logger.error("ALL PARSE ATTEMPTS FAILED. Using conservative fallback defaults.")
    logger.error(f"Raw LLM output was: {raw_output[:200]}...")
    
    return TenderRequirements(
        bid_number=fallback_bid_number,
        item_category=fallback_category,
        minimum_turnover_lakhs=100.0,    # conservative default
        mse_relaxation=False,
        mii_purchase_preference=False,
        mse_purchase_preference=False,
        required_certifications=["GeM_registered"],
        oem_authorization_required=False,
        emd_required=False
    )

# SECTION 5: DETERMINISTIC COMPLIANCE CHECK

def check_vendor_compliance(vendor: dict, requirements: TenderRequirements) -> dict:
    """
    Checks a vendor profile against extracted tender requirements.
    
    Returns a structured result with:
    - is_compliant: bool (hard pass/fail)
    - failures: list of disqualifying issues
    - warnings: list of non-disqualifying notes
    - preferences: list of regulatory advantages the vendor qualifies for
    """
    result = {
        "vendor_id": vendor["vendor_id"],
        "vendor_name": vendor["name"],
        "is_compliant": True,
        "failures": [],
        "warnings": [],
        "preferences": []
    }
    
    # --- Check 1: Minimum Turnover ---
    # MSE vendors may be exempt if mse_relaxation is True
    if requirements.minimum_turnover_lakhs is not None:
        is_exempt = vendor.get("is_msme") and requirements.mse_relaxation
        
        if not is_exempt:
            if vendor["annual_turnover_lakhs"] < requirements.minimum_turnover_lakhs:
                result["is_compliant"] = False
                result["failures"].append(
                    f"Turnover ₹{vendor['annual_turnover_lakhs']}L is below "
                    f"required ₹{requirements.minimum_turnover_lakhs}L"
                )
        else:
            result["warnings"].append(
                "Turnover check waived — vendor is MSE and MSE relaxation applies"
            )
    else:
        result["warnings"].append(
            "Turnover requirement not found in document — manual verification needed"
        )
    
    # --- Check 2: Required Certifications ---
    vendor_certs = set(vendor.get("certifications", []))
    required_certs = set(requirements.required_certifications)
    missing = required_certs - vendor_certs
    
    if missing:
        result["is_compliant"] = False
        result["failures"].append(f"Missing required certifications: {missing}")
    
    # --- Check 3: OEM Authorization ---
    if requirements.oem_authorization_required and not vendor.get("is_oem"):
        result["is_compliant"] = False
        result["failures"].append(
            "OEM Authorization Certificate required but vendor is not an OEM"
        )
    
    # --- Check 4: Local Supplier Class (MII Order) ---
    # This tender requires Class 1 or Class 2 local suppliers only
    # Non-local suppliers cannot participate (except MSEs)
    vendor_class = vendor.get("is_local_supplier_class")
    if vendor_class not in [1, 2]:
        if not vendor.get("is_msme"):
            result["is_compliant"] = False
            result["failures"].append(
                "Tender requires Class 1 or Class 2 local supplier "
                "(min 20% local content). Vendor does not qualify."
            )
        else:
            result["warnings"].append(
                "Vendor is not Class 1/2 local supplier but is MSME — eligible as exception"
            )
    
    # --- Preference Checks (non-disqualifying, but affect win probability) ---
    
    # MII Purchase Preference
    if requirements.mii_purchase_preference and vendor.get("msme_type") == "MII":
        local_pct = vendor.get("local_content_percent", 0)
        if local_pct >= 50:
            mii_band = f"{requirements.mii_price_band_percent}%" if requirements.mii_price_band_percent else "standard band (check tender)"
            mii_qty = f"{requirements.mii_max_quantity_percent}%" if requirements.mii_max_quantity_percent else "partial"
            result["preferences"].append(
                f"Eligible for MII purchase preference (Class 1, {local_pct}% local content). "
                f"Can bid up to L1+{mii_band} and still win "
                f"up to {mii_qty} of order quantity."
            )
        elif local_pct >= 20:
            result["preferences"].append(
                f"Eligible for MII Class 2 preference ({local_pct}% local content)."
            )
    
    # MSE Purchase Preference
    if requirements.mse_purchase_preference and vendor.get("is_msme"):
        mse_band = f"{requirements.mse_price_band_percent}%" if requirements.mse_price_band_percent else "standard band (check tender)"
        mse_qty = f"{requirements.mse_max_quantity_percent}%" if requirements.mse_max_quantity_percent else "partial"
        result["preferences"].append(
            f"Eligible for MSE purchase preference. "
            f"If within L1+{mse_band}, "
            f"can match L1 price and win {mse_qty} of quantity."
        )
    
    return result



# SECTION 6: MASTER PIPELINE FUNCTION
# Ties everything together. Takes a PDF path + vendor list, returns full matrix.

def run_compliance_pipeline(pdf_path: str, vendor_profiles_path: str) -> dict:
    """
    End-to-end compliance check for all vendors against one tender.
    This is what gets called from the Streamlit UI or CLI.
    """
    logger.info(f"=== Starting compliance pipeline for: {pdf_path} ===")
    
    # Step 1: Extract text from PDF
    tender_text = extract_tender_text(pdf_path)
    
    # Step 2: LLM extracts requirements
    raw_llm_output = extract_requirements_with_llm(tender_text)
    
    # Step 3: Validate and harden LLM output
    requirements = parse_and_validate_llm_output(raw_llm_output)
    
    logger.info(f"Extracted requirements: {requirements.model_dump()}")
    
    # Step 4: Load vendor profiles
    with open(vendor_profiles_path) as f:
        vendors = json.load(f)
    
    # Step 5: Check each vendor deterministically
    compliance_results = []
    for vendor in vendors:
        result = check_vendor_compliance(vendor, requirements)
        compliance_results.append(result)
        
        status = "PASS" if result["is_compliant"] else "FAIL"
        logger.info(f"Vendor {vendor['name']}: {status}")
    
    return {
        "tender_requirements": requirements.model_dump(),
        "compliance_results": compliance_results
    }


# testing
if __name__ == "__main__":
    # Test on all five PDFs
    for pdf_name in ["laptop_1.pdf", "laptop_2.pdf", "laptop_3.pdf" , "laptop_4.pdf", "bollard_1.pdf"]:
        print(f"\n{'='*50}")
        result = run_compliance_pipeline(
            pdf_path=f"data/raw_tenders/{pdf_name}",
            vendor_profiles_path="data/vendor_profiles.json"
        )
        print(f"\n- COMPLIANCE MATRIX -")
        print(f"\nTender: {result['tender_requirements']['bid_number']}")
        print(f"Category: {result['tender_requirements']['item_category']}")
        print(f"MSE Preference: {result['tender_requirements']['mse_purchase_preference']}")
        print(f"MII Preference: {result['tender_requirements']['mii_purchase_preference']}")
        print(f"MSE Band: {result['tender_requirements']['mse_price_band_percent']}%")
        print(f"MII Band: {result['tender_requirements']['mii_price_band_percent']}%")
        print("\nVendor Results:")
        for r in result["compliance_results"]:
            status = "✓ PASS" if r["is_compliant"] else "✗ FAIL"
            print(f"\n  {r['vendor_name']}: {status}")
            for f in r["failures"]:
                print(f"     {f}")
            for w in r["warnings"]:
                print(f"     {w}")
            for p in r["preferences"]:
                print(f"     {p}")