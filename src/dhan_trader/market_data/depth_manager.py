"""Market depth manager for 20-level market depth data."""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime, timedelta

from ..api.client import DhanAPIClient
from ..api.websocket_depth import DhanLevel3WebSocketClient
from ..api.models import MarketDepth20Response, MarketDepthAnalysis, DemandSupplyZones
from ..config import config
from ..exceptions import MarketDataError

logger = logging.getLogger(__name__)


class MarketDepthManager:
    """Manages 20-level market depth data and subscriptions."""
    
    def __init__(self, api_client: DhanAPIClient):
        """Initialize market depth manager.

        Args:
            api_client: Dhan API client instance
        """
        self.api_client = api_client
        self.ws_client = None
        
        # Data storage
        self.depth_data = {}  # {security_id: latest_depth_response}
        self.subscribers = defaultdict(list)  # {security_id: [callbacks]}
        self.analysis_cache = {}  # {security_id: analysis_data}
        
        # Threading
        self.lock = threading.Lock()
        
        # Configuration
        self.max_subscriptions = 50  # Level 3 limit
        self.cache_duration = timedelta(seconds=30)
        
        logger.info("Market depth manager initialized")
    
    def connect(self) -> None:
        """Establish Level 3 WebSocket connection."""
        try:
            # Get authentication details
            profile = self.api_client.get_user_profile()
            access_token = self.api_client.access_token
            client_id = profile.dhan_client_id
            
            # Create Level 3 WebSocket client
            self.ws_client = DhanLevel3WebSocketClient(
                access_token=access_token,
                client_id=client_id,
                on_depth_update=self._on_depth_update,
                on_error=self._on_error,
                on_connect=self._on_connect,
                on_disconnect=self._on_disconnect,
            )
            
            # Connect
            self.ws_client.connect()
            
            logger.info("Market depth manager connected")
            
        except Exception as e:
            logger.error(f"Failed to connect market depth manager: {e}")
            raise MarketDataError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from Level 3 WebSocket."""
        try:
            if self.ws_client:
                self.ws_client.disconnect()
                self.ws_client = None
            
            # Clear data
            with self.lock:
                self.depth_data.clear()
                self.subscribers.clear()
                self.analysis_cache.clear()
            
            logger.info("Market depth manager disconnected")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    def subscribe_depth(
        self, 
        security_id: str, 
        exchange_segment: str, 
        callback: Optional[Callable[[MarketDepth20Response], None]] = None
    ) -> None:
        """Subscribe to 20-level market depth for a security.
        
        Args:
            security_id: Security ID to subscribe to
            exchange_segment: Exchange segment (NSE_EQ or NSE_FNO only)
            callback: Optional callback for depth updates
        """
        if not self.ws_client or not self.ws_client.is_connected:
            raise MarketDataError("WebSocket not connected")
        
        # Validate exchange segment
        if exchange_segment not in ["NSE_EQ", "NSE_FNO"]:
            raise ValueError(f"Exchange segment {exchange_segment} not supported for 20-level depth")
        
        # Check subscription limit
        with self.lock:
            if len(self.subscribers) >= self.max_subscriptions:
                raise MarketDataError(f"Maximum {self.max_subscriptions} subscriptions reached")
            
            # Add callback if provided
            if callback:
                self.subscribers[security_id].append(callback)
            
            # Check if already subscribed
            if security_id in self.depth_data:
                logger.info(f"Already subscribed to depth for {security_id}")
                return
        
        try:
            # Subscribe via WebSocket
            instruments = [{
                "security_id": security_id,
                "exchange_segment": exchange_segment
            }]
            
            self.ws_client.subscribe_instruments(instruments)
            
            logger.info(f"Subscribed to 20-level depth for {security_id}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to depth for {security_id}: {e}")
            raise MarketDataError(f"Subscription failed: {e}")
    
    def unsubscribe_depth(self, security_id: str) -> None:
        """Unsubscribe from 20-level market depth.
        
        Args:
            security_id: Security ID to unsubscribe from
        """
        with self.lock:
            # Remove from data storage
            self.depth_data.pop(security_id, None)
            self.subscribers.pop(security_id, None)
            self.analysis_cache.pop(security_id, None)
        
        logger.info(f"Unsubscribed from depth for {security_id}")
    
    def get_depth_data(self, security_id: str) -> Optional[MarketDepth20Response]:
        """Get latest 20-level depth data for a security.
        
        Args:
            security_id: Security ID
            
        Returns:
            Latest depth data or None if not available
        """
        with self.lock:
            return self.depth_data.get(security_id)
    
    def get_depth_analysis(self, security_id: str, force_refresh: bool = False) -> Optional[MarketDepthAnalysis]:
        """Get market depth analysis for a security.
        
        Args:
            security_id: Security ID
            force_refresh: Force recalculation of analysis
            
        Returns:
            Market depth analysis or None if not available
        """
        with self.lock:
            # Check cache first
            if not force_refresh and security_id in self.analysis_cache:
                cached_analysis, timestamp = self.analysis_cache[security_id]
                if datetime.now() - timestamp < self.cache_duration:
                    return cached_analysis
            
            # Get depth data
            depth_data = self.depth_data.get(security_id)
            if not depth_data:
                return None
            
            # Calculate analysis
            analysis = self._calculate_depth_analysis(depth_data)
            
            # Cache result
            self.analysis_cache[security_id] = (analysis, datetime.now())
            
            return analysis
    
    def get_all_subscribed_securities(self) -> List[str]:
        """Get list of all subscribed security IDs.
        
        Returns:
            List of security IDs
        """
        with self.lock:
            return list(self.depth_data.keys())
    
    def _on_depth_update(self, depth_response: MarketDepth20Response) -> None:
        """Handle depth update from WebSocket."""
        security_id = depth_response.security_id
        
        with self.lock:
            # Store latest data
            self.depth_data[security_id] = depth_response
            
            # Clear analysis cache for this security
            self.analysis_cache.pop(security_id, None)
            
            # Notify subscribers
            callbacks = self.subscribers.get(security_id, [])
        
        # Call callbacks outside of lock
        for callback in callbacks:
            try:
                callback(depth_response)
            except Exception as e:
                logger.error(f"Error in depth callback: {e}")
    
    def _on_error(self, error: Exception) -> None:
        """Handle WebSocket error."""
        logger.error(f"Market depth WebSocket error: {error}")
    
    def _on_connect(self) -> None:
        """Handle WebSocket connection."""
        logger.info("Market depth WebSocket connected")
    
    def _on_disconnect(self) -> None:
        """Handle WebSocket disconnection."""
        logger.warning("Market depth WebSocket disconnected")
    
    def _calculate_depth_analysis(self, depth_data: MarketDepth20Response) -> MarketDepthAnalysis:
        """Calculate market depth analysis.
        
        Args:
            depth_data: 20-level market depth data
            
        Returns:
            Market depth analysis
        """
        # Calculate basic metrics
        total_bid_quantity = depth_data.get_total_bid_quantity()
        total_ask_quantity = depth_data.get_total_ask_quantity()
        bid_ask_ratio = depth_data.get_bid_ask_ratio()
        
        # Detect demand/supply zones
        zones = depth_data.detect_demand_supply_zones()
        
        # Find strongest and weakest levels
        bid_levels = depth_data.bid_depth.levels
        ask_levels = depth_data.ask_depth.levels
        
        strongest_bid = max(bid_levels, key=lambda x: x.quantity) if bid_levels else None
        strongest_ask = max(ask_levels, key=lambda x: x.quantity) if ask_levels else None
        weakest_bid = min(bid_levels, key=lambda x: x.quantity) if bid_levels else None
        weakest_ask = min(ask_levels, key=lambda x: x.quantity) if ask_levels else None
        
        return MarketDepthAnalysis(
            total_bid_quantity=total_bid_quantity,
            total_ask_quantity=total_ask_quantity,
            bid_ask_ratio=bid_ask_ratio,
            zones=DemandSupplyZones(
                demand_zones=zones["demand_zones"],
                supply_zones=zones["supply_zones"]
            ),
            price_levels={
                "strongest_bid": strongest_bid,
                "strongest_ask": strongest_ask,
                "weakest_bid": weakest_bid,
                "weakest_ask": weakest_ask,
            }
        )
