"""Gemini AI client for trading analysis and recommendations."""

import os
import logging
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from datetime import datetime
import json

from ..config import config

logger = logging.getLogger(__name__)


class GeminiAIClient:
    """Client for interacting with Google's Gemini AI for trading analysis."""
    
    def __init__(self):
        """Initialize the Gemini AI client."""
        self.api_key = config.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # System prompt for trading context
        self.system_prompt = """
You are an expert options trading advisor with REAL-TIME MARKET DATA ACCESS. You have deep knowledge of:
- Options Greeks (Delta, Gamma, Theta, Vega)
- Implied volatility analysis
- Option chain interpretation
- Volume and open interest analysis
- Technical analysis for options

IMPORTANT: You have access to live, real-time market data including:
- Current option chain data with live prices, volumes, and open interest
- Real-time underlying prices
- Live Greeks calculations
- Current implied volatility levels
- Up-to-the-minute trading volumes and OI changes
- **Open Interest Change Analysis**: Changes in OI compared to previous trading sessions
- **Institutional Activity Detection**: Significant OI build-up or unwinding patterns

When users ask about specific strikes, OI levels, or market conditions, you can provide accurate, current information based on the live data provided to you.

**OI Change Analysis Guidelines:**
- OI increases indicate new positions (bullish for puts, bearish for calls)
- OI decreases indicate position unwinding
- Significant changes (>15% or >100K contracts) suggest institutional activity
- Use OI changes to identify potential support/resistance levels

TRADING RECOMMENDATION GUIDELINES:
- When asked "what should I buy CE or PE", analyze current market data and provide SPECIFIC recommendations
- Always include: Exact strike price, entry price, stop loss, target price
- Base recommendations on: Volume analysis, OI changes, Greeks, implied volatility, PCR ratios
- Consider: ATM/OTM strikes with good liquidity, risk-reward ratios
- Provide clear reasoning for CE vs PE recommendation based on market sentiment
- Focus on actionable trades with proper risk management
- Always mention expiry date and time decay considerations
- Be decisive and provide actionable trades when data supports it
- Focus on liquid strikes with good volume and open interest
- Use PCR analysis: PCR < 0.8 = Bullish (suggest CE), PCR > 1.2 = Bearish (suggest PE)
- Assume sufficient trading capital is available - focus on market analysis and trade setup

You provide clear, actionable trading advice with specific entry/exit points based on real-time market data.
Be concise but thorough in your analysis.
"""
        
        logger.info("Gemini AI client initialized successfully")
    
    async def analyze_option_chain(
        self, 
        option_chain_data: Dict[str, Any],
        user_query: str = "Analyze this option chain data"
    ) -> str:
        """
        Analyze option chain data and provide trading insights.
        
        Args:
            option_chain_data: Option chain data from Dhan API
            user_query: Specific user question about the data
            
        Returns:
            AI-generated analysis and recommendations
        """
        try:
            # Check for data quality issues
            data_quality = option_chain_data.get('data_quality', {})
            quality_issues = data_quality.get('quality_issues', [])
            is_reliable = data_quality.get('is_reliable', True)

            quality_context = ""
            if quality_issues:
                quality_context = f"""
DATA QUALITY ALERT:
The following data quality issues have been identified:
{chr(10).join(f"• {issue}" for issue in quality_issues)}

Liquidity Ratio: {data_quality.get('liquidity_ratio', 0):.2%}
Total Volume: {data_quality.get('total_volume', 0):,}
Total Open Interest: {data_quality.get('total_oi', 0):,}
Reliability: {'Low' if not is_reliable else 'Acceptable'}

IMPORTANT: Factor these limitations into your analysis. If data is unreliable, focus on educational content rather than specific trading recommendations.
"""

            # Prepare the prompt with market data
            prompt = f"""
{self.system_prompt}

{quality_context}

Current Market Data:
{json.dumps(option_chain_data, indent=2)}

User Query: {user_query}

Please analyze this option chain data and provide:
1. Data quality assessment and analysis reliability
2. Key observations about the current market structure (where data permits)
3. Implied volatility insights (if sufficient data available)
4. Greeks analysis for key strikes (if data is reliable)
5. Trading opportunities (ONLY if data quality is sufficient)
6. Risk considerations and market limitations
7. Educational insights about options trading

If data quality is poor, clearly state limitations and provide educational content instead of specific trading advice.
Keep your response professional and include appropriate risk disclaimers.
"""

            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error analyzing option chain: {e}")
            return f"Sorry, I encountered an error analyzing the market data: {str(e)}"
    
    async def answer_trading_question(
        self,
        question: str,
        market_context: Optional[Dict[str, Any]] = None,
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Answer general trading questions with optional market context.
        
        Args:
            question: User's trading question
            market_context: Current market data for context
            portfolio_context: User's portfolio information
            
        Returns:
            AI-generated response
        """
        try:
            # Build context-aware prompt
            prompt = f"{self.system_prompt}\n\n"
            
            if market_context:
                prompt += f"🔴 LIVE MARKET DATA (Real-time as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n{json.dumps(market_context, indent=2)}\n\n"
                prompt += """✅ REAL-TIME DATA AVAILABLE: The above market data is LIVE and CURRENT. You have access to:
- Real-time option chain with current prices, volumes, and open interest
- Live underlying prices and movements
- Current Greeks calculations
- Real-time implied volatility levels
- Up-to-the-minute trading activity

You can provide specific, accurate answers about current market conditions, OI levels, and trading opportunities based on this live data.\n\n"""
            
            if portfolio_context:
                prompt += f"Portfolio Context:\n{json.dumps(portfolio_context, indent=2)}\n\n"
            
            prompt += f"User Question: {question}\n\n"
            prompt += "Please provide a helpful, specific answer based on the available context."
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error answering trading question: {e}")
            return f"Sorry, I encountered an error processing your question: {str(e)}"
    
    async def suggest_option_strategies(
        self,
        underlying_price: float,
        option_strikes: List[Dict[str, Any]],
        market_outlook: str = "neutral",
        risk_tolerance: str = "moderate"
    ) -> str:
        """
        Suggest option trading strategies based on market conditions.
        
        Args:
            underlying_price: Current price of underlying asset
            option_strikes: List of option strike data
            market_outlook: bullish/bearish/neutral
            risk_tolerance: low/moderate/high
            
        Returns:
            Strategy recommendations
        """
        try:
            prompt = f"""
{self.system_prompt}

Market Analysis Request:
- Underlying Price: {underlying_price}
- Market Outlook: {market_outlook}
- Risk Tolerance: {risk_tolerance}

Available Option Strikes:
{json.dumps(option_strikes, indent=2)}

Please suggest 2-3 option trading strategies that match the market outlook and risk tolerance.
For each strategy, provide:
1. Strategy name and description
2. Specific strikes to use
3. Entry criteria
4. Profit/loss potential
5. Risk management guidelines
"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error suggesting strategies: {e}")
            return f"Sorry, I encountered an error generating strategy suggestions: {str(e)}"
    
    async def analyze_unusual_activity(
        self,
        option_data: List[Dict[str, Any]]
    ) -> str:
        """
        Analyze option data for unusual activity or opportunities.
        
        Args:
            option_data: List of option data with volume, OI, etc.
            
        Returns:
            Analysis of unusual activity
        """
        try:
            prompt = f"""
{self.system_prompt}

Option Activity Data:
{json.dumps(option_data, indent=2)}

Please analyze this option activity data for:
1. Unusual volume patterns
2. Significant open interest changes
3. Potential institutional activity
4. Arbitrage opportunities
5. Market sentiment indicators

Highlight any notable patterns or opportunities.
"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error analyzing unusual activity: {e}")
            return f"Sorry, I encountered an error analyzing the activity data: {str(e)}"
