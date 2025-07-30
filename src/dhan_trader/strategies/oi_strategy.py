"""
Sameer Sir OI Strategy Implementation
Open Interest based trading strategy for NIFTY options
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class OIAnalysis:
    """Open Interest analysis result."""
    strike: float
    ce_oi: int
    pe_oi: int
    oi_ratio: float  # PE OI / CE OI
    signal: str  # "bullish", "bearish", "neutral"
    strength: float  # Signal strength 0-1


@dataclass
class RangeOIAnalysis:
    """Range-based OI analysis result."""
    lower_strike: float
    upper_strike: float
    total_ce_oi: int
    total_pe_oi: int
    oi_ratio: float  # Total PE OI / Total CE OI
    signal: str  # "bullish", "bearish", "neutral"
    strength: float
    current_price: float


@dataclass
class StrategySignal:
    """Complete strategy signal."""
    timestamp: datetime
    current_price: float
    range_analysis: RangeOIAnalysis
    strike_analyses: List[OIAnalysis]
    overall_signal: str
    confidence: float
    targets: List[float]
    alerts: List[str]


class SameerSirOIStrategy:
    """
    Sameer Sir's Open Interest Strategy Implementation
    
    Strategy Logic:
    1. Range OI Analysis: Compare total PE vs CE OI across strike range
    2. Single Strike Confirmation: Analyze individual strikes for target confirmation
    3. Signal Generation: Combine range and strike analysis for trading signals
    """
    
    def __init__(self, market_data_manager):
        self.market_data_manager = market_data_manager
        self.signal_history = []
        
        # Strategy parameters
        self.oi_threshold = 1.2  # OI ratio threshold for strong signals
        self.neutral_zone = 0.1  # Neutral zone around 1.0 ratio
        
    def analyze_oi_strategy(
        self, 
        underlying_scrip: int = 13,  # NIFTY
        expiry: Optional[str] = None,
        center_strike: Optional[float] = None,
        strike_range: int = 50
    ) -> StrategySignal:
        """
        Perform complete OI strategy analysis.
        
        Args:
            underlying_scrip: Security ID (13 for NIFTY)
            expiry: Option expiry date
            center_strike: Center strike for analysis (auto-detect if None)
            strike_range: Range around center strike for analysis
            
        Returns:
            Complete strategy signal with analysis
        """
        try:
            # Get option chain data
            option_chain = self.market_data_manager.get_option_chain(
                underlying_scrip, "IDX_I", expiry, use_cache=False
            )
            
            current_price = option_chain.underlying_price
            
            # Auto-detect center strike if not provided
            if center_strike is None:
                center_strike = self._find_nearest_strike(current_price, option_chain.strikes)
            
            # Define strike range for analysis
            lower_strike = center_strike - strike_range
            upper_strike = center_strike + strike_range
            
            # Perform range OI analysis
            range_analysis = self._analyze_range_oi(
                option_chain.strikes, current_price, lower_strike, upper_strike
            )
            
            # Perform individual strike analysis
            strike_analyses = self._analyze_individual_strikes(
                option_chain.strikes, current_price, [lower_strike, center_strike, upper_strike]
            )
            
            # Generate overall signal
            overall_signal, confidence = self._generate_overall_signal(
                range_analysis, strike_analyses
            )
            
            # Generate targets and alerts
            targets = self._generate_targets(range_analysis, strike_analyses, current_price)
            alerts = self._generate_alerts(range_analysis, strike_analyses)
            
            # Create strategy signal
            signal = StrategySignal(
                timestamp=datetime.now(),
                current_price=current_price,
                range_analysis=range_analysis,
                strike_analyses=strike_analyses,
                overall_signal=overall_signal,
                confidence=confidence,
                targets=targets,
                alerts=alerts
            )
            
            # Store in history
            self.signal_history.append(signal)
            if len(self.signal_history) > 100:  # Keep last 100 signals
                self.signal_history.pop(0)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in OI strategy analysis: {e}")
            raise
    
    def _find_nearest_strike(self, price: float, strikes) -> float:
        """Find the nearest strike price to current price."""
        if isinstance(strikes, list):
            strike_prices = [strike.strike for strike in strikes]
        else:
            strike_prices = [float(strike) for strike in strikes.keys()]
        
        return min(strike_prices, key=lambda x: abs(x - price))
    
    def _analyze_range_oi(
        self, 
        strikes, 
        current_price: float, 
        lower_strike: float, 
        upper_strike: float
    ) -> RangeOIAnalysis:
        """Analyze OI across a range of strikes."""
        total_ce_oi = 0
        total_pe_oi = 0
        
        # Handle both list and dict structures
        strikes_to_process = []
        if isinstance(strikes, dict):
            strikes_to_process = [(float(strike), data) for strike, data in strikes.items()]
        elif isinstance(strikes, list):
            strikes_to_process = [(strike.strike, strike) for strike in strikes]
        
        for strike_price, strike_data in strikes_to_process:
            if lower_strike <= strike_price <= upper_strike:
                if hasattr(strike_data, 'ce') and strike_data.ce:
                    total_ce_oi += strike_data.ce.oi
                if hasattr(strike_data, 'pe') and strike_data.pe:
                    total_pe_oi += strike_data.pe.oi
        
        # Calculate ratio and signal
        oi_ratio = total_pe_oi / total_ce_oi if total_ce_oi > 0 else float('inf')
        signal, strength = self._determine_signal(oi_ratio)
        
        return RangeOIAnalysis(
            lower_strike=lower_strike,
            upper_strike=upper_strike,
            total_ce_oi=total_ce_oi,
            total_pe_oi=total_pe_oi,
            oi_ratio=oi_ratio,
            signal=signal,
            strength=strength,
            current_price=current_price
        )
    
    def _analyze_individual_strikes(
        self, 
        strikes, 
        current_price: float, 
        target_strikes: List[float]
    ) -> List[OIAnalysis]:
        """Analyze individual strikes for target confirmation."""
        analyses = []
        
        # Handle both list and dict structures
        strikes_to_process = []
        if isinstance(strikes, dict):
            strikes_to_process = [(float(strike), data) for strike, data in strikes.items()]
        elif isinstance(strikes, list):
            strikes_to_process = [(strike.strike, strike) for strike in strikes]
        
        for target_strike in target_strikes:
            # Find the exact strike or closest one
            closest_strike = None
            min_distance = float('inf')
            
            for strike_price, strike_data in strikes_to_process:
                distance = abs(strike_price - target_strike)
                if distance < min_distance:
                    min_distance = distance
                    closest_strike = (strike_price, strike_data)
            
            if closest_strike:
                strike_price, strike_data = closest_strike
                ce_oi = strike_data.ce.oi if hasattr(strike_data, 'ce') and strike_data.ce else 0
                pe_oi = strike_data.pe.oi if hasattr(strike_data, 'pe') and strike_data.pe else 0
                
                oi_ratio = pe_oi / ce_oi if ce_oi > 0 else float('inf')
                signal, strength = self._determine_signal(oi_ratio)
                
                analyses.append(OIAnalysis(
                    strike=strike_price,
                    ce_oi=ce_oi,
                    pe_oi=pe_oi,
                    oi_ratio=oi_ratio,
                    signal=signal,
                    strength=strength
                ))
        
        return analyses
    
    def _determine_signal(self, oi_ratio: float) -> Tuple[str, float]:
        """Determine signal and strength from OI ratio."""
        if oi_ratio == float('inf'):
            return "bullish", 1.0
        
        if oi_ratio > (1 + self.neutral_zone):
            # PE OI > CE OI = Bullish
            strength = min((oi_ratio - 1) / (self.oi_threshold - 1), 1.0)
            return "bullish", strength
        elif oi_ratio < (1 - self.neutral_zone):
            # CE OI > PE OI = Bearish
            strength = min((1 - oi_ratio) / (1 - (1/self.oi_threshold)), 1.0)
            return "bearish", strength
        else:
            return "neutral", 0.0
    
    def _generate_overall_signal(
        self, 
        range_analysis: RangeOIAnalysis, 
        strike_analyses: List[OIAnalysis]
    ) -> Tuple[str, float]:
        """Generate overall signal combining range and strike analysis."""
        # Weight range analysis more heavily
        range_weight = 0.7
        strike_weight = 0.3
        
        # Calculate weighted confidence
        range_confidence = range_analysis.strength
        
        # Average strike confidence
        strike_confidence = 0
        if strike_analyses:
            strike_confidence = sum(analysis.strength for analysis in strike_analyses) / len(strike_analyses)
        
        overall_confidence = (range_confidence * range_weight + strike_confidence * strike_weight)
        
        # Determine overall signal
        if range_analysis.signal == "neutral":
            return "neutral", overall_confidence
        
        # Check if strikes confirm the range signal
        confirming_strikes = sum(1 for analysis in strike_analyses if analysis.signal == range_analysis.signal)
        total_strikes = len(strike_analyses)
        
        if total_strikes > 0 and confirming_strikes / total_strikes >= 0.6:
            return range_analysis.signal, overall_confidence
        else:
            return "neutral", overall_confidence * 0.5  # Reduce confidence if strikes don't confirm
    
    def _generate_targets(
        self, 
        range_analysis: RangeOIAnalysis, 
        strike_analyses: List[OIAnalysis], 
        current_price: float
    ) -> List[float]:
        """Generate target levels based on OI analysis."""
        targets = []
        
        if range_analysis.signal == "bullish":
            # Bullish targets above current price
            for analysis in strike_analyses:
                if analysis.strike > current_price and analysis.signal == "bullish":
                    targets.append(analysis.strike)
        elif range_analysis.signal == "bearish":
            # Bearish targets below current price
            for analysis in strike_analyses:
                if analysis.strike < current_price and analysis.signal == "bearish":
                    targets.append(analysis.strike)
        
        return sorted(targets)
    
    def _generate_alerts(
        self, 
        range_analysis: RangeOIAnalysis, 
        strike_analyses: List[OIAnalysis]
    ) -> List[str]:
        """Generate alerts based on OI analysis."""
        alerts = []
        
        # Range analysis alerts
        if range_analysis.strength > 0.7:
            alerts.append(f"Strong {range_analysis.signal} signal from range OI analysis (ratio: {range_analysis.oi_ratio:.2f})")
        
        # Individual strike alerts
        for analysis in strike_analyses:
            if analysis.strength > 0.8:
                alerts.append(f"Strong {analysis.signal} signal at {analysis.strike} strike (PE OI: {analysis.pe_oi:,}, CE OI: {analysis.ce_oi:,})")
        
        return alerts
    
    def get_signal_history(self, limit: int = 10) -> List[StrategySignal]:
        """Get recent signal history."""
        return self.signal_history[-limit:] if self.signal_history else []
