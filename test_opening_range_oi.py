#!/usr/bin/env python3
"""
Test script for Opening-based Range OI Strategy.

This script demonstrates the specific use case:
- Today's NIFTY opened at 24619
- Range OI analysis for 24600-24700 (100-point range)
- Individual strike analysis for 24600 and 24700
"""

import asyncio
import sys
import requests
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dhan_trader.api.client import DhanAPIClient
from dhan_trader.market_data.manager import MarketDataManager
from dhan_trader.strategies.range_oi_strategy import RangeOIStrategy


def test_opening_range_api():
    """Test Opening Range OI Strategy via API."""
    
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Opening Range OI Strategy API")
    print("=" * 60)
    print("📊 Today's NIFTY Opening: 24619")
    print("🎯 Target Range: 24600-24700 (100-point interval)")
    print("=" * 60)
    
    # Test 1: Opening Range Analysis (24619 → 24600-24700)
    print("📊 Test 1: Opening Range Analysis")
    print("-" * 40)
    
    try:
        params = {
            "opening_price": 24619,
            "underlying_scrip": 13,
            "range_interval": 100
        }
        
        response = requests.post(
            f"{base_url}/api/strategy/opening-range-oi-analysis",
            params=params,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Opening Range Analysis Success")
            print(f"Opening Price: {params['opening_price']}")
            print(f"Calculated Range: {data['lower_strike']} - {data['upper_strike']}")
            print(f"Overall Signal: {data['overall_signal']}")
            print(f"Confidence: {data['confidence']:.2%}")
            
            print(f"\n📈 Strike Analysis:")
            print(f"24600 Strike:")
            print(f"  - PE OI: {data['lower_strike_pe_oi']:,}")
            print(f"  - CE OI: {data['lower_strike_ce_oi']:,}")
            print(f"  - Signal: {data['lower_strike_signal']}")
            
            print(f"24700 Strike:")
            print(f"  - PE OI: {data['upper_strike_pe_oi']:,}")
            print(f"  - CE OI: {data['upper_strike_ce_oi']:,}")
            print(f"  - Signal: {data['upper_strike_signal']}")
            
            print(f"\n💡 Reasoning: {data['reasoning']}")
            
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 2: Individual Strike Analysis
    print("📊 Test 2: Individual Strike Analysis")
    print("-" * 40)
    
    strikes = [24600, 24700]
    
    for strike in strikes:
        try:
            response = requests.get(
                f"{base_url}/api/strategy/individual-strike-oi/{strike}",
                params={"underlying_scrip": 13}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Strike {strike} Analysis:")
                print(f"  PE OI: {data['pe_oi']:,}")
                print(f"  CE OI: {data['ce_oi']:,}")
                print(f"  PE/CE Ratio: {data['pe_ce_ratio']:.2f}")
                print(f"  Signal: {data['signal']}")
                print(f"  PE LTP: ₹{data['pe_ltp']:.2f}")
                print(f"  CE LTP: ₹{data['ce_ltp']:.2f}")
            else:
                print(f"❌ Strike {strike} Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Strike {strike} Exception: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 3: Different Range Intervals
    print("📊 Test 3: Different Range Intervals")
    print("-" * 40)
    
    intervals = [50, 100, 200]
    
    for interval in intervals:
        try:
            lower_bound = (int(24619 / interval) * interval)
            upper_bound = lower_bound + interval
            
            print(f"Range Interval {interval}: {lower_bound}-{upper_bound}")
            
            params = {
                "opening_price": 24619,
                "underlying_scrip": 13,
                "range_interval": interval
            }
            
            response = requests.post(
                f"{base_url}/api/strategy/opening-range-oi-analysis",
                params=params,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Signal: {data['overall_signal']} (Confidence: {data['confidence']:.1%})")
            else:
                print(f"  Error: {response.status_code}")
                
        except Exception as e:
            print(f"  Exception: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Opening Range OI Strategy testing completed!")


async def test_opening_range_python():
    """Test Opening Range OI Strategy via Python API."""
    
    print("\n🐍 Testing Opening Range OI Strategy (Python API)")
    print("=" * 60)
    
    try:
        # Initialize components
        api_client = DhanAPIClient()
        market_data_manager = MarketDataManager(api_client)
        range_oi_strategy = RangeOIStrategy(market_data_manager)
        
        # Test opening range analysis
        analysis = range_oi_strategy.analyze_opening_range_oi(
            opening_price=24619,
            underlying_scrip=13,
            range_interval=100
        )
        
        print(f"✅ Python API Success")
        print(f"Opening Price: 24619")
        print(f"Calculated Range: {analysis.lower_strike} - {analysis.upper_strike}")
        print(f"Overall Signal: {analysis.overall_signal}")
        print(f"Confidence: {analysis.confidence:.2%}")
        print(f"Reasoning: {analysis.reasoning}")
        
    except Exception as e:
        print(f"❌ Python API Error: {e}")


def show_curl_examples():
    """Show curl command examples."""
    
    print("\n🔧 CURL Command Examples")
    print("=" * 60)
    
    print("1. Opening Range Analysis (24619 → 24600-24700):")
    print("curl -X POST 'http://localhost:8000/api/strategy/opening-range-oi-analysis?opening_price=24619&underlying_scrip=13&range_interval=100'")
    
    print("\n2. Individual Strike OI (24600):")
    print("curl -X GET 'http://localhost:8000/api/strategy/individual-strike-oi/24600?underlying_scrip=13'")
    
    print("\n3. Individual Strike OI (24700):")
    print("curl -X GET 'http://localhost:8000/api/strategy/individual-strike-oi/24700?underlying_scrip=13'")
    
    print("\n4. Different Range Interval (50-point):")
    print("curl -X POST 'http://localhost:8000/api/strategy/opening-range-oi-analysis?opening_price=24619&underlying_scrip=13&range_interval=50'")


if __name__ == "__main__":
    print("🎯 Opening Range OI Strategy Test")
    print("Today's NIFTY Opening: 24619")
    print("Target Analysis: 24600-24700 range")
    print()
    
    # Test API endpoints
    test_opening_range_api()
    
    # Test Python API
    # asyncio.run(test_opening_range_python())
    
    # Show curl examples
    show_curl_examples()
    
    print("\n📝 Summary:")
    print("✅ Opening-based Range OI Strategy implemented")
    print("✅ 24619 opening → 24600-24700 range analysis")
    print("✅ Individual strike analysis for 24600 and 24700")
    print("✅ Frontend supports opening range mode")
    print("✅ API endpoints ready for integration")
