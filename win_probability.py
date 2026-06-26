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
    #
    # Core idea: how does your bid compare to the predicted L1?
    #
    # price_ratio = vendor_bid / predicted_l1
    # - ratio = 0.9 means you're bidding 10% BELOW predicted L1 (aggressive)
    # - ratio = 1.0 means you're matching predicted L1 exactly
    # - ratio = 1.1 means you're bidding 10% ABOVE predicted L1 (risky)
    #
    # We use exponential decay: score = exp(-k * (ratio - 1))
    #
    # Why exponential and not linear?
    # Linear would give negative scores for high ratios.
    # Exponential naturally stays between 0 and 1.
    # It also models real bidding behavior — the penalty for being
    # slightly above L1 is small, but being far above L1 kills your chances.
    #
    # k=3.0 is the decay rate. At k=3:
    # - ratio 1.0 (at L1): score = 1.0
    # - ratio 1.1 (+10%):  score = 0.74
    # - ratio 1.2 (+20%):  score = 0.55
    # - ratio 1.5 (+50%):  score = 0.22

    price_ratio = vendor_bid / predicted_l1
    k = 3.0

    price_score = np.exp(-k * (price_ratio - 1))

    # For bids below L1 (ratio < 1), exp gives values > 1.
    # Cap at 0.95 — you can never be 100% certain of winning
    # even with the lowest price (buyer can disqualify on technical grounds)
    price_score = min(0.95, price_score)
    price_score = max(0.0, price_score)  # floor at 0

    # COMPONENT 2: COMPETITION FACTOR
    #
    # More competitors = lower probability for any single vendor.
    #
    # Why sqrt instead of 1/n (linear)?
    # With 1/n: 1 bidder=100%, 2 bidders=50%, 10 bidders=10%
    # This is too aggressive — it assumes all vendors are identical.
    # In reality, quality and compliance differences mean some vendors
    # have significantly better odds than 1/n.
    #
    # With 1/sqrt(n): 1 bidder=100%, 4 bidders=50%, 16 bidders=25%
    # This is a softer decay that better reflects real procurement outcomes.

    competition_factor = 1.0 / np.sqrt(max(1, num_competitors))

    # COMPONENT 3: REGULATORY BONUS
    #
    # GeM policy gives purchase preference to local/MSME suppliers.
    # These are LEGAL ADVANTAGES defined in government policy:
    #
    # MII (Make in India) Class 1: 20% price preference
    #   → Can bid up to L1+20% and still win up to 50% of order
    # MSE (Micro/Small Enterprise): 15% price preference
    #   → Can bid up to L1+15% and still win up to 25% of order
    #
    # We model this as a direct additive bonus to the final probability.

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
    # - Price score carries 60% weight — price is the primary factor in L1 bidding
    # - Competition carries 30% weight — more bidders genuinely reduces your odds
    # - Regulatory bonus is additive — it's a real policy advantage, not just a weight
    #
    # Final = (0.6 * price_score + 0.3 * competition_factor) + regulatory_bonus
    # Then clamped to [0, 1] and converted to percentage.
    #
    # Why additive for regulatory bonus?
    # Because MSE/MII preference is a genuine legal entitlement that
    # exists independently of price and competition.
    # A weighted average would dilute it — adding it directly reflects
    # that it's a separate policy instrument.

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