#!/usr/bin/env python3
"""
API Usage Examples for Range OI Strategy

This script shows how to use the enhanced Range OI Strategy APIs:
1. Custom range analysis (25500-25600)
2. Individual strike OI data (25500)
3. Auto-detected range analysis
"""

import requests
import json
from datetime import datetime


def test_range_oi_api():
    """Test Range OI Strategy API endpoints."""
    
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Range OI Strategy API Endpoints")
    print("=" * 60)
    
    # Test 1: Custom Range Analysis (25500-25600)
    print("📊 Test 1: Custom Range Analysis (25500-25600)")
    print("-" * 40)
    
    try:
        custom_range_payload = {
            "underlying_scrip": 13,  # NIFTY
            "current_price": 25550,  # Current price
            "lower_strike": 25500,   # Custom lower strike
            "upper_strike": 25600    # Custom upper strike
        }
        
        response = requests.post(
            f"{base_url}/api/strategy/range-oi-analysis",
            json=custom_range_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Custom Range Analysis Success")
            print(f"Current Price: {data['current_price']}")
            print(f"Range: {data['lower_strike']} - {data['upper_strike']}")
            print(f"Overall Signal: {data['overall_signal']}")
            print(f"Confidence: {data['confidence']:.2%}")
            print(f"Lower Strike Signal: {data['lower_strike_signal']}")
            print(f"Upper Strike Signal: {data['upper_strike_signal']}")
            print(f"Reasoning: {data['reasoning']}")
            
            print(f"\n📈 OI Details:")
            print(f"25500 PE OI: {data['lower_strike_pe_oi']:,}")
            print(f"25500 CE OI: {data['lower_strike_ce_oi']:,}")
            print(f"25600 PE OI: {data['upper_strike_pe_oi']:,}")
            print(f"25600 CE OI: {data['upper_strike_ce_oi']:,}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 2: Auto-detected Range Analysis
    print("📊 Test 2: Auto-detected Range Analysis")
    print("-" * 40)
    
    try:
        auto_range_payload = {
            "underlying_scrip": 13,  # NIFTY
            "current_price": 25440   # Let system auto-detect strikes
        }
        
        response = requests.post(
            f"{base_url}/api/strategy/range-oi-analysis",
            json=auto_range_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Auto Range Analysis Success")
            print(f"Current Price: {data['current_price']}")
            print(f"Auto-detected Range: {data['lower_strike']} - {data['upper_strike']}")
            print(f"Overall Signal: {data['overall_signal']}")
            print(f"Confidence: {data['confidence']:.2%}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 3: Individual Strike OI Data
    print("📊 Test 3: Individual Strike OI Data (25500)")
    print("-" * 40)
    
    try:
        strike_price = 25500
        response = requests.get(
            f"{base_url}/api/strategy/individual-strike-oi/{strike_price}",
            params={"underlying_scrip": 13}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Individual Strike OI Success")
            print(f"Strike Price: {data['strike_price']}")
            print(f"PE OI: {data['pe_oi']:,}")
            print(f"CE OI: {data['ce_oi']:,}")
            print(f"PE Volume: {data['pe_volume']:,}")
            print(f"CE Volume: {data['ce_volume']:,}")
            print(f"PE LTP: ₹{data['pe_ltp']:.2f}")
            print(f"CE LTP: ₹{data['ce_ltp']:.2f}")
            print(f"PE/CE Ratio: {data['pe_ce_ratio']:.2f}")
            print(f"Signal: {data['signal']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 4: Multiple Individual Strikes
    print("📊 Test 4: Multiple Individual Strikes Comparison")
    print("-" * 40)
    
    strikes = [25400, 25450, 25500, 25550, 25600]
    
    print(f"{'Strike':<8} {'PE OI':<10} {'CE OI':<10} {'Ratio':<8} {'Signal':<12}")
    print("-" * 55)
    
    for strike in strikes:
        try:
            response = requests.get(
                f"{base_url}/api/strategy/individual-strike-oi/{strike}",
                params={"underlying_scrip": 13}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"{strike:<8} {data['pe_oi']:<10,} {data['ce_oi']:<10,} {data['pe_ce_ratio']:<8.2f} {data['signal']:<12}")
            else:
                print(f"{strike:<8} {'Error':<10} {'Error':<10} {'N/A':<8} {'N/A':<12}")
                
        except Exception as e:
            print(f"{strike:<8} {'Exception':<10} {'Exception':<10} {'N/A':<8} {'N/A':<12}")
    
    print("\n" + "=" * 60)
    print("✅ API Testing completed!")


def curl_examples():
    """Print curl command examples for API usage."""
    
    print("\n🔧 CURL Command Examples")
    print("=" * 60)
    
    print("1. Custom Range Analysis (25500-25600):")
    print("curl -X POST http://localhost:8000/api/strategy/range-oi-analysis \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{")
    print('    "underlying_scrip": 13,')
    print('    "current_price": 25550,')
    print('    "lower_strike": 25500,')
    print('    "upper_strike": 25600')
    print("  }'")
    
    print("\n2. Auto Range Analysis:")
    print("curl -X POST http://localhost:8000/api/strategy/range-oi-analysis \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{")
    print('    "underlying_scrip": 13,')
    print('    "current_price": 25440')
    print("  }'")
    
    print("\n3. Individual Strike OI (25500):")
    print("curl -X GET 'http://localhost:8000/api/strategy/individual-strike-oi/25500?underlying_scrip=13'")
    
    print("\n4. Range OI History:")
    print("curl -X GET 'http://localhost:8000/api/strategy/range-oi-history?limit=5'")


if __name__ == "__main__":
    print("🔍 Range OI Strategy API Usage Examples")
    print("Make sure your backend server is running on http://localhost:8000")
    print()
    
    # Test the APIs
    test_range_oi_api()
    
    # Show curl examples
    curl_examples()
    
    print("\n📝 Summary:")
    print("- Use custom strikes for specific range analysis (25500-25600)")
    print("- Get individual strike OI data for detailed analysis")
    print("- Compare multiple strikes to identify support/resistance levels")
    print("- Frontend now supports both auto and custom range modes")
