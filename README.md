# Dhan AI Trader

A comprehensive options trading platform built with the Dhan HQ API, featuring real-time market data, advanced options analytics, risk management, and automated trading strategies.

## Features

### 🔄 Live Market Data Integration
- Real-time price feeds for options contracts using Dhan HQ API
- WebSocket connections for live data streaming
- Bid/ask spreads, volume, and open interest data
- Support for NSE and BSE options chains

### 📊 Options-Focused Trading Features
- Interactive options chain viewer with strike prices and premiums
- Real-time Greeks calculations (Delta, Gamma, Theta, Vega)
- Live P&L tracking for open positions
- Options strategy builder (straddles, strangles, spreads, etc.)
- Implied volatility calculations and alerts

### 🛡️ Risk Management Tools
- Position sizing calculator based on account balance
- Automated stop-loss and take-profit orders
- Maximum drawdown alerts and protection
- Risk-reward ratio analysis for each trade
- Kelly Criterion position sizing

### 📈 Trading Analytics
- Historical performance tracking with detailed metrics
- Comprehensive trade journal with entry/exit analysis
- Backtesting capabilities for strategy validation
- Market sentiment indicators
- Performance attribution analysis

### 🔧 Technical Features
- Secure API key management for Dhan HQ
- Robust error handling and reconnection logic
- SQLite database for historical data and trade records
- Real-time dashboard with live updates
- Comprehensive logging and monitoring

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nanket/dhan-ai-trader.git
cd dhan-ai-trader
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Your Dhan API token is already configured in the `.env` file

5. Install the package in development mode:
```bash
pip install -e .
```

## Configuration

Edit `config/config.yaml` to customize:
- API settings and rate limits
- Risk management parameters
- Trading preferences
- Dashboard configuration

## Usage

### Quick Start - Test the Platform
```bash
# Start the main application (includes live demos)
python -m dhan_trader.main
```

### Command Line Interface
```bash
# View account information
dhan-trader account info

# Get user profile
dhan-trader account profile

# List active positions
dhan-trader positions list

# List holdings
dhan-trader holdings list

# Get market quote for NIFTY
dhan-trader quote NIFTY

# Get NIFTY option chain
dhan-trader optionchain NIFTY

# Get option chain for specific expiry
dhan-trader optionchain NIFTY --expiry 2024-12-26

# Get Bank NIFTY option chain
dhan-trader optionchain BANKNIFTY
```

### Python API Usage
```python
from dhan_trader.api.client import DhanAPIClient
from dhan_trader.market_data.manager import MarketDataManager

# Initialize API client
client = DhanAPIClient()

# Get user profile
profile = client.get_user_profile()
print(f"Client ID: {profile.dhan_client_id}")

# Get NIFTY option chain
option_chain = client.get_option_chain(13, "IDX_I")
print(f"NIFTY Price: {option_chain.underlying_price}")

# Initialize market data manager
market_data = MarketDataManager(client)

# Start live data feed
market_data.start_live_feed()

# Subscribe to NIFTY live updates
def on_update(packet):
    print(f"NIFTY: {packet.ltp}")

market_data.subscribe_instrument("13", "IDX_I", callback=on_update)
```

## Project Structure

```
dhan-ai-trader/
├── src/dhan_trader/
│   ├── api/              # Dhan API integration
│   ├── market_data/      # Real-time data handling
│   ├── options/          # Options analytics and Greeks
│   ├── trading/          # Trading engine and strategies
│   ├── risk/             # Risk management tools
│   ├── analytics/        # Performance analytics
│   ├── database/         # Data storage and models
│   ├── dashboard/        # Web dashboard
│   └── utils/            # Utility functions
├── tests/                # Test suites
├── config/               # Configuration files
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/ tests/
flake8 src/ tests/
```

### Type Checking
```bash
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading in financial markets involves substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software.

## Support

For questions and support, please open an issue on GitHub or contact the maintainers.
