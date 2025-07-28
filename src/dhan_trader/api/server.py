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
from ..exceptions import DhanTraderError, AuthenticationError, APIError

logger = logging.getLogger(__name__)

# Global instances
api_client: Optional[DhanAPIClient] = None
market_data_manager: Optional[MarketDataManager] = None
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


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global api_client, market_data_manager
    
    try:
        # Initialize API client
        api_client = DhanAPIClient()
        logger.info("API client initialized")
        
        # Initialize market data manager
        market_data_manager = MarketDataManager(api_client)
        
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
        option_chain = manager.get_option_chain(underlying_scrip, underlying_segment, expiry)
        
        # Convert strikes to list format
        strikes_list = []
        for strike_price, strike_data in option_chain.strikes.items():
            strike_response = OptionChainStrikeData(strike=float(strike_price))
            
            if strike_data.ce:
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
                )
            
            if strike_data.pe:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dhan_trader.api.server:app",
        host=config.dashboard.host,
        port=config.dashboard.port,
        reload=config.dashboard.debug,
        log_level="info"
    )
