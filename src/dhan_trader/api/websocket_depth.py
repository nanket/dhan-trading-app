"""Dhan WebSocket client for Level 3 Market Depth (20 levels)."""

import json
import struct
import threading
import time
import logging
from typing import Dict, List, Callable, Optional, Any
from enum import Enum
from datetime import datetime
import websocket

from ..config import config
from ..exceptions import WebSocketError, MarketDataError
from .models import (
    ExchangeSegment, 
    MarketDepthLevel, 
    MarketDepth20Level, 
    MarketDepth20Response
)

logger = logging.getLogger(__name__)


class DepthFeedResponseCode(Enum):
    """Feed response codes for 20-level market depth."""
    BID_DATA = 41  # Bid data (Buy)
    ASK_DATA = 51  # Ask data (Sell)
    DISCONNECT = 50


class DhanLevel3WebSocketClient:
    """Dhan WebSocket client for Level 3 Market Depth (20 levels)."""
    
    def __init__(
        self,
        access_token: str,
        client_id: str,
        on_depth_update: Optional[Callable[[MarketDepth20Response], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        """Initialize Level 3 WebSocket client.
        
        Args:
            access_token: Dhan access token
            client_id: Dhan client ID
            on_depth_update: Callback for 20-level market depth updates
            on_error: Callback for errors
            on_connect: Callback for connection events
            on_disconnect: Callback for disconnection events
        """
        self.access_token = access_token
        self.client_id = client_id
        self.base_url = "wss://depth-api-feed.dhan.co/twentydepth"
        
        # Callbacks
        self.on_depth_update = on_depth_update
        self.on_error = on_error
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        # Connection state
        self.ws = None
        self.is_connected = False
        self.ws_thread = None
        self.heartbeat_thread = None
        
        # Subscription management
        self.subscriptions = {}  # {security_id: subscription_info}
        self.lock = threading.Lock()
        
        # Reconnection settings
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5
        self.reconnect_attempts = 0
        
        # Depth data buffers for combining bid/ask packets
        self.depth_buffers = {}  # {security_id: {'bid': data, 'ask': data, 'timestamp': time}}
        self.buffer_timeout = 1.0  # seconds

        # Performance optimization
        self.message_queue = []
        self.processing_thread = None
        self.processing_lock = threading.Lock()
        self.stop_processing = False

        # Error handling
        self.error_count = 0
        self.max_errors = 10
        self.error_reset_time = 300  # 5 minutes
        self.last_error_time = 0

        # Rate limiting
        self.message_count = 0
        self.last_rate_check = time.time()
        self.max_messages_per_second = 1000

        logger.info("Level 3 WebSocket client initialized")
    
    def connect(self) -> None:
        """Establish WebSocket connection."""
        try:
            url = f"{self.base_url}?token={self.access_token}&clientId={self.client_id}&authType=2"
            
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
                raise WebSocketError("Failed to establish Level 3 WebSocket connection")
            
            logger.info("Level 3 WebSocket connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect Level 3 WebSocket: {e}")
            raise WebSocketError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Disconnect WebSocket."""
        try:
            # Stop processing thread
            self.stop_processing = True
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2)

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

            # Clear message queue
            with self.processing_lock:
                self.message_queue.clear()

            logger.info("Level 3 WebSocket disconnected")

        except Exception as e:
            logger.error(f"Error during Level 3 disconnect: {e}")
    
    def subscribe_instruments(self, instruments: List[Dict[str, str]]) -> None:
        """Subscribe to 20-level market depth for instruments.
        
        Args:
            instruments: List of instruments with exchange_segment and security_id
                        Maximum 50 instruments per connection
        """
        if not self.is_connected:
            raise WebSocketError("WebSocket not connected")
        
        if len(instruments) > 50:
            raise ValueError("Maximum 50 instruments allowed per connection")
        
        # Only NSE_EQ and NSE_FNO are supported for 20-level depth
        supported_segments = ["NSE_EQ", "NSE_FNO"]
        for inst in instruments:
            if inst["exchange_segment"] not in supported_segments:
                raise ValueError(f"Exchange segment {inst['exchange_segment']} not supported for 20-level depth")
        
        subscription_msg = {
            "RequestCode": 23,  # 20 Level Market Depth request code
            "InstrumentCount": len(instruments),
            "InstrumentList": [
                {
                    "ExchangeSegment": inst["exchange_segment"],
                    "SecurityId": inst["security_id"],
                }
                for inst in instruments
            ],
        }
        
        try:
            self.ws.send(json.dumps(subscription_msg))
            
            # Track subscriptions
            with self.lock:
                for inst in instruments:
                    key = f"{inst['exchange_segment']}:{inst['security_id']}"
                    self.subscriptions[key] = {
                        "exchange_segment": inst["exchange_segment"],
                        "security_id": inst["security_id"],
                    }
            
            logger.info(f"Subscribed to 20-level depth for {len(instruments)} instruments")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to 20-level depth: {e}")
            raise WebSocketError(f"Subscription failed: {e}")
    
    def _on_open(self, ws) -> None:
        """Handle WebSocket open event."""
        self.is_connected = True
        self.reconnect_attempts = 0
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

        # Start message processing thread
        self.stop_processing = False
        self.processing_thread = threading.Thread(target=self._process_message_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()

        # Reset error count on successful connection
        self.error_count = 0

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
            logger.info(f"Attempting Level 3 reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
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
                    self.subscribe_instruments(instruments)
            except Exception as e:
                logger.error(f"Level 3 reconnection failed: {e}")
    
    def _on_error(self, ws, error) -> None:
        """Handle WebSocket error."""
        logger.error(f"Level 3 WebSocket error: {error}")
        if self.on_error:
            self.on_error(WebSocketError(str(error)))
    
    def _on_message(self, ws, message) -> None:
        """Handle WebSocket message."""
        try:
            # Rate limiting check
            current_time = time.time()
            if current_time - self.last_rate_check >= 1.0:
                if self.message_count > self.max_messages_per_second:
                    logger.warning(f"Rate limit exceeded: {self.message_count} messages/second")
                self.message_count = 0
                self.last_rate_check = current_time

            self.message_count += 1

            # Add message to queue for processing
            with self.processing_lock:
                self.message_queue.append(message)

        except Exception as e:
            self._handle_error(f"Error handling message: {e}")

    def _process_message_queue(self) -> None:
        """Process messages from the queue in a separate thread."""
        while not self.stop_processing:
            try:
                messages_to_process = []

                # Get messages from queue
                with self.processing_lock:
                    if self.message_queue:
                        messages_to_process = self.message_queue.copy()
                        self.message_queue.clear()

                # Process messages
                for message in messages_to_process:
                    try:
                        self._parse_depth_message(message)
                    except Exception as e:
                        self._handle_error(f"Error parsing message: {e}")

                # Small delay to prevent excessive CPU usage
                time.sleep(0.001)  # 1ms

            except Exception as e:
                self._handle_error(f"Error in message processing thread: {e}")
                time.sleep(0.1)  # Longer delay on error

    def _handle_error(self, error_msg: str) -> None:
        """Handle errors with rate limiting and recovery."""
        current_time = time.time()

        # Reset error count if enough time has passed
        if current_time - self.last_error_time > self.error_reset_time:
            self.error_count = 0

        self.error_count += 1
        self.last_error_time = current_time

        logger.error(f"Level 3 WebSocket error ({self.error_count}/{self.max_errors}): {error_msg}")

        # If too many errors, disconnect and attempt reconnection
        if self.error_count >= self.max_errors:
            logger.error("Too many errors, forcing reconnection")
            self.disconnect()

        if self.on_error:
            self.on_error(WebSocketError(error_msg))
    
    def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep connection alive."""
        while self.is_connected:
            try:
                time.sleep(30)  # Send heartbeat every 30 seconds
                if self.is_connected and self.ws:
                    # WebSocket library handles ping/pong automatically
                    pass
            except Exception as e:
                logger.error(f"Level 3 heartbeat error: {e}")
                break

    def _parse_depth_message(self, message: bytes) -> None:
        """Parse 20-level market depth binary message."""
        if len(message) < 12:
            return

        # Parse response header (12 bytes)
        message_length = struct.unpack(">H", message[0:2])[0]
        feed_response_code = message[2]
        exchange_segment = message[3]
        security_id = struct.unpack(">I", message[4:8])[0]
        message_sequence = struct.unpack(">I", message[8:12])[0]

        # Convert to string representations
        security_id_str = str(security_id)
        exchange_segment_str = self._get_exchange_segment_name(exchange_segment)

        # Parse depth data based on response code
        if feed_response_code == DepthFeedResponseCode.BID_DATA.value:
            self._parse_bid_depth(message[12:], security_id_str, exchange_segment_str)
        elif feed_response_code == DepthFeedResponseCode.ASK_DATA.value:
            self._parse_ask_depth(message[12:], security_id_str, exchange_segment_str)
        elif feed_response_code == DepthFeedResponseCode.DISCONNECT.value:
            self._handle_disconnect_message(message[12:])

    def _parse_bid_depth(self, payload: bytes, security_id: str, exchange_segment: str) -> None:
        """Parse bid depth data (20 levels)."""
        if len(payload) < 320:  # 20 packets of 16 bytes each
            logger.warning(f"Insufficient bid depth data: {len(payload)} bytes")
            return

        levels = []
        for i in range(20):
            offset = i * 16
            price = struct.unpack(">d", payload[offset:offset + 8])[0]  # float64
            quantity = struct.unpack(">I", payload[offset + 8:offset + 12])[0]  # uint32
            orders = struct.unpack(">I", payload[offset + 12:offset + 16])[0]  # uint32

            levels.append(MarketDepthLevel(price=price, quantity=quantity, orders=orders))

        bid_depth = MarketDepth20Level(
            levels=levels,
            side="BID",
            security_id=security_id,
            exchange_segment=exchange_segment,
            timestamp=datetime.now()
        )

        # Store in buffer and try to combine with ask data
        self._store_depth_data(security_id, "bid", bid_depth)

    def _parse_ask_depth(self, payload: bytes, security_id: str, exchange_segment: str) -> None:
        """Parse ask depth data (20 levels)."""
        if len(payload) < 320:  # 20 packets of 16 bytes each
            logger.warning(f"Insufficient ask depth data: {len(payload)} bytes")
            return

        levels = []
        for i in range(20):
            offset = i * 16
            price = struct.unpack(">d", payload[offset:offset + 8])[0]  # float64
            quantity = struct.unpack(">I", payload[offset + 8:offset + 12])[0]  # uint32
            orders = struct.unpack(">I", payload[offset + 12:offset + 16])[0]  # uint32

            levels.append(MarketDepthLevel(price=price, quantity=quantity, orders=orders))

        ask_depth = MarketDepth20Level(
            levels=levels,
            side="ASK",
            security_id=security_id,
            exchange_segment=exchange_segment,
            timestamp=datetime.now()
        )

        # Store in buffer and try to combine with bid data
        self._store_depth_data(security_id, "ask", ask_depth)

    def _store_depth_data(self, security_id: str, side: str, depth_data: MarketDepth20Level) -> None:
        """Store depth data and combine bid/ask when both are available."""
        current_time = time.time()

        with self.lock:
            if security_id not in self.depth_buffers:
                self.depth_buffers[security_id] = {}

            self.depth_buffers[security_id][side] = depth_data
            self.depth_buffers[security_id]['timestamp'] = current_time

            # Check if we have both bid and ask data
            buffer = self.depth_buffers[security_id]
            if 'bid' in buffer and 'ask' in buffer:
                # Check if data is recent (within buffer timeout)
                if current_time - buffer['timestamp'] <= self.buffer_timeout:
                    # Create combined response
                    response = MarketDepth20Response(
                        security_id=security_id,
                        exchange_segment=depth_data.exchange_segment,
                        bid_depth=buffer['bid'],
                        ask_depth=buffer['ask'],
                        timestamp=datetime.now()
                    )

                    # Clear buffer
                    del self.depth_buffers[security_id]

                    # Send update
                    if self.on_depth_update:
                        self.on_depth_update(response)

    def _handle_disconnect_message(self, payload: bytes) -> None:
        """Handle disconnect message."""
        if len(payload) >= 2:
            disconnect_code = struct.unpack(">H", payload[0:2])[0]
            logger.warning(f"Level 3 WebSocket disconnected with code: {disconnect_code}")

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
