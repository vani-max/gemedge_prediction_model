# GemEdge Procurement Intelligence Engine
 
A production-grade procurement intelligence prototype for India's **Government e-Marketplace (GeM)** portal. Built as part of the GemEdge Core Systems Engineering Challenge.
 
---
 
## What This Does
 
Government procurement in India involves thousands of active tenders across GeM. Businesses — especially MSMEs — struggle to answer three critical questions before bidding:
 
1. **Am I eligible?** Does my company meet the turnover, certification, and regulatory requirements?
2. **What price should I quote?** What have similar contracts historically gone for?
3. **What are my chances?** Given my price and the competition, what is my win probability?
This engine answers all three questions automatically from a tender PDF, historical contract data, and a vendor profile.
 
---
 
## Architecture — 4-Component Pipeline
 
```
┌─────────────────────────────────────────────────────────────┐
│                    GemEdge Engine Pipeline                   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Component A  │ Component B  │ Component C  │ Component D    │
│ Data         │ Compliance   │ L1 Price     │ Win            │
│ Pipeline     │ Engine       │ Prediction   │ Probability    │
│              │              │              │                │
│ Validates    │ LLM parses   │ IQR outlier  │ Mathematical   │
│ all data     │ tender PDF   │ removal +    │ scoring with   │
│ sources      │ → Pydantic   │ Linear       │ GeM regulatory │
│ exist and    │ → Pure       │ Regression   │ modifiers      │
│ are valid    │ Python check │ blend        │ (MSE/MII)      │
└──────────────┴──────────────┴──────────────┴────────────────┘
                                    │
                          ┌─────────▼──────────┐
                          │   Streamlit UI      │
                          │  Select tender →    │
                          │  Select vendor →    │
                          │  Enter bid price →  │
                          │  Full analysis      │
                          └─────────────────────┘
```
 
**Core Design Philosophy:** The LLM is used exclusively for unstructured text parsing (Component B extraction). All compliance decisions, price calculations, and probability scores are deterministic Python — auditable, reproducible, and never hallucinated.
 
---
 
## Project Structure
 
```
gemedge_engine/
├── data_pipeline.py          # Component A — data validation & audit trail
├── compliance_engine.py      # Component B — LLM extraction + compliance check
├── pricing_model.py          # Component C — L1 price prediction
├── win_probability.py        # Component D — win probability scoring
├── app.py                    # Streamlit dashboard UI
├── tests/
│   └── test_win_probability.py  # Automated test suite (6 tests)
├── data/
│   ├── raw_tenders/          # Downloaded tender PDFs from GeM portal
│   │   ├── laptop_1.pdf      # GEM/2026/B/7553726 — Entry/Mid Laptop
│   │   ├── laptop_2.pdf      # GEM/2026/B/7704471 — High End Laptop
│   │   ├── laptop_3.pdf      # GEM/2026/B/7708073 — Rental Laptop
│   │   ├── laptop_4.pdf      # GEM/2026/B/7706864 — Laptop Express Card
│   │   └── bollard_1.pdf     # GEM/2025/B/5902895 — K4 Crash Bollard
│   ├── historical_awards.csv # 25 historical contract records
│   └── vendor_profiles.json  # 3 dummy vendor profiles
├── .env                      # GROQ_API_KEY (not committed)
├── requirements.txt
└── README.md
```
 
---
 
## Quickstart
 
### 1. Clone and install
 
```bash
git clone https://github.com/vani-max/gemedge-engine
cd gemedge-engine
pip install -r requirements.txt
```
 
### 2. Set up environment
 
Create a `.env` file in the root directory:
 
```
GROQ_API_KEY=your_groq_api_key_here
```
 
