"""Command line interface for Dhan AI Trader."""

import argparse
import asyncio
import sys
from typing import Optional

from .main import DhanTrader
from .api.client import DhanAPIClient
from .config import config


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Dhan AI Trader - Comprehensive Options Trading Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dhan-trader                           # Start the main application
  dhan-trader account info              # Show account information
  dhan-trader positions list            # List current positions
  dhan-trader quote NIFTY               # Get NIFTY quote
  dhan-trader optionchain NIFTY         # Get NIFTY option chain
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Account commands
    account_parser = subparsers.add_parser("account", help="Account operations")
    account_subparsers = account_parser.add_subparsers(dest="account_action")
    
    account_subparsers.add_parser("info", help="Show account information")
    account_subparsers.add_parser("profile", help="Show user profile")
    account_subparsers.add_parser("funds", help="Show fund limits")
    
    # Position commands
    positions_parser = subparsers.add_parser("positions", help="Position operations")
    positions_subparsers = positions_parser.add_subparsers(dest="positions_action")
    
    positions_subparsers.add_parser("list", help="List all positions")
    
    # Holdings commands
    holdings_parser = subparsers.add_parser("holdings", help="Holdings operations")
    holdings_subparsers = holdings_parser.add_subparsers(dest="holdings_action")
    
    holdings_subparsers.add_parser("list", help="List all holdings")
    
    # Market data commands
    quote_parser = subparsers.add_parser("quote", help="Get market quote")
    quote_parser.add_argument("symbol", help="Symbol name (e.g., NIFTY)")
    quote_parser.add_argument("--exchange", default="IDX_I", help="Exchange segment")
    quote_parser.add_argument("--security-id", help="Security ID (if known)")
    
    # Option chain commands
    optionchain_parser = subparsers.add_parser("optionchain", help="Get option chain")
    optionchain_parser.add_argument("symbol", help="Underlying symbol (e.g., NIFTY)")
    optionchain_parser.add_argument("--expiry", help="Expiry date (YYYY-MM-DD)")
    optionchain_parser.add_argument("--strikes", type=int, default=10, help="Number of strikes to show")
    
    # Configuration
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser


