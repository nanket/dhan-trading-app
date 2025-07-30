#!/usr/bin/env python3
"""
Test script for custom Range OI Strategy with specific strike ranges.

This script demonstrates:
1. Range OI analysis between specific strikes (25500-25600)
2. Individual strike OI data for specific strikes (25500)
3. Custom range analysis vs auto-detected range analysis
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dhan_trader.api.client import DhanAPIClient
from dhan_trader.market_data.manager import MarketDataManager
from dhan_trader.strategies.range_oi_strategy import RangeOIStrategy


async def test_custom_range_oi():
    """Test custom Range OI Strategy functionality."""
    
    print("🔧 Initializing Dhan AI Trader components...")
    
    # Initialize components
    api_client = DhanAPIClient()
    market_data_manager = MarketDataManager(api_client)
    range_oi_strategy = RangeOIStrategy(market_data_manager)
    
    print("✅ Components initialized successfully")
    print("=" * 60)
    
    # Test 1: Auto-detected range analysis
    print("📊 Test 1: Auto-detected Range Analysis")
    print("-" * 40)
    
    try:
        auto_analysis = range_oi_strategy.analyze_range_oi(
            underlying_scrip=13,  # NIFTY
            current_price=25440   # Example current price
        )
        
        print(f"Current Price: {auto_analysis.current_price}")
        print(f"Auto-detected Range: {auto_analysis.lower_strike} - {auto_analysis.upper_strike}")
        print(f"Lower Strike Signal: {auto_analysis.lower_strike_signal}")
        print(f"Upper Strike Signal: {auto_analysis.upper_strike_signal}")
        print(f"Overall Signal: {auto_analysis.overall_signal}")
        print(f"Confidence: {auto_analysis.confidence:.2%}")
        print(f"Reasoning: {auto_analysis.reasoning}")
        
    except Exception as e:
        print(f"❌ Error in auto-detected analysis: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 2: Custom range analysis (25500-25600)
    print("📊 Test 2: Custom Range Analysis (25500-25600)")
    print("-" * 40)
    
    try:
        custom_analysis = range_oi_strategy.analyze_range_oi(
            underlying_scrip=13,  # NIFTY
            current_price=25550,  # Price within the custom range
            lower_strike=25500,   # Custom lower strike
            upper_strike=25600    # Custom upper strike
        )
        
        print(f"Current Price: {custom_analysis.current_price}")
        print(f"Custom Range: {custom_analysis.lower_strike} - {custom_analysis.upper_strike}")
        print(f"Lower Strike (25500) Signal: {custom_analysis.lower_strike_signal}")
        print(f"Upper Strike (25600) Signal: {custom_analysis.upper_strike_signal}")
        print(f"Overall Signal: {custom_analysis.overall_signal}")
        print(f"Confidence: {custom_analysis.confidence:.2%}")
        print(f"Reasoning: {custom_analysis.reasoning}")
        
        # Show detailed OI data
        print(f"\n📈 Detailed OI Data:")
        print(f"25500 Strike - PE OI: {custom_analysis.lower_strike_pe_oi:,}, CE OI: {custom_analysis.lower_strike_ce_oi:,}")
        print(f"25600 Strike - PE OI: {custom_analysis.upper_strike_pe_oi:,}, CE OI: {custom_analysis.upper_strike_ce_oi:,}")
        
    except Exception as e:
        print(f"❌ Error in custom range analysis: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 3: Individual strike OI data
    print("📊 Test 3: Individual Strike OI Data (25500)")
    print("-" * 40)
    
    try:
        strike_oi_data = range_oi_strategy.get_individual_strike_oi(
            strike_price=25500,
            underlying_scrip=13  # NIFTY
        )
        
        if strike_oi_data:
            print(f"Strike Price: {strike_oi_data.strike_price}")
            print(f"PE OI: {strike_oi_data.pe_oi:,}")
            print(f"CE OI: {strike_oi_data.ce_oi:,}")
            print(f"PE Volume: {strike_oi_data.pe_volume:,}")
            print(f"CE Volume: {strike_oi_data.ce_volume:,}")
            print(f"PE LTP: ₹{strike_oi_data.pe_ltp:.2f}")
            print(f"CE LTP: ₹{strike_oi_data.ce_ltp:.2f}")
            
            # Calculate PE/CE ratio
            pe_ce_ratio = strike_oi_data.pe_oi / max(strike_oi_data.ce_oi, 1)
            print(f"PE/CE OI Ratio: {pe_ce_ratio:.2f}")
            
            # Determine signal
            if strike_oi_data.pe_oi > strike_oi_data.ce_oi:
                signal = "SUPPORT (PE > CE)"
            elif strike_oi_data.ce_oi > strike_oi_data.pe_oi:
                signal = "RESISTANCE (CE > PE)"
            else:
                signal = "NEUTRAL (PE = CE)"
            
            print(f"Signal: {signal}")
        else:
            print("❌ No OI data found for strike 25500")
            
    except Exception as e:
        print(f"❌ Error getting individual strike OI: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 4: Multiple individual strikes comparison
    print("📊 Test 4: Multiple Strikes Comparison")
    print("-" * 40)
    
    strikes_to_test = [25400, 25450, 25500, 25550, 25600]
    
    print(f"{'Strike':<8} {'PE OI':<10} {'CE OI':<10} {'Ratio':<8} {'Signal':<12}")
    print("-" * 55)
    
    for strike in strikes_to_test:
        try:
            oi_data = range_oi_strategy.get_individual_strike_oi(
                strike_price=strike,
                underlying_scrip=13
            )
            
            if oi_data:
                ratio = oi_data.pe_oi / max(oi_data.ce_oi, 1)
                if oi_data.pe_oi > oi_data.ce_oi:
                    signal = "Support"
                elif oi_data.ce_oi > oi_data.pe_oi:
                    signal = "Resistance"
                else:
                    signal = "Neutral"
                
                print(f"{strike:<8} {oi_data.pe_oi:<10,} {oi_data.ce_oi:<10,} {ratio:<8.2f} {signal:<12}")
            else:
                print(f"{strike:<8} {'N/A':<10} {'N/A':<10} {'N/A':<8} {'No Data':<12}")
                
        except Exception as e:
            print(f"{strike:<8} Error: {str(e)[:30]}")
    
    print("\n" + "=" * 60)
    print("✅ Range OI Strategy testing completed!")
    print("\n📝 Usage Summary:")
    print("1. Auto Range: Let the system find nearest strikes automatically")
    print("2. Custom Range: Specify exact strikes (e.g., 25500-25600)")
    print("3. Individual Strike: Get detailed OI data for specific strikes")
    print("4. API Endpoints:")
    print("   - POST /api/strategy/range-oi-analysis (with lower_strike, upper_strike)")
    print("   - GET /api/strategy/individual-strike-oi/{strike_price}")


if __name__ == "__main__":
    asyncio.run(test_custom_range_oi())