Get a free API key at [console.groq.com](https://console.groq.com) — no payment required.
 
### 3. Validate data pipeline
 
```bash
python data_pipeline.py
```
 
Expected output:
```
Pipeline Ready: True
Tender Files: Valid: 5, Missing: []
Historical Data: Records: 25
Vendor Profiles: Count: 3
```
 
### 4. Run the full test suite
 
```bash
pytest tests/ -v
```
 
Expected output:
```
tests/test_win_probability.py::test_monotonic_decrease_with_price PASSED
tests/test_win_probability.py::test_non_compliant_vendor_gets_zero PASSED
tests/test_win_probability.py::test_msme_outperforms_non_msme_at_same_price PASSED
tests/test_win_probability.py::test_probability_bounds PASSED
tests/test_win_probability.py::test_more_competitors_reduces_probability PASSED
tests/test_win_probability.py::test_invalid_inputs_raise_errors PASSED
6 passed in 0.03s
```
 
### 5. Launch the dashboard
 
```bash
streamlit run app.py
```
 
Opens at `http://localhost:8501`
 
---
 
## Component Details
 
### Component A — Data Pipeline (`data_pipeline.py`)
 
Validates all data sources before the pipeline runs. Acts as the system's health check and audit trail.
 
- Verifies all 5 tender PDFs exist and are readable via `pdfplumber`
- Validates `historical_awards.csv` has required columns and non-null prices
- Validates `vendor_profiles.json` has all required fields
- Returns a structured validation report with `pipeline_ready: bool`
Run independently: `python data_pipeline.py`
 
---
 
### Component B — Compliance Engine (`compliance_engine.py`)
 
The most critical component. Determines whether a vendor is legally eligible to bid.
 
**Pipeline:**
```
PDF → pdfplumber text extraction
    → Groq LLM (Llama 3.3 70B, temperature=0) extracts JSON
    → Pydantic TenderRequirements schema validates output
    → 3-stage hardening layer catches malformed/hallucinated output
    → Pure Python deterministic compliance check
    → Structured result: PASS/FAIL with specific reasons
```
 
**Why temperature=0?**
Compliance decisions in government procurement must be reproducible. The same tender PDF must always produce the same extracted requirements. Any temperature > 0 introduces randomness that could cause different compliance outcomes on identical inputs.
 
**The hardening layer — 3 recovery attempts:**
1. Direct JSON parse (LLM behaved perfectly)
2. Strip markdown fences (` ```json ``` `) and retry
3. Regex extract JSON block from surrounding text
4. Conservative fallback defaults if all attempts fail — system never crashes
**Checks performed:**
- Minimum annual turnover (with MSE relaxation if applicable)
- Required certifications (ISO 9001, OEM Authorization)
- Local supplier class (Class 1/2 per MII Order)
- EMD/bid security requirements
- MSE/MII purchase preference eligibility
Run independently: `python compliance_engine.py`
 
---
 
### Component C — L1 Price Prediction (`pricing_model.py`)

`historical_awards.csv` contains 25 records across the laptop category.

**Real records (collected from public GeM bid result pages):**
Bid result pages at `bidplus.gem.gov.in/bidding/bid/getBidResultView/`
are publicly accessible without authentication, showing L1/L2/L3
prices for completed RAs. 8 records were collected directly from
these pages (GEM/2026/R/686608, GEM/2026/R/686211, GEM/2026/R/684994,
GEM/2026/B/7503143, GEM/2026/B/7687612, GEM/2026/B/7563697,
GEM/2025/R/685299, GEM/2026/R/684157).

**Synthetic records:**
17 records were generated with realistic gem_ref_numbers and
statistically consistent prices based on the observed real data
distribution (₹36,900–₹5,23,110 raw range, ₹38,000–₹80,000
after IQR outlier removal). Product names, buyer types, and
bidder counts reflect actual GeM procurement patterns.

The IQR outlier removal in pricing_model.py correctly filters the
high-value defence procurement records (₹5.23L, ₹1.82L, ₹1.79L,
₹1.52L) leaving a clean entry/mid-level laptop baseline for prediction.
 
Predicts the likely winning (L1) bid price using historical contract data.
 
**Two-layer approach:**
 
**Layer 1 — Data sanitization (IQR outlier removal)**
 
GeM bidding data contains predatory pricing (₹1 bids), data entry errors, and emergency procurement outliers. These are removed using the IQR (Interquartile Range) method:
 
```
Q1 = 25th percentile price
Q3 = 75th percentile price
IQR = Q3 - Q1
Valid range = [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
```
 
IQR was chosen over standard deviation because procurement prices are right-skewed — a few very expensive outliers would inflate σ and let predatory low bids through. IQR is distribution-agnostic.
 
**Layer 2 — Prediction**
 
- Statistical baseline: median of clean data (resistant to residual skew)
- ML refinement: Linear Regression on `num_bidders` + `days_ago` features
- Final output: 60% ML + 40% statistical median blend
**Why Linear Regression over complex models?**
With 20–25 data points after outlier removal, complex models (Random Forest, XGBoost) overfit severely. Linear Regression is interpretable — the coefficient for `num_bidders` of −₹3,988 means "each additional competitor reduces the winning price by ~₹4,000", which is economically intuitive and defensible.
 
Run independently: `python pricing_model.py`
 
---
 
### Component D — Win Probability Engine (`win_probability.py`)
 
Scores a vendor's win likelihood from 0–100% using three factors:
 
```
Final = (0.6 × price_score) + (0.3 × competition_factor) + regulatory_bonus
```
 
**Price Score** — exponential decay based on bid/L1 ratio:
```python
price_score = exp(-3.0 × (vendor_bid/predicted_l1 - 1))
```
Exponential decay was chosen over linear because the penalty for being slightly above L1 is small, but being far above L1 should collapse the probability — this matches real procurement behavior.
 
**Competition Factor** — square root decay:
```python
competition_factor = 1 / sqrt(num_competitors)
```
Square root (not linear 1/n) reflects that vendors differ in quality and compliance — not all competitors have equal odds.
 
**Regulatory Bonus** — additive, based on GeM policy:
- MII (Make in India) Class 1: +0.15
- MSE (Micro/Small Enterprise): +0.10
- General MSME: +0.05
Additive (not weighted) because MSE/MII preference is a legal entitlement that exists independently of price competitiveness.
 
**Hard gate:** Non-compliant vendors (failed Component B) receive exactly 0% regardless of bid price.
 
**Monotonicity guarantee:** Automated tests verify that as bid price increases, win probability strictly decreases — a required property for any valid bidding model.
 
Run independently: `python win_probability.py`
 
---
 
## Data Sources
 
### Tender Documents (Component A/B)
 
5 real tender PDFs downloaded directly from `bidplus.gem.gov.in`:
 
| File | Bid Number | Category | Buyer |
|------|-----------|----------|-------|
| laptop_1.pdf | GEM/2026/B/7553726 | Entry/Mid Laptop | Indian Army |
| laptop_2.pdf | GEM/2026/B/7704471 | High End Laptop | — |
| laptop_3.pdf | GEM/2026/B/7708073 | Rental Laptop | — |
| laptop_4.pdf | GEM/2026/B/7706864 | Laptop Express Card | — |
| bollard_1.pdf | GEM/2025/B/5902895 | K4 Crash Bollard | Indian Army |
 
### Historical Contract Data (Component C)
 
GeM's public order data requires authenticated login for individual order-level pricing. The public statistics portal (`gem.gov.in/statistics`) provides only aggregate figures. Bid result pages (`bidplus.gem.gov.in/bidding/bid/getBidResultView/`) show L1/L2/L3 prices for completed RAs but are category-diverse and sparse for laptops specifically.
 
`historical_awards.csv` contains 25 records generated to be statistically consistent with publicly known GeM laptop procurement price ranges (₹35,000–₹1,30,000) and observed bidder density patterns (3–18 bidders per lot). This is standard practice for prototype development prior to production data pipeline establishment.
 
---
 
## Vendor Profiles
 
Three dummy profiles designed to produce varied compliance outcomes:
 
| Vendor | Turnover | MSME | OEM | Local Class | Expected Result |
|--------|----------|------|-----|-------------|-----------------|
| TechSupply India | ₹120L | MSE | Yes | 1 (55%) | PASS most tenders |
| GlobalTech Solutions | ₹28L | No | No | 2 (22%) | FAIL most tenders |
| BharatMake Electronics | ₹300L | MII | Yes | 1 (68%) | PASS + strong preferences |
 
---
 
## Test Suite
 
```bash
pytest tests/ -v
```
 
| Test | What it verifies |
|------|-----------------|
| `test_monotonic_decrease_with_price` | Win probability strictly decreases as bid price increases |
| `test_non_compliant_vendor_gets_zero` | Component B → Component D hard gate works |
| `test_msme_outperforms_non_msme_at_same_price` | Regulatory bonus correctly applied |
| `test_probability_bounds` | Output always in [0, 100] for any inputs |
| `test_more_competitors_reduces_probability` | Competition factor behaves correctly |
| `test_invalid_inputs_raise_errors` | System fails loudly on bad input |
 
---
 
## Key Design Decisions
 
| Decision | Rationale |
|----------|-----------|
| LLM only for text parsing | All evaluative logic is deterministic Python — auditable and never hallucinates a compliance decision |
| Pydantic for schema validation | First line of defense against hallucinated values — wrong types raise errors before reaching business logic |
| 3-stage fallback in hardening layer | LLMs fail in predictable ways (markdown fences, extra text, bad values) — all handled gracefully |
| IQR over std deviation for outliers | Distribution-agnostic — procurement prices are right-skewed, not normally distributed |
| Linear Regression over complex ML | 20 data points after cleaning — complex models overfit. LR coefficients are interpretable and defensible |
| Median over mean for price baseline | Resistant to residual skew after outlier removal |
| Additive regulatory bonus | MSE/MII preference is a legal policy instrument, not a scoring weight |
| Monotonicity test | Required property for any valid bidding model — verified automatically |
 
---
 
## Requirements
 
```
pdfplumber
pydantic>=2.0.0
groq
python-dotenv
pandas
numpy
scikit-learn
streamlit
pytest
```
 
Install: `pip install -r requirements.txt`
 
Python 3.10+ required.
 
---
