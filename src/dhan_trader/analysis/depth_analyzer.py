"""Advanced market depth analysis for trading insights."""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque

from ..api.models import MarketDepth20Response, MarketDepthLevel
from ..exceptions import AnalysisError

logger = logging.getLogger(__name__)


@dataclass
class MarketMicrostructure:
    """Market microstructure analysis results."""
    order_flow_imbalance: float  # Positive = buying pressure, Negative = selling pressure
    price_impact_estimate: float  # Estimated price impact of large orders
    liquidity_score: float  # 0-100 score of market liquidity
    market_efficiency: float  # How efficiently prices reflect information
    volatility_estimate: float  # Estimated short-term volatility


@dataclass
class TradingSignal:
    """Trading signal based on market depth analysis."""
    signal_type: str  # "BUY", "SELL", "HOLD"
    strength: float  # 0-100 signal strength
    confidence: float  # 0-100 confidence level
    reasoning: List[str]  # Human-readable reasons for the signal
    target_levels: List[float]  # Suggested target price levels
    stop_loss: Optional[float]  # Suggested stop loss level
    time_horizon: str  # "SCALP", "INTRADAY", "SWING"


@dataclass
class LiquidityAnalysis:
    """Liquidity analysis results."""
    total_liquidity: int  # Total quantity available
    liquidity_distribution: Dict[str, float]  # Distribution across price levels
    market_impact_curve: List[Tuple[int, float]]  # (quantity, price_impact) pairs
    optimal_order_size: int  # Optimal order size to minimize impact
    fragmentation_score: float  # How fragmented the liquidity is


