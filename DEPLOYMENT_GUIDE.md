# Dhan AI Trader - Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Valid Dhan trading account
- Dhan API access token

### Installation Steps

1. **Clone and Setup**
```bash
git clone <repository-url>
cd dhan-ai-trader
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

2. **Configure API Token**
Your Dhan API token is already configured in the `.env` file. To get a new token:
- Login to [web.dhan.co](https://web.dhan.co)
- Go to My Profile → Access DhanHQ APIs
- Generate a new access token
- Update the `.env` file with your token

3. **Test Installation**
```bash
# Test basic functionality
python -c "from src.dhan_trader.api.client import DhanAPIClient; print('✅ Installation successful')"

# Test API connection
dhan-trader account info
```

## 🔧 Configuration

### Environment Variables
```bash
# .env file
DHAN_TOKEN=your_jwt_token_here
```

### Configuration File
Edit `config/config.yaml` to customize:

```yaml
# API settings
api:
  timeout: 30
  max_retries: 3

# Market data settings
market_data:
  subscription_limit: 1000
  reconnect_attempts: 5

# Risk management
risk_management:
  max_position_size_percent: 5.0
  max_daily_loss_percent: 2.0
```

## 📱 Usage Examples

### 1. Account Information
```bash
# Get user profile
dhan-trader account info

# Check fund limits
dhan-trader account funds

# List positions
dhan-trader positions list

# List holdings
dhan-trader holdings list
```

### 2. Market Data
```bash
# Get NIFTY quote
dhan-trader quote NIFTY

# Get Bank NIFTY quote
dhan-trader quote BANKNIFTY

# Get option chain
dhan-trader optionchain NIFTY

# Get option chain for specific expiry
dhan-trader optionchain NIFTY --expiry 2024-12-26
```

### 3. Python API
```python
from dhan_trader.api.client import DhanAPIClient
from dhan_trader.market_data.manager import MarketDataManager

# Initialize API client
client = DhanAPIClient()

# Get user profile
profile = client.get_user_profile()
print(f"Connected as: {profile.dhan_client_id}")

# Get NIFTY option chain
option_chain = client.get_option_chain(13, "IDX_I")
print(f"NIFTY Price: ₹{option_chain.underlying_price:,.2f}")

# Show ATM strikes
for strike_price, strike_data in option_chain.strikes.items():
    if strike_data.ce and strike_data.pe:
        print(f"Strike {strike_price}: CE={strike_data.ce.last_price}, PE={strike_data.pe.last_price}")
```

### 4. Live Market Data
```python
from dhan_trader.market_data.manager import MarketDataManager

# Initialize market data manager
manager = MarketDataManager(client)

# Start live feed
manager.start_live_feed()

# Subscribe to NIFTY live updates
def on_nifty_update(packet):
    print(f"NIFTY Live: ₹{packet.ltp:,.2f}")

manager.subscribe_instrument("13", "IDX_I", callback=on_nifty_update)

# Keep running to receive updates
import time
while True:
    time.sleep(1)
```

## 🏗️ Development Setup

### Development Dependencies
```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Code formatting
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Project Structure
```
dhan-ai-trader/
├── src/dhan_trader/          # Main package
│   ├── api/                  # API integration
│   ├── market_data/          # Market data handling
│   ├── config.py            # Configuration
│   ├── main.py              # Main application
│   └── cli.py               # Command line interface
├── tests/                    # Test suite
├── config/                   # Configuration files
├── docs/                     # Documentation
└── requirements.txt          # Dependencies
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
Error: Invalid or expired access token
```
**Solution**: 
- Check if your Dhan API token is valid
- Ensure Data Plan is active in your Dhan account
- Generate a new token from Dhan web platform

#### 2. Import Errors
```
ModuleNotFoundError: No module named 'dhan_trader'
```
**Solution**:
```bash
pip install -e .
```

#### 3. WebSocket Connection Issues
```
WebSocket connection failed
```
**Solution**:
- Check internet connectivity
- Verify API token has WebSocket permissions
- Check if firewall is blocking WebSocket connections

#### 4. Rate Limit Errors
```
Rate limit exceeded
```
**Solution**:
- The client automatically handles rate limits
- Reduce request frequency if needed
- Check API usage in Dhan dashboard

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Monitoring & Logging

### Log Files
- Application logs: `logs/dhan_trader.log`
- Error logs: Console output
- Debug logs: Enable via configuration

### Performance Monitoring
```python
# Check subscription count
manager = MarketDataManager(client)
print(f"Active subscriptions: {manager.get_subscription_count()}")

# Monitor WebSocket status
if manager.ws_client and manager.ws_client.is_connected:
    print("✅ WebSocket connected")
else:
    print("❌ WebSocket disconnected")
```

## 🔐 Security Best Practices

### 1. Token Security
- Never commit API tokens to version control
- Use environment variables for sensitive data
- Rotate tokens regularly
- Monitor API usage for unusual activity

### 2. Network Security
- Use HTTPS for all API calls
- Verify SSL certificates
- Monitor for man-in-the-middle attacks

### 3. Application Security
- Validate all input data
- Implement proper error handling
- Log security events
- Regular dependency updates

## 🚀 Production Deployment

### 1. Server Requirements
- Python 3.9+ runtime
- 512MB+ RAM
- Stable internet connection
- SSL/TLS support

### 2. Environment Setup
```bash
# Production environment
export DHAN_TOKEN="your_production_token"
export ENVIRONMENT="production"

# Start application
python -m dhan_trader.main
```

### 3. Process Management
```bash
# Using systemd (Linux)
sudo systemctl start dhan-trader
sudo systemctl enable dhan-trader

# Using PM2 (Node.js process manager)
pm2 start "python -m dhan_trader.main" --name dhan-trader
```

### 4. Health Checks
```bash
# Check API connectivity
curl -H "access-token: $DHAN_TOKEN" https://api.dhan.co/v2/profile

# Check application status
dhan-trader account info
```

## 📈 Scaling Considerations

### 1. Multiple Connections
- Each WebSocket supports 5000 instruments
- Use multiple connections for more instruments
- Implement connection pooling

### 2. Data Storage
- Consider database integration for historical data
- Implement data archiving strategies
- Monitor storage usage

### 3. Performance Optimization
- Use async/await for concurrent operations
- Implement caching for frequently accessed data
- Monitor memory usage and optimize

## 🆘 Support & Resources

### Documentation
- API Documentation: [dhanhq.co/docs](https://dhanhq.co/docs)
- Python Client: [github.com/dhan-oss/DhanHQ-py](https://github.com/dhan-oss/DhanHQ-py)

### Community
- Dhan Developer Forum
- GitHub Issues
- Stack Overflow (tag: dhan-api)

### Professional Support
- Contact Dhan support for API issues
- Consider professional consultation for complex implementations

## ✅ Deployment Checklist

- [ ] Python 3.9+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] API token configured in `.env`
- [ ] Configuration customized in `config/config.yaml`
- [ ] Basic functionality tested (`dhan-trader account info`)
- [ ] Logs directory created and writable
- [ ] Network connectivity verified
- [ ] Security measures implemented
- [ ] Monitoring setup configured
- [ ] Backup and recovery plan in place

## 🎉 Ready to Trade!

Your Dhan AI Trader platform is now ready for:
- Real-time market data analysis
- Options chain monitoring
- Account management
- Custom strategy development

Start with the CLI commands and gradually integrate the Python API into your trading workflows!
