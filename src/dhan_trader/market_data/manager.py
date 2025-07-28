"""Market data manager for coordinating real-time and historical data."""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime, timedelta

from ..api.client import DhanAPIClient
from ..api.websocket import DhanWebSocketClient, MarketDataPacket, FeedMode
from ..api.models import MarketQuote, ExchangeSegment
from ..config import config
from ..exceptions import MarketDataError

logger = logging.getLogger(__name__)


class MarketDataManager:
    """Manages real-time and historical market data."""
    
    def __init__(self, api_client: DhanAPIClient):
        """Initialize market data manager.
        
        Args:
            api_client: Dhan API client instance
        """
        self.api_client = api_client
        self.ws_client = None
        
        # Data storage
        self.live_data = {}  # {security_id: latest_packet}
        self.subscribers = defaultdict(list)  # {security_id: [callbacks]}
        self.option_chains = {}  # {underlying_scrip: option_chain_data}
        
        # Threading
        self.lock = threading.Lock()
        
        # Configuration
        self.max_subscriptions = config.market_data.get("subscription_limit", 1000)
        self.supported_exchanges = config.market_data.get("exchanges", ["NSE", "BSE"])
        
        logger.info("Market data manager initialized")
    
    def start_live_feed(self) -> None:
        """Start real-time market data feed."""
        try:
            if self.ws_client and self.ws_client.is_connected:
                logger.warning("Live feed already started")
                return
            
            self.ws_client = DhanWebSocketClient(
                access_token=self.api_client.access_token,
                client_id=self.api_client.client_id,
                on_message=self._on_market_data,
                on_error=self._on_websocket_error,
                on_connect=self._on_websocket_connect,
                on_disconnect=self._on_websocket_disconnect,
            )
            
            self.ws_client.connect()
            logger.info("Live market data feed started")
            
        except Exception as e:
            logger.error(f"Failed to start live feed: {e}")
            raise MarketDataError(f"Failed to start live feed: {e}")
    
    def stop_live_feed(self) -> None:
        """Stop real-time market data feed."""
        try:
            if self.ws_client:
                self.ws_client.disconnect()
                self.ws_client = None
            
            logger.info("Live market data feed stopped")
            
        except Exception as e:
            logger.error(f"Error stopping live feed: {e}")
    
    def subscribe_instrument(
        self,
        security_id: str,
        exchange_segment: str,
        callback: Optional[Callable[[MarketDataPacket], None]] = None,
        feed_mode: FeedMode = FeedMode.QUOTE,
    ) -> None:
        """Subscribe to real-time data for an instrument.
        
        Args:
            security_id: Security ID of the instrument
            exchange_segment: Exchange segment
            callback: Optional callback for data updates
            feed_mode: Type of market data feed
        """
        if not self.ws_client or not self.ws_client.is_connected:
            raise MarketDataError("Live feed not started")
        
        # Check subscription limits
        with self.lock:
            if len(self.subscribers) >= self.max_subscriptions:
                raise MarketDataError(f"Maximum subscriptions ({self.max_subscriptions}) reached")
        
        try:
            # Subscribe via WebSocket
            instruments = [{"security_id": security_id, "exchange_segment": exchange_segment}]
            self.ws_client.subscribe(instruments, feed_mode)
            
            # Add callback if provided
            if callback:
                with self.lock:
                    self.subscribers[security_id].append(callback)
            
            logger.info(f"Subscribed to {security_id} on {exchange_segment}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {security_id}: {e}")
            raise MarketDataError(f"Subscription failed: {e}")
    
    def unsubscribe_instrument(self, security_id: str, exchange_segment: str) -> None:
        """Unsubscribe from real-time data for an instrument.
        
        Args:
            security_id: Security ID of the instrument
            exchange_segment: Exchange segment
        """
        try:
            if self.ws_client:
                instruments = [{"security_id": security_id, "exchange_segment": exchange_segment}]
                self.ws_client.unsubscribe(instruments)
            
            # Remove from local storage
            with self.lock:
                self.live_data.pop(security_id, None)
                self.subscribers.pop(security_id, None)
            
            logger.info(f"Unsubscribed from {security_id}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {security_id}: {e}")
    
    def get_live_quote(self, security_id: str) -> Optional[MarketDataPacket]:
        """Get latest live quote for an instrument.
        
        Args:
            security_id: Security ID of the instrument
            
        Returns:
            Latest market data packet or None
        """
        with self.lock:
            return self.live_data.get(security_id)
    
    def get_market_quote(self, security_id: str, exchange_segment: str) -> MarketQuote:
        """Get market quote via REST API.
        
        Args:
            security_id: Security ID of the instrument
            exchange_segment: Exchange segment
            
        Returns:
            Market quote data
        """
        try:
            return self.api_client.get_market_quote(security_id, exchange_segment)
        except Exception as e:
            logger.error(f"Failed to get market quote for {security_id}: {e}")
            raise MarketDataError(f"Failed to get market quote: {e}")
    
    def get_option_chain(
        self,
        underlying_scrip: int,
        underlying_segment: str = "IDX_I",
        expiry: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get option chain data.
        
        Args:
            underlying_scrip: Security ID of underlying instrument
            underlying_segment: Exchange segment of underlying
            expiry: Expiry date (YYYY-MM-DD format)
            use_cache: Whether to use cached data
            
        Returns:
            Option chain data
        """
        cache_key = f"{underlying_scrip}:{underlying_segment}:{expiry}"
        
        # Check cache first
        if use_cache and cache_key in self.option_chains:
            cached_data = self.option_chains[cache_key]
            # Check if cache is still valid (less than 3 seconds old)
            if datetime.now() - cached_data["timestamp"] < timedelta(seconds=3):
                return cached_data["data"]
        
        try:
            option_chain = self.api_client.get_option_chain(
                underlying_scrip, underlying_segment, expiry
            )
            
            # Cache the data
            self.option_chains[cache_key] = {
                "data": option_chain,
                "timestamp": datetime.now(),
            }
            
            return option_chain
            
        except Exception as e:
            logger.error(f"Failed to get option chain for {underlying_scrip}: {e}")
            raise MarketDataError(f"Failed to get option chain: {e}")
    
    def get_option_expiry_list(
        self, underlying_scrip: int, underlying_segment: str = "IDX_I"
    ) -> List[str]:
        """Get list of option expiry dates.
        
        Args:
            underlying_scrip: Security ID of underlying instrument
            underlying_segment: Exchange segment of underlying
            
        Returns:
            List of expiry dates
        """
        try:
            return self.api_client.get_option_expiry_list(underlying_scrip, underlying_segment)
        except Exception as e:
            logger.error(f"Failed to get expiry list for {underlying_scrip}: {e}")
            raise MarketDataError(f"Failed to get expiry list: {e}")
    
    def subscribe_option_chain(
        self,
        underlying_scrip: int,
        underlying_segment: str = "IDX_I",
        expiry: Optional[str] = None,
        strike_range: Optional[int] = None,
        callback: Optional[Callable[[str, MarketDataPacket], None]] = None,
    ) -> None:
        """Subscribe to real-time data for an entire option chain.
        
        Args:
            underlying_scrip: Security ID of underlying instrument
            underlying_segment: Exchange segment of underlying
            expiry: Expiry date (YYYY-MM-DD format)
            strike_range: Number of strikes around ATM to subscribe
            callback: Optional callback for data updates
        """
        try:
            # Get option chain to find all instruments
            option_chain = self.get_option_chain(underlying_scrip, underlying_segment, expiry)
            
            # Determine strikes to subscribe to
            strikes_to_subscribe = []
            if strike_range:
                # Find ATM strike
                underlying_price = option_chain.underlying_price
                all_strikes = sorted([float(strike) for strike in option_chain.strikes.keys()])
                
                # Find closest strike to underlying price
                atm_strike = min(all_strikes, key=lambda x: abs(x - underlying_price))
                atm_index = all_strikes.index(atm_strike)
                
                # Select strikes around ATM
                start_idx = max(0, atm_index - strike_range // 2)
                end_idx = min(len(all_strikes), atm_index + strike_range // 2 + 1)
                strikes_to_subscribe = all_strikes[start_idx:end_idx]
            else:
                strikes_to_subscribe = [float(strike) for strike in option_chain.strikes.keys()]
            
            # Subscribe to each option contract
            instruments = []
            for strike in strikes_to_subscribe:
                strike_key = str(strike)
                if strike_key in option_chain.strikes:
                    strike_data = option_chain.strikes[strike_key]
                    
                    # Add call option if exists
                    if strike_data.ce:
                        # Note: We need to get the actual security IDs for options
                        # This would require additional API calls or instrument master data
                        pass
                    
                    # Add put option if exists
                    if strike_data.pe:
                        # Note: We need to get the actual security IDs for options
                        # This would require additional API calls or instrument master data
                        pass
            
            # TODO: Implement actual subscription once we have option security IDs
            logger.info(f"Option chain subscription prepared for {len(strikes_to_subscribe)} strikes")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to option chain: {e}")
            raise MarketDataError(f"Option chain subscription failed: {e}")
    
    def _on_market_data(self, packet: MarketDataPacket) -> None:
        """Handle incoming market data."""
        try:
            # Store latest data
            with self.lock:
                self.live_data[packet.security_id] = packet
                
                # Notify subscribers
                for callback in self.subscribers.get(packet.security_id, []):
                    try:
                        callback(packet)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")
            
        except Exception as e:
            logger.error(f"Error handling market data: {e}")
    
    def _on_websocket_error(self, error: Exception) -> None:
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_websocket_connect(self) -> None:
        """Handle WebSocket connection."""
        logger.info("WebSocket connected")
    
    def _on_websocket_disconnect(self) -> None:
        """Handle WebSocket disconnection."""
        logger.warning("WebSocket disconnected")
    
    def get_subscribed_instruments(self) -> List[str]:
        """Get list of currently subscribed instruments.
        
        Returns:
            List of security IDs
        """
        with self.lock:
            return list(self.subscribers.keys())
    
    def get_subscription_count(self) -> int:
        """Get current subscription count.
        
        Returns:
            Number of subscribed instruments
        """
        with self.lock:
            return len(self.subscribers)
