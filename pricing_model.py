"""
pricing_model.py

Component C of the GemEdge engine.
Responsibility: Given historical contract award data, predict the likely
L1 (lowest winning) price for an active tender.

Two-layer approach:
1. Data sanitization — remove outliers before any calculation
2. Prediction — statistical baseline + ML refinement if enough data

Key design principle: prediction is always accompanied by a confidence
interval and a clear count of how many data points were used.
This makes the output auditable and honest.
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SECTION 1: DATA LOADING

def load_historical_data(csv_path: str) -> pd.DataFrame:
    """
    Loads and does basic cleaning on the historical awards CSV.
    
    Why separate from outlier removal?
    Loading/cleaning is about data integrity (missing values, wrong types).
    Outlier removal is a business decision about what's a valid price.
    Mixing them makes both harder to debug.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found at: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Convert date column to datetime for recency calculations later
    df['award_date'] = pd.to_datetime(df['award_date'], format='mixed', dayfirst=False)
    
    # Drop rows where the price itself is missing — unusable for prediction
    original_len = len(df)
    df = df.dropna(subset=['l1_price'])
    dropped = original_len - len(df)
    
    if dropped > 0:
        logger.warning(f"Dropped {dropped} rows with missing l1_price")
    
    # Ensure numeric columns are actually numeric
    # pd.to_numeric with errors='coerce' turns bad values into NaN
    # instead of crashing — safer for real-world messy data
    df['l1_price'] = pd.to_numeric(df['l1_price'], errors='coerce')
    df['num_bidders'] = pd.to_numeric(df['num_bidders'], errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    
    # Drop any rows that became NaN after coercion
    df = df.dropna(subset=['l1_price'])
    
    logger.info(f"Loaded {len(df)} valid records from {csv_path}")
    return df


# SECTION 2: OUTLIER REMOVAL — THE GUARDRAIL
# This is the most important part of Component C.
#
# Why do outliers exist in GeM data?
# - Predatory pricing: a vendor quotes ₹1 to win, planning to renegotiate
# - Data entry errors: someone typed 4500000 instead of 45000
# - Completely different product specs under same category name
# - Emergency procurement at non-market rates
#
# Why IQR and not standard deviation?
# Standard deviation assumes a normal distribution.
# Procurement prices are often right-skewed (a few very expensive outliers).
# IQR is distribution-agnostic — it just looks at the middle 50% spread.

def remove_outliers_iqr(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Removes statistical outliers using the IQR (Interquartile Range) method.
    
    How IQR works:
    - Sort all prices
    - Q1 = value at 25th percentile (bottom quarter boundary)
    - Q3 = value at 75th percentile (top quarter boundary)  
    - IQR = Q3 - Q1 (the spread of the middle 50%)
    - Lower fence = Q1 - 1.5 * IQR
    - Upper fence = Q3 + 1.5 * IQR
    - Anything outside the fences = outlier, removed
    
    The 1.5 multiplier is Tukey's standard — used in every box plot.
    It keeps ~99.3% of normally distributed data while catching true outliers.
    """
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_fence = Q1 - 1.5 * IQR
    upper_fence = Q3 + 1.5 * IQR
    
    original_count = len(df)
    clean_df = df[
        (df[column] >= lower_fence) & 
        (df[column] <= upper_fence)
    ].copy()
    
    removed = original_count - len(clean_df)
    
    logger.info(f"IQR outlier removal on '{column}':")
    logger.info(f"  Q1=₹{Q1:,.0f}, Q3=₹{Q3:,.0f}, IQR=₹{IQR:,.0f}")
    logger.info(f"  Fences: [₹{lower_fence:,.0f}, ₹{upper_fence:,.0f}]")
    logger.info(f"  Removed {removed} outliers from {original_count} records")
    logger.info(f"  Clean dataset: {len(clean_df)} records")
    
    return clean_df


# SECTION 3: STATISTICAL PREDICTION
# Always computed — this is your fallback if ML can't run.
# Median is used instead of mean because it's resistant to remaining skew.
# Even after IQR removal, distributions can be asymmetric.

def statistical_prediction(clean_df: pd.DataFrame) -> dict:
    """
    Pure statistics — no ML, no model.
    Median, mean, std, and a confidence interval.
    
    Why median over mean for the primary estimate?
    If 9 bids come in at ₹45,000 and one at ₹38,000 (aggressive bidder),
    mean pulls down toward ₹44,300 but median stays at ₹45,000.
    The median better represents what a "typical" winning price looks like.
    """
    prices = clean_df['l1_price']
    
    median_price = prices.median()
    mean_price = prices.mean()
    std_price = prices.std()
    min_price = prices.min()
    max_price = prices.max()
    
    # 90% confidence interval using 1.645 standard deviations
    # (assumes approximately normal distribution after outlier removal)
    margin = 1.645 * (std_price / np.sqrt(len(prices)))
    ci_lower = mean_price - margin
    ci_upper = mean_price + margin
    
    return {
        "method": "statistical",
        "median": round(median_price, 2),
        "mean": round(mean_price, 2),
        "std_deviation": round(std_price, 2),
        "min_observed": round(min_price, 2),
        "max_observed": round(max_price, 2),
        "confidence_interval_90": {
            "lower": round(max(0, ci_lower), 2),
            "upper": round(ci_upper, 2)
        },
        "data_points_used": len(prices)
    }


# SECTION 4: ML PREDICTION
# Linear Regression with two features: num_bidders and recency.
#
# Why these two features?
# - num_bidders: more competition drives price down (economic theory)
#   your historical data should show this correlation
# - recency (days_ago): prices change over time due to inflation,
#   component costs, market conditions — recent data is more relevant
#
# Why Linear Regression over something fancier?
# With 25 data points, complex models overfit badly.
# Linear Regression is interpretable — you can explain every coefficient.
# In the live interview they WILL ask "why not Random Forest?" and
# "coefficients show that each additional bidder reduces price by ₹X"
# is a much stronger answer than a black-box model.

def ml_prediction(clean_df: pd.DataFrame, target_specs: dict) -> dict:
    """
    Linear Regression to predict L1 price for a new tender.
    
    Features:
    - num_bidders: expected number of competing bids
    - days_ago: how many days ago was this historical contract (recency weight)
    
    StandardScaler normalizes features so coefficients are comparable.
    Without scaling, days_ago (large numbers) would dominate num_bidders (small).
    """
    df = clean_df.copy()
    
    # Calculate recency feature
    # More recent contracts = days_ago closer to 0 = more relevant
    reference_date = pd.Timestamp.now()
    df['days_ago'] = (reference_date - df['award_date']).dt.days
    
    # Select available features
    feature_cols = []
    if 'num_bidders' in df.columns:
        df['num_bidders'] = df['num_bidders'].fillna(df['num_bidders'].median())
        feature_cols.append('num_bidders')
    if 'days_ago' in df.columns:
        feature_cols.append('days_ago')
    
    if not feature_cols:
        logger.warning("No features available for ML prediction")
        return None
    
    X = df[feature_cols].values
    y = df['l1_price'].values
    
    # Scale features — critical for Linear Regression
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train model
    model = LinearRegression()
    model.fit(X_scaled, y)
    
    # Calculate training error so we can report model quality
    y_pred_train = model.predict(X_scaled)
    mae = mean_absolute_error(y, y_pred_train)
    
    # Log what the model learned — important for interview
    for i, col in enumerate(feature_cols):
        logger.info(
            f"ML coefficient for '{col}': {model.coef_[i]:.2f} "
            f"(each unit increase changes predicted price by ₹{model.coef_[i]:.2f})"
        )
    
    # Build feature vector for the target tender
    target_num_bidders = target_specs.get(
        'expected_bidders', 
        df['num_bidders'].median() if 'num_bidders' in df.columns else 8
    )
    target_days_ago = 0  # the tender we're predicting for is current
    
    target_features = []
    if 'num_bidders' in feature_cols:
        target_features.append(target_num_bidders)
    if 'days_ago' in feature_cols:
        target_features.append(target_days_ago)
    
    target_scaled = scaler.transform([target_features])
    predicted_price = float(model.predict(target_scaled)[0])
    
    return {
        "method": "linear_regression",
        "predicted_price": round(max(0, predicted_price), 2),
        "mean_absolute_error": round(mae, 2),
        "features_used": feature_cols,
        "coefficients": {
            col: round(model.coef_[i], 2) 
            for i, col in enumerate(feature_cols)
        },
        "intercept": round(float(model.intercept_), 2),
        "training_samples": len(df)
    }


# SECTION 5: MASTER PREDICTION FUNCTION
# Combines both approaches and returns a unified recommendation.

def predict_l1_price(csv_path: str, target_specs: dict) -> dict:
    """
    Full prediction pipeline for a target tender.
    
    target_specs should contain:
    - category: str (to filter historical data by category)
    - expected_bidders: int (how many competitors expected)
    
    Returns a unified dict with both statistical and ML predictions,
    plus a final recommended estimate.
    """
    logger.info("=== Starting L1 Price Prediction Pipeline ===")
    logger.info(f"Target specs: {target_specs}")
    
    # Step 1: Load all data
    df = load_historical_data(csv_path)
    
    # Step 2: Filter by category if possible
    category = target_specs.get('category', '').lower()
    if category:
        category_df = df[df['category'].str.lower().str.contains(category, na=False)]
        logger.info(f"Category filter '{category}': {len(category_df)} matching records")
    else:
        category_df = df
    
    # Fall back to all data if category filter gives too few rows
    if len(category_df) < 5:
        logger.warning(
            f"Only {len(category_df)} records for category '{category}'. "
            f"Using all {len(df)} records as fallback."
        )
        category_df = df
    
    # Step 3: Remove outliers
    clean_df = remove_outliers_iqr(category_df, 'l1_price')
    
    # Step 4: Statistical prediction (always runs)
    stats = statistical_prediction(clean_df)
    
    # Step 5: ML prediction (only if enough data)
    ml_result = None
    if len(clean_df) >= 8:
        ml_result = ml_prediction(clean_df, target_specs)
        logger.info(f"ML predicted price: ₹{ml_result['predicted_price']:,.2f}")
    else:
        logger.warning(
            f"Only {len(clean_df)} records after cleaning — "
            f"need 8+ for ML. Using statistical prediction only."
        )
    
    # Step 6: Final recommendation
    # If ML ran successfully and its error is reasonable, blend it with median
    # Otherwise use median alone
    if ml_result and ml_result['predicted_price'] > 0:
        # Weighted blend: 60% ML, 40% statistical median
        # Rationale: ML accounts for current market conditions (recency, competition)
        # but statistical median is more robust with small datasets
        recommended = (
            0.6 * ml_result['predicted_price'] + 
            0.4 * stats['median']
        )
        recommendation_method = "blended (60% ML + 40% statistical median)"
    else:
        recommended = stats['median']
        recommendation_method = "statistical median (ML unavailable)"
    
    recommended = round(recommended, 2)
    
    logger.info(f"Final recommended L1 estimate: ₹{recommended:,.2f}")
    logger.info(f"Method: {recommendation_method}")
    
    return {
        "target_specs": target_specs,
        "recommended_l1_estimate": recommended,
        "recommendation_method": recommendation_method,
        "statistical": stats,
        "ml": ml_result,
        "data_points_used": len(clean_df)
    }

# testing 

if __name__ == "__main__":
    
    # Test 1: Laptop category prediction (most of our data)
    result = predict_l1_price(
        csv_path="data/historical_awards.csv",
        target_specs={
            "category": "laptop",
            "expected_bidders": 8
        }
    )
    
    print("\n========== L1 PRICE PREDICTION ==========")
    print(f"\nCategory: {result['target_specs']['category']}")
    print(f"Data points used: {result['data_points_used']}")
    print(f"\nStatistical Prediction:")
    print(f"  Median:  ₹{result['statistical']['median']:,.2f}")
    print(f"  Mean:    ₹{result['statistical']['mean']:,.2f}")
    print(f"  Std Dev: ₹{result['statistical']['std_deviation']:,.2f}")
    print(f"  90% CI:  ₹{result['statistical']['confidence_interval_90']['lower']:,.2f}"
          f" – ₹{result['statistical']['confidence_interval_90']['upper']:,.2f}")
    
    if result['ml']:
        print(f"\nML Prediction (Linear Regression):")
        print(f"  Predicted: ₹{result['ml']['predicted_price']:,.2f}")
        print(f"  MAE:       ₹{result['ml']['mean_absolute_error']:,.2f}")
        print(f"  Features:  {result['ml']['features_used']}")
        print(f"  Coefficients: {result['ml']['coefficients']}")
    
    print(f"\n{'='*40}")
    print(f"RECOMMENDED L1 ESTIMATE: ₹{result['recommended_l1_estimate']:,.2f}")
    print(f"Method: {result['recommendation_method']}")
    print(f"{'='*40}")