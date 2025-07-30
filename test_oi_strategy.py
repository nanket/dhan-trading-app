#!/usr/bin/env python3
"""
Test script for Sameer Sir OI Strategy
This demonstrates the OI strategy functionality with mock data
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dhan_trader.strategies.oi_strategy import SameerSirOIStrategy
from dhan_trader.api.models import OptionChain, OptionChainStrike, OptionData, Greeks
from datetime import datetime

def create_mock_option_data(last_price, volume, oi, iv=12.0, delta=0.5, gamma=0.001, theta=-5.0, vega=0.1):
    """Create mock option data for testing."""
    greeks = Greeks(
        delta=delta,
        gamma=gamma,
        theta=theta,
        vega=vega
    )

    return OptionData(
        last_price=last_price,
        volume=volume,
        oi=oi,
        top_bid_price=last_price - 0.5,
        top_ask_price=last_price + 0.5,
        top_bid_quantity=100,
        top_ask_quantity=100,
        implied_volatility=iv,
        greeks=greeks,
        previous_close_price=last_price,
        previous_oi=oi,
        previous_volume=volume
    )

def create_mock_option_chain():
    """Create a mock option chain for testing."""
    current_price = 25550.0
    strikes = []
    
    # Create strikes around current price
    for i in range(-5, 6):  # 11 strikes total
        strike_price = current_price + (i * 50)  # 50 point intervals
        
        # Mock volume and OI patterns
        # Higher volume/OI closer to ATM
        distance_factor = max(0.1, 1 - abs(i) * 0.15)
        
        # Create CE data
        ce_volume = int(50000000 * distance_factor)  # 50M base volume
        ce_oi = int(2000000 * distance_factor)       # 2M base OI
        ce_price = max(1, 200 - abs(i) * 30)
        ce_delta = max(0.05, 0.5 + i * 0.1)
        
        # Create PE data with different pattern
        pe_volume = int(60000000 * distance_factor)  # 60M base volume (higher for puts)
        pe_oi = int(1500000 * distance_factor)       # 1.5M base OI
        pe_price = max(1, 180 - abs(i) * 25)
        pe_delta = min(-0.05, -0.5 - i * 0.1)
        
        ce_data = create_mock_option_data(ce_price, ce_volume, ce_oi, delta=ce_delta)
        pe_data = create_mock_option_data(pe_price, pe_volume, pe_oi, delta=pe_delta)
        
        strike = OptionChainStrike(
            strike=strike_price,
            ce=ce_data,
            pe=pe_data
        )
        strikes.append(strike)
    
    return OptionChain(
        underlying_scrip=13,
        underlying_segment="IDX_I",
        underlying_price=current_price,
        expiry="2025-07-31",
        strikes=strikes
    )

class MockMarketDataManager:
    """Mock market data manager for testing."""
    
    def get_option_chain(self, underlying_scrip, segment, expiry, use_cache=False):
        return create_mock_option_chain()

def test_oi_strategy():
    """Test the OI strategy with mock data."""
    print("🚀 Testing Sameer Sir OI Strategy")
    print("=" * 50)
    
    # Create mock market data manager
    mock_manager = MockMarketDataManager()
    
    # Initialize strategy
    strategy = SameerSirOIStrategy(mock_manager)
    
    # Test the strategy analysis
    print("📊 Running OI Strategy Analysis...")
    signal = strategy.analyze_oi_strategy(
        underlying_scrip=13,
        expiry="2025-07-31",
        center_strike=25550,
        strike_range=100
    )
    
    print(f"\n✅ Analysis Complete!")
    print(f"📈 Current Price: ₹{signal.current_price}")
    print(f"🎯 Overall Signal: {signal.overall_signal.upper()}")
    print(f"💪 Confidence: {signal.confidence:.1%}")
    
    print(f"\n📊 Range Analysis (25450-25650):")
    range_analysis = signal.range_analysis
    print(f"   CE OI Total: {range_analysis.total_ce_oi:,}")
    print(f"   PE OI Total: {range_analysis.total_pe_oi:,}")
    print(f"   OI Ratio (PE/CE): {range_analysis.oi_ratio:.2f}")
    print(f"   Range Signal: {range_analysis.signal.upper()}")
    print(f"   Signal Strength: {range_analysis.strength:.1%}")
    
    print(f"\n🎯 Individual Strike Analysis:")
    for analysis in signal.strike_analyses:
        print(f"   Strike {analysis.strike}: {analysis.signal.upper()} "
              f"(PE: {analysis.pe_oi:,}, CE: {analysis.ce_oi:,}, "
              f"Ratio: {analysis.oi_ratio:.2f})")
    
    if signal.targets:
        print(f"\n🎯 Target Levels:")
        for i, target in enumerate(signal.targets, 1):
            print(f"   Target {i}: ₹{target}")
    
    if signal.alerts:
        print(f"\n🚨 Strategy Alerts:")
        for alert in signal.alerts:
            print(f"   • {alert}")
    
    print(f"\n📈 Strategy Logic:")
    print(f"   • Range Analysis: Compare total PE vs CE OI across strikes")
    print(f"   • PE OI > CE OI → Bullish signal (writers expect support)")
    print(f"   • CE OI > PE OI → Bearish signal (writers expect resistance)")
    print(f"   • Individual strikes confirm target levels")
    
    print(f"\n✨ Test completed successfully!")
    return signal

if __name__ == "__main__":
    test_oi_strategy()