async def handle_account_commands(api_client: DhanAPIClient, action: str) -> None:
    """Handle account-related commands."""
    try:
        if action == "info" or action == "profile":
            profile = api_client.get_user_profile()
            print(f"Client ID: {profile.dhan_client_id}")
            print(f"Token Validity: {profile.token_validity}")
            print(f"Active Segments: {profile.active_segment}")
            print(f"DDPI Status: {profile.ddpi}")
            print(f"MTF Status: {profile.mtf}")
            print(f"Data Plan: {profile.data_plan}")
            print(f"Data Validity: {profile.data_validity}")
            
        elif action == "funds":
            fund_limit = api_client.get_fund_limit()
            print(f"Available Balance: ₹{fund_limit.available_balance:,.2f}")
            print(f"SOD Limit: ₹{fund_limit.sod_limit:,.2f}")
            print(f"Collateral Amount: ₹{fund_limit.collateral_amount:,.2f}")
            print(f"Margin Used: ₹{fund_limit.margin_used:,.2f}")
            print(f"Exposure Margin: ₹{fund_limit.exposure_margin:,.2f}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


async def handle_positions_commands(api_client: DhanAPIClient, action: str) -> None:
    """Handle position-related commands."""
    try:
        if action == "list":
            positions = api_client.get_positions()
            
            if not positions:
                print("No positions found")
                return
            
            print(f"{'Security ID':<15} {'Exchange':<10} {'Product':<10} {'Qty':<8} {'Avg Price':<12} {'P&L':<12}")
            print("-" * 80)
            
            for pos in positions:
                print(f"{pos.security_id:<15} {pos.exchange_segment.value:<10} {pos.product_type.value:<10} "
                      f"{pos.net_quantity:<8} {pos.net_avg:<12.2f} {pos.pnl:<12.2f}")
            
            total_pnl = sum(pos.pnl for pos in positions)
            print("-" * 80)
            print(f"Total P&L: ₹{total_pnl:,.2f}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


async def handle_holdings_commands(api_client: DhanAPIClient, action: str) -> None:
    """Handle holdings-related commands."""
    try:
        if action == "list":
            holdings = api_client.get_holdings()
            
            if not holdings:
                print("No holdings found")
                return
            
            print(f"{'Security ID':<15} {'Exchange':<10} {'Qty':<8} {'Avg Cost':<12} {'LTP':<12} {'P&L':<12}")
            print("-" * 80)
            
            for holding in holdings:
                print(f"{holding.security_id:<15} {holding.exchange_segment.value:<10} "
                      f"{holding.quantity:<8} {holding.avg_cost_price:<12.2f} "
                      f"{holding.last_price:<12.2f} {holding.pnl:<12.2f}")
            
            total_pnl = sum(holding.pnl for holding in holdings)
            print("-" * 80)
            print(f"Total P&L: ₹{total_pnl:,.2f}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


async def handle_quote_command(api_client: DhanAPIClient, symbol: str, exchange: str, security_id: Optional[str]) -> None:
    """Handle quote command."""
    try:
        # Map common symbols to security IDs
        symbol_map = {
            "NIFTY": ("13", "IDX_I"),
            "BANKNIFTY": ("25", "IDX_I"),
            "SENSEX": ("1", "IDX_I"),
        }
        
        if not security_id and symbol.upper() in symbol_map:
            security_id, exchange = symbol_map[symbol.upper()]
        
        if not security_id:
            print(f"Security ID not found for symbol: {symbol}")
            print("Please provide --security-id parameter")
            sys.exit(1)
        
        quote = api_client.get_market_quote(security_id, exchange)
        
        print(f"Quote for {symbol} ({security_id}):")
        print(f"Last Price: ₹{quote.last_price:,.2f}")
        print(f"Change: ₹{quote.change:,.2f} ({quote.change_percent:.2f}%)")
        print(f"Open: ₹{quote.open_price:,.2f}")
        print(f"High: ₹{quote.high_price:,.2f}")
        print(f"Low: ₹{quote.low_price:,.2f}")
        print(f"Previous Close: ₹{quote.prev_close_price:,.2f}")
        print(f"Volume: {quote.volume:,}")
        
        if quote.oi:
            print(f"Open Interest: {quote.oi:,}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


async def handle_optionchain_command(
    api_client: DhanAPIClient, symbol: str, expiry: Optional[str], strikes: int
) -> None:
    """Handle option chain command."""
    try:
        # Map symbols to underlying scrip IDs
        symbol_map = {
            "NIFTY": (13, "IDX_I"),
            "BANKNIFTY": (25, "IDX_I"),
        }
        
        if symbol.upper() not in symbol_map:
            print(f"Option chain not available for symbol: {symbol}")
            sys.exit(1)
        
        underlying_scrip, underlying_segment = symbol_map[symbol.upper()]
        
        # Get expiry list if not provided
        if not expiry:
            expiry_list = api_client.get_option_expiry_list(underlying_scrip, underlying_segment)
            if expiry_list:
                expiry = expiry_list[0]  # Use nearest expiry
                print(f"Using nearest expiry: {expiry}")
            else:
                print("No expiries found")
                sys.exit(1)
        
        option_chain = api_client.get_option_chain(underlying_scrip, underlying_segment, expiry)
        
        print(f"Option Chain for {symbol} - Expiry: {expiry}")
        print(f"Underlying Price: ₹{option_chain.underlying_price:,.2f}")
        print()
        
        # Find ATM strikes
        underlying_price = option_chain.underlying_price
        all_strikes = sorted([float(strike) for strike in option_chain.strikes.keys()])
        
        # Find closest strike to underlying price
        atm_strike = min(all_strikes, key=lambda x: abs(x - underlying_price))
        atm_index = all_strikes.index(atm_strike)
        
        # Select strikes around ATM
        start_idx = max(0, atm_index - strikes // 2)
        end_idx = min(len(all_strikes), atm_index + strikes // 2 + 1)
        selected_strikes = all_strikes[start_idx:end_idx]
        
        # Display option chain
        print(f"{'Strike':<8} {'CE LTP':<10} {'CE IV':<8} {'CE OI':<10} {'PE LTP':<10} {'PE IV':<8} {'PE OI':<10}")
        print("-" * 70)
        
        for strike in selected_strikes:
            strike_key = str(strike)
            if strike_key in option_chain.strikes:
                strike_data = option_chain.strikes[strike_key]
                
                ce_ltp = f"{strike_data.ce.last_price:.2f}" if strike_data.ce else "N/A"
                ce_iv = f"{strike_data.ce.implied_volatility:.2f}" if strike_data.ce else "N/A"
                ce_oi = f"{strike_data.ce.oi:,}" if strike_data.ce else "N/A"
                
                pe_ltp = f"{strike_data.pe.last_price:.2f}" if strike_data.pe else "N/A"
                pe_iv = f"{strike_data.pe.implied_volatility:.2f}" if strike_data.pe else "N/A"
                pe_oi = f"{strike_data.pe.oi:,}" if strike_data.pe else "N/A"
                
                print(f"{strike:<8.0f} {ce_ltp:<10} {ce_iv:<8} {ce_oi:<10} {pe_ltp:<10} {pe_iv:<8} {pe_oi:<10}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


async def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle no command - start main application
    if not args.command:
        trader = DhanTrader()
        await trader.run()
        return
    
    # Initialize API client for other commands
    try:
        api_client = DhanAPIClient()
    except Exception as e:
        print(f"Failed to initialize API client: {e}")
        sys.exit(1)
    
    # Handle commands
    if args.command == "account":
        await handle_account_commands(api_client, args.account_action)
    elif args.command == "positions":
        await handle_positions_commands(api_client, args.positions_action)
    elif args.command == "holdings":
        await handle_holdings_commands(api_client, args.holdings_action)
    elif args.command == "quote":
        await handle_quote_command(api_client, args.symbol, args.exchange, args.security_id)
    elif args.command == "optionchain":
        await handle_optionchain_command(api_client, args.symbol, args.expiry, args.strikes)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
