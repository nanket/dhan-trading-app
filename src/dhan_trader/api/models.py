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
