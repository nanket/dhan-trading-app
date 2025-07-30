"""Data models for Dhan API responses."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class ExchangeSegment(Enum):
    """Exchange segments supported by Dhan."""
    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    NSE_CURR = "NSE_CURR"
    BSE_EQ = "BSE_EQ"
    BSE_FNO = "BSE_FNO"
    BSE_CURR = "BSE_CURR"
    MCX_COMM = "MCX_COMM"
    IDX_I = "IDX_I"


class OrderType(Enum):
    """Order types."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    TRADED = "TRADED"
    EXPIRED = "EXPIRED"


class TransactionType(Enum):
    """Transaction types."""
    BUY = "BUY"
    SELL = "SELL"


class ProductType(Enum):
    """Product types."""
    CNC = "CNC"  # Cash and Carry
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"
    MTF = "MTF"  # Margin Trading Facility
    CO = "CO"  # Cover Order
    BO = "BO"  # Bracket Order


@dataclass
class UserProfile:
    """User profile information."""
    dhan_client_id: str
    token_validity: str
    active_segment: str
    ddpi: str
    mtf: str
    data_plan: str
    data_validity: str


@dataclass
class Greeks:
    """Options Greeks."""
    delta: float
    gamma: float
    theta: float
    vega: float


@dataclass
class OIChangeData:
    """Open Interest change data."""
    absolute_change: int  # Absolute change in OI
    percentage_change: float  # Percentage change in OI
    previous_oi: int  # Previous session OI
    current_oi: int  # Current OI
    timestamp: datetime  # When the change was calculated


@dataclass
class OptionData:
    """Option contract data."""
    greeks: Greeks
    implied_volatility: float
    last_price: float
    oi: int
    previous_close_price: float
    previous_oi: int
    previous_volume: int
    top_ask_price: float
    top_ask_quantity: int
    top_bid_price: float
    top_bid_quantity: int
    volume: int
    oi_change: Optional[OIChangeData] = None  # OI change data


@dataclass
class OptionChainStrike:
    """Option chain data for a specific strike."""
    strike: float
    ce: Optional[OptionData] = None  # Call option
    pe: Optional[OptionData] = None  # Put option


@dataclass
class OptionChain:
    """Complete option chain data."""
    underlying_price: float
    strikes: Dict[str, OptionChainStrike]
    expiry: str
    underlying_scrip: int
    underlying_segment: str


@dataclass
class MarketQuote:
    """Market quote data."""
    security_id: str
    exchange_segment: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    prev_close_price: float
    change: float
    change_percent: float
    volume: int
    value: float
    oi: Optional[int] = None
    timestamp: Optional[datetime] = None


@dataclass
class Order:
    """Order information."""
    order_id: str
    dhan_client_id: str
    order_status: OrderStatus
    transaction_type: TransactionType
    exchange_segment: ExchangeSegment
    product_type: ProductType
    order_type: OrderType
    security_id: str
    quantity: int
    disclosed_quantity: int
    price: float
    trigger_price: float
    validity: str
    traded_quantity: int
    remaining_quantity: int
    created_at: datetime
    updated_at: datetime
    bo_profit_value: Optional[float] = None
    bo_stop_loss_value: Optional[float] = None


@dataclass
class Position:
    """Position information."""
    dhan_client_id: str
    exchange_segment: ExchangeSegment
    product_type: ProductType
    security_id: str
    net_quantity: int
    buy_avg: float
    sell_avg: float
    net_avg: float
    day_buy_quantity: int
    day_sell_quantity: int
    day_buy_value: float
    day_sell_value: float
    pnl: float
    realized_pnl: float
    unrealized_pnl: float


@dataclass
class Holding:
    """Holdings information."""
    isin: str
    security_id: str
    exchange_segment: ExchangeSegment
    product_type: ProductType
    quantity: int
    avg_cost_price: float
    last_price: float
    pnl: float
    pnl_percent: float


