"""
Automated test suite for the Win Probability Engine.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from win_probability import calculate_win_probability

# TEST 1: MONOTONIC CONSISTENCY — THE REQUIRED TEST

def test_monotonic_decrease_with_price():
    """
    Core invariant: higher bid = lower win probability, always.
    Tests across a wide range from 20% below L1 to 60% above L1.
    """
    base_params = {
        "predicted_l1": 47159.0,
        "num_competitors": 8,
        "is_msme": False,
        "msme_type": None,
        "is_compliant": True
    }

    bid_prices = [
        37727,   # 20% below L1
        42443,   # 10% below L1
        47159,   # exactly at L1
        51875,   # 10% above L1
        56591,   # 20% above L1
        61307,   # 30% above L1
        70739,   # 50% above L1
        75454,   # 60% above L1
    ]

    probabilities = [
        calculate_win_probability(bid, **base_params)["win_probability"]
        for bid in bid_prices
    ]

    print("\nMonotonicity check:")
    for price, prob in zip(bid_prices, probabilities):
        print(f"  Bid ₹{price:,} → {prob}%")

    # Strict monotonic decrease
    for i in range(len(probabilities) - 1):
        assert probabilities[i] >= probabilities[i + 1], (
            f"MONOTONICITY VIOLATED at index {i}:\n"
            f"  P(bid=₹{bid_prices[i]:,}) = {probabilities[i]}%\n"
            f"  P(bid=₹{bid_prices[i+1]:,}) = {probabilities[i+1]}%\n"
            f"  Expected {probabilities[i]}% >= {probabilities[i+1]}%"
        )

# TEST 2: NON-COMPLIANT VENDOR ALWAYS GETS ZERO
def test_non_compliant_vendor_gets_zero():
    result = calculate_win_probability(
        vendor_bid=40000,
        predicted_l1=47159.0,
        num_competitors=5,
        is_msme=True,
        msme_type="MSE",
        is_compliant=False  # failed compliance
    )
    assert result["win_probability"] == 0.0, (
        f"Non-compliant vendor should get 0% but got {result['win_probability']}%"
    )

# TEST 3: MSME VENDOR BEATS NON-MSME AT SAME BID
# Regulatory bonus must translate into higher probability.

def test_msme_outperforms_non_msme_at_same_price():
    shared_params = {
        "vendor_bid": 47159.0,
        "predicted_l1": 47159.0,
        "num_competitors": 8,
        "is_compliant": True
    }

    mse_result = calculate_win_probability(
        **shared_params, is_msme=True, msme_type="MSE"
    )
    mii_result = calculate_win_probability(
        **shared_params, is_msme=True, msme_type="MII"
    )
    non_msme_result = calculate_win_probability(
        **shared_params, is_msme=False, msme_type=None
    )

    assert mse_result["win_probability"] > non_msme_result["win_probability"], (
        "MSE vendor should have higher probability than non-MSME at same price"
    )
    assert mii_result["win_probability"] > mse_result["win_probability"], (
        "MII vendor should have higher probability than MSE vendor at same price"
    )

# TEST 4: PROBABILITY ALWAYS WITHIN [0, 100]

def test_probability_bounds():
    # Test extreme low bid
    result_low = calculate_win_probability(
        vendor_bid=1,
        predicted_l1=47159.0,
        num_competitors=1,
        is_msme=True,
        msme_type="MII",
        is_compliant=True
    )
    assert 0 <= result_low["win_probability"] <= 100

    # Test extreme high bid
    result_high = calculate_win_probability(
        vendor_bid=9999999,
        predicted_l1=47159.0,
        num_competitors=100,
        is_msme=False,
        msme_type=None,
        is_compliant=True
    )
    assert 0 <= result_high["win_probability"] <= 100

# TEST 5: MORE COMPETITORS = LOWER PROBABILITY

def test_more_competitors_reduces_probability():
    shared_params = {
        "vendor_bid": 47159.0,
        "predicted_l1": 47159.0,
        "is_msme": False,
        "msme_type": None,
        "is_compliant": True
    }

    results = {
        n: calculate_win_probability(num_competitors=n, **shared_params)["win_probability"]
        for n in [1, 3, 5, 10, 20]
    }

    print("\nCompetition effect:")
    for n, prob in results.items():
        print(f"  {n} competitors → {prob}%")

    competitor_counts = sorted(results.keys())
    for i in range(len(competitor_counts) - 1):
        n1, n2 = competitor_counts[i], competitor_counts[i + 1]
        assert results[n1] >= results[n2], (
            f"More competitors should reduce probability: "
            f"P({n1} competitors)={results[n1]}% should >= P({n2})={results[n2]}%"
        )

# TEST 6: INVALID INPUTS RAISE ERRORS

def test_invalid_inputs_raise_errors():
    with pytest.raises((ValueError, ZeroDivisionError)):
        calculate_win_probability(
            vendor_bid=0,  # invalid
            predicted_l1=47159.0,
            num_competitors=5,
            is_msme=False,
            is_compliant=True
        )