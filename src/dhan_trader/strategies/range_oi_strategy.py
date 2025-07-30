"""
Range-based Open Interest (OI) Strategy for Nifty Options Trading

This strategy implements the specific logic:
1. Define Range OI around current Nifty price
2. Compare PE vs CE OI for nearest strikes
3. Generate bullish/bearish/neutral signals based on OI comparison
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..api.models import OptionChain, OptionChainStrike
from ..exceptions import StrategyError

logger = logging.getLogger(__name__)


@dataclass
class RangeOIAnalysis:
    """Analysis result for range-based OI strategy."""
    current_price: float
    lower_strike: float
    upper_strike: float
    lower_strike_pe_oi: int
    lower_strike_ce_oi: int
    upper_strike_pe_oi: int
    upper_strike_ce_oi: int
    lower_strike_signal: str  # "support", "resistance", "neutral"
    upper_strike_signal: str  # "support", "resistance", "neutral"
    overall_signal: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    timestamp: datetime


@dataclass
class StrikeOIData:
    """OI data for a specific strike."""
    strike_price: float
    pe_oi: int
    ce_oi: int
    pe_volume: int
    ce_volume: int
    pe_ltp: float
    ce_ltp: float


class RangeOIStrategy:
    """
    Range-based Open Interest Strategy
    
    Strategy Logic:
    1. Find nearest strikes to current price (e.g., 25400 and 25500 for price 25440)
    2. Compare PE OI vs CE OI for each strike
    3. Generate signals:
       - PE > CE on both strikes → Bullish (Support)
       - CE > PE on both strikes → Bearish (Resistance)
       - Mixed signals → Neutral/Range-bound
    """
    
    def __init__(self, market_data_manager):
        """Initialize the Range OI Strategy.
        
        Args:
            market_data_manager: Market data manager instance
        """
        self.market_data_manager = market_data_manager
        self.signal_history = []
        
        # Strategy parameters
        self.strike_interval = 50  # Standard Nifty strike interval
        self.range_interval = 100  # Range interval for opening-based analysis (e.g., 24600-24700)
        self.min_oi_threshold = 1000  # Minimum OI to consider valid
        self.strong_signal_ratio = 1.5  # PE/CE ratio for strong signals
        
    def analyze_range_oi(
        self,
        underlying_scrip: int = 13,  # NIFTY
        expiry: Optional[str] = None,
        current_price: Optional[float] = None,
        lower_strike: Optional[float] = None,
        upper_strike: Optional[float] = None
    ) -> RangeOIAnalysis:
        """
        Analyze range-based OI for trading signals.

        Args:
            underlying_scrip: Security ID (default: 13 for NIFTY)
            expiry: Option expiry date (uses nearest if None)
            current_price: Current underlying price (fetched if None)
            lower_strike: Lower strike price (auto-detect if None)
            upper_strike: Upper strike price (auto-detect if None)

        Returns:
            RangeOIAnalysis with complete analysis
        """
        try:
            # Get option chain data
            option_chain = self.market_data_manager.get_option_chain(
                underlying_scrip, "IDX_I", expiry, use_cache=False
            )
            
            if not option_chain or not option_chain.strikes:
                raise StrategyError("No option chain data available")
            
            # Use current price from option chain if not provided
            if current_price is None:
                current_price = option_chain.underlying_price

            # Find strikes - use provided strikes or auto-detect nearest strikes
            if lower_strike is None or upper_strike is None:
                auto_lower, auto_upper = self._find_nearest_strikes(current_price)
                lower_strike = lower_strike or auto_lower
                upper_strike = upper_strike or auto_upper
            
            # Extract OI data for both strikes
            lower_oi_data = self._extract_strike_oi_data(option_chain.strikes, lower_strike)
            upper_oi_data = self._extract_strike_oi_data(option_chain.strikes, upper_strike)
            
            if not lower_oi_data or not upper_oi_data:
                raise StrategyError(f"OI data not available for strikes {lower_strike} or {upper_strike}")
            
            # Analyze individual strikes
            lower_signal = self._analyze_strike_signal(lower_oi_data)
            upper_signal = self._analyze_strike_signal(upper_oi_data)
            
            # Generate overall signal
            overall_signal, confidence, reasoning = self._generate_overall_signal(
                lower_signal, upper_signal, lower_oi_data, upper_oi_data
            )
            
            # Create analysis result
            analysis = RangeOIAnalysis(
                current_price=current_price,
                lower_strike=lower_strike,
                upper_strike=upper_strike,
                lower_strike_pe_oi=lower_oi_data.pe_oi,
                lower_strike_ce_oi=lower_oi_data.ce_oi,
                upper_strike_pe_oi=upper_oi_data.pe_oi,
                upper_strike_ce_oi=upper_oi_data.ce_oi,
                lower_strike_signal=lower_signal,
                upper_strike_signal=upper_signal,
                overall_signal=overall_signal,
                confidence=confidence,
                reasoning=reasoning,
                timestamp=datetime.now()
            )
            
            # Store in history
            self.signal_history.append(analysis)
            
            # Keep only last 100 signals
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]
            
            return analysis

        except Exception as e:
            logger.error(f"Error in range OI analysis: {e}")
            raise StrategyError(f"Range OI analysis failed: {str(e)}")

    def get_individual_strike_oi(
        self,
        strike_price: float,
        underlying_scrip: int = 13,  # NIFTY
        expiry: Optional[str] = None
    ) -> Optional[StrikeOIData]:
        """
        Get OI data for a specific individual strike price.

        Args:
            strike_price: Target strike price (e.g., 25500)
            underlying_scrip: Security ID (default: 13 for NIFTY)
            expiry: Option expiry date (uses nearest if None)

        Returns:
            StrikeOIData for the specific strike or None if not found
        """
        try:
            # Get option chain data
            option_chain = self.market_data_manager.get_option_chain(
                underlying_scrip, "IDX_I", expiry, use_cache=False
            )

            if not option_chain or not option_chain.strikes:
                logger.error("No option chain data available")
                return None

            # Extract OI data for the specific strike
            strike_oi_data = self._extract_strike_oi_data(option_chain.strikes, strike_price)

            if not strike_oi_data:
                logger.warning(f"No OI data found for strike {strike_price}")
                return None

            return strike_oi_data

        except Exception as e:
            logger.error(f"Error getting individual strike OI for {strike_price}: {e}")
            return None

    def analyze_opening_range_oi(
        self,
        opening_price: float,
        underlying_scrip: int = 13,  # NIFTY
        expiry: Optional[str] = None,
        range_interval: int = 100
    ) -> RangeOIAnalysis:
        """
        Analyze Range OI based on opening price with specified range interval.

        For opening price 24619:
        - With range_interval=100: Analyzes 24600-24700
        - With range_interval=50: Analyzes 24600-24650

        Args:
            opening_price: Today's opening price (e.g., 24619)
            underlying_scrip: Security ID (default: 13 for NIFTY)
            expiry: Option expiry date (uses nearest if None)
            range_interval: Range interval in points (default: 100)

        Returns:
            RangeOIAnalysis for the opening-based range
        """
        # Calculate range based on opening price
        # For 24619 with 100-point interval: 24600-24700
        lower_bound = (int(opening_price / range_interval) * range_interval)
        upper_bound = lower_bound + range_interval

        logger.info(f"Opening price: {opening_price}, Range: {lower_bound}-{upper_bound}")

        return self.analyze_range_oi(
            underlying_scrip=underlying_scrip,
            expiry=expiry,
            current_price=opening_price,
            lower_strike=float(lower_bound),
            upper_strike=float(upper_bound)
        )

    def _find_nearest_strikes(self, current_price: float) -> Tuple[float, float]:
        """
        Find the nearest strikes below and above current price.

        For example, if current price is 25440:
        - Lower strike: 25400 (nearest 50-point interval below)
        - Upper strike: 25500 (nearest 50-point interval above)

        Args:
            current_price: Current underlying price

        Returns:
            Tuple of (lower_strike, upper_strike)
        """
        # Find the lower strike (nearest 50-point interval below current price)
        lower_strike = (int(current_price / self.strike_interval) * self.strike_interval)

        # Find the upper strike (next 50-point interval above)
        upper_strike = lower_strike + self.strike_interval

        return float(lower_strike), float(upper_strike)
    
    def _extract_strike_oi_data(
        self,
        strikes,
        strike_price: float
    ) -> Optional[StrikeOIData]:
        """
        Extract OI data for a specific strike.

        Args:
            strikes: Option chain strikes data (list or dict)
            strike_price: Target strike price

        Returns:
            StrikeOIData if found, None otherwise
        """
        # Handle both list and dict formats
        strike_data = None

        if isinstance(strikes, list):
            # API returns list format
            for strike in strikes:
                if isinstance(strike, dict) and strike.get('strike') == strike_price:
                    # Convert dict to object-like access for consistent interface
                    class StrikeObj:
                        def __init__(self, data):
                            self.strike = data['strike']
                            # Handle PE data
                            pe_data = data.get('pe', {})
                            if pe_data:
                                self.pe = type('PE', (), {
                                    'oi': pe_data.get('oi', 0),
                                    'volume': pe_data.get('volume', 0),
                                    'last_price': pe_data.get('last_price', 0.0)
                                })()
                            else:
                                self.pe = None

                            # Handle CE data
                            ce_data = data.get('ce', {})
                            if ce_data:
                                self.ce = type('CE', (), {
                                    'oi': ce_data.get('oi', 0),
                                    'volume': ce_data.get('volume', 0),
                                    'last_price': ce_data.get('last_price', 0.0)
                                })()
                            else:
                                self.ce = None

                    strike_data = StrikeObj(strike)
                    break
                elif hasattr(strike, 'strike') and strike.strike == strike_price:
                    # Object format (legacy)
                    strike_data = strike
                    break
        elif isinstance(strikes, dict):
            # Legacy dict format
            strike_key = str(int(strike_price))
            if strike_key in strikes:
                strike_data = strikes[strike_key]

        if not strike_data:
            logger.warning(f"Strike {strike_price} not found in option chain")
            return None

        # Extract PE and CE data
        pe_data = strike_data.pe if hasattr(strike_data, 'pe') else None
        ce_data = strike_data.ce if hasattr(strike_data, 'ce') else None

        if not pe_data or not ce_data:
            logger.warning(f"Incomplete option data for strike {strike_price}")
            return None
        
        return StrikeOIData(
            strike_price=strike_price,
            pe_oi=pe_data.oi or 0,
            ce_oi=ce_data.oi or 0,
            pe_volume=pe_data.volume or 0,
            ce_volume=ce_data.volume or 0,
            pe_ltp=pe_data.last_price or 0.0,
            ce_ltp=ce_data.last_price or 0.0
        )
    
    def _analyze_strike_signal(self, oi_data: StrikeOIData) -> str:
        """
        Analyze signal for a single strike based on PE vs CE OI.
        
        Args:
            oi_data: OI data for the strike
            
        Returns:
            Signal: "support", "resistance", or "neutral"
        """
        pe_oi = oi_data.pe_oi
        ce_oi = oi_data.ce_oi
        
        # Check minimum OI threshold
        if pe_oi < self.min_oi_threshold and ce_oi < self.min_oi_threshold:
            return "neutral"
        
        # Calculate ratio
        if ce_oi == 0:
            return "support"  # Only PE OI exists
        elif pe_oi == 0:
            return "resistance"  # Only CE OI exists
        
        pe_ce_ratio = pe_oi / ce_oi
        
        if pe_ce_ratio > 1.0:
            return "support"  # PE > CE indicates support
        elif pe_ce_ratio < 1.0:
            return "resistance"  # CE > PE indicates resistance
        else:
            return "neutral"  # Equal OI
    
    def _generate_overall_signal(
        self,
        lower_signal: str,
        upper_signal: str,
        lower_oi_data: StrikeOIData,
        upper_oi_data: StrikeOIData
    ) -> Tuple[str, float, str]:
        """
        Generate overall trading signal based on both strikes.
        
        Args:
            lower_signal: Signal from lower strike
            upper_signal: Signal from upper strike
            lower_oi_data: OI data for lower strike
            upper_oi_data: OI data for upper strike
            
        Returns:
            Tuple of (overall_signal, confidence, reasoning)
        """
        # Calculate OI ratios for confidence
        lower_ratio = (lower_oi_data.pe_oi / max(lower_oi_data.ce_oi, 1))
        upper_ratio = (upper_oi_data.pe_oi / max(upper_oi_data.ce_oi, 1))
        
        # Determine overall signal based on strategy logic
        if lower_signal == "support" and upper_signal == "support":
            # PE > CE on both strikes → Bullish
            signal = "bullish"
            confidence = min(0.9, (lower_ratio + upper_ratio - 2) * 0.5 + 0.6)
            reasoning = (f"Strong bullish signal: PE OI dominates on both strikes. "
                        f"Lower strike ({lower_oi_data.strike_price}): PE {lower_oi_data.pe_oi:,} > CE {lower_oi_data.ce_oi:,}. "
                        f"Upper strike ({upper_oi_data.strike_price}): PE {upper_oi_data.pe_oi:,} > CE {upper_oi_data.ce_oi:,}. "
                        f"This indicates strong support levels and bullish sentiment.")
            
        elif lower_signal == "resistance" and upper_signal == "resistance":
            # CE > PE on both strikes → Bearish
            signal = "bearish"
            confidence = min(0.9, (2 - (lower_ratio + upper_ratio)) * 0.5 + 0.6)
            reasoning = (f"Strong bearish signal: CE OI dominates on both strikes. "
                        f"Lower strike ({lower_oi_data.strike_price}): CE {lower_oi_data.ce_oi:,} > PE {lower_oi_data.pe_oi:,}. "
                        f"Upper strike ({upper_oi_data.strike_price}): CE {upper_oi_data.ce_oi:,} > PE {upper_oi_data.pe_oi:,}. "
                        f"This indicates strong resistance levels and bearish sentiment.")
            
        else:
            # Mixed signals → Neutral/Range-bound
            signal = "neutral"
            confidence = 0.3 + abs(lower_ratio - upper_ratio) * 0.1
            reasoning = (f"Mixed signals detected: Lower strike shows {lower_signal}, upper strike shows {upper_signal}. "
                        f"Lower strike ({lower_oi_data.strike_price}): PE {lower_oi_data.pe_oi:,}, CE {lower_oi_data.ce_oi:,}. "
                        f"Upper strike ({upper_oi_data.strike_price}): PE {upper_oi_data.pe_oi:,}, CE {upper_oi_data.ce_oi:,}. "
                        f"Market likely to remain range-bound between these levels.")
        
        # Ensure confidence is within bounds
        confidence = max(0.1, min(0.95, confidence))
        
        return signal, confidence, reasoning
    
    def get_latest_signal(self) -> Optional[RangeOIAnalysis]:
        """Get the latest signal from history."""
        return self.signal_history[-1] if self.signal_history else None
    
    def get_signal_history(self, limit: int = 10) -> List[RangeOIAnalysis]:
        """Get recent signal history."""
        return self.signal_history[-limit:] if self.signal_history else []
