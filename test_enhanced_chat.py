#!/usr/bin/env python3
"""
Test script for the enhanced chat service with dynamic OI analysis.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_enhanced_chat():
    """Test the enhanced chat endpoint."""
    
    # Test data
    test_requests = [
        {
            "message": "Provide a comprehensive dynamic OI analysis with AI-powered pattern recognition",
            "use_market_data": True,
            "force_oi_analysis": False
        },
        {
            "message": "Analyze current OI patterns using machine learning and statistical methods",
            "use_market_data": True,
            "force_oi_analysis": False
        },
        {
            "message": "What's the current market sentiment based on OI data?",
            "use_market_data": True,
            "force_oi_analysis": False
        }
    ]
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        print("🚀 Testing Enhanced Chat Service with Dynamic OI Analysis")
        print("=" * 60)
        
        for i, request_data in enumerate(test_requests, 1):
            print(f"\n📝 Test {i}: {request_data['message'][:50]}...")
            
            try:
                async with session.post(
                    f"{base_url}/api/chat/enhanced",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        print(f"✅ Status: {response.status}")
                        print(f"📊 Analysis Type: {result.get('analysis_type', 'N/A')}")
                        print(f"⏱️  Processing Time: {result.get('processing_time', 0):.2f}s")
                        print(f"🎯 Confidence Score: {result.get('confidence_score', 'N/A')}")
                        
                        # Check if OI analysis was performed
                        if result.get('oi_analysis'):
                            oi_analysis = result['oi_analysis']
                            print(f"🔍 OI Analysis Performed:")
                            print(f"   - Sentiment: {oi_analysis.get('overall_sentiment', 'N/A')}")
                            print(f"   - Patterns Detected: {len(oi_analysis.get('patterns', []))}")
                            print(f"   - Recommendation: {oi_analysis.get('recommendation', 'N/A')}")
                            print(f"   - Key Levels: {len(oi_analysis.get('key_levels', []))}")
                        
                        # Show response message (truncated)
                        message_content = result.get('message', {}).get('content', '')
                        if message_content:
                            print(f"💬 Response Preview: {message_content[:200]}...")
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ Status: {response.status}")
                        print(f"Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ Request failed: {str(e)}")
        
        # Test direct OI analysis endpoint
        print(f"\n🔬 Testing Direct OI Analysis Endpoint")
        print("-" * 40)
        
        try:
            async with session.get(
                f"{base_url}/api/chat/dynamic-oi-analysis?underlying_scrip=13"
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    print(f"✅ Status: {response.status}")
                    print(f"📈 Underlying Price: ₹{result.get('underlying_price', 0):,.2f}")
                    print(f"🎯 Overall Sentiment: {result.get('overall_sentiment', 'N/A')}")
                    print(f"🔍 Patterns Detected: {len(result.get('patterns', []))}")
                    print(f"📊 Confidence Score: {result.get('confidence_score', 0):.1%}")
                    print(f"💡 Recommendation: {result.get('recommendation', 'N/A')}")
                    
                    # Show detected patterns
                    patterns = result.get('patterns', [])
                    if patterns:
                        print(f"\n🔍 Top Patterns:")
                        for j, pattern in enumerate(patterns[:3], 1):
                            print(f"   {j}. {pattern.get('pattern_type', 'Unknown')} "
                                  f"({pattern.get('confidence', 0):.1%} confidence)")
                    
                    # Show key levels
                    key_levels = result.get('key_levels', [])
                    if key_levels:
                        levels_str = ", ".join([f"₹{level:,.0f}" for level in key_levels[:5]])
                        print(f"🎯 Key Levels: {levels_str}")
                
                else:
                    error_text = await response.text()
                    print(f"❌ Status: {response.status}")
                    print(f"Error: {error_text}")
                    
        except Exception as e:
            print(f"❌ Direct OI analysis failed: {str(e)}")
        
        print(f"\n🏁 Testing completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_chat())
