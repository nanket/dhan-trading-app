"""Dhan WebSocket client for real-time market data."""

import json
import struct
import threading
import time
import logging
from typing import Dict, List, Callable, Optional, Any
from enum import Enum
import websocket

from ..config import config
from ..exceptions import WebSocketError, MarketDataError
from .models import ExchangeSegment

logger = logging.getLogger(__name__)


class FeedMode(Enum):
    """Market data feed modes."""
    TICKER = 15  # LTP and LTT
    QUOTE = 17   # Complete quote data
    FULL = 19    # Full market depth


class FeedResponseCode(Enum):
    """Feed response codes."""
    TICKER = 2
    QUOTE = 4
    OI_DATA = 5
    PREV_CLOSE = 6
    FULL = 8
    DISCONNECT = 50


class MarketDataPacket:
    """Base class for market data packets."""
    
    def __init__(self, security_id: str, exchange_segment: str):
        self.security_id = security_id
        self.exchange_segment = exchange_segment
        self.timestamp = time.time()


class TickerPacket(MarketDataPacket):
    """Ticker data packet (LTP and LTT)."""
    
    def __init__(self, security_id: str, exchange_segment: str, ltp: float, ltt: int):
        super().__init__(security_id, exchange_segment)
        self.ltp = ltp
        self.ltt = ltt


class QuotePacket(MarketDataPacket):
    """Quote data packet."""
    
    def __init__(
        self,
        security_id: str,
        exchange_segment: str,
        ltp: float,
        ltq: int,
        ltt: int,
        atp: float,
        volume: int,
        total_sell_qty: int,
        total_buy_qty: int,
        open_price: float,
        close_price: float,
        high_price: float,
        low_price: float,
    ):
        super().__init__(security_id, exchange_segment)
        self.ltp = ltp
        self.ltq = ltq
        self.ltt = ltt
        self.atp = atp
        self.volume = volume
        self.total_sell_qty = total_sell_qty
        self.total_buy_qty = total_buy_qty
        self.open_price = open_price
        self.close_price = close_price
        self.high_price = high_price
        self.low_price = low_price


