"""
Range OI Analysis Service for NIFTY Options Trading.

This service provides comprehensive analysis of Open Interest changes
across a specified strike price range with detailed calculations and metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import asyncio

from ..market_data.manager import MarketDataManager

logger = logging.getLogger(__name__)


@dataclass
class StrikeOIData:
    """Individual strike OI data."""
    strike: float
    call_oi: int
    put_oi: int
    call_oi_change: int
    put_oi_change: int
    call_oi_change_pct: float
    put_oi_change_pct: float
    call_volume: int
    put_volume: int
    timestamp: datetime


@dataclass
class RangeOIMetrics:
    """Calculated metrics for the range."""
    total_call_oi: int
    total_put_oi: int
    total_call_oi_change: int
    total_put_oi_change: int
    average_call_oi: float
    average_put_oi: float
    average_call_oi_change: float
    average_put_oi_change: float
    strike_count: int
    call_put_ratio: float
    net_oi_change: int  # Total Call OI Change - Total Put OI Change
    dominant_side: str  # "CALL", "PUT", or "NEUTRAL"


@dataclass
class RangeOIAnalysis:
    """Complete range OI analysis result."""
    expiry: str
    range_start: float
    range_end: float
    interval: str
    strikes_data: List[StrikeOIData]
    metrics: RangeOIMetrics
    analysis_time: datetime
    underlying_price: float
    total_strikes_analyzed: int
    
    # Time series data for charts
    historical_data: Optional[List[Dict[str, Any]]] = None


class RangeOIAnalyzer:
    """Service for analyzing OI changes across a strike price range."""
    
    def __init__(self, market_data_manager: MarketDataManager):
        """Initialize the range OI analyzer."""
        self.market_data_manager = market_data_manager
        
    async def analyze_range_oi(
        self,
        expiry: str,
        range_start: float,
        range_end: float,
        interval: str = "1min",
        underlying_scrip: int = 13,
        underlying_segment: str = "IDX_I"
    ) -> RangeOIAnalysis:
        """
        Analyze OI changes for a specified strike range.
        
        Args:
            expiry: Option expiry date (YYYY-MM-DD)
            range_start: Starting strike price (inclusive)
            range_end: Ending strike price (inclusive)
            interval: Data interval (1min, 5min, etc.)
            underlying_scrip: Underlying instrument ID
            underlying_segment: Market segment
            
        Returns:
            RangeOIAnalysis with complete analysis results
        """
        try:
            logger.info(f"Starting range OI analysis: {range_start}-{range_end}, expiry: {expiry}")
            
            # Get option chain data
            option_chain = self.market_data_manager.get_option_chain_with_oi_changes(
                underlying_scrip, underlying_segment, expiry, use_cache=False
            )
            
            # Extract strikes in the specified range
            strikes_in_range = self._get_strikes_in_range(
                option_chain.strikes, range_start, range_end
            )
            
            # Process strike data
            strikes_data = self._process_strikes_data(strikes_in_range)
            
            # Calculate metrics
            metrics = self._calculate_range_metrics(strikes_data)
            
            # Create analysis result
            analysis = RangeOIAnalysis(
                expiry=expiry,
                range_start=range_start,
                range_end=range_end,
                interval=interval,
                strikes_data=strikes_data,
                metrics=metrics,
                analysis_time=datetime.now(),
                underlying_price=option_chain.underlying_price,
                total_strikes_analyzed=len(strikes_data)
            )
            
            logger.info(f"Range OI analysis completed: {len(strikes_data)} strikes analyzed")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in range OI analysis: {e}")
            raise
    
    def _get_strikes_in_range(
        self,
        all_strikes: Dict[str, Any],
        range_start: float,
        range_end: float
    ) -> Dict[str, Any]:
        """Filter strikes within the specified range."""
        strikes_in_range = {}
        
        for strike_key, strike_data in all_strikes.items():
            try:
                strike_price = float(strike_key)
                if range_start <= strike_price <= range_end:
                    strikes_in_range[strike_key] = strike_data
            except (ValueError, TypeError):
                logger.warning(f"Invalid strike price format: {strike_key}")
                continue
        
        logger.info(f"Found {len(strikes_in_range)} strikes in range {range_start}-{range_end}")
        return strikes_in_range
    
    def _process_strikes_data(self, strikes: Dict[str, Any]) -> List[StrikeOIData]:
        """Process strike data into structured format."""
        strikes_data = []
        
        for strike_key, strike_data in strikes.items():
            try:
                strike_price = float(strike_key)
                
                # Extract Call data
                call_oi = 0
                call_volume = 0
                call_oi_change = 0
                call_oi_change_pct = 0.0

                if hasattr(strike_data, 'ce') and strike_data.ce:
                    call_oi = getattr(strike_data.ce, 'oi', 0)
                    call_volume = getattr(strike_data.ce, 'volume', 0)
                    if hasattr(strike_data.ce, 'oi_change') and strike_data.ce.oi_change:
                        call_oi_change = getattr(strike_data.ce.oi_change, 'absolute_change', 0)
                        call_oi_change_pct = getattr(strike_data.ce.oi_change, 'percentage_change', 0.0)

                # Extract Put data
                put_oi = 0
                put_volume = 0
                put_oi_change = 0
                put_oi_change_pct = 0.0

                if hasattr(strike_data, 'pe') and strike_data.pe:
                    put_oi = getattr(strike_data.pe, 'oi', 0)
                    put_volume = getattr(strike_data.pe, 'volume', 0)
                    if hasattr(strike_data.pe, 'oi_change') and strike_data.pe.oi_change:
                        put_oi_change = getattr(strike_data.pe.oi_change, 'absolute_change', 0)
                        put_oi_change_pct = getattr(strike_data.pe.oi_change, 'percentage_change', 0.0)
                
                # Create strike OI data
                strike_oi_data = StrikeOIData(
                    strike=strike_price,
                    call_oi=call_oi,
                    put_oi=put_oi,
                    call_oi_change=call_oi_change,
                    put_oi_change=put_oi_change,
                    call_oi_change_pct=call_oi_change_pct,
                    put_oi_change_pct=put_oi_change_pct,
                    call_volume=call_volume,
                    put_volume=put_volume,
                    timestamp=datetime.now()
                )
                
                strikes_data.append(strike_oi_data)
                
            except Exception as e:
                logger.error(f"Error processing strike {strike_key}: {e}")
                continue
        
        # Sort by strike price
        strikes_data.sort(key=lambda x: x.strike)
        return strikes_data
    
    def _calculate_range_metrics(self, strikes_data: List[StrikeOIData]) -> RangeOIMetrics:
        """Calculate comprehensive metrics for the range."""
        if not strikes_data:
            return RangeOIMetrics(
                total_call_oi=0, total_put_oi=0, total_call_oi_change=0, total_put_oi_change=0,
                average_call_oi=0.0, average_put_oi=0.0, average_call_oi_change=0.0, 
                average_put_oi_change=0.0, strike_count=0, call_put_ratio=0.0,
                net_oi_change=0, dominant_side="NEUTRAL"
            )
        
        # Calculate totals
        total_call_oi = sum(strike.call_oi for strike in strikes_data)
        total_put_oi = sum(strike.put_oi for strike in strikes_data)
        total_call_oi_change = sum(strike.call_oi_change for strike in strikes_data)
        total_put_oi_change = sum(strike.put_oi_change for strike in strikes_data)
        
        strike_count = len(strikes_data)
        
        # Calculate averages
        average_call_oi = total_call_oi / strike_count if strike_count > 0 else 0.0
        average_put_oi = total_put_oi / strike_count if strike_count > 0 else 0.0
        average_call_oi_change = total_call_oi_change / strike_count if strike_count > 0 else 0.0
        average_put_oi_change = total_put_oi_change / strike_count if strike_count > 0 else 0.0
        
        # Calculate ratios and dominance
        call_put_ratio = total_call_oi / total_put_oi if total_put_oi > 0 else float('inf')
        net_oi_change = total_call_oi_change - total_put_oi_change
        
        # Determine dominant side based on OI changes
        if abs(total_call_oi_change) > abs(total_put_oi_change) * 1.1:  # 10% threshold
            dominant_side = "CALL" if total_call_oi_change > 0 else "CALL_NEGATIVE"
        elif abs(total_put_oi_change) > abs(total_call_oi_change) * 1.1:
            dominant_side = "PUT" if total_put_oi_change > 0 else "PUT_NEGATIVE"
        else:
            dominant_side = "NEUTRAL"
        
        return RangeOIMetrics(
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            total_call_oi_change=total_call_oi_change,
            total_put_oi_change=total_put_oi_change,
            average_call_oi=average_call_oi,
            average_put_oi=average_put_oi,
            average_call_oi_change=average_call_oi_change,
            average_put_oi_change=average_put_oi_change,
            strike_count=strike_count,
            call_put_ratio=call_put_ratio,
            net_oi_change=net_oi_change,
            dominant_side=dominant_side
        )
    
    async def get_historical_range_data(
        self,
        expiry: str,
        range_start: float,
        range_end: float,
        lookback_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get historical OI data for time series charts.
        
        Note: This is a placeholder for historical data.
        In a real implementation, you would store and retrieve historical OI data.
        """
        # For now, return mock historical data
        # In production, this would query a time-series database
        historical_data = []
        
        current_time = datetime.now()
        for i in range(lookback_minutes, 0, -5):  # Every 5 minutes
            timestamp = current_time - timedelta(minutes=i)
            
            # Mock data - in production, fetch real historical data
            historical_data.append({
                "timestamp": timestamp.isoformat(),
                "total_call_oi_change": 1000000 + (i * 50000),  # Mock increasing trend
                "total_put_oi_change": 800000 + (i * 30000),
                "net_oi_change": 200000 + (i * 20000)
            })
        
        return historical_data
    
    def format_oi_value(self, value: int) -> str:
        """Format OI value in lakhs for display."""
        if value >= 10000000:  # 1 crore
            return f"{value / 10000000:.1f}Cr"
        elif value >= 100000:  # 1 lakh
            return f"{value / 100000:.1f}L"
        else:
            return str(value)
