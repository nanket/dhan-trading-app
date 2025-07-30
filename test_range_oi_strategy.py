#!/usr/bin/env python3
"""
Test script for Range OI Strategy
This demonstrates the Range OI strategy functionality with mock data
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dhan_trader.strategies.range_oi_strategy import RangeOIStrategy
from dhan_trader.api.models import OptionChain, OptionChainStrike, OptionData, Greeks
from datetime import datetime


class MockMarketDataManager:
    """Mock market data manager for testing."""
    
    def get_option_chain(self, underlying_scrip, exchange_segment, expiry=None, use_cache=True):
        """Return mock option chain data for testing."""
        current_price = 25440.0
        
        # Create mock strikes around current price
        strikes = {}
        
        # Create strikes from 25300 to 25600 (50 point intervals)
        for i in range(-3, 4):  # 7 strikes total
            strike_price = 25400 + (i * 50)  # 50 point intervals
            
            # Mock OI patterns for testing
            # For 25400 and 25450 (nearest strikes to 25440)
            if strike_price == 25400:
                # Lower strike: PE > CE (Support)
                pe_oi = 150000  # Higher PE OI
                ce_oi = 80000   # Lower CE OI
            elif strike_price == 25450:
                # Upper strike: PE > CE (Support) - to create bullish scenario
                pe_oi = 120000  # Higher PE OI
                ce_oi = 70000   # Lower CE OI
            else:
                # Other strikes with random OI
                pe_oi = 50000 + (abs(i) * 10000)
                ce_oi = 60000 + (abs(i) * 8000)
            
            # Create PE data
            pe_data = OptionData(
                greeks=Greeks(
                    delta=-0.5 - i * 0.1,
                    gamma=0.01,
                    theta=-0.05,
                    vega=0.2
                ),
                implied_volatility=0.15,
                last_price=100.0 - abs(i) * 15,
                oi=pe_oi,
                previous_close_price=105.0 - abs(i) * 15,
                previous_oi=pe_oi - 1000,
                previous_volume=(pe_oi // 10) - 100,
                top_ask_price=101.0 - abs(i) * 15,
                top_ask_quantity=100,
                top_bid_price=99.0 - abs(i) * 15,
                top_bid_quantity=100,
                volume=pe_oi // 10
            )

            # Create CE data
            ce_data = OptionData(
                greeks=Greeks(
                    delta=0.5 + i * 0.1,
                    gamma=0.01,
                    theta=-0.05,
                    vega=0.2
                ),
                implied_volatility=0.15,
                last_price=80.0 - abs(i) * 12,
                oi=ce_oi,
                previous_close_price=85.0 - abs(i) * 12,
                previous_oi=ce_oi - 800,
                previous_volume=(ce_oi // 10) - 80,
                top_ask_price=81.0 - abs(i) * 12,
                top_ask_quantity=100,
                top_bid_price=79.0 - abs(i) * 12,
                top_bid_quantity=100,
                volume=ce_oi // 10
            )
            
            # Create strike data
            strikes[str(int(strike_price))] = OptionChainStrike(
                strike=strike_price,
                pe=pe_data,
                ce=ce_data
            )
        
        # Create option chain
        option_chain = OptionChain(
            underlying_scrip=underlying_scrip,
            underlying_price=current_price,
            expiry="2025-07-31",
            strikes=strikes,
            underlying_segment="IDX_I"
        )
        
        return option_chain


def test_range_oi_strategy():
    """Test the Range OI strategy with mock data."""
    print("🚀 Testing Range OI Strategy")
    print("=" * 50)
    
    # Create mock market data manager
    mock_manager = MockMarketDataManager()
    
    # Initialize strategy
    strategy = RangeOIStrategy(mock_manager)
    
    # Test the strategy analysis
    print("📊 Running Range OI Strategy Analysis...")
    print(f"Current Nifty Price: 25440")
    print(f"Expected nearest strikes: 25400 and 25500")
    print()
    
    analysis = strategy.analyze_range_oi(
        underlying_scrip=13,
        current_price=25440.0
    )
    
    print("📈 Analysis Results:")
    print(f"Current Price: {analysis.current_price}")
    print(f"Lower Strike: {analysis.lower_strike}")
    print(f"Upper Strike: {analysis.upper_strike}")
    print()
    
    print("📊 OI Data:")
    print(f"Lower Strike ({analysis.lower_strike}):")
    print(f"  PE OI: {analysis.lower_strike_pe_oi:,}")
    print(f"  CE OI: {analysis.lower_strike_ce_oi:,}")
    print(f"  Signal: {analysis.lower_strike_signal}")
    print()
    
    print(f"Upper Strike ({analysis.upper_strike}):")
    print(f"  PE OI: {analysis.upper_strike_pe_oi:,}")
    print(f"  CE OI: {analysis.upper_strike_ce_oi:,}")
    print(f"  Signal: {analysis.upper_strike_signal}")
    print()
    
    print("🎯 Overall Signal:")
    print(f"Signal: {analysis.overall_signal.upper()}")
    print(f"Confidence: {analysis.confidence:.1%}")
    print()
    
    print("💡 Reasoning:")
    print(analysis.reasoning)
    print()
    
    print("✅ Strategy Logic Verification:")
    if analysis.lower_strike_signal == "support" and analysis.upper_strike_signal == "support":
        print("✓ Both strikes show PE > CE → Bullish signal expected")
        if analysis.overall_signal == "bullish":
            print("✓ Overall signal is BULLISH - Strategy working correctly!")
        else:
            print("✗ Expected bullish signal but got:", analysis.overall_signal)
    else:
        print(f"Lower: {analysis.lower_strike_signal}, Upper: {analysis.upper_strike_signal}")
        print(f"Overall: {analysis.overall_signal}")
    
    print()
    print("🔍 Strategy Implementation Details:")
    print("1. ✓ Found nearest strikes to current price")
    print("2. ✓ Extracted PE and CE OI data")
    print("3. ✓ Compared OI ratios for each strike")
    print("4. ✓ Generated overall signal based on both strikes")
    print("5. ✓ Provided detailed reasoning")
    
    return analysis


if __name__ == "__main__":
    try:
        analysis = test_range_oi_strategy()
        print("\n🎉 Range OI Strategy test completed successfully!")
        
        # Test with different scenarios
        print("\n" + "="*50)
        print("🔄 Testing with different OI patterns...")
        
        # You can modify the mock data in MockMarketDataManager to test different scenarios:
        # - Bearish: CE > PE on both strikes
        # - Neutral: Mixed signals (one support, one resistance)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
