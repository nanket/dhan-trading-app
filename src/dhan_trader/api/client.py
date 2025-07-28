"""Dhan API client implementation."""

import time
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import config
from ..exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)
from .models import (
    UserProfile,
    OptionChain,
    OptionChainStrike,
    OptionData,
    Greeks,
    MarketQuote,
    Order,
    Position,
    Holding,
    FundLimit,
    HistoricalData,
    ExchangeSegment,
    OrderType,
    OrderStatus,
    TransactionType,
    ProductType,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self):
        self.requests = {}
        self.limits = {
            'order': {'per_second': 25, 'per_minute': 250, 'per_hour': 1000, 'per_day': 7000},
            'data': {'per_second': 5, 'per_minute': None, 'per_hour': None, 'per_day': 100000},
            'quote': {'per_second': 1, 'per_minute': None, 'per_hour': None, 'per_day': None},
            'non_trading': {'per_second': 20, 'per_minute': None, 'per_hour': None, 'per_day': None},
        }
    
    def can_make_request(self, endpoint_type: str) -> bool:
        """Check if request can be made based on rate limits."""
        now = time.time()
        
        if endpoint_type not in self.requests:
            self.requests[endpoint_type] = []
        
        # Clean old requests
        self.requests[endpoint_type] = [
            req_time for req_time in self.requests[endpoint_type]
            if now - req_time < 86400  # Keep last 24 hours
        ]
        
        limits = self.limits.get(endpoint_type, self.limits['non_trading'])
        
        # Check per second limit
        recent_requests = [
            req_time for req_time in self.requests[endpoint_type]
            if now - req_time < 1
        ]
        if len(recent_requests) >= limits['per_second']:
            return False
        
        return True
    
    def record_request(self, endpoint_type: str):
        """Record a request for rate limiting."""
        if endpoint_type not in self.requests:
            self.requests[endpoint_type] = []
        self.requests[endpoint_type].append(time.time())