class MarketDepthAnalyzer:
    """Advanced analyzer for 20-level market depth data."""
    
    def __init__(self, history_size: int = 100):
        """Initialize the analyzer.
        
        Args:
            history_size: Number of historical depth snapshots to maintain
        """
        self.history_size = history_size
        self.depth_history = deque(maxlen=history_size)
        self.analysis_cache = {}
        self.cache_duration = timedelta(seconds=5)
        
        logger.info("Market depth analyzer initialized")
    
    def add_depth_snapshot(self, depth_data: MarketDepth20Response) -> None:
        """Add a new depth snapshot to the history.
        
        Args:
            depth_data: 20-level market depth data
        """
        self.depth_history.append(depth_data)
        
        # Clear cache for this security
        cache_key = f"{depth_data.security_id}_{depth_data.exchange_segment}"
        self.analysis_cache.pop(cache_key, None)
    
    def analyze_market_microstructure(self, depth_data: MarketDepth20Response) -> MarketMicrostructure:
        """Analyze market microstructure from depth data.
        
        Args:
            depth_data: 20-level market depth data
            
        Returns:
            Market microstructure analysis
        """
        bid_levels = depth_data.bid_depth.levels
        ask_levels = depth_data.ask_depth.levels
        
        # Calculate order flow imbalance
        total_bid_qty = sum(level.quantity for level in bid_levels)
        total_ask_qty = sum(level.quantity for level in ask_levels)
        total_qty = total_bid_qty + total_ask_qty
        
        if total_qty > 0:
            order_flow_imbalance = (total_bid_qty - total_ask_qty) / total_qty
        else:
            order_flow_imbalance = 0.0
        
        # Estimate price impact
        price_impact = self._calculate_price_impact(bid_levels, ask_levels)
        
        # Calculate liquidity score
        liquidity_score = self._calculate_liquidity_score(bid_levels, ask_levels)
        
        # Estimate market efficiency
        market_efficiency = self._calculate_market_efficiency(bid_levels, ask_levels)
        
        # Estimate volatility
        volatility_estimate = self._estimate_volatility(depth_data)
        
        return MarketMicrostructure(
            order_flow_imbalance=order_flow_imbalance,
            price_impact_estimate=price_impact,
            liquidity_score=liquidity_score,
            market_efficiency=market_efficiency,
            volatility_estimate=volatility_estimate
        )
    
    def generate_trading_signal(self, depth_data: MarketDepth20Response) -> TradingSignal:
        """Generate trading signal based on depth analysis.
        
        Args:
            depth_data: 20-level market depth data
            
        Returns:
            Trading signal with recommendations
        """
        microstructure = self.analyze_market_microstructure(depth_data)
        zones = depth_data.detect_demand_supply_zones()
        
        # Analyze signal components
        signal_components = []
        reasoning = []
        
        # Order flow analysis
        if microstructure.order_flow_imbalance > 0.3:
            signal_components.append(("BUY", 70))
            reasoning.append(f"Strong buying pressure (OFI: {microstructure.order_flow_imbalance:.2f})")
        elif microstructure.order_flow_imbalance < -0.3:
            signal_components.append(("SELL", 70))
            reasoning.append(f"Strong selling pressure (OFI: {microstructure.order_flow_imbalance:.2f})")
        
        # Demand/supply zone analysis
        if len(zones["demand_zones"]) > len(zones["supply_zones"]) + 2:
            signal_components.append(("BUY", 60))
            reasoning.append(f"Multiple demand zones detected ({len(zones['demand_zones'])} vs {len(zones['supply_zones'])})")
        elif len(zones["supply_zones"]) > len(zones["demand_zones"]) + 2:
            signal_components.append(("SELL", 60))
            reasoning.append(f"Multiple supply zones detected ({len(zones['supply_zones'])} vs {len(zones['demand_zones'])})")
        
        # Liquidity analysis
        if microstructure.liquidity_score < 30:
            reasoning.append(f"Low liquidity environment (score: {microstructure.liquidity_score:.1f})")
        elif microstructure.liquidity_score > 70:
            reasoning.append(f"High liquidity environment (score: {microstructure.liquidity_score:.1f})")
        
        # Market efficiency analysis
        if microstructure.market_efficiency < 50:
            reasoning.append("Market showing inefficiencies - potential arbitrage opportunities")
        
        # Combine signals
        if not signal_components:
            signal_type = "HOLD"
            strength = 0
            confidence = 50
        else:
            # Aggregate signals
            buy_signals = [s for s in signal_components if s[0] == "BUY"]
            sell_signals = [s for s in signal_components if s[0] == "SELL"]
            
            if len(buy_signals) > len(sell_signals):
                signal_type = "BUY"
                strength = sum(s[1] for s in buy_signals) / len(buy_signals)
            elif len(sell_signals) > len(buy_signals):
                signal_type = "SELL"
                strength = sum(s[1] for s in sell_signals) / len(sell_signals)
            else:
                signal_type = "HOLD"
                strength = 0
            
            # Calculate confidence based on signal consistency and market conditions
            confidence = min(90, strength * (microstructure.liquidity_score / 100))
        
        # Generate target levels and stop loss
        target_levels = self._calculate_target_levels(depth_data, signal_type)
        stop_loss = self._calculate_stop_loss(depth_data, signal_type)
        
        # Determine time horizon
        if microstructure.volatility_estimate > 0.8:
            time_horizon = "SCALP"
        elif microstructure.volatility_estimate > 0.4:
            time_horizon = "INTRADAY"
        else:
            time_horizon = "SWING"
        
        return TradingSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            reasoning=reasoning,
            target_levels=target_levels,
            stop_loss=stop_loss,
            time_horizon=time_horizon
        )
    
    def analyze_liquidity(self, depth_data: MarketDepth20Response) -> LiquidityAnalysis:
        """Analyze liquidity characteristics.
        
        Args:
            depth_data: 20-level market depth data
            
        Returns:
            Liquidity analysis results
        """
        bid_levels = depth_data.bid_depth.levels
        ask_levels = depth_data.ask_depth.levels
        
        # Calculate total liquidity
        total_liquidity = sum(level.quantity for level in bid_levels + ask_levels)
        
        # Calculate liquidity distribution
        top_5_liquidity = sum(level.quantity for level in bid_levels[:5] + ask_levels[:5])
        mid_10_liquidity = sum(level.quantity for level in bid_levels[5:15] + ask_levels[5:15])
        bottom_5_liquidity = sum(level.quantity for level in bid_levels[15:] + ask_levels[15:])
        
        if total_liquidity > 0:
            distribution = {
                "top_5_levels": (top_5_liquidity / total_liquidity) * 100,
                "mid_10_levels": (mid_10_liquidity / total_liquidity) * 100,
                "bottom_5_levels": (bottom_5_liquidity / total_liquidity) * 100,
            }
        else:
            distribution = {"top_5_levels": 0, "mid_10_levels": 0, "bottom_5_levels": 0}
        
        # Calculate market impact curve
        impact_curve = self._calculate_market_impact_curve(bid_levels, ask_levels)
        
        # Calculate optimal order size
        optimal_size = self._calculate_optimal_order_size(impact_curve)
        
        # Calculate fragmentation score
        fragmentation_score = self._calculate_fragmentation_score(bid_levels, ask_levels)
        
        return LiquidityAnalysis(
            total_liquidity=total_liquidity,
            liquidity_distribution=distribution,
            market_impact_curve=impact_curve,
            optimal_order_size=optimal_size,
            fragmentation_score=fragmentation_score
        )
    
    def _calculate_price_impact(self, bid_levels: List[MarketDepthLevel], ask_levels: List[MarketDepthLevel]) -> float:
        """Calculate estimated price impact."""
        if not bid_levels or not ask_levels:
            return 0.0
        
        best_bid = bid_levels[0].price
        best_ask = ask_levels[0].price
        spread = best_ask - best_bid
        
        # Simple price impact model based on spread and depth
        avg_top_5_qty = sum(level.quantity for level in bid_levels[:5] + ask_levels[:5]) / 10
        if avg_top_5_qty > 0:
            impact = spread / avg_top_5_qty * 1000  # Normalized impact
        else:
            impact = spread
        
        return min(impact, 1.0)  # Cap at 1.0
    
    def _calculate_liquidity_score(self, bid_levels: List[MarketDepthLevel], ask_levels: List[MarketDepthLevel]) -> float:
        """Calculate liquidity score (0-100)."""
        if not bid_levels or not ask_levels:
            return 0.0
        
        # Factors: total quantity, distribution, and order count
        total_qty = sum(level.quantity for level in bid_levels + ask_levels)
        total_orders = sum(level.orders for level in bid_levels + ask_levels)
        
        # Normalize based on typical market values
        qty_score = min(total_qty / 10000, 1.0) * 50  # Max 50 points for quantity
        order_score = min(total_orders / 1000, 1.0) * 30  # Max 30 points for order count
        
        # Distribution score - prefer even distribution
        quantities = [level.quantity for level in bid_levels + ask_levels]
        if quantities:
            std_dev = (sum((q - sum(quantities)/len(quantities))**2 for q in quantities) / len(quantities))**0.5
            avg_qty = sum(quantities) / len(quantities)
            distribution_score = max(0, 20 - (std_dev / avg_qty * 10)) if avg_qty > 0 else 0
        else:
            distribution_score = 0
        
        return min(qty_score + order_score + distribution_score, 100)
    
    def _calculate_market_efficiency(self, bid_levels: List[MarketDepthLevel], ask_levels: List[MarketDepthLevel]) -> float:
        """Calculate market efficiency score."""
        if not bid_levels or not ask_levels:
            return 50.0
        
        # Check for price gaps and irregularities
        bid_prices = [level.price for level in bid_levels]
        ask_prices = [level.price for level in ask_levels]
        
        # Calculate price consistency
        bid_gaps = [abs(bid_prices[i] - bid_prices[i+1]) for i in range(len(bid_prices)-1)]
        ask_gaps = [abs(ask_prices[i+1] - ask_prices[i]) for i in range(len(ask_prices)-1)]
        
        if bid_gaps and ask_gaps:
            avg_bid_gap = sum(bid_gaps) / len(bid_gaps)
            avg_ask_gap = sum(ask_gaps) / len(ask_gaps)
            
            # More consistent gaps indicate higher efficiency
            bid_consistency = 1.0 - (max(bid_gaps) - min(bid_gaps)) / avg_bid_gap if avg_bid_gap > 0 else 1.0
            ask_consistency = 1.0 - (max(ask_gaps) - min(ask_gaps)) / avg_ask_gap if avg_ask_gap > 0 else 1.0
            
            efficiency = (bid_consistency + ask_consistency) / 2 * 100
        else:
            efficiency = 50.0
        
        return max(0, min(efficiency, 100))
    
    def _estimate_volatility(self, depth_data: MarketDepth20Response) -> float:
        """Estimate short-term volatility from depth data."""
        if len(self.depth_history) < 2:
            return 0.5  # Default moderate volatility
        
        # Calculate price changes from recent history
        recent_snapshots = list(self.depth_history)[-10:]  # Last 10 snapshots
        price_changes = []
        
        for i in range(1, len(recent_snapshots)):
            prev_mid = (recent_snapshots[i-1].bid_depth.levels[0].price + 
                       recent_snapshots[i-1].ask_depth.levels[0].price) / 2
            curr_mid = (recent_snapshots[i].bid_depth.levels[0].price + 
                       recent_snapshots[i].ask_depth.levels[0].price) / 2
            
            if prev_mid > 0:
                change = abs(curr_mid - prev_mid) / prev_mid
                price_changes.append(change)
        
        if price_changes:
            volatility = sum(price_changes) / len(price_changes)
            return min(volatility * 100, 1.0)  # Normalize to 0-1
        
        return 0.5
    
    def _calculate_target_levels(self, depth_data: MarketDepth20Response, signal_type: str) -> List[float]:
        """Calculate target price levels."""
        bid_levels = depth_data.bid_depth.levels
        ask_levels = depth_data.ask_depth.levels
        
        if not bid_levels or not ask_levels:
            return []
        
        best_bid = bid_levels[0].price
        best_ask = ask_levels[0].price
        mid_price = (best_bid + best_ask) / 2
        
        targets = []
        
        if signal_type == "BUY":
            # Target levels above current ask
            for i in range(min(3, len(ask_levels))):
                if ask_levels[i].quantity > ask_levels[0].quantity * 1.5:  # Resistance level
                    targets.append(ask_levels[i].price)
        elif signal_type == "SELL":
            # Target levels below current bid
            for i in range(min(3, len(bid_levels))):
                if bid_levels[i].quantity > bid_levels[0].quantity * 1.5:  # Support level
                    targets.append(bid_levels[i].price)
        
        return targets[:3]  # Max 3 targets
    
    def _calculate_stop_loss(self, depth_data: MarketDepth20Response, signal_type: str) -> Optional[float]:
        """Calculate stop loss level."""
        bid_levels = depth_data.bid_depth.levels
        ask_levels = depth_data.ask_depth.levels
        
        if not bid_levels or not ask_levels:
            return None
        
        best_bid = bid_levels[0].price
        best_ask = ask_levels[0].price
        spread = best_ask - best_bid
        
        if signal_type == "BUY":
            # Stop loss below strong support
            for level in bid_levels[1:6]:  # Check levels 2-6
                if level.quantity > bid_levels[0].quantity * 2:
                    return level.price - spread
            return best_bid - spread * 2
        elif signal_type == "SELL":
            # Stop loss above strong resistance
            for level in ask_levels[1:6]:  # Check levels 2-6
                if level.quantity > ask_levels[0].quantity * 2:
                    return level.price + spread
            return best_ask + spread * 2
        
        return None
    
    def _calculate_market_impact_curve(self, bid_levels: List[MarketDepthLevel], ask_levels: List[MarketDepthLevel]) -> List[Tuple[int, float]]:
        """Calculate market impact curve."""
        curve = []
        cumulative_qty = 0
        
        # Combine and sort all levels by price
        all_levels = [(level.price, level.quantity, 'bid') for level in bid_levels] + \
                    [(level.price, level.quantity, 'ask') for level in ask_levels]
        all_levels.sort(key=lambda x: x[0])
        
        if not all_levels:
            return curve
        
        base_price = all_levels[len(all_levels)//2][0]  # Mid price
        
        for price, quantity, side in all_levels:
            cumulative_qty += quantity
            impact = abs(price - base_price) / base_price if base_price > 0 else 0
            curve.append((cumulative_qty, impact))
        
        return curve
    
    def _calculate_optimal_order_size(self, impact_curve: List[Tuple[int, float]]) -> int:
        """Calculate optimal order size to minimize market impact."""
        if not impact_curve:
            return 0
        
        # Find the point where impact starts increasing significantly
        for i in range(1, len(impact_curve)):
            prev_qty, prev_impact = impact_curve[i-1]
            curr_qty, curr_impact = impact_curve[i]
            
            if curr_impact > prev_impact * 1.5:  # 50% increase in impact
                return prev_qty
        
        # If no significant increase found, return 25% of total liquidity
        total_qty = impact_curve[-1][0] if impact_curve else 0
        return int(total_qty * 0.25)
    
    def _calculate_fragmentation_score(self, bid_levels: List[MarketDepthLevel], ask_levels: List[MarketDepthLevel]) -> float:
        """Calculate liquidity fragmentation score."""
        all_quantities = [level.quantity for level in bid_levels + ask_levels]
        
        if not all_quantities:
            return 0.0
        
        # Calculate coefficient of variation
        mean_qty = sum(all_quantities) / len(all_quantities)
        variance = sum((q - mean_qty)**2 for q in all_quantities) / len(all_quantities)
        std_dev = variance**0.5
        
        if mean_qty > 0:
            cv = std_dev / mean_qty
            # Higher CV indicates more fragmentation
            return min(cv * 100, 100)
        
        return 0.0
