"""FastAPI server for Dhan AI Trader frontend integration."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import config
from ..api.client import DhanAPIClient
from ..market_data.manager import MarketDataManager
from ..market_data.depth_manager import MarketDepthManager
from ..ai.trading_advisor import TradingAdvisor
from ..ai.chat_service import ChatService
from ..strategies.oi_strategy import SameerSirOIStrategy
from ..strategies.range_oi_strategy import RangeOIStrategy
from ..analysis.depth_analyzer import MarketDepthAnalyzer
from ..exceptions import DhanTraderError, AuthenticationError, APIError
from .chat_models import (
    ChatRequest, ChatResponse, AnalysisRequest, AnalysisResponse,
    StrategyRequest, StrategyResponse, QuickAnalysisRequest, QuickAnalysisResponse,
    RangeOIRequest, RangeOIResponse, OIRecommendationRequest, OIRecommendationResponse,
    QuickOISignalResponse
)
from .models import EnhancedOIRecommendationResponse, RangeOIResponse as RangeOIResponseModel, IndividualStrikeResponse

logger = logging.getLogger(__name__)

# Global instances
api_client: Optional[DhanAPIClient] = None
market_data_manager: Optional[MarketDataManager] = None
market_depth_manager: Optional[MarketDepthManager] = None
depth_analyzer: Optional[MarketDepthAnalyzer] = None
trading_advisor: Optional[TradingAdvisor] = None
chat_service: Optional[ChatService] = None
oi_strategy: Optional[SameerSirOIStrategy] = None
range_oi_strategy: Optional[RangeOIStrategy] = None
websocket_connections: List[WebSocket] = []


# Pydantic models for API requests/responses
class UserProfileResponse(BaseModel):
    dhan_client_id: str
    token_validity: str
    active_segment: str
    ddpi: str
    mtf: str
    data_plan: str
    data_validity: str


class MarketQuoteResponse(BaseModel):
    security_id: str
    exchange_segment: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    prev_close_price: float
    change: float
    change_percent: float
    volume: int
    timestamp: Optional[datetime] = None


class GreeksData(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float


class OIChangeData(BaseModel):
    absolute_change: int
    percentage_change: float
    previous_oi: int
    current_oi: int
    timestamp: datetime


class OptionContractData(BaseModel):
    greeks: GreeksData
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
    oi_change: Optional[OIChangeData] = None


class OptionChainStrikeData(BaseModel):
    strike: float
    ce: Optional[OptionContractData] = None
    pe: Optional[OptionContractData] = None


class OptionChainResponse(BaseModel):
    underlying_price: float
    underlying_scrip: int
    underlying_segment: str
    expiry: str
    strikes: List[OptionChainStrikeData]


class OrderRequest(BaseModel):
    security_id: str
    exchange_segment: str
    transaction_type: str
    quantity: int
    order_type: str
    product_type: str
    price: float = 0.0
    trigger_price: float = 0.0
    validity: str = "DAY"


class PositionResponse(BaseModel):
    security_id: str
    exchange_segment: str
    product_type: str
    net_quantity: int
    buy_avg: float
    sell_avg: float
    net_avg: float
    pnl: float
    realized_pnl: float
    unrealized_pnl: float


class FundLimitResponse(BaseModel):
    available_balance: float
    sod_limit: float
    collateral_amount: float
    margin_used: float
    exposure_margin: float


class OIStrategyRequest(BaseModel):
    """Request for OI strategy analysis."""
    underlying_scrip: int = Field(default=13, description="Security ID (13 for NIFTY)")
    expiry: Optional[str] = Field(default=None, description="Option expiry date")
    center_strike: Optional[float] = Field(default=None, description="Center strike for analysis")
    strike_range: int = Field(default=100, description="Range around center strike")


class OIStrategyResponse(BaseModel):
    """Response for OI strategy analysis."""
    timestamp: datetime
    current_price: float
    range_analysis: Dict[str, Any]
    strike_analyses: List[Dict[str, Any]]
    overall_signal: str
    confidence: float
    targets: List[float]
    alerts: List[str]


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global api_client, market_data_manager, market_depth_manager, depth_analyzer, trading_advisor, chat_service, range_oi_strategy

    try:
        # Initialize API client
        api_client = DhanAPIClient()
        logger.info("API client initialized")

        # Initialize market data manager
        market_data_manager = MarketDataManager(api_client)

        # Initialize market depth manager for 20-level data
        market_depth_manager = MarketDepthManager(api_client)
        logger.info("Market depth manager initialized")

        # Initialize depth analyzer
        depth_analyzer = MarketDepthAnalyzer()
        logger.info("Depth analyzer initialized")

        # Initialize AI trading advisor
        trading_advisor = TradingAdvisor(market_data_manager, api_client)
        logger.info("Trading advisor initialized")

        # Initialize chat service
        chat_service = ChatService(trading_advisor)
        logger.info("Chat service initialized")

        # Initialize OI strategy
        global oi_strategy, range_oi_strategy
        oi_strategy = SameerSirOIStrategy(market_data_manager)
        logger.info("OI strategy initialized")

        # Initialize Range OI strategy
        range_oi_strategy = RangeOIStrategy(market_data_manager)
        logger.info("Range OI strategy initialized")

        # Start live market data feed
        try:
            market_data_manager.start_live_feed()
            logger.info("Market data feed started")
        except Exception as e:
            logger.warning(f"Could not start market data feed: {e}")

        yield

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Cleanup
        if market_data_manager:
            market_data_manager.stop_live_feed()
        logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Dhan AI Trader API",
    description="Backend API for Dhan AI Trader frontend",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:5173"
    ],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_api_client() -> DhanAPIClient:
    """Dependency to get API client."""
    if api_client is None:
        raise HTTPException(status_code=500, detail="API client not initialized")
    return api_client


def get_market_data_manager() -> MarketDataManager:
    """Dependency to get market data manager."""
    if market_data_manager is None:
        raise HTTPException(status_code=500, detail="Market data manager not initialized")
    return market_data_manager


def get_trading_advisor() -> TradingAdvisor:
    """Dependency to get trading advisor."""
    if trading_advisor is None:
        raise HTTPException(status_code=500, detail="Trading advisor not initialized")
    return trading_advisor


def get_chat_service() -> ChatService:
    """Dependency to get chat service."""
    if chat_service is None:
        raise HTTPException(status_code=500, detail="Chat service not initialized")
    return chat_service


def get_oi_strategy() -> SameerSirOIStrategy:
    """Dependency to get OI strategy."""
    if oi_strategy is None:
        raise HTTPException(status_code=500, detail="OI strategy not initialized")
    return oi_strategy


def get_range_oi_strategy() -> RangeOIStrategy:
    """Dependency to get Range OI strategy."""
    if range_oi_strategy is None:
        raise HTTPException(status_code=500, detail="Range OI strategy not initialized")
    return range_oi_strategy


@app.exception_handler(DhanTraderError)
async def dhan_trader_exception_handler(request, exc: DhanTraderError):
    """Handle Dhan Trader exceptions."""
    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "type": type(exc).__name__}
    )


@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request, exc: AuthenticationError):
    """Handle authentication exceptions."""
    return JSONResponse(
        status_code=401,
        content={"error": str(exc), "type": "AuthenticationError"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now()}


# User profile endpoints
@app.get("/api/profile", response_model=UserProfileResponse)
async def get_user_profile(client: DhanAPIClient = Depends(get_api_client)):
    """Get user profile information."""
    try:
        profile = client.get_user_profile()
        return UserProfileResponse(
            dhan_client_id=profile.dhan_client_id,
            token_validity=profile.token_validity,
            active_segment=profile.active_segment,
            ddpi=profile.ddpi,
            mtf=profile.mtf,
            data_plan=profile.data_plan,
            data_validity=profile.data_validity,
        )
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Market data endpoints
@app.get("/api/quote/{security_id}")
async def get_market_quote(
    security_id: str,
    exchange_segment: str = "NSE_EQ",
    client: DhanAPIClient = Depends(get_api_client)
):
    """Get market quote for an instrument."""
    try:
        quote = client.get_market_quote(security_id, exchange_segment)
        return MarketQuoteResponse(
            security_id=quote.security_id,
            exchange_segment=quote.exchange_segment,
            last_price=quote.last_price,
            open_price=quote.open_price,
            high_price=quote.high_price,
            low_price=quote.low_price,
            prev_close_price=quote.prev_close_price,
            change=quote.change,
            change_percent=quote.change_percent,
            volume=quote.volume,
            timestamp=quote.timestamp,
        )
    except Exception as e:
        logger.error(f"Error getting market quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/optionchain/{underlying_scrip}", response_model=OptionChainResponse)
async def get_option_chain(
    underlying_scrip: int,
    underlying_segment: str = "IDX_I",
    expiry: Optional[str] = None,
    manager: MarketDataManager = Depends(get_market_data_manager)
):
    """Get option chain data."""
    try:
        option_chain = manager.get_option_chain_with_oi_changes(underlying_scrip, underlying_segment, expiry, use_cache=False)
        
        # Convert strikes to list format
        strikes_list = []
        for strike_price, strike_data in option_chain.strikes.items():
            strike_response = OptionChainStrikeData(strike=float(strike_price))
            
            if strike_data.ce:
                # Convert OI change data if available
                oi_change_data = None
                if strike_data.ce.oi_change:
                    oi_change_data = OIChangeData(
                        absolute_change=strike_data.ce.oi_change.absolute_change,
                        percentage_change=strike_data.ce.oi_change.percentage_change,
                        previous_oi=strike_data.ce.oi_change.previous_oi,
                        current_oi=strike_data.ce.oi_change.current_oi,
                        timestamp=strike_data.ce.oi_change.timestamp,
                    )

                strike_response.ce = OptionContractData(
                    greeks=GreeksData(
                        delta=strike_data.ce.greeks.delta,
                        gamma=strike_data.ce.greeks.gamma,
                        theta=strike_data.ce.greeks.theta,
                        vega=strike_data.ce.greeks.vega,
                    ),
                    implied_volatility=strike_data.ce.implied_volatility,
                    last_price=strike_data.ce.last_price,
                    oi=strike_data.ce.oi,
                    previous_close_price=strike_data.ce.previous_close_price,
                    previous_oi=strike_data.ce.previous_oi,
                    previous_volume=strike_data.ce.previous_volume,
                    top_ask_price=strike_data.ce.top_ask_price,
                    top_ask_quantity=strike_data.ce.top_ask_quantity,
                    top_bid_price=strike_data.ce.top_bid_price,
                    top_bid_quantity=strike_data.ce.top_bid_quantity,
                    volume=strike_data.ce.volume,
                    oi_change=oi_change_data,
                )
            
            if strike_data.pe:
                # Convert OI change data if available
                oi_change_data = None
                if strike_data.pe.oi_change:
                    oi_change_data = OIChangeData(
                        absolute_change=strike_data.pe.oi_change.absolute_change,
                        percentage_change=strike_data.pe.oi_change.percentage_change,
                        previous_oi=strike_data.pe.oi_change.previous_oi,
                        current_oi=strike_data.pe.oi_change.current_oi,
                        timestamp=strike_data.pe.oi_change.timestamp,
                    )

                strike_response.pe = OptionContractData(
                    greeks=GreeksData(
                        delta=strike_data.pe.greeks.delta,
                        gamma=strike_data.pe.greeks.gamma,
                        theta=strike_data.pe.greeks.theta,
                        vega=strike_data.pe.greeks.vega,
                    ),
                    implied_volatility=strike_data.pe.implied_volatility,
                    last_price=strike_data.pe.last_price,
                    oi=strike_data.pe.oi,
                    previous_close_price=strike_data.pe.previous_close_price,
                    previous_oi=strike_data.pe.previous_oi,
                    previous_volume=strike_data.pe.previous_volume,
                    top_ask_price=strike_data.pe.top_ask_price,
                    top_ask_quantity=strike_data.pe.top_ask_quantity,
                    top_bid_price=strike_data.pe.top_bid_price,
                    top_bid_quantity=strike_data.pe.top_bid_quantity,
                    volume=strike_data.pe.volume,
                    oi_change=oi_change_data,
                )
            
            strikes_list.append(strike_response)
        
        return OptionChainResponse(
            underlying_price=option_chain.underlying_price,
            underlying_scrip=option_chain.underlying_scrip,
            underlying_segment=option_chain.underlying_segment,
            expiry=option_chain.expiry,
            strikes=strikes_list,
        )
    except Exception as e:
        logger.error(f"Error getting option chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/optionchain/{underlying_scrip}/expiries")
async def get_option_expiry_list(
    underlying_scrip: int,
    underlying_segment: str = "IDX_I",
    manager: MarketDataManager = Depends(get_market_data_manager)
):
    """Get list of option expiry dates."""
    try:
        expiries = manager.get_option_expiry_list(underlying_scrip, underlying_segment)
        return {"expiries": expiries}
    except Exception as e:
        logger.error(f"Error getting expiry list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 20-Level Market Depth endpoints
def get_market_depth_manager() -> MarketDepthManager:
    """Get market depth manager dependency."""
    if market_depth_manager is None:
        raise HTTPException(status_code=503, detail="Market depth manager not initialized")
    return market_depth_manager


def get_depth_analyzer() -> MarketDepthAnalyzer:
    """Get depth analyzer dependency."""
    if depth_analyzer is None:
        raise HTTPException(status_code=503, detail="Depth analyzer not initialized")
    return depth_analyzer


@app.post("/api/depth/subscribe")
async def subscribe_market_depth(
    security_id: str,
    exchange_segment: str,
    manager: MarketDepthManager = Depends(get_market_depth_manager)
):
    """Subscribe to 20-level market depth."""
    try:
        # Validate exchange segment
        if exchange_segment not in ["NSE_EQ", "NSE_FNO"]:
            raise HTTPException(
                status_code=400,
                detail=f"Exchange segment {exchange_segment} not supported for 20-level depth"
            )

        manager.subscribe_depth(security_id, exchange_segment)
        return {"status": "subscribed", "security_id": security_id, "exchange_segment": exchange_segment}
    except Exception as e:
        logger.error(f"Error subscribing to market depth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/depth/unsubscribe")
async def unsubscribe_market_depth(
    security_id: str,
    manager: MarketDepthManager = Depends(get_market_depth_manager)
):
    """Unsubscribe from 20-level market depth."""
    try:
        manager.unsubscribe_depth(security_id)
        return {"status": "unsubscribed", "security_id": security_id}
    except Exception as e:
        logger.error(f"Error unsubscribing from market depth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/depth/{security_id}")
async def get_market_depth_data(
    security_id: str,
    manager: MarketDepthManager = Depends(get_market_depth_manager)
):
    """Get current 20-level market depth data."""
    try:
        depth_data = manager.get_depth_data(security_id)
        if depth_data is None:
            raise HTTPException(status_code=404, detail=f"No depth data found for security {security_id}")

        return {
            "security_id": depth_data.security_id,
            "exchange_segment": depth_data.exchange_segment,
            "bid_depth": {
                "levels": [
                    {
                        "price": level.price,
                        "quantity": level.quantity,
                        "orders": level.orders
                    }
                    for level in depth_data.bid_depth.levels
                ],
                "side": depth_data.bid_depth.side,
                "timestamp": depth_data.bid_depth.timestamp.isoformat()
            },
            "ask_depth": {
                "levels": [
                    {
                        "price": level.price,
                        "quantity": level.quantity,
                        "orders": level.orders
                    }
                    for level in depth_data.ask_depth.levels
                ],
                "side": depth_data.ask_depth.side,
                "timestamp": depth_data.ask_depth.timestamp.isoformat()
            },
            "timestamp": depth_data.timestamp.isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting depth data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/depth/{security_id}/analysis")
async def get_market_depth_analysis(
    security_id: str,
    manager: MarketDepthManager = Depends(get_market_depth_manager),
    analyzer: MarketDepthAnalyzer = Depends(get_depth_analyzer)
):
    """Get market depth analysis."""
    try:
        depth_data = manager.get_depth_data(security_id)
        if depth_data is None:
            raise HTTPException(status_code=404, detail=f"No depth data found for security {security_id}")

        analysis = analyzer.analyze_depth(depth_data)

        return {
            "security_id": security_id,
            "total_bid_quantity": analysis.total_bid_quantity,
            "total_ask_quantity": analysis.total_ask_quantity,
            "bid_ask_ratio": analysis.bid_ask_ratio,
            "zones": {
                "demand_zones": analysis.zones.demand_zones,
                "supply_zones": analysis.zones.supply_zones
            },
            "microstructure": {
                "order_flow_imbalance": analysis.microstructure.order_flow_imbalance,
                "liquidity_score": analysis.microstructure.liquidity_score,
                "market_efficiency": analysis.microstructure.market_efficiency,
                "volatility_estimate": analysis.microstructure.volatility_estimate
            },
            "trading_signal": {
                "signal_type": analysis.trading_signal.signal_type,
                "strength": analysis.trading_signal.strength,
                "confidence": analysis.trading_signal.confidence,
                "time_horizon": analysis.trading_signal.time_horizon,
                "target_levels": analysis.trading_signal.target_levels,
                "stop_loss": analysis.trading_signal.stop_loss,
                "reasoning": analysis.trading_signal.reasoning
            },
            "timestamp": analysis.timestamp.isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting depth analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/depth/subscriptions")
async def get_depth_subscriptions(
    manager: MarketDepthManager = Depends(get_market_depth_manager)
):
    """Get list of active depth subscriptions."""
    try:
        subscriptions = manager.get_all_subscribed_securities()
        return {"subscriptions": subscriptions, "count": len(subscriptions)}
    except Exception as e:
        logger.error(f"Error getting depth subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Trading endpoints
@app.post("/api/orders")
async def place_order(
    order: OrderRequest,
    client: DhanAPIClient = Depends(get_api_client)
):
    """Place a new order."""
    try:
        from ..api.models import ExchangeSegment, TransactionType, OrderType, ProductType

        order_id = client.place_order(
            security_id=order.security_id,
            exchange_segment=ExchangeSegment(order.exchange_segment),
            transaction_type=TransactionType(order.transaction_type),
            quantity=order.quantity,
            order_type=OrderType(order.order_type),
            product_type=ProductType(order.product_type),
            price=order.price,
            trigger_price=order.trigger_price,
            validity=order.validity,
        )
        return {"order_id": order_id, "status": "success"}
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orders")
async def get_orders(client: DhanAPIClient = Depends(get_api_client)):
    """Get all orders."""
    try:
        orders = client.get_orders()
        return {
            "orders": [
                {
                    "order_id": order.order_id,
                    "security_id": order.security_id,
                    "exchange_segment": order.exchange_segment.value,
                    "transaction_type": order.transaction_type.value,
                    "order_type": order.order_type.value,
                    "product_type": order.product_type.value,
                    "quantity": order.quantity,
                    "price": order.price,
                    "trigger_price": order.trigger_price,
                    "order_status": order.order_status.value,
                    "traded_quantity": order.traded_quantity,
                    "remaining_quantity": order.remaining_quantity,
                    "created_at": order.created_at.isoformat(),
                    "updated_at": order.updated_at.isoformat(),
                }
                for order in orders
            ]
        }
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/positions", response_model=List[PositionResponse])
async def get_positions(client: DhanAPIClient = Depends(get_api_client)):
    """Get all positions."""
    try:
        positions = client.get_positions()
        return [
            PositionResponse(
                security_id=pos.security_id,
                exchange_segment=pos.exchange_segment.value,
                product_type=pos.product_type.value,
                net_quantity=pos.net_quantity,
                buy_avg=pos.buy_avg,
                sell_avg=pos.sell_avg,
                net_avg=pos.net_avg,
                pnl=pos.pnl,
                realized_pnl=pos.realized_pnl,
                unrealized_pnl=pos.unrealized_pnl,
            )
            for pos in positions
        ]
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/holdings")
async def get_holdings(client: DhanAPIClient = Depends(get_api_client)):
    """Get all holdings."""
    try:
        holdings = client.get_holdings()
        return {
            "holdings": [
                {
                    "security_id": holding.security_id,
                    "exchange_segment": holding.exchange_segment.value,
                    "product_type": holding.product_type.value,
                    "quantity": holding.quantity,
                    "avg_cost_price": holding.avg_cost_price,
                    "last_price": holding.last_price,
                    "pnl": holding.pnl,
                    "pnl_percent": holding.pnl_percent,
                }
                for holding in holdings
            ]
        }
    except Exception as e:
        logger.error(f"Error getting holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/funds", response_model=FundLimitResponse)
async def get_fund_limits(client: DhanAPIClient = Depends(get_api_client)):
    """Get fund limit information."""
    try:
        fund_limit = client.get_fund_limit()
        return FundLimitResponse(
            available_balance=fund_limit.available_balance,
            sod_limit=fund_limit.sod_limit,
            collateral_amount=fund_limit.collateral_amount,
            margin_used=fund_limit.margin_used,
            exposure_margin=fund_limit.exposure_margin,
        )
    except Exception as e:
        logger.error(f"Error getting fund limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time data
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data."""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        while True:
            # Wait for client messages
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "subscribe":
                # Handle subscription requests
                security_id = data.get("security_id")
                exchange_segment = data.get("exchange_segment", "NSE_EQ")

                if security_id and market_data_manager:
                    try:
                        # Subscribe to live data with callback
                        def on_update(packet):
                            asyncio.create_task(send_market_update(websocket, packet))

                        market_data_manager.subscribe_instrument(
                            security_id, exchange_segment, callback=on_update
                        )

                        await websocket.send_json({
                            "type": "subscription_success",
                            "security_id": security_id,
                            "exchange_segment": exchange_segment
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })

            elif message_type == "unsubscribe":
                # Handle unsubscription requests
                security_id = data.get("security_id")
                exchange_segment = data.get("exchange_segment", "NSE_EQ")

                if security_id and market_data_manager:
                    try:
                        market_data_manager.unsubscribe_instrument(security_id, exchange_segment)
                        await websocket.send_json({
                            "type": "unsubscription_success",
                            "security_id": security_id
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })

            elif message_type == "subscribe_depth_20":
                # Handle 20-level market depth subscription
                security_id = data.get("security_id")
                exchange_segment = data.get("exchange_segment", "NSE_EQ")

                if security_id and market_depth_manager:
                    try:
                        # Subscribe to 20-level depth with callback
                        def on_depth_update(depth_response):
                            asyncio.create_task(send_depth_update(websocket, depth_response))

                        market_depth_manager.subscribe_depth(
                            security_id, exchange_segment, callback=on_depth_update
                        )

                        await websocket.send_json({
                            "type": "subscription_success",
                            "security_id": security_id,
                            "exchange_segment": exchange_segment,
                            "data_type": "market_depth_20"
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })

            elif message_type == "unsubscribe_depth_20":
                # Handle 20-level market depth unsubscription
                security_id = data.get("security_id")

                if security_id and market_depth_manager:
                    try:
                        market_depth_manager.unsubscribe_depth(security_id)
                        await websocket.send_json({
                            "type": "unsubscription_success",
                            "security_id": security_id,
                            "data_type": "market_depth_20"
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })

    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