class FullPacket(QuotePacket):
    """Full market data packet with depth."""
    
    def __init__(self, *args, oi: int = 0, market_depth: List[Dict] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.oi = oi
        self.market_depth = market_depth or []


class DhanWebSocketClient:
    """Dhan WebSocket client for real-time market data."""
    
    def __init__(
        self,
        access_token: str,
        client_id: str,
        on_message: Optional[Callable[[MarketDataPacket], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        """Initialize WebSocket client.
        
        Args:
            access_token: Dhan access token
            client_id: Dhan client ID
            on_message: Callback for market data messages
            on_error: Callback for errors
            on_connect: Callback for connection events
            on_disconnect: Callback for disconnection events
        """
        self.access_token = access_token
        self.client_id = client_id
        self.base_url = config.market_data.get("websocket_url", "wss://api-feed.dhan.co")
        
        # Callbacks
        self.on_message = on_message
        self.on_error = on_error
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        # WebSocket connection
        self.ws = None
        self.is_connected = False
        self.subscriptions = {}  # {security_id: {exchange_segment, feed_mode}}
        
        # Threading
        self.lock = threading.Lock()
        self.heartbeat_thread = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.market_data.get("reconnect_attempts", 5)
        self.reconnect_delay = config.market_data.get("reconnect_delay", 5.0)
    
    def connect(self) -> None:
        """Establish WebSocket connection."""
        try:
            url = f"{self.base_url}?version=2&token={self.access_token}&clientId={self.client_id}&authType=2"
            
            self.ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not self.is_connected:
                raise WebSocketError("Failed to establish WebSocket connection")
            
            logger.info("WebSocket connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            raise WebSocketError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Disconnect WebSocket."""
        try:
            if self.ws:
                # Send disconnect message
                disconnect_msg = {"RequestCode": 12}
                self.ws.send(json.dumps(disconnect_msg))
                
                # Close connection
                self.ws.close()
                
            self.is_connected = False
            
            # Stop heartbeat thread
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=1)
            
            logger.info("WebSocket disconnected")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    def subscribe(
        self,
        instruments: List[Dict[str, str]],
        feed_mode: FeedMode = FeedMode.QUOTE,
    ) -> None:
        """Subscribe to market data for instruments.
        
        Args:
            instruments: List of instruments with exchange_segment and security_id
            feed_mode: Type of market data feed
        """
        if not self.is_connected:
            raise WebSocketError("WebSocket not connected")
        
        # Split into chunks of 100 instruments
        chunk_size = 100
        for i in range(0, len(instruments), chunk_size):
            chunk = instruments[i:i + chunk_size]
            
            subscription_msg = {
                "RequestCode": feed_mode.value,
                "InstrumentCount": len(chunk),
                "InstrumentList": [
                    {
                        "ExchangeSegment": inst["exchange_segment"],
                        "SecurityId": inst["security_id"],
                    }
                    for inst in chunk
                ],
            }
            
            try:
                self.ws.send(json.dumps(subscription_msg))
                
                # Track subscriptions
                with self.lock:
                    for inst in chunk:
                        key = f"{inst['exchange_segment']}:{inst['security_id']}"
                        self.subscriptions[key] = {
                            "exchange_segment": inst["exchange_segment"],
                            "security_id": inst["security_id"],
                            "feed_mode": feed_mode,
                        }
                
                logger.info(f"Subscribed to {len(chunk)} instruments")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to instruments: {e}")
                raise WebSocketError(f"Subscription failed: {e}")
    
    def unsubscribe(self, instruments: List[Dict[str, str]]) -> None:
        """Unsubscribe from market data.
        
        Args:
            instruments: List of instruments to unsubscribe
        """
        # Remove from tracking
        with self.lock:
            for inst in instruments:
                key = f"{inst['exchange_segment']}:{inst['security_id']}"
                self.subscriptions.pop(key, None)
        
        logger.info(f"Unsubscribed from {len(instruments)} instruments")
    
    def _on_open(self, ws) -> None:
        """Handle WebSocket open event."""
        self.is_connected = True
        self.reconnect_attempts = 0
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        if self.on_connect:
            self.on_connect()
    
    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """Handle WebSocket close event."""
        self.is_connected = False
        
        if self.on_disconnect:
            self.on_disconnect()
        
        # Attempt reconnection
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            time.sleep(self.reconnect_delay)
            try:
                self.connect()
                # Resubscribe to instruments
                if self.subscriptions:
                    instruments = [
                        {
                            "exchange_segment": sub["exchange_segment"],
                            "security_id": sub["security_id"],
                        }
                        for sub in self.subscriptions.values()
                    ]
                    self.subscribe(instruments)
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
    
    def _on_error(self, ws, error) -> None:
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")
        if self.on_error:
            self.on_error(WebSocketError(str(error)))
    
    def _on_message(self, ws, message) -> None:
        """Handle WebSocket message."""
        try:
            # Parse binary message
            packet = self._parse_binary_message(message)
            if packet and self.on_message:
                self.on_message(packet)
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
    
    def _parse_binary_message(self, message: bytes) -> Optional[MarketDataPacket]:
        """Parse binary market data message."""
        if len(message) < 8:
            return None
        
        # Parse header (8 bytes)
        response_code = message[0]
        message_length = struct.unpack(">H", message[1:3])[0]
        exchange_segment = message[3]
        security_id = struct.unpack(">I", message[4:8])[0]
        
        # Convert to string representations
        security_id_str = str(security_id)
        exchange_segment_str = self._get_exchange_segment_name(exchange_segment)
        
        # Parse payload based on response code
        if response_code == FeedResponseCode.TICKER.value:
            return self._parse_ticker_packet(message[8:], security_id_str, exchange_segment_str)
        elif response_code == FeedResponseCode.QUOTE.value:
            return self._parse_quote_packet(message[8:], security_id_str, exchange_segment_str)
        elif response_code == FeedResponseCode.FULL.value:
            return self._parse_full_packet(message[8:], security_id_str, exchange_segment_str)
        
        return None
    
    def _parse_ticker_packet(self, payload: bytes, security_id: str, exchange_segment: str) -> TickerPacket:
        """Parse ticker packet."""
        ltp = struct.unpack(">f", payload[0:4])[0]
        ltt = struct.unpack(">I", payload[4:8])[0]
        
        return TickerPacket(security_id, exchange_segment, ltp, ltt)
    
    def _parse_quote_packet(self, payload: bytes, security_id: str, exchange_segment: str) -> QuotePacket:
        """Parse quote packet."""
        ltp = struct.unpack(">f", payload[0:4])[0]
        ltq = struct.unpack(">H", payload[4:6])[0]
        ltt = struct.unpack(">I", payload[6:10])[0]
        atp = struct.unpack(">f", payload[10:14])[0]
        volume = struct.unpack(">I", payload[14:18])[0]
        total_sell_qty = struct.unpack(">I", payload[18:22])[0]
        total_buy_qty = struct.unpack(">I", payload[22:26])[0]
        open_price = struct.unpack(">f", payload[26:30])[0]
        close_price = struct.unpack(">f", payload[30:34])[0]
        high_price = struct.unpack(">f", payload[34:38])[0]
        low_price = struct.unpack(">f", payload[38:42])[0]
        
        return QuotePacket(
            security_id,
            exchange_segment,
            ltp,
            ltq,
            ltt,
            atp,
            volume,
            total_sell_qty,
            total_buy_qty,
            open_price,
            close_price,
            high_price,
            low_price,
        )
    
    def _parse_full_packet(self, payload: bytes, security_id: str, exchange_segment: str) -> FullPacket:
        """Parse full packet with market depth."""
        # Parse quote data first
        quote_data = self._parse_quote_packet(payload[:42], security_id, exchange_segment)
        
        # Parse OI data
        oi = struct.unpack(">I", payload[26:30])[0] if len(payload) > 30 else 0
        
        # Parse market depth (5 levels, 20 bytes each)
        market_depth = []
        depth_start = 54  # After quote data
        for i in range(5):
            if len(payload) >= depth_start + (i + 1) * 20:
                depth_offset = depth_start + i * 20
                bid_qty = struct.unpack(">I", payload[depth_offset:depth_offset + 4])[0]
                ask_qty = struct.unpack(">I", payload[depth_offset + 4:depth_offset + 8])[0]
                bid_orders = struct.unpack(">H", payload[depth_offset + 8:depth_offset + 10])[0]
                ask_orders = struct.unpack(">H", payload[depth_offset + 10:depth_offset + 12])[0]
                bid_price = struct.unpack(">f", payload[depth_offset + 12:depth_offset + 16])[0]
                ask_price = struct.unpack(">f", payload[depth_offset + 16:depth_offset + 20])[0]
                
                market_depth.append({
                    "bid_qty": bid_qty,
                    "ask_qty": ask_qty,
                    "bid_orders": bid_orders,
                    "ask_orders": ask_orders,
                    "bid_price": bid_price,
                    "ask_price": ask_price,
                })
        
        return FullPacket(
            security_id,
            exchange_segment,
            quote_data.ltp,
            quote_data.ltq,
            quote_data.ltt,
            quote_data.atp,
            quote_data.volume,
            quote_data.total_sell_qty,
            quote_data.total_buy_qty,
            quote_data.open_price,
            quote_data.close_price,
            quote_data.high_price,
            quote_data.low_price,
            oi=oi,
            market_depth=market_depth,
        )
    
    def _get_exchange_segment_name(self, segment_code: int) -> str:
        """Convert exchange segment code to name."""
        segment_map = {
            1: "NSE_EQ",
            2: "NSE_FNO",
            3: "NSE_CURR",
            4: "BSE_EQ",
            5: "BSE_FNO",
            6: "BSE_CURR",
            7: "MCX_COMM",
            8: "IDX_I",
        }
        return segment_map.get(segment_code, "UNKNOWN")
    
    def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep connection alive."""
        while self.is_connected:
            try:
                time.sleep(30)  # Send heartbeat every 30 seconds
                if self.is_connected and self.ws:
                    # WebSocket library handles ping/pong automatically
                    pass
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
