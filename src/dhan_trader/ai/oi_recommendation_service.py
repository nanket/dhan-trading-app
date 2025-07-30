"""
OI-based Trading Recommendation Service

This service implements the specific OI-based trading algorithm:
1. Find the two nearest strike prices that bracket the current Nifty index price
2. Analyze PE vs CE OI at both strikes
3. Generate bullish/bearish/neutral signals based on OI comparison
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..market_data.manager import MarketDataManager
from ..api.client import DhanAPIClient
from ..api.models import OptionChain, OptionChainStrike

logger = logging.getLogger(__name__)


@dataclass
class IndividualStrikeAnalysis:
    """Detailed analysis for an individual strike."""
    strike: float
    ce_oi: int
    pe_oi: int
    ce_volume: int
    pe_volume: int
    pe_ce_oi_ratio: float
    signal: str  # "bullish", "bearish", "neutral"
    significance: str  # "high", "medium", "low"
    distance_from_spot: float
    distance_category: str  # "ITM", "ATM", "OTM"
    reasoning: str
    trading_implications: str
    data_available: bool


@dataclass
class RangeOIAnalysis:
    """Range-based OI analysis around current price."""
    range_start: float
    range_end: float
    current_price: float
    total_ce_oi: int
    total_pe_oi: int
    pe_ce_ratio: float
    range_sentiment: str  # "bullish", "bearish", "neutral"
    confidence: float
    key_strikes: List[float]
    interpretation: str
    trading_implications: str


@dataclass
class OIRecommendation:
    """Enhanced OI-based trading recommendation with range and individual analysis."""
    # Overall recommendation
    signal: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0 to 1.0
    current_price: float

    # Range-based analysis
    range_analysis: RangeOIAnalysis

    # Individual strike analysis
    individual_strikes: List[IndividualStrikeAnalysis]

    # Key bracketing strikes (for backward compatibility)
    lower_strike: float
    upper_strike: float
    lower_strike_analysis: Dict[str, Any]  # For backward compatibility
    upper_strike_analysis: Dict[str, Any]  # For backward compatibility

    # Combined interpretation
    reasoning: str
    risk_warning: str
    timestamp: datetime
    ai_enhancement: Optional[str] = None


class OIRecommendationService:
    """Service for generating OI-based trading recommendations."""
    
    def __init__(self, market_data_manager: MarketDataManager, api_client: DhanAPIClient):
        """
        Initialize the OI recommendation service.
        
        Args:
            market_data_manager: Market data manager instance
            api_client: Dhan API client instance
        """
        self.market_data_manager = market_data_manager
        self.api_client = api_client
        logger.info("OI Recommendation Service initialized")
    
    def get_oi_recommendation(
        self,
        underlying_scrip: int = 13,  # NIFTY
        expiry: Optional[str] = None
    ) -> OIRecommendation:
        """
        Generate OI-based trading recommendation using the specific algorithm.
        
        Algorithm:
        1. Find two nearest strikes that bracket current price
        2. Analyze PE vs CE OI at both strikes
        3. Bullish if PE OI > CE OI at BOTH strikes
        4. Bearish if CE OI > PE OI at BOTH strikes
        5. Neutral if signals are mixed
        
        Args:
            underlying_scrip: Security ID (default: 13 for NIFTY)
            expiry: Option expiry date (uses nearest if None)
            
        Returns:
            OIRecommendation with signal and analysis
        """
        try:
            # Get option chain data with OI changes (same as API endpoint)
            option_chain = self.market_data_manager.get_option_chain_with_oi_changes(
                underlying_scrip, "IDX_I", expiry, use_cache=True
            )
            
            current_price = option_chain.underlying_price
            
            # Find the two nearest strikes that bracket the current price
            lower_strike, upper_strike = self._find_bracketing_strikes(
                current_price, option_chain.strikes
            )
            
            # Analyze OI at both strikes
            lower_analysis = self._analyze_strike_oi(
                lower_strike, option_chain.strikes, current_price
            )
            upper_analysis = self._analyze_strike_oi(
                upper_strike, option_chain.strikes, current_price
            )
            
            # Generate signal based on OI comparison
            signal, confidence, reasoning = self._generate_signal(
                lower_analysis, upper_analysis, current_price, lower_strike, upper_strike
            )
            
            # Generate risk warning
            risk_warning = self._generate_risk_warning(signal, confidence, current_price)

            # For backward compatibility, create simplified range and individual analysis
            range_analysis = self._create_simple_range_analysis(current_price, lower_strike, upper_strike, lower_analysis, upper_analysis)
            individual_strikes = self._create_simple_individual_analysis(lower_strike, upper_strike, lower_analysis, upper_analysis, current_price)

            return OIRecommendation(
                signal=signal,
                confidence=confidence,
                current_price=current_price,
                range_analysis=range_analysis,
                individual_strikes=individual_strikes,
                lower_strike=lower_strike,
                upper_strike=upper_strike,
                lower_strike_analysis=lower_analysis,
                upper_strike_analysis=upper_analysis,
                reasoning=reasoning,
                risk_warning=risk_warning,
                timestamp=datetime.now(),
                ai_enhancement=None
            )
            
        except Exception as e:
            logger.error(f"Error generating OI recommendation: {e}")
            # Return neutral recommendation with error info
            return self._create_error_recommendation(str(e))

    def _find_bracketing_strikes(
        self,
        current_price: float,
        strikes: Dict[str, OptionChainStrike]
    ) -> Tuple[float, float]:
        """
        Find two strikes that bracket the current price with approximately 100 points range.

        For NIFTY at 24863, should return (24800, 24900) - 100 points apart.

        Args:
            current_price: Current underlying price
            strikes: Dictionary of strike prices and data

        Returns:
            Tuple of (lower_strike, upper_strike) approximately 100 points apart
        """
        strike_prices = [float(strike) for strike in strikes.keys()]
        strike_prices.sort()

        # Target range of 100 points - find the best combination
        target_range = 100

        # Find all possible combinations that bracket the current price
        valid_combinations = []

        for i, lower in enumerate(strike_prices):
            for j, upper in enumerate(strike_prices[i+1:], i+1):
                # Check if this combination brackets the current price
                if lower <= current_price <= upper:
                    range_size = upper - lower
                    range_diff = abs(range_size - target_range)

                    # Prefer combinations closer to 100 points
                    valid_combinations.append({
                        'lower': lower,
                        'upper': upper,
                        'range': range_size,
                        'diff_from_target': range_diff,
                        'distance_from_center': abs((lower + upper) / 2 - current_price)
                    })

        if valid_combinations:
            # Sort by: 1) closest to 100 points, 2) most centered around current price
            valid_combinations.sort(key=lambda x: (x['diff_from_target'], x['distance_from_center']))

            best = valid_combinations[0]
            lower_strike = best['lower']
            upper_strike = best['upper']
        else:
            # Fallback to original logic if no valid combinations found
            lower_strike = None
            upper_strike = None

            for strike in reversed(strike_prices):
                if strike <= current_price:
                    lower_strike = strike
                    break

            for strike in strike_prices:
                if strike > current_price:
                    upper_strike = strike
                    break

            # Handle edge cases
            if lower_strike is None:
                lower_strike = strike_prices[0]
            if upper_strike is None:
                upper_strike = strike_prices[-1]

        return lower_strike, upper_strike

    def _analyze_strike_oi(
        self,
        strike_price: float,
        strikes: Dict[str, OptionChainStrike],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Analyze OI data for a specific strike price.

        Args:
            strike_price: Strike price to analyze
            strikes: Dictionary of strike prices and data
            current_price: Current underlying price

        Returns:
            Dictionary with OI analysis data
        """
        # Match the key format used by market data manager (with 6 decimal places)
        strike_key = f"{strike_price:.6f}"
        strike_data = strikes.get(strike_key)

        # Debug logging
        logger.info(f"Looking for strike {strike_price} with key '{strike_key}'")
        logger.info(f"Available strikes: {list(strikes.keys())}")
        if strike_data:
            logger.info(f"Found strike data: CE OI={strike_data.ce.oi if strike_data.ce else 'None'}, PE OI={strike_data.pe.oi if strike_data.pe else 'None'}")

        if not strike_data:
            return {
                "strike": strike_price,
                "ce_oi": 0,
                "pe_oi": 0,
                "ce_volume": 0,
                "pe_volume": 0,
                "pe_ce_oi_ratio": 0,
                "signal": "neutral",
                "data_available": False,
                "distance_from_spot": abs(strike_price - current_price)
            }

        # Extract CE and PE data
        ce_oi = strike_data.ce.oi if strike_data.ce else 0
        pe_oi = strike_data.pe.oi if strike_data.pe else 0
        ce_volume = strike_data.ce.volume if strike_data.ce else 0
        pe_volume = strike_data.pe.volume if strike_data.pe else 0

        # Calculate PE/CE OI ratio
        pe_ce_oi_ratio = pe_oi / ce_oi if ce_oi > 0 else float('inf') if pe_oi > 0 else 0

        # Determine signal for this strike
        if pe_oi > ce_oi:
            signal = "bullish"  # More put OI indicates support
        elif ce_oi > pe_oi:
            signal = "bearish"  # More call OI indicates resistance
        else:
            signal = "neutral"

        return {
            "strike": strike_price,
            "ce_oi": ce_oi,
            "pe_oi": pe_oi,
            "ce_volume": ce_volume,
            "pe_volume": pe_volume,
            "pe_ce_oi_ratio": pe_ce_oi_ratio,
            "signal": signal,
            "data_available": True,
            "distance_from_spot": abs(strike_price - current_price)
        }

    def _generate_signal(
        self,
        lower_analysis: Dict[str, Any],
        upper_analysis: Dict[str, Any],
        current_price: float,
        lower_strike: float,
        upper_strike: float
    ) -> Tuple[str, float, str]:
        """
        Generate overall signal based on OI analysis of both strikes.

        Algorithm:
        - Bullish: PE OI > CE OI at BOTH strikes
        - Bearish: CE OI > PE OI at BOTH strikes
        - Neutral: Mixed signals

        Args:
            lower_analysis: OI analysis for lower strike
            upper_analysis: OI analysis for upper strike
            current_price: Current underlying price
            lower_strike: Lower strike price
            upper_strike: Upper strike price

        Returns:
            Tuple of (signal, confidence, reasoning)
        """
        lower_signal = lower_analysis.get("signal", "neutral")
        upper_signal = upper_analysis.get("signal", "neutral")

        # Check data availability
        if not lower_analysis.get("data_available") or not upper_analysis.get("data_available"):
            return "neutral", 0.2, "Insufficient OI data available for analysis"

        # Apply the specific algorithm
        if lower_signal == "bullish" and upper_signal == "bullish":
            # PE OI > CE OI at both strikes - Strong support levels
            confidence = self._calculate_confidence(lower_analysis, upper_analysis, "bullish")
            reasoning = f"""
🟢 **BULLISH SIGNAL DETECTED**

**Analysis for Nifty at {current_price:.0f}:**
• Lower Strike {lower_strike:.0f}: PE OI ({lower_analysis['pe_oi']:,}) > CE OI ({lower_analysis['ce_oi']:,}) - Strong Support
• Upper Strike {upper_strike:.0f}: PE OI ({upper_analysis['pe_oi']:,}) > CE OI ({upper_analysis['ce_oi']:,}) - Strong Support

**Interpretation:**
Both key strikes show higher Put OI than Call OI, indicating strong institutional support levels. This suggests bullish sentiment and potential upward movement.

**Confidence Level:** {confidence:.1%}
            """.strip()
            return "bullish", confidence, reasoning

        elif lower_signal == "bearish" and upper_signal == "bearish":
            # CE OI > PE OI at both strikes - Strong resistance levels
            confidence = self._calculate_confidence(lower_analysis, upper_analysis, "bearish")
            reasoning = f"""
🔴 **BEARISH SIGNAL DETECTED**

**Analysis for Nifty at {current_price:.0f}:**
• Lower Strike {lower_strike:.0f}: CE OI ({lower_analysis['ce_oi']:,}) > PE OI ({lower_analysis['pe_oi']:,}) - Strong Resistance
• Upper Strike {upper_strike:.0f}: CE OI ({upper_analysis['ce_oi']:,}) > PE OI ({upper_analysis['pe_oi']:,}) - Strong Resistance

**Interpretation:**
Both key strikes show higher Call OI than Put OI, indicating strong institutional resistance levels. This suggests bearish sentiment and potential downward movement.

**Confidence Level:** {confidence:.1%}
            """.strip()
            return "bearish", confidence, reasoning

        else:
            # Mixed signals - Range-bound or unclear direction
            confidence = 0.3
            reasoning = f"""
🟡 **NEUTRAL/RANGE-BOUND SIGNAL**

**Analysis for Nifty at {current_price:.0f}:**
• Lower Strike {lower_strike:.0f}: {lower_signal.upper()} signal (PE: {lower_analysis['pe_oi']:,}, CE: {lower_analysis['ce_oi']:,})
• Upper Strike {upper_strike:.0f}: {upper_signal.upper()} signal (PE: {upper_analysis['pe_oi']:,}, CE: {upper_analysis['ce_oi']:,})

**Interpretation:**
Mixed signals from the two key strikes suggest no clear directional bias. Market may be range-bound between these levels or awaiting a catalyst for direction.

**Recommendation:** Wait for clearer signals or consider range-bound strategies.
            """.strip()
            return "neutral", confidence, reasoning

    def _calculate_confidence(
        self,
        lower_analysis: Dict[str, Any],
        upper_analysis: Dict[str, Any],
        signal: str
    ) -> float:
        """
        Calculate confidence level for the signal based on OI data quality and strength.

        Args:
            lower_analysis: OI analysis for lower strike
            upper_analysis: OI analysis for upper strike
            signal: The generated signal (bullish/bearish)

        Returns:
            Confidence level between 0.0 and 1.0
        """
        base_confidence = 0.6  # Base confidence for matching signals

        # Factor 1: OI magnitude (higher OI = higher confidence)
        total_oi = (lower_analysis['ce_oi'] + lower_analysis['pe_oi'] +
                   upper_analysis['ce_oi'] + upper_analysis['pe_oi'])

        if total_oi > 1000000:  # High OI
            oi_factor = 0.2
        elif total_oi > 500000:  # Medium OI
            oi_factor = 0.1
        else:  # Low OI
            oi_factor = 0.0

        # Factor 2: Signal strength (ratio difference)
        lower_ratio = lower_analysis.get('pe_ce_oi_ratio', 1)
        upper_ratio = upper_analysis.get('pe_ce_oi_ratio', 1)

        if signal == "bullish":
            # Higher PE/CE ratios = stronger bullish signal
            avg_ratio = (lower_ratio + upper_ratio) / 2
            if avg_ratio > 2.0:
                ratio_factor = 0.15
            elif avg_ratio > 1.5:
                ratio_factor = 0.1
            else:
                ratio_factor = 0.05
        elif signal == "bearish":
            # Lower PE/CE ratios = stronger bearish signal
            avg_ratio = (lower_ratio + upper_ratio) / 2
            if avg_ratio < 0.5:
                ratio_factor = 0.15
            elif avg_ratio < 0.7:
                ratio_factor = 0.1
            else:
                ratio_factor = 0.05
        else:
            ratio_factor = 0.0

        # Factor 3: Volume confirmation
        total_volume = (lower_analysis['ce_volume'] + lower_analysis['pe_volume'] +
                       upper_analysis['ce_volume'] + upper_analysis['pe_volume'])

        if total_volume > 100000:  # High volume
            volume_factor = 0.05
        else:
            volume_factor = 0.0

        final_confidence = min(0.95, base_confidence + oi_factor + ratio_factor + volume_factor)
        return final_confidence

    def _generate_risk_warning(self, signal: str, confidence: float, current_price: float) -> str:
        """
        Generate appropriate risk warning based on signal and confidence.

        Args:
            signal: Trading signal (bullish/bearish/neutral)
            confidence: Confidence level
            current_price: Current underlying price

        Returns:
            Risk warning message
        """
        base_warning = """
⚠️ **RISK DISCLAIMER:**
• Options trading involves substantial risk and may not be suitable for all investors
• Past performance does not guarantee future results
• This analysis is based on current OI data and market conditions can change rapidly
• Always use proper position sizing and risk management
• Consider consulting with a financial advisor before making trading decisions
        """.strip()

        if confidence < 0.4:
            return f"""
🚨 **LOW CONFIDENCE WARNING:**
The current analysis shows low confidence ({confidence:.1%}) due to insufficient or conflicting OI data.
Exercise extreme caution and consider waiting for clearer market signals.

{base_warning}
            """.strip()
        elif signal == "neutral":
            return f"""
⚡ **RANGE-BOUND MARKET:**
Mixed signals suggest a range-bound market around {current_price:.0f}.
Consider range-bound strategies or wait for a clear breakout.

{base_warning}
            """.strip()
        else:
            return f"""
📊 **DIRECTIONAL SIGNAL ({confidence:.1%} confidence):**
While the analysis suggests a {signal} bias, always validate with other technical indicators
and maintain strict risk management protocols.

{base_warning}
            """.strip()

    def _analyze_oi_range(
        self,
        current_price: float,
        strikes: Dict[str, OptionChainStrike],
        range_width: int
    ) -> RangeOIAnalysis:
        """
        Analyze OI across a range of strikes around current price.

        Args:
            current_price: Current underlying price
            strikes: Dictionary of strike data
            range_width: Width of range around current price

        Returns:
            RangeOIAnalysis with aggregated data and sentiment
        """
        range_start = current_price - range_width
        range_end = current_price + range_width

        total_ce_oi = 0
        total_pe_oi = 0
        key_strikes = []

        # Aggregate OI data for strikes within range
        for strike_key, strike_data in strikes.items():
            strike_price = float(strike_key)

            if range_start <= strike_price <= range_end:
                key_strikes.append(strike_price)

                if strike_data.ce:
                    total_ce_oi += strike_data.ce.oi
                if strike_data.pe:
                    total_pe_oi += strike_data.pe.oi

        # Calculate PE/CE ratio and determine sentiment
        pe_ce_ratio = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

        # Determine range sentiment
        if pe_ce_ratio > 1.2:  # Strong put bias
            range_sentiment = "bullish"
            confidence = min(0.8, pe_ce_ratio / 2)
        elif pe_ce_ratio < 0.8:  # Strong call bias
            range_sentiment = "bearish"
            confidence = min(0.8, (2 - pe_ce_ratio) / 2)
        else:  # Balanced
            range_sentiment = "neutral"
            confidence = 0.3

        # Generate interpretation
        interpretation = self._generate_range_interpretation(
            range_sentiment, pe_ce_ratio, total_ce_oi, total_pe_oi, current_price
        )

        # Generate trading implications
        trading_implications = self._generate_range_trading_implications(
            range_sentiment, confidence, current_price, range_start, range_end
        )

        key_strikes.sort()

        return RangeOIAnalysis(
            range_start=range_start,
            range_end=range_end,
            current_price=current_price,
            total_ce_oi=total_ce_oi,
            total_pe_oi=total_pe_oi,
            pe_ce_ratio=pe_ce_ratio,
            range_sentiment=range_sentiment,
            confidence=confidence,
            key_strikes=key_strikes,
            interpretation=interpretation,
            trading_implications=trading_implications
        )

    def _analyze_individual_strikes(
        self,
        current_price: float,
        strikes: Dict[str, OptionChainStrike],
        range_width: int
    ) -> List[IndividualStrikeAnalysis]:
        """
        Analyze individual strikes within the range for detailed insights.

        Args:
            current_price: Current underlying price
            strikes: Dictionary of strike data
            range_width: Width of range around current price

        Returns:
            List of IndividualStrikeAnalysis for key strikes
        """
        individual_analyses = []
        range_start = current_price - range_width
        range_end = current_price + range_width

        # Get strikes within range and sort them
        relevant_strikes = []
        for strike_key, strike_data in strikes.items():
            strike_price = float(strike_key)
            if range_start <= strike_price <= range_end:
                relevant_strikes.append((strike_price, strike_key, strike_data))

        relevant_strikes.sort(key=lambda x: x[0])  # Sort by strike price

        # Analyze each strike
        for strike_price, strike_key, strike_data in relevant_strikes:
            analysis = self._create_individual_strike_analysis(
                strike_price, strike_data, current_price
            )
            individual_analyses.append(analysis)

        return individual_analyses

    def _create_individual_strike_analysis(
        self,
        strike_price: float,
        strike_data: OptionChainStrike,
        current_price: float
    ) -> IndividualStrikeAnalysis:
        """Create detailed analysis for an individual strike."""
        # Extract data
        ce_oi = strike_data.ce.oi if strike_data.ce else 0
        pe_oi = strike_data.pe.oi if strike_data.pe else 0
        ce_volume = strike_data.ce.volume if strike_data.ce else 0
        pe_volume = strike_data.pe.volume if strike_data.pe else 0

        # Calculate metrics
        pe_ce_oi_ratio = pe_oi / ce_oi if ce_oi > 0 else 0
        distance_from_spot = strike_price - current_price

        # Determine signal
        if pe_oi > ce_oi * 1.2:  # Strong put bias
            signal = "bullish"
        elif ce_oi > pe_oi * 1.2:  # Strong call bias
            signal = "bearish"
        else:
            signal = "neutral"

        # Determine significance based on total OI
        total_oi = ce_oi + pe_oi
        if total_oi > 10_000_000:  # 10M+
            significance = "high"
        elif total_oi > 5_000_000:  # 5M+
            significance = "medium"
        else:
            significance = "low"

        # Determine distance category
        abs_distance = abs(distance_from_spot)
        if abs_distance <= 25:
            distance_category = "ATM"
        elif (distance_from_spot > 0 and signal == "bearish") or (distance_from_spot < 0 and signal == "bullish"):
            distance_category = "ITM"
        else:
            distance_category = "OTM"

        # Generate reasoning and implications
        reasoning = self._generate_strike_reasoning(
            strike_price, signal, pe_oi, ce_oi, distance_from_spot, significance
        )

        trading_implications = self._generate_strike_trading_implications(
            strike_price, signal, distance_category, significance, current_price
        )

        return IndividualStrikeAnalysis(
            strike=strike_price,
            ce_oi=ce_oi,
            pe_oi=pe_oi,
            ce_volume=ce_volume,
            pe_volume=pe_volume,
            pe_ce_oi_ratio=pe_ce_oi_ratio,
            signal=signal,
            significance=significance,
            distance_from_spot=distance_from_spot,
            distance_category=distance_category,
            reasoning=reasoning,
            trading_implications=trading_implications,
            data_available=ce_oi > 0 or pe_oi > 0
        )

    def _generate_range_interpretation(
        self,
        sentiment: str,
        pe_ce_ratio: float,
        total_ce_oi: int,
        total_pe_oi: int,
        current_price: float
    ) -> str:
        """Generate interpretation for range-based analysis."""
        if sentiment == "bullish":
            return f"""
🟢 **BULLISH RANGE SENTIMENT**
The {current_price-50:.0f}-{current_price+50:.0f} range shows strong put bias with PE/CE ratio of {pe_ce_ratio:.2f}.
Total PE OI: {total_pe_oi:,} vs CE OI: {total_ce_oi:,}
This suggests institutional support and potential upward momentum.
            """.strip()
        elif sentiment == "bearish":
            return f"""
🔴 **BEARISH RANGE SENTIMENT**
The {current_price-50:.0f}-{current_price+50:.0f} range shows strong call bias with PE/CE ratio of {pe_ce_ratio:.2f}.
Total PE OI: {total_pe_oi:,} vs CE OI: {total_ce_oi:,}
This suggests institutional resistance and potential downward pressure.
            """.strip()
        else:
            return f"""
🟡 **NEUTRAL RANGE SENTIMENT**
The {current_price-50:.0f}-{current_price+50:.0f} range shows balanced OI with PE/CE ratio of {pe_ce_ratio:.2f}.
Total PE OI: {total_pe_oi:,} vs CE OI: {total_ce_oi:,}
This suggests range-bound movement or indecision in the market.
            """.strip()

    def _generate_range_trading_implications(
        self,
        sentiment: str,
        confidence: float,
        current_price: float,
        range_start: float,
        range_end: float
    ) -> str:
        """Generate trading implications for range analysis."""
        if sentiment == "bullish" and confidence > 0.6:
            return f"Consider bullish strategies. Range {range_start:.0f}-{range_end:.0f} may act as support zone."
        elif sentiment == "bearish" and confidence > 0.6:
            return f"Consider bearish strategies. Range {range_start:.0f}-{range_end:.0f} may act as resistance zone."
        else:
            return f"Range-bound strategies recommended. Trade within {range_start:.0f}-{range_end:.0f} range."

    def _generate_strike_reasoning(
        self,
        strike: float,
        signal: str,
        pe_oi: int,
        ce_oi: int,
        distance: float,
        significance: str
    ) -> str:
        """Generate reasoning for individual strike analysis."""
        direction = "above" if distance > 0 else "below"
        abs_distance = abs(distance)

        if signal == "bullish":
            return f"Strike {strike:.0f} ({abs_distance:.0f} pts {direction} spot) shows bullish bias with PE OI {pe_oi:,} > CE OI {ce_oi:,}. {significance.title()} significance."
        elif signal == "bearish":
            return f"Strike {strike:.0f} ({abs_distance:.0f} pts {direction} spot) shows bearish bias with CE OI {ce_oi:,} > PE OI {pe_oi:,}. {significance.title()} significance."
        else:
            return f"Strike {strike:.0f} ({abs_distance:.0f} pts {direction} spot) shows neutral bias with balanced OI. {significance.title()} significance."

    def _generate_strike_trading_implications(
        self,
        strike: float,
        signal: str,
        distance_category: str,
        significance: str,
        current_price: float
    ) -> str:
        """Generate trading implications for individual strike."""
        if significance == "high":
            if signal == "bullish":
                return f"Strong support expected at {strike:.0f}. Consider bullish strategies if price approaches this level."
            elif signal == "bearish":
                return f"Strong resistance expected at {strike:.0f}. Consider bearish strategies if price approaches this level."
            else:
                return f"Key level at {strike:.0f} with balanced interest. Watch for breakout direction."
        else:
            return f"Moderate interest at {strike:.0f}. Monitor for confirmation with other strikes."

    def _generate_enhanced_signal(
        self,
        range_analysis: RangeOIAnalysis,
        individual_strikes: List[IndividualStrikeAnalysis],
        lower_analysis: Dict[str, Any],
        upper_analysis: Dict[str, Any],
        current_price: float,
        lower_strike: float,
        upper_strike: float
    ) -> Tuple[str, float, str]:
        """
        Generate enhanced signal combining range and individual analysis.

        Returns:
            Tuple of (signal, confidence, reasoning)
        """
        # Get range sentiment and confidence
        range_sentiment = range_analysis.range_sentiment
        range_confidence = range_analysis.confidence

        # Get traditional bracketing signal
        traditional_signal, traditional_confidence, _ = self._generate_signal(
            lower_analysis, upper_analysis, current_price, lower_strike, upper_strike
        )

        # Count individual strike signals
        bullish_strikes = sum(1 for strike in individual_strikes if strike.signal == "bullish")
        bearish_strikes = sum(1 for strike in individual_strikes if strike.signal == "bearish")
        neutral_strikes = sum(1 for strike in individual_strikes if strike.signal == "neutral")

        # Determine final signal by combining all factors
        if range_sentiment == traditional_signal and range_sentiment != "neutral":
            # Range and traditional agree on direction
            final_signal = range_sentiment
            final_confidence = min(0.9, (range_confidence + traditional_confidence) / 2 + 0.1)
        elif range_sentiment == "neutral" and traditional_signal != "neutral":
            # Range neutral, traditional has direction
            final_signal = traditional_signal
            final_confidence = traditional_confidence * 0.7  # Reduce confidence
        elif range_sentiment != "neutral" and traditional_signal == "neutral":
            # Range has direction, traditional neutral
            final_signal = range_sentiment
            final_confidence = range_confidence * 0.8  # Slight reduction
        elif bullish_strikes > bearish_strikes and bullish_strikes > neutral_strikes:
            # Individual strikes favor bullish
            final_signal = "bullish"
            final_confidence = min(0.7, bullish_strikes / len(individual_strikes))
        elif bearish_strikes > bullish_strikes and bearish_strikes > neutral_strikes:
            # Individual strikes favor bearish
            final_signal = "bearish"
            final_confidence = min(0.7, bearish_strikes / len(individual_strikes))
        else:
            # Mixed or unclear signals
            final_signal = "neutral"
            final_confidence = 0.3

        # Generate comprehensive reasoning
        reasoning = self._generate_comprehensive_reasoning(
            final_signal, range_analysis, individual_strikes,
            lower_analysis, upper_analysis, current_price, lower_strike, upper_strike
        )

        return final_signal, final_confidence, reasoning

    def _generate_comprehensive_reasoning(
        self,
        final_signal: str,
        range_analysis: RangeOIAnalysis,
        individual_strikes: List[IndividualStrikeAnalysis],
        lower_analysis: Dict[str, Any],
        upper_analysis: Dict[str, Any],
        current_price: float,
        lower_strike: float,
        upper_strike: float
    ) -> str:
        """Generate comprehensive reasoning combining all analysis types."""

        # Header with current price
        reasoning = f"📊 **COMPREHENSIVE OI ANALYSIS for NIFTY at {current_price:.1f}**\n\n"

        # Range Analysis Section
        reasoning += "🎯 **RANGE ANALYSIS:**\n"
        reasoning += f"• Range {range_analysis.range_start:.0f}-{range_analysis.range_end:.0f}: **{range_analysis.range_sentiment.upper()}** sentiment\n"
        reasoning += f"• Total PE OI: {range_analysis.total_pe_oi:,} | Total CE OI: {range_analysis.total_ce_oi:,}\n"
        reasoning += f"• PE/CE Ratio: {range_analysis.pe_ce_ratio:.2f} | Confidence: {range_analysis.confidence:.1%}\n"
        reasoning += f"• {range_analysis.trading_implications}\n\n"

        # Individual Strikes Section
        reasoning += "🎯 **KEY STRIKE ANALYSIS:**\n"
        for strike in individual_strikes[:5]:  # Show top 5 strikes
            if strike.significance in ["high", "medium"]:
                reasoning += f"• **{strike.strike:.0f}** ({strike.distance_category}): {strike.signal.upper()} "
                reasoning += f"[PE: {strike.pe_oi:,}, CE: {strike.ce_oi:,}] - {strike.significance} significance\n"

        reasoning += "\n"

        # Traditional Bracketing Analysis
        reasoning += "🎯 **BRACKETING STRIKES:**\n"
        reasoning += f"• Lower Strike {lower_strike:.0f}: **{lower_analysis['signal'].upper()}** "
        reasoning += f"(PE: {lower_analysis['pe_oi']:,}, CE: {lower_analysis['ce_oi']:,})\n"
        reasoning += f"• Upper Strike {upper_strike:.0f}: **{upper_analysis['signal'].upper()}** "
        reasoning += f"(PE: {upper_analysis['pe_oi']:,}, CE: {upper_analysis['ce_oi']:,})\n\n"

        # Final Interpretation
        if final_signal == "bullish":
            reasoning += "🟢 **BULLISH CONCLUSION:**\n"
            reasoning += "Multiple analysis layers suggest upward bias. Strong put interest indicates institutional support.\n"
            reasoning += "**Strategy:** Consider bullish positions with proper risk management.\n"
        elif final_signal == "bearish":
            reasoning += "🔴 **BEARISH CONCLUSION:**\n"
            reasoning += "Multiple analysis layers suggest downward pressure. Strong call interest indicates institutional resistance.\n"
            reasoning += "**Strategy:** Consider bearish positions with proper risk management.\n"
        else:
            reasoning += "🟡 **NEUTRAL/RANGE-BOUND CONCLUSION:**\n"
            reasoning += "Mixed signals across analysis layers suggest consolidation or indecision.\n"
            reasoning += "**Strategy:** Range-bound strategies or wait for clearer directional signals.\n"

        return reasoning

    def _create_simple_range_analysis(
        self,
        current_price: float,
        lower_strike: float,
        upper_strike: float,
        lower_analysis: Dict[str, Any],
        upper_analysis: Dict[str, Any]
    ) -> RangeOIAnalysis:
        """Create simplified range analysis for backward compatibility."""
        total_ce_oi = lower_analysis.get('ce_oi', 0) + upper_analysis.get('ce_oi', 0)
        total_pe_oi = lower_analysis.get('pe_oi', 0) + upper_analysis.get('pe_oi', 0)
        pe_ce_ratio = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

        # Simple sentiment based on bracketing strikes
        lower_signal = lower_analysis.get('signal', 'neutral')
        upper_signal = upper_analysis.get('signal', 'neutral')

        if lower_signal == upper_signal and lower_signal != 'neutral':
            range_sentiment = lower_signal
            confidence = 0.6
        else:
            range_sentiment = 'neutral'
            confidence = 0.3

        return RangeOIAnalysis(
            range_start=lower_strike,
            range_end=upper_strike,
            current_price=current_price,
            total_ce_oi=total_ce_oi,
            total_pe_oi=total_pe_oi,
            pe_ce_ratio=pe_ce_ratio,
            range_sentiment=range_sentiment,
            confidence=confidence,
            key_strikes=[lower_strike, upper_strike],
            interpretation=f"Simplified analysis based on bracketing strikes {lower_strike:.0f}-{upper_strike:.0f}",
            trading_implications=f"Monitor key levels at {lower_strike:.0f} and {upper_strike:.0f}"
        )

    def _create_simple_individual_analysis(
        self,
        lower_strike: float,
        upper_strike: float,
        lower_analysis: Dict[str, Any],
        upper_analysis: Dict[str, Any],
        current_price: float
    ) -> List[IndividualStrikeAnalysis]:
        """Create simplified individual analysis for backward compatibility."""
        analyses = []

        # Lower strike analysis
        if lower_analysis.get('data_available', False):
            analyses.append(IndividualStrikeAnalysis(
                strike=lower_strike,
                ce_oi=lower_analysis.get('ce_oi', 0),
                pe_oi=lower_analysis.get('pe_oi', 0),
                ce_volume=lower_analysis.get('ce_volume', 0),
                pe_volume=lower_analysis.get('pe_volume', 0),
                pe_ce_oi_ratio=lower_analysis.get('pe_ce_oi_ratio', 0),
                signal=lower_analysis.get('signal', 'neutral'),
                significance="medium",
                distance_from_spot=lower_analysis.get('distance_from_spot', 0),
                distance_category="ATM" if abs(lower_analysis.get('distance_from_spot', 0)) <= 25 else "OTM",
                reasoning=f"Lower bracketing strike analysis",
                trading_implications=f"Key support/resistance level",
                data_available=lower_analysis.get('data_available', False)
            ))

        # Upper strike analysis
        if upper_analysis.get('data_available', False):
            analyses.append(IndividualStrikeAnalysis(
                strike=upper_strike,
                ce_oi=upper_analysis.get('ce_oi', 0),
                pe_oi=upper_analysis.get('pe_oi', 0),
                ce_volume=upper_analysis.get('ce_volume', 0),
                pe_volume=upper_analysis.get('pe_volume', 0),
                pe_ce_oi_ratio=upper_analysis.get('pe_ce_oi_ratio', 0),
                signal=upper_analysis.get('signal', 'neutral'),
                significance="medium",
                distance_from_spot=upper_analysis.get('distance_from_spot', 0),
                distance_category="ATM" if abs(upper_analysis.get('distance_from_spot', 0)) <= 25 else "OTM",
                reasoning=f"Upper bracketing strike analysis",
                trading_implications=f"Key support/resistance level",
                data_available=upper_analysis.get('data_available', False)
            ))

        return analyses

    def get_enhanced_oi_recommendation(
        self,
        underlying_scrip: int = 13,  # NIFTY
        expiry: Optional[str] = None,
        range_width: int = 100,  # Range width around current price
        include_ai_analysis: bool = False
    ) -> OIRecommendation:
        """
        Generate enhanced OI-based trading recommendation with comprehensive analysis.

        Args:
            underlying_scrip: Security ID (default: 13 for NIFTY)
            expiry: Option expiry date (uses nearest if None)
            range_width: Width of range around current price for analysis
            include_ai_analysis: Whether to include AI enhancement

        Returns:
            Enhanced OIRecommendation with range and individual analysis
        """
        try:
            # Get option chain data with OI changes (same as API endpoint)
            option_chain = self.market_data_manager.get_option_chain_with_oi_changes(
                underlying_scrip, "IDX_I", expiry, use_cache=True
            )

            current_price = option_chain.underlying_price

            # Perform range-based OI analysis
            range_analysis = self._analyze_oi_range(
                current_price, option_chain.strikes, range_width
            )

            # Perform individual strike analysis for key strikes
            individual_strikes = self._analyze_individual_strikes(
                current_price, option_chain.strikes, range_width
            )

            # Find the two nearest strikes that bracket the current price (for backward compatibility)
            lower_strike, upper_strike = self._find_bracketing_strikes(
                current_price, option_chain.strikes
            )

            # Analyze OI at both strikes (for backward compatibility)
            lower_analysis = self._analyze_strike_oi(
                lower_strike, option_chain.strikes, current_price
            )
            upper_analysis = self._analyze_strike_oi(
                upper_strike, option_chain.strikes, current_price
            )

            # Generate combined signal based on range and individual analysis
            signal, confidence, reasoning = self._generate_enhanced_signal(
                range_analysis, individual_strikes, lower_analysis, upper_analysis,
                current_price, lower_strike, upper_strike
            )

            # Generate risk warning
            risk_warning = self._generate_risk_warning(signal, confidence, current_price)

            return OIRecommendation(
                signal=signal,
                confidence=confidence,
                current_price=current_price,
                range_analysis=range_analysis,
                individual_strikes=individual_strikes,
                lower_strike=lower_strike,
                upper_strike=upper_strike,
                lower_strike_analysis=lower_analysis,
                upper_strike_analysis=upper_analysis,
                reasoning=reasoning,
                risk_warning=risk_warning,
                timestamp=datetime.now(),
                ai_enhancement=None  # Will be added if requested
            )

        except Exception as e:
            logger.error(f"Error generating enhanced OI recommendation: {e}")
            return self._create_error_recommendation(str(e))
