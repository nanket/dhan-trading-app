"""Main application entry point for Dhan AI Trader."""

import asyncio
import logging
import signal
import sys
from typing import Optional
from datetime import datetime

from .config import config
from .api.client import DhanAPIClient
from .market_data.manager import MarketDataManager
from .exceptions import DhanTraderError, AuthenticationError

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.logging.get("level", "INFO")),
    format=config.logging.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.logging.get("file", "logs/dhan_trader.log"), mode="a"),
    ],
)

logger = logging.getLogger(__name__)


class DhanTrader:
    """Main application class for Dhan AI Trader."""
    
    def __init__(self):
        """Initialize the trading platform."""
        self.api_client = None
        self.market_data_manager = None
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    async def initialize(self) -> None:
        """Initialize all components."""
        try:
            logger.info("Initializing Dhan AI Trader...")
            
            # Initialize API client
            self.api_client = DhanAPIClient()
            
            # Test connection and get user profile
            profile = self.api_client.get_user_profile()
            logger.info(f"Connected as client: {profile.dhan_client_id}")
            logger.info(f"Token validity: {profile.token_validity}")
            logger.info(f"Active segments: {profile.active_segment}")
            
            # Initialize market data manager
            self.market_data_manager = MarketDataManager(self.api_client)
            
            # Start live market data feed
            if not config.development.get("mock_api", False):
                self.market_data_manager.start_live_feed()
            
            logger.info("Dhan AI Trader initialized successfully")
            
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise DhanTraderError(f"Initialization failed: {e}")
    
    async def run(self) -> None:
        """Run the main application loop."""
        try:
            await self.initialize()
            self.is_running = True
            
            logger.info("Dhan AI Trader is running...")
            
            # Demo: Subscribe to NIFTY index for live data
            await self._demo_market_data()
            
            # Demo: Get option chain data
            await self._demo_option_chain()
            
            # Keep the application running
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _demo_market_data(self) -> None:
        """Demonstrate market data functionality."""
        try:
            logger.info("=== Market Data Demo ===")
            
            # NIFTY 50 index (security ID: 13)
            nifty_security_id = "13"
            nifty_exchange = "IDX_I"
            
            # Get market quote via REST API
            try:
                quote = self.market_data_manager.get_market_quote(nifty_security_id, nifty_exchange)
                logger.info(f"NIFTY Quote - LTP: {quote.last_price}, Change: {quote.change} ({quote.change_percent}%)")
            except Exception as e:
                logger.warning(f"Could not get NIFTY quote: {e}")
            
            # Subscribe to live data
            if self.market_data_manager.ws_client and self.market_data_manager.ws_client.is_connected:
                def on_nifty_update(packet):
                    logger.info(f"NIFTY Live Update - LTP: {packet.ltp}")
                
                try:
                    self.market_data_manager.subscribe_instrument(
                        nifty_security_id,
                        nifty_exchange,
                        callback=on_nifty_update
                    )
                    logger.info("Subscribed to NIFTY live data")
                except Exception as e:
                    logger.warning(f"Could not subscribe to NIFTY live data: {e}")
            
        except Exception as e:
            logger.error(f"Market data demo failed: {e}")
    
    async def _demo_option_chain(self) -> None:
        """Demonstrate option chain functionality."""
        try:
            logger.info("=== Option Chain Demo ===")
            
            # NIFTY 50 options (underlying security ID: 13)
            underlying_scrip = 13
            underlying_segment = "IDX_I"
            
            # Get expiry list
            try:
                expiry_list = self.market_data_manager.get_option_expiry_list(
                    underlying_scrip, underlying_segment
                )
                logger.info(f"Available expiries: {expiry_list[:5]}...")  # Show first 5
                
                if expiry_list:
                    # Get option chain for nearest expiry
                    nearest_expiry = expiry_list[0]
                    option_chain = self.market_data_manager.get_option_chain(
                        underlying_scrip, underlying_segment, nearest_expiry
                    )
                    
                    logger.info(f"Option Chain for {nearest_expiry}:")
                    logger.info(f"Underlying Price: {option_chain.underlying_price}")
                    logger.info(f"Total Strikes: {len(option_chain.strikes)}")
                    
                    # Show ATM strikes
                    underlying_price = option_chain.underlying_price
                    atm_strikes = []
                    
                    for strike_price, strike_data in option_chain.strikes.items():
                        strike_float = float(strike_price)
                        if abs(strike_float - underlying_price) <= 200:  # Within 200 points of ATM
                            atm_strikes.append((strike_float, strike_data))
                    
                    # Sort by strike price
                    atm_strikes.sort(key=lambda x: x[0])
                    
                    logger.info("ATM Strikes (CE/PE):")
                    for strike_price, strike_data in atm_strikes[:10]:  # Show first 10
                        ce_ltp = strike_data.ce.last_price if strike_data.ce else "N/A"
                        pe_ltp = strike_data.pe.last_price if strike_data.pe else "N/A"
                        ce_iv = f"{strike_data.ce.implied_volatility:.2f}" if strike_data.ce else "N/A"
                        pe_iv = f"{strike_data.pe.implied_volatility:.2f}" if strike_data.pe else "N/A"
                        
                        logger.info(f"  {strike_price}: CE={ce_ltp}(IV:{ce_iv}), PE={pe_ltp}(IV:{pe_iv})")
                
            except Exception as e:
                logger.warning(f"Could not get option chain: {e}")
                
        except Exception as e:
            logger.error(f"Option chain demo failed: {e}")
    
    async def _demo_account_info(self) -> None:
        """Demonstrate account information retrieval."""
        try:
            logger.info("=== Account Information Demo ===")
            
            # Get fund limits
            try:
                fund_limit = self.api_client.get_fund_limit()
                logger.info(f"Available Balance: ₹{fund_limit.available_balance:,.2f}")
                logger.info(f"Margin Used: ₹{fund_limit.margin_used:,.2f}")
            except Exception as e:
                logger.warning(f"Could not get fund limits: {e}")
            
            # Get positions
            try:
                positions = self.api_client.get_positions()
                logger.info(f"Total Positions: {len(positions)}")
                for pos in positions[:5]:  # Show first 5
                    logger.info(f"  {pos.security_id}: Qty={pos.net_quantity}, P&L=₹{pos.pnl:.2f}")
            except Exception as e:
                logger.warning(f"Could not get positions: {e}")
            
            # Get holdings
            try:
                holdings = self.api_client.get_holdings()
                logger.info(f"Total Holdings: {len(holdings)}")
                for holding in holdings[:5]:  # Show first 5
                    logger.info(f"  {holding.security_id}: Qty={holding.quantity}, P&L=₹{holding.pnl:.2f}")
            except Exception as e:
                logger.warning(f"Could not get holdings: {e}")
                
        except Exception as e:
            logger.error(f"Account info demo failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        try:
            logger.info("Shutting down Dhan AI Trader...")
            self.is_running = False
            
            # Stop market data feed
            if self.market_data_manager:
                self.market_data_manager.stop_live_feed()
            
            logger.info("Shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}")
        self.is_running = False


async def main() -> None:
    """Main entry point."""
    try:
        trader = DhanTrader()
        await trader.run()
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Run the application
    asyncio.run(main())
