"""AI-powered trading advisor that integrates with market data and provides intelligent recommendations."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio

from .gemini_client import GeminiAIClient
from .oi_recommendation_service import OIRecommendationService, OIRecommendation
from ..market_data.manager import MarketDataManager
from ..api.client import DhanAPIClient
from ..api.models import OptionChain, OptionChainStrike

logger = logging.getLogger(__name__)


class TradingAdvisor:
    """AI-powered trading advisor for options trading."""
    
    def __init__(self, market_data_manager: MarketDataManager, api_client: DhanAPIClient):
        """
        Initialize the trading advisor.
        
        Args:
            market_data_manager: Market data manager instance
            api_client: Dhan API client instance
        """
        self.market_data_manager = market_data_manager
        self.api_client = api_client
        self.ai_client = GeminiAIClient()
        self.oi_recommendation_service = OIRecommendationService(market_data_manager, api_client)

        # Cache for recent analyses to avoid redundant API calls
        self.analysis_cache = {}
        self.cache_duration = timedelta(minutes=5)

        logger.info("Trading advisor initialized")
    
    async def analyze_current_market(self, underlying_scrip: int = 13) -> Dict[str, Any]:
        """
        Analyze current market conditions for the given underlying.
        
        Args:
            underlying_scrip: Security ID (default: 13 for NIFTY)
            
        Returns:
            Market analysis data
        """
        try:
            # Get current option chain data
            expiries = self.api_client.get_option_expiry_list(underlying_scrip)
            if not expiries:
                return {"error": "No expiry data available"}
            
            # Use the nearest expiry for analysis
            nearest_expiry = expiries[0]
            # Force fresh data for AI analysis to ensure live data access
            option_chain = self.market_data_manager.get_option_chain(
                underlying_scrip, "IDX_I", nearest_expiry, use_cache=False
            )
            
            # Prepare market data for analysis
            market_data = self._prepare_market_data(option_chain)
            
            return {
                "underlying_price": option_chain.underlying_price,
                "expiry": nearest_expiry,
                "total_strikes": len(option_chain.strikes),
                "market_data": market_data,
                "data_source": "live_market_feed",
                "analysis_time": datetime.now().strftime("%H:%M:%S"),
                "data_freshness": "real_time"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing current market: {e}")
            return {"error": str(e)}
    
    def _prepare_market_data(self, option_chain: OptionChain) -> Dict[str, Any]:
        """Prepare option chain data for AI analysis."""
        strikes_data = []
        atm_strikes = []
        
        underlying_price = option_chain.underlying_price
        
        # Handle both dictionary and list structures for strikes
        strikes_to_process = []
        if isinstance(option_chain.strikes, dict):
            # Dictionary structure: {strike_price: strike_data}
            strikes_to_process = [(float(strike_price), strike_data) for strike_price, strike_data in option_chain.strikes.items()]
        elif isinstance(option_chain.strikes, list):
            # List structure: [strike_data_with_strike_field]
            strikes_to_process = [(strike_data.strike, strike_data) for strike_data in option_chain.strikes]

        for strike_float, strike_data in strikes_to_process:
            # Focus on ATM and near-ATM strikes (within 5% of underlying)
            if abs(strike_float - underlying_price) / underlying_price <= 0.05:
                strike_info = {
                    "strike": strike_float,
                    "distance_from_atm": abs(strike_float - underlying_price),
                    "call_data": self._extract_option_data(strike_data.ce) if strike_data.ce else None,
                    "put_data": self._extract_option_data(strike_data.pe) if strike_data.pe else None
                }
                atm_strikes.append(strike_info)

            # Collect all strikes for broader analysis
            strikes_data.append({
                "strike": strike_float,
                "call_data": self._extract_option_data(strike_data.ce) if strike_data.ce else None,
                "put_data": self._extract_option_data(strike_data.pe) if strike_data.pe else None
            })
        
        # Find ATM strike and analyze volume patterns
        atm_strike = self._find_atm_strike(underlying_price, strikes_to_process)
        volume_analysis = self._analyze_volume_patterns(strikes_to_process, underlying_price)

        # Filter and prioritize liquid strikes for AI analysis
        liquid_strikes = [strike for strike in strikes_data if
                         (strike["call_data"] and strike["call_data"]["volume"] > 0) or
                         (strike["put_data"] and strike["put_data"]["volume"] > 0)]

        # Sort by distance from underlying price and take most relevant strikes
        relevant_strikes = sorted(strikes_data,
                                key=lambda x: abs(x["strike"] - underlying_price))[:30]

        return {
            "liquid_strikes": liquid_strikes[:15],  # Top 15 liquid strikes
            "relevant_strikes": relevant_strikes,   # 30 strikes closest to current price
            "atm_strikes": sorted(atm_strikes, key=lambda x: x["distance_from_atm"])[:10],
            "underlying_price": underlying_price,
            "atm_strike": atm_strike,
            "volume_analysis": volume_analysis,
            "data_quality": self._assess_data_quality(option_chain)
        }
    
    def _extract_option_data(self, option_data) -> Dict[str, Any]:
        """Extract relevant option data for analysis."""
        if not option_data:
            return None

        return {
            "last_price": option_data.last_price,
            "implied_volatility": option_data.implied_volatility,
            "volume": option_data.volume,
            "open_interest": option_data.oi,  # OptionData uses 'oi' not 'open_interest'
            "greeks": {
                "delta": option_data.greeks.delta if option_data.greeks else None,
                "gamma": option_data.greeks.gamma if option_data.greeks else None,
                "theta": option_data.greeks.theta if option_data.greeks else None,
                "vega": option_data.greeks.vega if option_data.greeks else None
            } if option_data.greeks else None
        }

    def _find_atm_strike(self, underlying_price: float, strikes_to_process: List) -> Dict[str, Any]:
        """Find the at-the-money strike and nearby strikes."""
        closest_strike = None
        min_distance = float('inf')

        for strike_float, strike_data in strikes_to_process:
            distance = abs(strike_float - underlying_price)
            if distance < min_distance:
                min_distance = distance
                closest_strike = {
                    "strike": strike_float,
                    "distance": distance,
                    "ce_data": self._extract_option_data(strike_data.ce) if strike_data.ce else None,
                    "pe_data": self._extract_option_data(strike_data.pe) if strike_data.pe else None
                }

        return closest_strike

    def _analyze_volume_patterns(self, strikes_to_process: List, underlying_price: float) -> Dict[str, Any]:
        """Analyze volume patterns to identify market sentiment."""
        ce_volume_total = 0
        pe_volume_total = 0
        ce_oi_total = 0
        pe_oi_total = 0

        high_volume_strikes = []

        for strike_float, strike_data in strikes_to_process:
            # Only consider strikes within 5% of underlying for sentiment analysis
            if abs(strike_float - underlying_price) / underlying_price <= 0.05:
                if strike_data.ce:
                    ce_volume_total += strike_data.ce.volume
                    ce_oi_total += strike_data.ce.oi

                    if strike_data.ce.volume > 1000000:  # 1M+ volume
                        high_volume_strikes.append({
                            "strike": strike_float,
                            "type": "CE",
                            "volume": strike_data.ce.volume,
                            "oi": strike_data.ce.oi,
                            "last_price": strike_data.ce.last_price
                        })

                if strike_data.pe:
                    pe_volume_total += strike_data.pe.volume
                    pe_oi_total += strike_data.pe.oi

                    if strike_data.pe.volume > 1000000:  # 1M+ volume
                        high_volume_strikes.append({
                            "strike": strike_float,
                            "type": "PE",
                            "volume": strike_data.pe.volume,
                            "oi": strike_data.pe.oi,
                            "last_price": strike_data.pe.last_price
                        })

        # Calculate PCR (Put-Call Ratio)
        pcr_volume = pe_volume_total / ce_volume_total if ce_volume_total > 0 else 0
        pcr_oi = pe_oi_total / ce_oi_total if ce_oi_total > 0 else 0

        # Determine market sentiment
        sentiment = "neutral"
        if pcr_volume < 0.7:
            sentiment = "bullish"
        elif pcr_volume > 1.3:
            sentiment = "bearish"

        return {
            "ce_volume_total": ce_volume_total,
            "pe_volume_total": pe_volume_total,
            "ce_oi_total": ce_oi_total,
            "pe_oi_total": pe_oi_total,
            "pcr_volume": pcr_volume,
            "pcr_oi": pcr_oi,
            "market_sentiment": sentiment,
            "high_volume_strikes": sorted(high_volume_strikes, key=lambda x: x["volume"], reverse=True)[:5]
        }

    async def get_trading_recommendation(self, user_query: str) -> str:
        """
        Get AI-powered trading recommendation based on user query.
        
        Args:
            user_query: User's trading question or request
            
        Returns:
            AI-generated recommendation
        """
        try:
            # Check cache first
            cache_key = f"recommendation_{hash(user_query)}"
            if cache_key in self.analysis_cache:
                cached_time, cached_result = self.analysis_cache[cache_key]
                if datetime.now() - cached_time < self.cache_duration:
                    return cached_result
            
            # Get current market data
            market_analysis = await self.analyze_current_market()
            
            if "error" in market_analysis:
                return f"Unable to analyze market: {market_analysis['error']}"
            
            # Skip portfolio context to focus on market analysis
            portfolio_context = {"note": "Using separate trading account with sufficient capital"}
            
            # Generate AI recommendation
            recommendation = await self.ai_client.answer_trading_question(
                question=user_query,
                market_context=market_analysis,
                portfolio_context=portfolio_context
            )
            
            # Cache the result
            self.analysis_cache[cache_key] = (datetime.now(), recommendation)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting trading recommendation: {e}")
            return f"Sorry, I encountered an error processing your request: {str(e)}"

    async def get_specific_oi_data(self, strike_price: float, expiry: str = None) -> str:
        """Get specific open interest data for a strike price."""
        try:
            # Get option chain data
            option_chain = await self.market_data_manager.get_option_chain(
                underlying_scrip=13,  # NIFTY
                expiry=expiry
            )

            if not option_chain or 'data' not in option_chain:
                return f"Unable to fetch option chain data for strike {strike_price}"

            # Find the specific strike
            ce_data = None
            pe_data = None

            for option in option_chain['data']:
                if abs(float(option.get('strike_price', 0)) - strike_price) < 0.01:
                    if option.get('option_type') == 'CE':
                        ce_data = option
                    elif option.get('option_type') == 'PE':
                        pe_data = option

            if not ce_data and not pe_data:
                return f"No option data found for strike price {strike_price}"

            # Format the response with real-time data
            response = f"📊 **Real-time Open Interest Data for {strike_price} Strike:**\n\n"

            if ce_data:
                response += f"**Call Options (CE):**\n"
                response += f"• Open Interest: {ce_data.get('open_interest', 'N/A'):,}\n"
                response += f"• Volume: {ce_data.get('volume', 'N/A'):,}\n"
                response += f"• LTP: ₹{ce_data.get('ltp', 'N/A')}\n"
                response += f"• Change: {ce_data.get('change', 'N/A')}%\n\n"

            if pe_data:
                response += f"**Put Options (PE):**\n"
                response += f"• Open Interest: {pe_data.get('open_interest', 'N/A'):,}\n"
                response += f"• Volume: {pe_data.get('volume', 'N/A'):,}\n"
                response += f"• LTP: ₹{pe_data.get('ltp', 'N/A')}\n"
                response += f"• Change: {pe_data.get('change', 'N/A')}%\n\n"

            # Add analysis
            if ce_data and pe_data:
                ce_oi = ce_data.get('open_interest', 0)
                pe_oi = pe_data.get('open_interest', 0)
                if ce_oi and pe_oi:
                    ratio = pe_oi / ce_oi if ce_oi > 0 else 0
                    response += f"**Analysis:**\n"
                    response += f"• Put/Call OI Ratio: {ratio:.2f}\n"
                    if ratio > 1.5:
                        response += f"• Signal: Bullish (High Put OI suggests support)\n"
                    elif ratio < 0.7:
                        response += f"• Signal: Bearish (High Call OI suggests resistance)\n"
                    else:
                        response += f"• Signal: Neutral\n"

            response += f"\n*Data as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            return response

        except Exception as e:
            logger.error(f"Error getting specific OI data: {e}")
            return f"Error fetching OI data for strike {strike_price}: {str(e)}"

    async def analyze_oi_changes(self, underlying_scrip: int = 13, expiry: str = None) -> str:
        """Analyze OI changes across the option chain for trading insights."""
        try:
            # Get option chain with OI changes
            option_chain = self.market_data_manager.get_option_chain_with_oi_changes(
                underlying_scrip=underlying_scrip,
                expiry=expiry
            )

            if not option_chain or not hasattr(option_chain, 'strikes'):
                return "Unable to fetch option chain data for OI change analysis"

            # Analyze significant OI changes
            significant_changes = []
            total_ce_oi_change = 0
            total_pe_oi_change = 0

            for strike_price, strike_data in option_chain.strikes.items():
                strike = float(strike_price)

                # Analyze CE OI changes
                if strike_data.ce and strike_data.ce.oi_change:
                    oi_change = strike_data.ce.oi_change
                    total_ce_oi_change += oi_change.absolute_change

                    # Consider changes > 15% or > 100K contracts as significant
                    if abs(oi_change.percentage_change) > 15 or abs(oi_change.absolute_change) > 100000:
                        significant_changes.append({
                            'strike': strike,
                            'type': 'CE',
                            'change': oi_change.absolute_change,
                            'percentage': oi_change.percentage_change,
                            'current_oi': oi_change.current_oi,
                            'previous_oi': oi_change.previous_oi
                        })

                # Analyze PE OI changes
                if strike_data.pe and strike_data.pe.oi_change:
                    oi_change = strike_data.pe.oi_change
                    total_pe_oi_change += oi_change.absolute_change

                    # Consider changes > 15% or > 100K contracts as significant
                    if abs(oi_change.percentage_change) > 15 or abs(oi_change.absolute_change) > 100000:
                        significant_changes.append({
                            'strike': strike,
                            'type': 'PE',
                            'change': oi_change.absolute_change,
                            'percentage': oi_change.percentage_change,
                            'current_oi': oi_change.current_oi,
                            'previous_oi': oi_change.previous_oi
                        })

            # Generate analysis
            response = f"📊 **Open Interest Change Analysis:**\n\n"

            # Overall OI flow
            response += f"**Overall OI Flow:**\n"
            response += f"• Total CE OI Change: {total_ce_oi_change:+,}\n"
            response += f"• Total PE OI Change: {total_pe_oi_change:+,}\n"

            if total_ce_oi_change > total_pe_oi_change:
                response += f"• **Bias: Bearish** (More Call writing/Put unwinding)\n\n"
            elif total_pe_oi_change > total_ce_oi_change:
                response += f"• **Bias: Bullish** (More Put writing/Call unwinding)\n\n"
            else:
                response += f"• **Bias: Neutral** (Balanced OI changes)\n\n"

            # Significant changes
            if significant_changes:
                response += f"**Significant OI Changes (>15% or >100K contracts):**\n"

                # Sort by absolute change
                significant_changes.sort(key=lambda x: abs(x['change']), reverse=True)

                for change in significant_changes[:10]:  # Top 10
                    change_type = "📈 Build-up" if change['change'] > 0 else "📉 Unwinding"
                    response += f"• **{change['strike']} {change['type']}**: {change_type}\n"
                    response += f"  - Change: {change['change']:+,} ({change['percentage']:+.1f}%)\n"
                    response += f"  - OI: {change['previous_oi']:,} → {change['current_oi']:,}\n\n"
            else:
                response += f"**No significant OI changes detected.**\n\n"

            # Trading implications
            response += f"**Trading Implications:**\n"
            if len(significant_changes) > 0:
                ce_changes = [c for c in significant_changes if c['type'] == 'CE']
                pe_changes = [c for c in significant_changes if c['type'] == 'PE']

                if len(ce_changes) > len(pe_changes):
                    response += f"• High Call activity suggests resistance levels or bearish sentiment\n"
                elif len(pe_changes) > len(ce_changes):
                    response += f"• High Put activity suggests support levels or bullish sentiment\n"

                response += f"• Monitor these strikes for potential support/resistance\n"
                response += f"• Consider contrarian trades if OI build-up is excessive\n"
            else:
                response += f"• Limited institutional activity detected\n"
                response += f"• Market may be in consolidation phase\n"

            response += f"\n*Analysis based on OI changes from previous trading session*"
            return response

        except Exception as e:
            logger.error(f"Error analyzing OI changes: {e}")
            return f"Error analyzing OI changes: {str(e)}"
    
    async def analyze_option_chain_ai(self, underlying_scrip: int = 13, expiry: Optional[str] = None) -> str:
        """
        Get AI analysis of current option chain.
        
        Args:
            underlying_scrip: Security ID
            expiry: Specific expiry to analyze
            
        Returns:
            AI-generated option chain analysis
        """
        try:
            market_analysis = await self.analyze_current_market(underlying_scrip)
            
            if "error" in market_analysis:
                return f"Unable to analyze option chain: {market_analysis['error']}"
            
            # Generate AI analysis
            analysis = await self.ai_client.analyze_option_chain(
                option_chain_data=market_analysis,
                user_query="Provide a comprehensive analysis of this option chain"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing option chain: {e}")
            return f"Sorry, I encountered an error analyzing the option chain: {str(e)}"
    
    async def suggest_strategies(self, market_outlook: str = "neutral", risk_tolerance: str = "moderate") -> str:
        """
        Suggest option trading strategies based on current market conditions.
        
        Args:
            market_outlook: bullish/bearish/neutral
            risk_tolerance: low/moderate/high
            
        Returns:
            Strategy suggestions
        """
        try:
            market_analysis = await self.analyze_current_market()
            
            if "error" in market_analysis:
                return f"Unable to suggest strategies: {market_analysis['error']}"
            
            # Extract ATM strikes for strategy suggestions
            atm_strikes = market_analysis["market_data"]["atm_strikes"]
            underlying_price = market_analysis["underlying_price"]
            
            strategies = await self.ai_client.suggest_option_strategies(
                underlying_price=underlying_price,
                option_strikes=atm_strikes,
                market_outlook=market_outlook,
                risk_tolerance=risk_tolerance
            )
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error suggesting strategies: {e}")
            return f"Sorry, I encountered an error suggesting strategies: {str(e)}"
    
    async def _get_portfolio_context(self) -> Dict[str, Any]:
        """Get user's portfolio context for personalized advice."""
        try:
            # Get current positions and funds
            positions = self.api_client.get_positions()
            fund_limit = self.api_client.get_fund_limit()
            
            return {
                "available_balance": fund_limit.available_balance,
                "positions_count": len(positions),
                "has_options_positions": any(
                    pos.exchange_segment.value in ["NSE_FNO", "BSE_FNO"] 
                    for pos in positions
                ),
                "total_margin_used": fund_limit.margin_used
            }
            
        except Exception as e:
            logger.warning(f"Could not get portfolio context: {e}")
            return {"error": "Portfolio data unavailable"}

    async def get_oi_based_recommendation(
        self,
        underlying_scrip: int = 13,
        expiry: Optional[str] = None,
        include_ai_analysis: bool = True
    ) -> str:
        """
        Get OI-based trading recommendation using the specific algorithm.

        This method implements the core OI analysis algorithm:
        1. Find nearest strikes bracketing current price
        2. Compare PE vs CE OI at both strikes
        3. Generate bullish/bearish/neutral signals

        Args:
            underlying_scrip: Security ID (default: 13 for NIFTY)
            expiry: Option expiry date (uses nearest if None)
            include_ai_analysis: Whether to include AI-enhanced analysis

        Returns:
            Formatted recommendation with analysis
        """
        try:
            # Get OI-based recommendation
            recommendation = self.oi_recommendation_service.get_oi_recommendation(
                underlying_scrip, expiry
            )

            # Format the basic recommendation
            formatted_response = f"""
🎯 **OI-BASED TRADING RECOMMENDATION**

{recommendation.reasoning}

**Risk Assessment:**
{recommendation.risk_warning}

**Data Timestamp:** {recommendation.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()

            # Add AI-enhanced analysis if requested
            if include_ai_analysis and recommendation.signal != "neutral":
                try:
                    ai_context = {
                        "signal": recommendation.signal,
                        "confidence": recommendation.confidence,
                        "current_price": recommendation.current_price,
                        "lower_strike": recommendation.lower_strike,
                        "upper_strike": recommendation.upper_strike,
                        "lower_analysis": recommendation.lower_strike_analysis,
                        "upper_analysis": recommendation.upper_strike_analysis
                    }

                    ai_enhancement = await self.ai_client.answer_trading_question(
                        question=f"Based on this OI analysis showing a {recommendation.signal} signal with {recommendation.confidence:.1%} confidence, provide specific trading strategies and entry/exit points for NIFTY options.",
                        market_context=ai_context,
                        portfolio_context=None
                    )

                    formatted_response += f"\n\n🤖 **AI-ENHANCED STRATEGY SUGGESTIONS:**\n{ai_enhancement}"

                except Exception as e:
                    logger.warning(f"Could not get AI enhancement: {e}")

            return formatted_response

        except Exception as e:
            logger.error(f"Error getting OI-based recommendation: {e}")
            return f"Sorry, I encountered an error generating OI-based recommendations: {str(e)}"

    async def get_quick_oi_signal(self, underlying_scrip: int = 13) -> Dict[str, Any]:
        """
        Get a quick OI signal for dashboard or quick reference.

        Args:
            underlying_scrip: Security ID (default: 13 for NIFTY)

        Returns:
            Dictionary with quick signal data
        """
        try:
            recommendation = self.oi_recommendation_service.get_oi_recommendation(underlying_scrip)

            return {
                "signal": recommendation.signal,
                "confidence": recommendation.confidence,
                "current_price": recommendation.current_price,
                "lower_strike": recommendation.lower_strike,
                "upper_strike": recommendation.upper_strike,
                "summary": f"{recommendation.signal.upper()} signal with {recommendation.confidence:.1%} confidence",
                "timestamp": recommendation.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting quick OI signal: {e}")
            return {
                "signal": "error",
                "confidence": 0.0,
                "current_price": 0.0,
                "lower_strike": 0.0,
                "upper_strike": 0.0,
                "summary": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def detect_unusual_activity(self) -> str:
        """Detect unusual option activity and opportunities."""
        try:
            market_analysis = await self.analyze_current_market()
            
            if "error" in market_analysis:
                return f"Unable to detect unusual activity: {market_analysis['error']}"
            
            # Focus on volume and OI data
            option_data = []
            for strike_data in market_analysis["market_data"]["all_strikes"]:
                if strike_data["call_data"]:
                    option_data.append({
                        "type": "CALL",
                        "strike": strike_data["strike"],
                        "volume": strike_data["call_data"]["volume"],
                        "open_interest": strike_data["call_data"]["open_interest"],
                        "last_price": strike_data["call_data"]["last_price"]
                    })
                
                if strike_data["put_data"]:
                    option_data.append({
                        "type": "PUT",
                        "strike": strike_data["strike"],
                        "volume": strike_data["put_data"]["volume"],
                        "open_interest": strike_data["put_data"]["open_interest"],
                        "last_price": strike_data["put_data"]["last_price"]
                    })
            
            analysis = await self.ai_client.analyze_unusual_activity(option_data)
            return analysis

        except Exception as e:
            logger.error(f"Error detecting unusual activity: {e}")
            return f"Sorry, I encountered an error analyzing market activity: {str(e)}"

    def _assess_data_quality(self, option_chain) -> Dict[str, Any]:
        """Assess the quality of option chain data for analysis."""
        try:
            if not option_chain or not hasattr(option_chain, 'strikes'):
                return {
                    "total_strikes": 0,
                    "liquid_strikes": 0,
                    "liquidity_ratio": 0,
                    "total_volume": 0,
                    "total_oi": 0,
                    "quality_issues": ["No option chain data available"],
                    "is_reliable": False
                }

            # Handle both dictionary and list structures for strikes
            strikes_to_process = []
            if isinstance(option_chain.strikes, dict):
                strikes_to_process = list(option_chain.strikes.values())
                total_strikes = len(option_chain.strikes)
            elif isinstance(option_chain.strikes, list):
                strikes_to_process = option_chain.strikes
                total_strikes = len(option_chain.strikes)
            else:
                total_strikes = 0

            liquid_strikes = 0
            total_volume = 0
            total_oi = 0

            for strike_data in strikes_to_process:
                # Check call data
                if strike_data.ce and hasattr(strike_data.ce, 'volume') and hasattr(strike_data.ce, 'oi'):
                    if strike_data.ce.volume > 0 or strike_data.ce.oi > 0:
                        liquid_strikes += 1
                        total_volume += strike_data.ce.volume
                        total_oi += strike_data.ce.oi

                # Check put data
                if strike_data.pe and hasattr(strike_data.pe, 'volume') and hasattr(strike_data.pe, 'oi'):
                    if strike_data.pe.volume > 0 or strike_data.pe.oi > 0:
                        liquid_strikes += 1
                        total_volume += strike_data.pe.volume
                        total_oi += strike_data.pe.oi

            liquidity_ratio = liquid_strikes / (total_strikes * 2) if total_strikes > 0 else 0

            quality_issues = []
            if liquidity_ratio < 0.1:
                quality_issues.append("Very low liquidity - most strikes have zero volume/OI")
            if total_volume < 1000:
                quality_issues.append("Extremely low total volume")
            if total_oi < 1000:
                quality_issues.append("Very low open interest")

            return {
                "total_strikes": total_strikes,
                "liquid_strikes": liquid_strikes,
                "liquidity_ratio": liquidity_ratio,
                "total_volume": total_volume,
                "total_oi": total_oi,
                "quality_issues": quality_issues,
                "is_reliable": liquidity_ratio > 0.2 and total_volume > 10000
            }

        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return {
                "total_strikes": 0,
                "liquid_strikes": 0,
                "liquidity_ratio": 0,
                "total_volume": 0,
                "total_oi": 0,
                "quality_issues": [f"Error assessing data quality: {str(e)}"],
                "is_reliable": False
            }