async def send_market_update(websocket: WebSocket, packet):
    """Send market data update to WebSocket client."""
    try:
        await websocket.send_json({
            "type": "market_update",
            "data": {
                "security_id": packet.security_id,
                "exchange_segment": packet.exchange_segment,
                "ltp": getattr(packet, 'ltp', None),
                "ltt": getattr(packet, 'ltt', None),
                "volume": getattr(packet, 'volume', None),
                "timestamp": packet.timestamp
            }
        })
    except Exception as e:
        logger.error(f"Error sending market update: {e}")


async def send_depth_update(websocket: WebSocket, depth_response):
    """Send 20-level market depth update to WebSocket client."""
    try:
        await websocket.send_json({
            "type": "market_update",
            "data": {
                "market_depth_20": {
                    "security_id": depth_response.security_id,
                    "exchange_segment": depth_response.exchange_segment,
                    "bid_depth": {
                        "levels": [
                            {
                                "price": level.price,
                                "quantity": level.quantity,
                                "orders": level.orders
                            }
                            for level in depth_response.bid_depth.levels
                        ],
                        "side": depth_response.bid_depth.side,
                        "timestamp": depth_response.bid_depth.timestamp.isoformat()
                    },
                    "ask_depth": {
                        "levels": [
                            {
                                "price": level.price,
                                "quantity": level.quantity,
                                "orders": level.orders
                            }
                            for level in depth_response.ask_depth.levels
                        ],
                        "side": depth_response.ask_depth.side,
                        "timestamp": depth_response.ask_depth.timestamp.isoformat()
                    },
                    "timestamp": depth_response.timestamp.isoformat()
                }
            }
        })
    except Exception as e:
        logger.error(f"Error sending depth update: {e}")