@dataclass
class FundLimit:
    """Fund limit information."""
    dhan_client_id: str
    available_balance: float
    sod_limit: float
    collateral_amount: float
    intraday_payin: float
    adhoc_margin: float
    notional_cash: float
    margin_used: float
    exposure_margin: float


@dataclass
class HistoricalData:
    """Historical price data."""
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    oi: Optional[int] = None


@dataclass
class MarketDepthLevel:
    """Single level of market depth data."""
    price: float
    quantity: int
    orders: int


@dataclass
class MarketDepth20Level:
    """20-level market depth data for a single side (bid or ask)."""
    levels: List[MarketDepthLevel]
    side: str  # "BID" or "ASK"
    security_id: str
    exchange_segment: str
    timestamp: datetime


@dataclass
class MarketDepth20Response:
    """Complete 20-level market depth response."""
    security_id: str
    exchange_segment: str
    bid_depth: MarketDepth20Level
    ask_depth: MarketDepth20Level
    timestamp: datetime

    def get_total_bid_quantity(self) -> int:
        """Get total bid quantity across all levels."""
        return sum(level.quantity for level in self.bid_depth.levels)

    def get_total_ask_quantity(self) -> int:
        """Get total ask quantity across all levels."""
        return sum(level.quantity for level in self.ask_depth.levels)

    def get_bid_ask_ratio(self) -> float:
        """Get bid to ask quantity ratio."""
        total_ask = self.get_total_ask_quantity()
        if total_ask == 0:
            return float('inf')
        return self.get_total_bid_quantity() / total_ask

    def detect_demand_supply_zones(self, threshold_multiplier: float = 2.0) -> Dict[str, List[int]]:
        """Detect significant demand/supply zones based on quantity concentration."""
        avg_bid_qty = self.get_total_bid_quantity() / len(self.bid_depth.levels) if self.bid_depth.levels else 0
        avg_ask_qty = self.get_total_ask_quantity() / len(self.ask_depth.levels) if self.ask_depth.levels else 0

        demand_zones = []  # Indices of significant bid levels
        supply_zones = []  # Indices of significant ask levels

        # Find bid levels with significantly higher quantity
        for i, level in enumerate(self.bid_depth.levels):
            if level.quantity > avg_bid_qty * threshold_multiplier:
                demand_zones.append(i)

        # Find ask levels with significantly higher quantity
        for i, level in enumerate(self.ask_depth.levels):
            if level.quantity > avg_ask_qty * threshold_multiplier:
                supply_zones.append(i)

        return {
            "demand_zones": demand_zones,
            "supply_zones": supply_zones
        }


@dataclass
class DemandSupplyZones:
    """Demand and supply zones in market depth."""
    demand_zones: List[int]  # Indices of significant bid levels
    supply_zones: List[int]  # Indices of significant ask levels


@dataclass
class MarketDepthAnalysis:
    """Analysis of 20-level market depth data."""
    total_bid_quantity: int
    total_ask_quantity: int
    bid_ask_ratio: float
    zones: DemandSupplyZones
    price_levels: Dict[str, Optional[MarketDepthLevel]]


# Enhanced OI Recommendation Models
@dataclass
class IndividualStrikeResponse:
    """Response model for individual strike analysis."""
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
class RangeOIResponse:
    """Response model for range-based OI analysis."""
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
class EnhancedOIRecommendationResponse:
    """Enhanced OI-based trading recommendation response."""
    # Overall recommendation
    signal: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0 to 1.0
    current_price: float

    # Range-based analysis
    range_analysis: RangeOIResponse

    # Individual strike analysis
    individual_strikes: List[IndividualStrikeResponse]

    # Key bracketing strikes (for backward compatibility)
    lower_strike: float
    upper_strike: float
    lower_strike_analysis: Dict[str, Any]  # For backward compatibility
    upper_strike_analysis: Dict[str, Any]  # For backward compatibility

    # Combined interpretation
    reasoning: str
    risk_warning: str
    timestamp: str
    ai_enhancement: Optional[str] = None