class DhanAPIClient:
    """Dhan API client for trading and market data operations."""
    
    def __init__(self, access_token: Optional[str] = None, client_id: Optional[str] = None):
        """Initialize Dhan API client.
        
        Args:
            access_token: Dhan access token (defaults to config)
            client_id: Dhan client ID (defaults to config)
        """
        self.access_token = access_token or config.api.token
        self.client_id = client_id
        self.base_url = config.api.base_url
        self.timeout = config.api.timeout
        
        if not self.access_token:
            raise AuthenticationError("Access token is required")
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=config.api.max_retries,
            backoff_factor=config.api.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Rate limiter
        self.rate_limiter = RateLimiter()
        
        # Get client ID from profile if not provided
        if not self.client_id:
            profile = self.get_user_profile()
            self.client_id = profile.dhan_client_id
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "access-token": self.access_token,
            "Content-Type": "application/json",
        }
        if self.client_id:
            headers["client-id"] = self.client_id
        return headers
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        endpoint_type: str = "non_trading",
    ) -> Dict[str, Any]:
        """Make API request with error handling and rate limiting.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            endpoint_type: Type of endpoint for rate limiting
            
        Returns:
            API response data
            
        Raises:
            RateLimitError: If rate limit exceeded
            APIError: If API request fails
        """
        # Check rate limits
        if not self.rate_limiter.can_make_request(endpoint_type):
            raise RateLimitError(f"Rate limit exceeded for {endpoint_type} endpoints")
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=self.timeout, params=data)
            else:
                response = self.session.request(
                    method, url, headers=headers, json=data, timeout=self.timeout
                )
            
            # Record request for rate limiting
            self.rate_limiter.record_request(endpoint_type)
            
            # Handle response
            if response.status_code == 401:
                raise AuthenticationError("Invalid or expired access token")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif not response.ok:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("errorMessage", f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                raise APIError(error_msg, response.status_code, error_data if 'error_data' in locals() else None)
            
            return response.json()
            
        except requests.exceptions.Timeout:
            raise APIError("Request timeout")
        except requests.exceptions.ConnectionError:
            raise APIError("Connection error")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def get_user_profile(self) -> UserProfile:
        """Get user profile information.
        
        Returns:
            User profile data
        """
        response = self._make_request("GET", "/v2/profile", endpoint_type="non_trading")
        
        return UserProfile(
            dhan_client_id=response["dhanClientId"],
            token_validity=response["tokenValidity"],
            active_segment=response["activeSegment"],
            ddpi=response["ddpi"],
            mtf=response["mtf"],
            data_plan=response["dataPlan"],
            data_validity=response["dataValidity"],
        )
    
    def get_option_chain(
        self,
        underlying_scrip: int,
        underlying_segment: str = "IDX_I",
        expiry: Optional[str] = None,
    ) -> OptionChain:
        """Get option chain data.
        
        Args:
            underlying_scrip: Security ID of underlying instrument
            underlying_segment: Exchange segment of underlying
            expiry: Expiry date (YYYY-MM-DD format)
            
        Returns:
            Option chain data
        """
        data = {
            "UnderlyingScrip": underlying_scrip,
            "UnderlyingSeg": underlying_segment,
        }
        if expiry:
            data["Expiry"] = expiry
        
        response = self._make_request("POST", "/v2/optionchain", data, endpoint_type="data")
        
        # Parse option chain data
        strikes = {}
        for strike_price, strike_data in response["data"]["oc"].items():
            strike = OptionChainStrike(strike=float(strike_price))
            
            # Parse call option data
            if "ce" in strike_data:
                ce_data = strike_data["ce"]
                strike.ce = OptionData(
                    greeks=Greeks(
                        delta=ce_data["greeks"]["delta"],
                        gamma=ce_data["greeks"]["gamma"],
                        theta=ce_data["greeks"]["theta"],
                        vega=ce_data["greeks"]["vega"],
                    ),
                    implied_volatility=ce_data["implied_volatility"],
                    last_price=ce_data["last_price"],
                    oi=ce_data["oi"],
                    previous_close_price=ce_data["previous_close_price"],
                    previous_oi=ce_data["previous_oi"],
                    previous_volume=ce_data["previous_volume"],
                    top_ask_price=ce_data["top_ask_price"],
                    top_ask_quantity=ce_data["top_ask_quantity"],
                    top_bid_price=ce_data["top_bid_price"],
                    top_bid_quantity=ce_data["top_bid_quantity"],
                    volume=ce_data["volume"],
                )
            
            # Parse put option data
            if "pe" in strike_data:
                pe_data = strike_data["pe"]
                strike.pe = OptionData(
                    greeks=Greeks(
                        delta=pe_data["greeks"]["delta"],
                        gamma=pe_data["greeks"]["gamma"],
                        theta=pe_data["greeks"]["theta"],
                        vega=pe_data["greeks"]["vega"],
                    ),
                    implied_volatility=pe_data["implied_volatility"],
                    last_price=pe_data["last_price"],
                    oi=pe_data["oi"],
                    previous_close_price=pe_data["previous_close_price"],
                    previous_oi=pe_data["previous_oi"],
                    previous_volume=pe_data["previous_volume"],
                    top_ask_price=pe_data["top_ask_price"],
                    top_ask_quantity=pe_data["top_ask_quantity"],
                    top_bid_price=pe_data["top_bid_price"],
                    top_bid_quantity=pe_data["top_bid_quantity"],
                    volume=pe_data["volume"],
                )
            
            strikes[strike_price] = strike
        
        return OptionChain(
            underlying_price=response["data"]["last_price"],
            strikes=strikes,
            expiry=expiry or "",
            underlying_scrip=underlying_scrip,
            underlying_segment=underlying_segment,
        )
    
    def get_option_expiry_list(
        self, underlying_scrip: int, underlying_segment: str = "IDX_I"
    ) -> List[str]:
        """Get list of option expiry dates.
        
        Args:
            underlying_scrip: Security ID of underlying instrument
            underlying_segment: Exchange segment of underlying
            
        Returns:
            List of expiry dates in YYYY-MM-DD format
        """
        data = {
            "UnderlyingScrip": underlying_scrip,
            "UnderlyingSeg": underlying_segment,
        }
        
        response = self._make_request("POST", "/v2/optionchain/expirylist", data, endpoint_type="data")
        return response["data"]

    def get_market_quote(self, security_id: str, exchange_segment: str) -> MarketQuote:
        """Get market quote for an instrument.

        Args:
            security_id: Security ID of the instrument
            exchange_segment: Exchange segment

        Returns:
            Market quote data
        """
        data = {
            "NSE_EQ": [security_id] if exchange_segment == "NSE_EQ" else [],
            "NSE_FNO": [security_id] if exchange_segment == "NSE_FNO" else [],
            "BSE_EQ": [security_id] if exchange_segment == "BSE_EQ" else [],
            "BSE_FNO": [security_id] if exchange_segment == "BSE_FNO" else [],
            "MCX_COMM": [security_id] if exchange_segment == "MCX_COMM" else [],
            "NSE_CURR": [security_id] if exchange_segment == "NSE_CURR" else [],
            "BSE_CURR": [security_id] if exchange_segment == "BSE_CURR" else [],
        }

        response = self._make_request("POST", "/v2/marketfeed/quote", data, endpoint_type="quote")

        # Parse response (assuming single instrument)
        quote_data = response["data"][exchange_segment][security_id]

        return MarketQuote(
            security_id=security_id,
            exchange_segment=exchange_segment,
            last_price=quote_data["LTP"],
            open_price=quote_data["open"],
            high_price=quote_data["high"],
            low_price=quote_data["low"],
            close_price=quote_data.get("close", 0.0),
            prev_close_price=quote_data["prev_close"],
            change=quote_data["change"],
            change_percent=quote_data["change_percent"],
            volume=quote_data["volume"],
            value=quote_data["value"],
            oi=quote_data.get("OI"),
        )

    def place_order(
        self,
        security_id: str,
        exchange_segment: ExchangeSegment,
        transaction_type: TransactionType,
        quantity: int,
        order_type: OrderType,
        product_type: ProductType,
        price: float = 0.0,
        trigger_price: float = 0.0,
        disclosed_quantity: int = 0,
        validity: str = "DAY",
        amo_time: Optional[str] = None,
        bo_profit_value: Optional[float] = None,
        bo_stop_loss_value: Optional[float] = None,
    ) -> str:
        """Place a new order.

        Args:
            security_id: Security ID of the instrument
            exchange_segment: Exchange segment
            transaction_type: BUY or SELL
            quantity: Order quantity
            order_type: Order type (LIMIT, MARKET, etc.)
            product_type: Product type (CNC, INTRADAY, etc.)
            price: Order price (for limit orders)
            trigger_price: Trigger price (for stop loss orders)
            disclosed_quantity: Disclosed quantity
            validity: Order validity (DAY, IOC, etc.)
            amo_time: AMO time
            bo_profit_value: Bracket order profit value
            bo_stop_loss_value: Bracket order stop loss value

        Returns:
            Order ID
        """
        data = {
            "dhanClientId": self.client_id,
            "transactionType": transaction_type.value,
            "exchangeSegment": exchange_segment.value,
            "productType": product_type.value,
            "orderType": order_type.value,
            "validity": validity,
            "securityId": security_id,
            "quantity": quantity,
            "disclosedQuantity": disclosed_quantity,
            "price": price,
            "triggerPrice": trigger_price,
        }

        if amo_time:
            data["amoTime"] = amo_time
        if bo_profit_value:
            data["boProfitValue"] = bo_profit_value
        if bo_stop_loss_value:
            data["boStopLossValue"] = bo_stop_loss_value

        response = self._make_request("POST", "/v2/orders", data, endpoint_type="order")
        return response["data"]["orderId"]

    def get_orders(self) -> List[Order]:
        """Get all orders.

        Returns:
            List of orders
        """
        response = self._make_request("GET", "/v2/orders", endpoint_type="non_trading")

        # Log the actual response structure for debugging
        logger.debug(f"Orders API response: {response}")

        # Dhan API returns direct array, not wrapped in "data"
        orders_data = response if isinstance(response, list) else response.get("data", [])
        if not isinstance(orders_data, list):
            logger.warning(f"Expected list but got {type(orders_data)}: {orders_data}")
            return []

        orders = []
        for order_data in orders_data:
            try:
                orders.append(self._parse_order(order_data))
            except Exception as e:
                logger.error(f"Error parsing order data {order_data}: {e}")
                continue

        return orders

    def get_positions(self) -> List[Position]:
        """Get all positions.

        Returns:
            List of positions
        """
        response = self._make_request("GET", "/v2/positions", endpoint_type="non_trading")

        # Log the actual response structure for debugging
        logger.debug(f"Positions API response: {response}")

        # Dhan API returns direct array, not wrapped in "data"
        positions_data = response if isinstance(response, list) else response.get("data", [])
        if not isinstance(positions_data, list):
            logger.warning(f"Expected list but got {type(positions_data)}: {positions_data}")
            return []

        positions = []
        for pos_data in positions_data:
            try:
                positions.append(self._parse_position(pos_data))
            except Exception as e:
                logger.error(f"Error parsing position data {pos_data}: {e}")
                continue

        return positions

    def get_holdings(self) -> List[Holding]:
        """Get all holdings.

        Returns:
            List of holdings
        """
        response = self._make_request("GET", "/v2/holdings", endpoint_type="non_trading")

        # Log the actual response structure for debugging
        logger.debug(f"Holdings API response: {response}")

        # Dhan API returns direct array, not wrapped in "data"
        holdings_data = response if isinstance(response, list) else response.get("data", [])
        if not isinstance(holdings_data, list):
            logger.warning(f"Expected list but got {type(holdings_data)}: {holdings_data}")
            return []

        holdings = []
        for holding_data in holdings_data:
            try:
                holdings.append(self._parse_holding(holding_data))
            except Exception as e:
                logger.error(f"Error parsing holding data {holding_data}: {e}")
                continue

        return holdings

    def get_fund_limit(self) -> FundLimit:
        """Get fund limit information.

        Returns:
            Fund limit data
        """
        response = self._make_request("GET", "/v2/fundlimit", endpoint_type="non_trading")

        # Log the actual response structure for debugging
        logger.debug(f"Fund limit API response: {response}")

        # Dhan API returns direct object, not wrapped in "data"
        data = response if isinstance(response, dict) and "dhanClientId" in response else response.get("data", {})

        return FundLimit(
            dhan_client_id=data.get("dhanClientId", ""),
            available_balance=data.get("availabelBalance", 0.0),  # Note: API has typo "availabelBalance"
            sod_limit=data.get("sodLimit", 0.0),
            collateral_amount=data.get("collateralAmount", 0.0),
            intraday_payin=data.get("receiveableAmount", 0.0),  # Map to closest field
            adhoc_margin=data.get("utilizedAmount", 0.0),  # Map to closest field
            notional_cash=data.get("withdrawableBalance", 0.0),  # Map to closest field
            margin_used=data.get("utilizedAmount", 0.0),
            exposure_margin=data.get("blockedPayoutAmount", 0.0),  # Map to closest field
        )

    def _parse_order(self, order_data: Dict[str, Any]) -> Order:
        """Parse order data from API response."""
        return Order(
            order_id=order_data["orderId"],
            dhan_client_id=order_data["dhanClientId"],
            order_status=OrderStatus(order_data["orderStatus"]),
            transaction_type=TransactionType(order_data["transactionType"]),
            exchange_segment=ExchangeSegment(order_data["exchangeSegment"]),
            product_type=ProductType(order_data["productType"]),
            order_type=OrderType(order_data["orderType"]),
            security_id=order_data["securityId"],
            quantity=order_data["quantity"],
            disclosed_quantity=order_data["disclosedQuantity"],
            price=order_data["price"],
            trigger_price=order_data["triggerPrice"],
            validity=order_data["validity"],
            traded_quantity=order_data.get("filledQty", 0),  # API uses "filledQty"
            remaining_quantity=order_data["remainingQuantity"],
            created_at=datetime.fromisoformat(order_data["createTime"]),
            updated_at=datetime.fromisoformat(order_data["updateTime"]),
            bo_profit_value=order_data.get("boProfitValue"),
            bo_stop_loss_value=order_data.get("boStopLossValue"),
        )

    def _parse_position(self, pos_data: Dict[str, Any]) -> Position:
        """Parse position data from API response."""
        return Position(
            dhan_client_id=pos_data["dhanClientId"],
            exchange_segment=ExchangeSegment(pos_data["exchangeSegment"]),
            product_type=ProductType(pos_data["productType"]),
            security_id=pos_data["securityId"],
            net_quantity=pos_data["netQty"],
            buy_avg=pos_data["buyAvg"],
            sell_avg=pos_data["sellAvg"],
            net_avg=pos_data["netAvg"],
            day_buy_quantity=pos_data["dayBuyQty"],
            day_sell_quantity=pos_data["daySellQty"],
            day_buy_value=pos_data["dayBuyValue"],
            day_sell_value=pos_data["daySellValue"],
            pnl=pos_data["pnl"],
            realized_pnl=pos_data["realizedPnl"],
            unrealized_pnl=pos_data["unrealizedPnl"],
        )

    def _parse_holding(self, holding_data: Dict[str, Any]) -> Holding:
        """Parse holding data from API response."""
        # Map API fields to our model fields
        # API uses "exchange" instead of "exchangeSegment"
        # API doesn't have "productType", "lastPrice", "pnl", "pnlPercent"
        return Holding(
            isin=holding_data["isin"],
            security_id=holding_data["securityId"],
            exchange_segment=ExchangeSegment("NSE_EQ"),  # Default since API uses "exchange" field
            product_type=ProductType("CNC"),  # Default since API doesn't provide this
            quantity=holding_data.get("totalQty", 0),  # API uses "totalQty"
            avg_cost_price=holding_data["avgCostPrice"],
            last_price=0.0,  # API doesn't provide this in holdings
            pnl=0.0,  # API doesn't provide this in holdings
            pnl_percent=0.0,  # API doesn't provide this in holdings
        )