# AI Chat endpoints
@app.post("/api/chat/message")
async def send_chat_message(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Send a message to the AI trading advisor."""
    try:
        response = await chat_service.process_chat_message(request)
        return response
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/analysis")
async def get_market_analysis(
    request: AnalysisRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get detailed market analysis."""
    try:
        response = await chat_service.get_market_analysis(request)
        return response
    except Exception as e:
        logger.error(f"Error getting market analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/strategies")
async def get_strategy_suggestions(
    request: StrategyRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get trading strategy suggestions."""
    try:
        response = await chat_service.get_strategy_suggestions(request)
        return response
    except Exception as e:
        logger.error(f"Error getting strategy suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/sessions")
async def get_all_chat_sessions(
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get all chat sessions."""
    try:
        sessions = chat_service.get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error getting all chat sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get chat session history."""
    try:
        session = chat_service.get_session_history(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/quick-analysis")
async def get_quick_analysis(
    query_type: str = "market_overview",
    trading_advisor: TradingAdvisor = Depends(get_trading_advisor)
):
    """Get quick market analysis."""
    try:
        if query_type == "option_chain":
            analysis = await trading_advisor.analyze_option_chain_ai()
        elif query_type == "unusual_activity":
            analysis = await trading_advisor.detect_unusual_activity()
        elif query_type == "oi_changes":
            analysis = await trading_advisor.analyze_oi_changes()
        elif query_type == "market_overview":
            analysis = await trading_advisor.get_trading_recommendation(
                "Provide a quick overview of current market conditions"
            )
        else:
            analysis = await trading_advisor.get_trading_recommendation(
                f"Provide analysis for {query_type}"
            )

        return QuickAnalysisResponse(
            insight=analysis,
            confidence=0.8,
            data_freshness="real-time",
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error getting quick analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/oi-changes")
async def get_oi_changes_analysis(
    underlying_scrip: int = 13,
    expiry: Optional[str] = None,
    trading_advisor: TradingAdvisor = Depends(get_trading_advisor)
):
    """Get detailed OI changes analysis."""
    try:
        analysis = await trading_advisor.analyze_oi_changes(underlying_scrip, expiry)
        return {
            "analysis": analysis,
            "timestamp": datetime.now(),
            "underlying_scrip": underlying_scrip,
            "expiry": expiry
        }
    except Exception as e:
        logger.error(f"Error getting OI changes analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# OI Strategy endpoints
@app.post("/api/strategy/oi-analysis")
async def get_oi_strategy_analysis(
    request: OIStrategyRequest,
    oi_strategy: SameerSirOIStrategy = Depends(get_oi_strategy)
) -> OIStrategyResponse:
    """Get Sameer Sir OI Strategy analysis."""
    try:
        signal = oi_strategy.analyze_oi_strategy(
            underlying_scrip=request.underlying_scrip,
            expiry=request.expiry,
            center_strike=request.center_strike,
            strike_range=request.strike_range
        )

        # Convert to response format
        return OIStrategyResponse(
            timestamp=signal.timestamp,
            current_price=signal.current_price,
            range_analysis={
                "lower_strike": signal.range_analysis.lower_strike,
                "upper_strike": signal.range_analysis.upper_strike,
                "total_ce_oi": signal.range_analysis.total_ce_oi,
                "total_pe_oi": signal.range_analysis.total_pe_oi,
                "oi_ratio": signal.range_analysis.oi_ratio,
                "signal": signal.range_analysis.signal,
                "strength": signal.range_analysis.strength
            },
            strike_analyses=[
                {
                    "strike": analysis.strike,
                    "ce_oi": analysis.ce_oi,
                    "pe_oi": analysis.pe_oi,
                    "oi_ratio": analysis.oi_ratio,
                    "signal": analysis.signal,
                    "strength": analysis.strength
                }
                for analysis in signal.strike_analyses
            ],
            overall_signal=signal.overall_signal,
            confidence=signal.confidence,
            targets=signal.targets,
            alerts=signal.alerts
        )
    except Exception as e:
        logger.error(f"Error getting OI strategy analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/oi-history")
async def get_oi_strategy_history(
    limit: int = 10,
    oi_strategy: SameerSirOIStrategy = Depends(get_oi_strategy)
):
    """Get OI strategy signal history."""
    try:
        history = oi_strategy.get_signal_history(limit)
        return {
            "signals": [
                {
                    "timestamp": signal.timestamp.isoformat(),
                    "current_price": signal.current_price,
                    "overall_signal": signal.overall_signal,
                    "confidence": signal.confidence,
                    "targets": signal.targets,
                    "alerts": signal.alerts
                }
                for signal in history
            ]
        }
    except Exception as e:
        logger.error(f"Error getting OI strategy history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Range OI Strategy endpoints
@app.post("/api/strategy/range-oi-analysis", response_model=RangeOIResponse)
async def get_range_oi_analysis(
    request: RangeOIRequest,
    strategy: RangeOIStrategy = Depends(get_range_oi_strategy)
) -> RangeOIResponse:
    """
    Get Range-based OI Strategy analysis.

    This endpoint implements the specific logic:
    1. Find nearest strikes to current price (e.g., 25400 and 25500 for price 25440)
    2. Compare PE vs CE OI for each strike
    3. Generate bullish/bearish/neutral signals based on OI comparison
    """
    try:
        analysis = strategy.analyze_range_oi(
            underlying_scrip=request.underlying_scrip,
            expiry=request.expiry,
            current_price=request.current_price,
            lower_strike=request.lower_strike,
            upper_strike=request.upper_strike
        )

        return RangeOIResponse(
            current_price=analysis.current_price,
            lower_strike=analysis.lower_strike,
            upper_strike=analysis.upper_strike,
            lower_strike_pe_oi=analysis.lower_strike_pe_oi,
            lower_strike_ce_oi=analysis.lower_strike_ce_oi,
            upper_strike_pe_oi=analysis.upper_strike_pe_oi,
            upper_strike_ce_oi=analysis.upper_strike_ce_oi,
            lower_strike_signal=analysis.lower_strike_signal,
            upper_strike_signal=analysis.upper_strike_signal,
            overall_signal=analysis.overall_signal,
            confidence=analysis.confidence,
            reasoning=analysis.reasoning,
            timestamp=analysis.timestamp
        )

    except Exception as e:
        logger.error(f"Error in Range OI analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/range-oi-history")
async def get_range_oi_history(
    limit: int = 10,
    strategy: RangeOIStrategy = Depends(get_range_oi_strategy)
):
    """Get Range OI strategy signal history."""
    try:
        history = strategy.get_signal_history(limit)
        return {
            "signals": [
                {
                    "timestamp": signal.timestamp.isoformat(),
                    "current_price": signal.current_price,
                    "lower_strike": signal.lower_strike,
                    "upper_strike": signal.upper_strike,
                    "overall_signal": signal.overall_signal,
                    "confidence": signal.confidence,
                    "reasoning": signal.reasoning
                }
                for signal in history
            ]
        }
    except Exception as e:
        logger.error(f"Error getting Range OI history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/individual-strike-oi/{strike_price}")
async def get_individual_strike_oi(
    strike_price: float,
    underlying_scrip: int = 13,
    expiry: Optional[str] = None,
    strategy: RangeOIStrategy = Depends(get_range_oi_strategy)
):
    """
    Get OI data for a specific individual strike price.

    Example: /api/strategy/individual-strike-oi/25500
    """
    try:
        strike_oi_data = strategy.get_individual_strike_oi(
            strike_price=strike_price,
            underlying_scrip=underlying_scrip,
            expiry=expiry
        )

        if not strike_oi_data:
            raise HTTPException(
                status_code=404,
                detail=f"No OI data found for strike {strike_price}"
            )

        return {
            "strike_price": strike_oi_data.strike_price,
            "pe_oi": strike_oi_data.pe_oi,
            "ce_oi": strike_oi_data.ce_oi,
            "pe_volume": strike_oi_data.pe_volume,
            "ce_volume": strike_oi_data.ce_volume,
            "pe_ltp": strike_oi_data.pe_ltp,
            "ce_ltp": strike_oi_data.ce_ltp,
            "pe_ce_ratio": strike_oi_data.pe_oi / max(strike_oi_data.ce_oi, 1),
            "signal": "support" if strike_oi_data.pe_oi > strike_oi_data.ce_oi else "resistance" if strike_oi_data.ce_oi > strike_oi_data.pe_oi else "neutral",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting individual strike OI for {strike_price}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/strategy/opening-range-oi-analysis")
async def get_opening_range_oi_analysis(
    opening_price: float,
    underlying_scrip: int = 13,
    expiry: Optional[str] = None,
    range_interval: int = 100,
    strategy: RangeOIStrategy = Depends(get_range_oi_strategy)
):
    """
    Get Range OI analysis based on opening price.

    Example: For opening price 24619 with range_interval=100
    Analyzes range 24600-24700

    Args:
        opening_price: Today's opening price (e.g., 24619)
        range_interval: Range interval in points (default: 100)
    """
    try:
        analysis = strategy.analyze_opening_range_oi(
            opening_price=opening_price,
            underlying_scrip=underlying_scrip,
            expiry=expiry,
            range_interval=range_interval
        )

        return RangeOIResponse(
            current_price=analysis.current_price,
            lower_strike=analysis.lower_strike,
            upper_strike=analysis.upper_strike,
            lower_strike_pe_oi=analysis.lower_strike_pe_oi,
            lower_strike_ce_oi=analysis.lower_strike_ce_oi,
            upper_strike_pe_oi=analysis.upper_strike_pe_oi,
            upper_strike_ce_oi=analysis.upper_strike_ce_oi,
            lower_strike_signal=analysis.lower_strike_signal,
            upper_strike_signal=analysis.upper_strike_signal,
            overall_signal=analysis.overall_signal,
            confidence=analysis.confidence,
            reasoning=analysis.reasoning,
            timestamp=analysis.timestamp
        )

    except Exception as e:
        logger.error(f"Error in opening range OI analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# OI-based Trading Recommendation endpoints
@app.post("/api/recommendations/oi-based", response_model=OIRecommendationResponse)
async def get_oi_based_recommendation(
    request: OIRecommendationRequest,
    trading_advisor: TradingAdvisor = Depends(get_trading_advisor)
):
    """
    Get OI-based trading recommendation using the specific algorithm.

    This endpoint implements the core OI analysis:
    1. Find nearest strikes bracketing current price
    2. Compare PE vs CE OI at both strikes
    3. Generate bullish/bearish/neutral signals with confidence levels
    """
    try:
        # Get the OI recommendation
        recommendation = trading_advisor.oi_recommendation_service.get_oi_recommendation(
            request.underlying_scrip, request.expiry
        )

        # Get AI enhancement if requested
        ai_enhancement = None
        if request.include_ai_analysis and recommendation.signal != "neutral":
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

                ai_enhancement = await trading_advisor.ai_client.answer_trading_question(
                    question=f"Based on this OI analysis showing a {recommendation.signal} signal with {recommendation.confidence:.1%} confidence, provide specific trading strategies and entry/exit points for NIFTY options.",
                    market_context=ai_context,
                    portfolio_context=None
                )
            except Exception as e:
                logger.warning(f"Could not get AI enhancement: {e}")

        return OIRecommendationResponse(
            signal=recommendation.signal,
            confidence=recommendation.confidence,
            current_price=recommendation.current_price,
            lower_strike=recommendation.lower_strike,
            upper_strike=recommendation.upper_strike,
            lower_strike_analysis=recommendation.lower_strike_analysis,
            upper_strike_analysis=recommendation.upper_strike_analysis,
            reasoning=recommendation.reasoning,
            risk_warning=recommendation.risk_warning,
            ai_enhancement=ai_enhancement,
            timestamp=recommendation.timestamp
        )

    except Exception as e:
        logger.error(f"Error getting OI-based recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/quick-oi-signal", response_model=QuickOISignalResponse)
async def get_quick_oi_signal(
    underlying_scrip: int = 13,
    trading_advisor: TradingAdvisor = Depends(get_trading_advisor)
):
    """Get a quick OI signal for dashboard or quick reference."""
    try:
        signal_data = await trading_advisor.get_quick_oi_signal(underlying_scrip)

        return QuickOISignalResponse(
            signal=signal_data["signal"],
            confidence=signal_data["confidence"],
            current_price=signal_data["current_price"],
            lower_strike=signal_data["lower_strike"],
            upper_strike=signal_data["upper_strike"],
            summary=signal_data["summary"],
            timestamp=signal_data["timestamp"]
        )

    except Exception as e:
        logger.error(f"Error getting quick OI signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommendations/oi-enhanced", response_model=EnhancedOIRecommendationResponse)
async def get_enhanced_oi_recommendation(
    request: OIRecommendationRequest,
    trading_advisor: TradingAdvisor = Depends(get_trading_advisor)
):
    """
    Get enhanced OI-based trading recommendation with comprehensive range and individual strike analysis.

    This endpoint provides:
    - Range-based OI analysis around current price
    - Individual strike analysis for key strikes
    - Combined interpretation with macro and micro insights
    - Enhanced reasoning and trading implications
    """
    try:
        # Get enhanced OI recommendation
        recommendation = trading_advisor.oi_recommendation_service.get_enhanced_oi_recommendation(
            underlying_scrip=request.underlying_scrip,
            expiry=request.expiry,
            range_width=100,  # 100 points range around current price
            include_ai_analysis=request.include_ai_analysis
        )

        # Convert range analysis to response model
        range_response = RangeOIResponseModel(
            range_start=recommendation.range_analysis.range_start,
            range_end=recommendation.range_analysis.range_end,
            current_price=recommendation.range_analysis.current_price,
            total_ce_oi=recommendation.range_analysis.total_ce_oi,
            total_pe_oi=recommendation.range_analysis.total_pe_oi,
            pe_ce_ratio=recommendation.range_analysis.pe_ce_ratio,
            range_sentiment=recommendation.range_analysis.range_sentiment,
            confidence=recommendation.range_analysis.confidence,
            key_strikes=recommendation.range_analysis.key_strikes,
            interpretation=recommendation.range_analysis.interpretation,
            trading_implications=recommendation.range_analysis.trading_implications
        )

        # Convert individual strikes to response models
        individual_responses = [
            IndividualStrikeResponse(
                strike=strike.strike,
                ce_oi=strike.ce_oi,
                pe_oi=strike.pe_oi,
                ce_volume=strike.ce_volume,
                pe_volume=strike.pe_volume,
                pe_ce_oi_ratio=strike.pe_ce_oi_ratio,
                signal=strike.signal,
                significance=strike.significance,
                distance_from_spot=strike.distance_from_spot,
                distance_category=strike.distance_category,
                reasoning=strike.reasoning,
                trading_implications=strike.trading_implications,
                data_available=strike.data_available
            )
            for strike in recommendation.individual_strikes
        ]

        # Add AI enhancement if requested
        ai_enhancement = None
        if request.include_ai_analysis:
            try:
                ai_enhancement = await trading_advisor.chat_service.get_ai_enhancement(
                    analysis_type="oi_recommendation",
                    market_data={
                        "signal": recommendation.signal,
                        "confidence": recommendation.confidence,
                        "current_price": recommendation.current_price,
                        "range_analysis": recommendation.range_analysis.__dict__,
                        "individual_strikes": [strike.__dict__ for strike in recommendation.individual_strikes[:3]]
                    },
                    portfolio_context=None
                )
            except Exception as e:
                logger.warning(f"Could not get AI enhancement: {e}")

        return EnhancedOIRecommendationResponse(
            signal=recommendation.signal,
            confidence=recommendation.confidence,
            current_price=recommendation.current_price,
            range_analysis=range_response,
            individual_strikes=individual_responses,
            lower_strike=recommendation.lower_strike,
            upper_strike=recommendation.upper_strike,
            lower_strike_analysis=recommendation.lower_strike_analysis,
            upper_strike_analysis=recommendation.upper_strike_analysis,
            reasoning=recommendation.reasoning,
            risk_warning=recommendation.risk_warning,
            timestamp=recommendation.timestamp.isoformat(),
            ai_enhancement=ai_enhancement
        )

    except Exception as e:
        logger.error(f"Error getting enhanced OI recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Utility endpoints
@app.get("/api/instruments/popular")
async def get_popular_instruments():
    """Get list of popular instruments."""
    return {
        "instruments": [
            {"security_id": "13", "symbol": "NIFTY", "exchange_segment": "IDX_I", "name": "NIFTY 50"},
            {"security_id": "25", "symbol": "BANKNIFTY", "exchange_segment": "IDX_I", "name": "BANK NIFTY"},
            {"security_id": "1", "symbol": "SENSEX", "exchange_segment": "IDX_I", "name": "SENSEX"},
            {"security_id": "11536", "symbol": "RELIANCE", "exchange_segment": "NSE_EQ", "name": "Reliance Industries"},
            {"security_id": "1333", "symbol": "INFY", "exchange_segment": "NSE_EQ", "name": "Infosys"},
        ]
    }


@app.get("/api/debug/oi-data/{underlying_scrip}")
async def debug_oi_data(
    underlying_scrip: int,
    underlying_segment: str = "IDX_I",
    expiry: Optional[str] = None,
    manager: MarketDataManager = Depends(get_market_data_manager)
):
    """Debug endpoint to check OI data that OI recommendation service sees."""
    try:
        # Get the same data that OI recommendation service uses
        option_chain = manager.get_option_chain_with_oi_changes(underlying_scrip, underlying_segment, expiry, use_cache=True)

        # Extract data for strikes around current price
        current_price = option_chain.underlying_price
        debug_data = {
            "current_price": current_price,
            "expiry": option_chain.expiry,
            "total_strikes": len(option_chain.strikes),
            "strikes_sample": {}
        }

        # Get strikes around current price
        for strike_key, strike_data in option_chain.strikes.items():
            strike_price = float(strike_key)
            if abs(strike_price - current_price) <= 100:  # Within 100 points
                debug_data["strikes_sample"][strike_key] = {
                    "strike": strike_price,
                    "ce_oi": strike_data.ce.oi if strike_data.ce else None,
                    "pe_oi": strike_data.pe.oi if strike_data.pe else None,
                    "ce_volume": strike_data.ce.volume if strike_data.ce else None,
                    "pe_volume": strike_data.pe.volume if strike_data.pe else None,
                }

        return debug_data
    except Exception as e:
        logger.error(f"Error in debug OI data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dhan_trader.api.server:app",
        host=config.dashboard.host,
        port=config.dashboard.port,
        reload=config.dashboard.debug,
        log_level="info"
    )
