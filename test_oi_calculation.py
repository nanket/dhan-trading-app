#!/usr/bin/env python3
"""
Test script to verify OI change calculation accuracy.

This script tests the OI change calculation to ensure it matches official values.
Example: Strike 27700 should show 45.2% change but currently shows 40.7%
"""

def calculate_oi_change(current_oi, previous_oi):
    """
    Calculate OI change exactly as the backend does.
    
    Args:
        current_oi: Current Open Interest
        previous_oi: Previous Open Interest
        
    Returns:
        Tuple of (absolute_change, percentage_change)
    """
    absolute_change = current_oi - previous_oi
    percentage_change = (absolute_change / previous_oi * 100) if previous_oi > 0 else 0.0
    
    return absolute_change, percentage_change


def test_oi_calculations():
    """Test various OI change scenarios."""
    
    print("🧮 OI Change Calculation Test")
    print("=" * 50)
    
    # Test cases - trying to reverse engineer the 45.2% vs 40.7% discrepancy
    test_cases = [
        {
            "name": "Strike 27700 - Official 45.2%",
            "scenarios": [
                # Different possible current/previous OI combinations that could give 45.2%
                {"current": 145200, "previous": 100000, "expected": 45.2},
                {"current": 290400, "previous": 200000, "expected": 45.2},
                {"current": 72600, "previous": 50000, "expected": 45.2},
                {"current": 1452, "previous": 1000, "expected": 45.2},
            ]
        },
        {
            "name": "Strike 27700 - Current System 40.7%", 
            "scenarios": [
                # Possible combinations that give 40.7%
                {"current": 140700, "previous": 100000, "expected": 40.7},
                {"current": 281400, "previous": 200000, "expected": 40.7},
                {"current": 70350, "previous": 50000, "expected": 40.7},
            ]
        }
    ]
    
    for test_group in test_cases:
        print(f"\n📊 {test_group['name']}")
        print("-" * 40)
        
        for i, scenario in enumerate(test_group['scenarios'], 1):
            current = scenario['current']
            previous = scenario['previous']
            expected = scenario['expected']
            
            abs_change, pct_change = calculate_oi_change(current, previous)
            
            print(f"Scenario {i}:")
            print(f"  Current OI: {current:,}")
            print(f"  Previous OI: {previous:,}")
            print(f"  Calculated: {pct_change:.2f}%")
            print(f"  Expected: {expected}%")
            print(f"  Match: {'✅' if abs(pct_change - expected) < 0.01 else '❌'}")
            print()
    
    print("=" * 50)
    
    # Test rounding scenarios
    print("\n🔍 Rounding Analysis")
    print("-" * 30)
    
    # Test what happens with different rounding
    test_value = 45.23456
    
    print(f"Original value: {test_value}")
    print(f"toFixed(1): {test_value:.1f}")  # JavaScript equivalent
    print(f"toFixed(2): {test_value:.2f}")  # JavaScript equivalent
    print(f"Python round(1): {round(test_value, 1)}")
    print(f"Python round(2): {round(test_value, 2)}")
    
    # Test edge case that might cause 45.2 -> 40.7
    print(f"\nEdge case analysis:")
    print(f"If 45.2 gets truncated: {int(45.2 * 10) / 10}")
    print(f"If 40.7 is from different calculation...")
    
    # Reverse calculate what previous OI would give 40.7% for various current OI
    print(f"\nReverse calculation for 40.7%:")
    target_pct = 40.7
    for current_oi in [100000, 150000, 200000]:
        # current = previous * (1 + target_pct/100)
        # previous = current / (1 + target_pct/100)
        previous_oi = current_oi / (1 + target_pct/100)
        abs_change, calc_pct = calculate_oi_change(current_oi, previous_oi)
        print(f"  Current: {current_oi:,}, Previous: {previous_oi:.0f}, Calc: {calc_pct:.2f}%")


def test_frontend_formatting():
    """Test how the frontend formats the values."""
    
    print("\n🖥️ Frontend Formatting Test")
    print("=" * 40)
    
    # Simulate the frontend formatting logic
    def format_oi_change_old(absolute_change, percentage_change):
        """Old formatting (1 decimal place)"""
        sign = '+' if absolute_change > 0 else '-' if absolute_change < 0 else ''
        return f"{sign}{abs(absolute_change):,} ({sign}{abs(percentage_change):.1f}%)"
    
    def format_oi_change_new(absolute_change, percentage_change):
        """New formatting (2 decimal places)"""
        sign = '+' if absolute_change > 0 else '-' if absolute_change < 0 else ''
        return f"{sign}{abs(absolute_change):,} ({sign}{abs(percentage_change):.2f}%)"
    
    # Test with example values
    test_values = [
        (45200, 45.23),
        (40700, 40.67),
        (45200, 45.2),
        (40700, 40.7),
    ]
    
    print(f"{'Absolute':<10} {'Percentage':<12} {'Old Format':<20} {'New Format':<20}")
    print("-" * 70)
    
    for abs_change, pct_change in test_values:
        old_format = format_oi_change_old(abs_change, pct_change)
        new_format = format_oi_change_new(abs_change, pct_change)
        print(f"{abs_change:<10} {pct_change:<12} {old_format:<20} {new_format:<20}")


def suggest_debugging_steps():
    """Suggest steps to debug the OI calculation issue."""
    
    print("\n🔧 Debugging Steps")
    print("=" * 30)
    
    steps = [
        "1. Check the actual OI values from Dhan API for strike 27700",
        "2. Compare with official source (NSE, broker platform)",
        "3. Verify the timestamp of data (ensure same session)",
        "4. Check if there's any data preprocessing/filtering",
        "5. Verify the previous OI storage mechanism",
        "6. Test with known good data points",
        "7. Check for any rounding in the API response",
        "8. Verify the calculation formula matches official method"
    ]
    
    for step in steps:
        print(f"  {step}")
    
    print(f"\n📝 API Endpoints to Test:")
    print(f"  GET /api/optionchain/13?underlying_segment=IDX_I")
    print(f"  Check the 'oi_change' field for strike 27700")
    
    print(f"\n🔍 Manual Verification:")
    print(f"  1. Note current OI for strike 27700")
    print(f"  2. Note previous OI from yesterday's close")
    print(f"  3. Calculate: (current - previous) / previous * 100")
    print(f"  4. Compare with system calculation")


if __name__ == "__main__":
    test_oi_calculations()
    test_frontend_formatting()
    suggest_debugging_steps()
    
    print(f"\n✅ Summary:")
    print(f"  - Frontend formatting fixed (1 decimal → 2 decimal places)")
    print(f"  - Backend calculation formula appears correct")
    print(f"  - Issue likely in data source or timing")
    print(f"  - Need to verify actual OI values from API")
    print(f"  - Compare with official NSE/broker data")
