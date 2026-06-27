# Component D

import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_win_probability(
    vendor_bid: float,
    predicted_l1: float,
    num_competitors: int,
    is_msme: bool,
    msme_type: str = None,
    is_compliant: bool = True
) -> dict:
    """
    Calculates win probability for a vendor given their bid price.

    Parameters:
    - vendor_bid: the price the vendor wants to quote
    - predicted_l1: our predicted winning price from Component C
    - num_competitors: expected number of other bidders
    - is_msme: whether vendor is MSME registered
    - msme_type: "MSE", "MII", or None
    - is_compliant: whether vendor passed Component B compliance check

    Returns dict with final probability and full breakdown.
    """

    if not is_compliant:
        logger.info(f"Vendor failed compliance — win probability: 0%")
        return {
            "win_probability": 0.0,
            "reason": "Vendor did not pass compliance check",
            "breakdown": None
        }

    if vendor_bid <= 0 or predicted_l1 <= 0:
        raise ValueError("Bid price and predicted L1 must be positive")

    # COMPONENT 1: PRICE SCORE

    price_ratio = vendor_bid / predicted_l1
    k = 3.0

    price_score = np.exp(-k * (price_ratio - 1))

    # For bids below L1 (ratio < 1), exp gives values > 1.
    price_score = min(0.95, price_score)
    price_score = max(0.0, price_score)  # floor at 0

    # COMPONENT 2: COMPETITION FACTOR

    competition_factor = 1.0 / np.sqrt(max(1, num_competitors))

    # COMPONENT 3: REGULATORY BONUS

    regulatory_bonus = 0.0
    regulatory_note = "No preference applicable"

    if is_msme:
        if msme_type == "MII":
            regulatory_bonus = 0.15
            regulatory_note = "MII purchase preference (20% price band)"
        elif msme_type == "MSE":
            regulatory_bonus = 0.10
            regulatory_note = "MSE purchase preference (15% price band)"
        else:
            regulatory_bonus = 0.05
            regulatory_note = "General MSME preference"

    # FINAL COMBINATION
    # Weighted formula:
    # - Price score carries 60% weight
    # - Competition carries 30% weight
    raw_score = (
        0.6 * price_score +
        0.3 * competition_factor +
        regulatory_bonus
    )

    # Clamp to [0, 1]
    final_score = max(0.0, min(1.0, raw_score))

    # Convert to percentage
    win_probability = round(final_score * 100, 2)

    logger.info(
        f"Win Probability | "
        f"Bid: ₹{vendor_bid:,.0f} | "
        f"Ratio: {price_ratio:.3f} | "
        f"Price Score: {price_score:.3f} | "
        f"Competition: {competition_factor:.3f} | "
        f"Regulatory: {regulatory_bonus} | "
        f"Final: {win_probability}%"
    )

    return {
        "win_probability": win_probability,
        "breakdown": {
            "price_ratio": round(price_ratio, 4),
            "price_score": round(price_score, 4),
            "competition_factor": round(competition_factor, 4),
            "regulatory_bonus": regulatory_bonus,
            "regulatory_note": regulatory_note,
            "weights": {
                "price": "60%",
                "competition": "30%",
                "regulatory": "additive"
            }
        }
    }

# testing

if __name__ == "__main__":

    predicted_l1 = 47159.0  # from Component C output

    print("\n- WIN PROBABILITY ENGINE -")
    print(f"Predicted L1: ₹{predicted_l1:,.2f}")
    print(f"Competitors: 8\n")

    vendors = [
        {"name": "TechSupply India (MSE)", "bid": 44000,
         "is_msme": True, "msme_type": "MSE", "is_compliant": True},
        {"name": "BharatMake Electronics (MII)", "bid": 46000,
         "is_msme": True, "msme_type": "MII", "is_compliant": True},
        {"name": "GlobalTech Solutions", "bid": 45000,
         "is_msme": False, "msme_type": None, "is_compliant": False},
    ]

    for v in vendors:
        result = calculate_win_probability(
            vendor_bid=v["bid"],
            predicted_l1=predicted_l1,
            num_competitors=8,
            is_msme=v["is_msme"],
            msme_type=v["msme_type"],
            is_compliant=v["is_compliant"]
        )
        print(f"{v['name']} | Bid: ₹{v['bid']:,}")
        print(f"  Win Probability: {result['win_probability']}%")
        if result['breakdown']:
            print(f"  Price Score: {result['breakdown']['price_score']}")
            print(f"  Competition Factor: {result['breakdown']['competition_factor']}")
            print(f"  Regulatory Bonus: {result['breakdown']['regulatory_bonus']}")
            print(f"  Note: {result['breakdown']['regulatory_note']}")
        print()