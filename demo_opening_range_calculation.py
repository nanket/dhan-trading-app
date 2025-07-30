#!/usr/bin/env python3
"""
Demo: Opening Range OI Strategy Calculation Logic

This script demonstrates how the opening range calculation works
for different opening prices and range intervals.
"""

def calculate_opening_range(opening_price, range_interval=100):
    """
    Calculate range bounds based on opening price and interval.
    
    Args:
        opening_price: Today's opening price
        range_interval: Range interval in points
        
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    lower_bound = (int(opening_price / range_interval) * range_interval)
    upper_bound = lower_bound + range_interval
    
    return lower_bound, upper_bound


def demo_calculations():
    """Demonstrate opening range calculations."""
    
    print("🎯 Opening Range OI Strategy - Calculation Demo")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        # Today's actual case
        {"opening": 24619, "interval": 100, "description": "Today's NIFTY Opening"},
        
        # Different intervals for same opening
        {"opening": 24619, "interval": 50, "description": "50-point interval"},
        {"opening": 24619, "interval": 200, "description": "200-point interval"},
        
        # Different opening prices
        {"opening": 25440, "interval": 100, "description": "Higher opening"},
        {"opening": 23850, "interval": 100, "description": "Lower opening"},
        
        # Edge cases
        {"opening": 24600, "interval": 100, "description": "Exact boundary"},
        {"opening": 24699, "interval": 100, "description": "Near upper boundary"},
    ]
    
    print(f"{'Opening':<8} {'Interval':<8} {'Lower':<8} {'Upper':<8} {'Range':<12} {'Description'}")
    print("-" * 70)
    
    for case in test_cases:
        opening = case["opening"]
        interval = case["interval"]
        description = case["description"]
        
        lower, upper = calculate_opening_range(opening, interval)
        range_str = f"{lower}-{upper}"
        
        print(f"{opening:<8} {interval:<8} {lower:<8} {upper:<8} {range_str:<12} {description}")
    
    print("\n" + "=" * 60)
    
    # Detailed explanation for today's case
    print("📊 Detailed Calculation for Today's Opening (24619)")
    print("-" * 50)
    
    opening_price = 24619
    range_interval = 100
    
    print(f"Opening Price: {opening_price}")
    print(f"Range Interval: {range_interval}")
    print()
    
    # Step-by-step calculation
    print("Step 1: Calculate lower bound")
    print(f"  lower_bound = int({opening_price} / {range_interval}) * {range_interval}")
    print(f"  lower_bound = int({opening_price / range_interval}) * {range_interval}")
    print(f"  lower_bound = {int(opening_price / range_interval)} * {range_interval}")
    print(f"  lower_bound = {int(opening_price / range_interval) * range_interval}")
    
    print()
    print("Step 2: Calculate upper bound")
    lower_bound = int(opening_price / range_interval) * range_interval
    upper_bound = lower_bound + range_interval
    print(f"  upper_bound = lower_bound + {range_interval}")
    print(f"  upper_bound = {lower_bound} + {range_interval}")
    print(f"  upper_bound = {upper_bound}")
    
    print()
    print(f"🎯 Result: Analyze range {lower_bound} - {upper_bound}")
    
    print("\n" + "=" * 60)
    
    # Show what this means for trading
    print("💡 Trading Interpretation")
    print("-" * 30)
    print(f"• Opening Price: {opening_price}")
    print(f"• Lower Strike: {lower_bound} (Support level to watch)")
    print(f"• Upper Strike: {upper_bound} (Resistance level to watch)")
    print()
    print("Strategy Logic:")
    print("• If PE OI > CE OI at both strikes → Bullish (Support)")
    print("• If CE OI > PE OI at both strikes → Bearish (Resistance)")
    print("• If mixed signals → Neutral/Range-bound")
    
    print("\n" + "=" * 60)
    
    # Show API usage
    print("🔧 API Usage Examples")
    print("-" * 25)
    print("1. Opening Range Analysis:")
    print(f"   POST /api/strategy/opening-range-oi-analysis")
    print(f"   Params: opening_price={opening_price}, range_interval={range_interval}")
    print()
    print("2. Individual Strike Analysis:")
    print(f"   GET /api/strategy/individual-strike-oi/{lower_bound}")
    print(f"   GET /api/strategy/individual-strike-oi/{upper_bound}")
    
    print("\n" + "=" * 60)
    
    # Show different scenarios
    print("📈 Different Market Scenarios")
    print("-" * 35)
    
    scenarios = [
        {
            "name": "Strong Support",
            "24600_pe": 200000, "24600_ce": 100000,
            "24700_pe": 180000, "24700_ce": 90000,
            "signal": "BULLISH"
        },
        {
            "name": "Strong Resistance", 
            "24600_pe": 80000, "24600_ce": 150000,
            "24700_pe": 70000, "24700_ce": 160000,
            "signal": "BEARISH"
        },
        {
            "name": "Range-bound",
            "24600_pe": 150000, "24600_ce": 120000,
            "24700_pe": 90000, "24700_ce": 140000,
            "signal": "NEUTRAL"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']} Scenario:")
        print(f"  24600: PE={scenario['24600_pe']:,}, CE={scenario['24600_ce']:,}")
        print(f"  24700: PE={scenario['24700_pe']:,}, CE={scenario['24700_ce']:,}")
        print(f"  Signal: {scenario['signal']}")


if __name__ == "__main__":
    demo_calculations()
    
    print("\n🎯 Summary:")
    print("✅ Opening range calculation logic demonstrated")
    print("✅ Today's case: 24619 → 24600-24700 range")
    print("✅ Different intervals and scenarios shown")
    print("✅ API usage examples provided")
    print("✅ Trading interpretation explained")
