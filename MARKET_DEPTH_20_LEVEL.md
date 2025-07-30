# 20-Level Market Depth Implementation

## Overview

This implementation provides real-time 20-level market depth data streaming and analysis using the Dhan HQ API Level 3 Market Depth feature. It includes advanced trading analysis, demand/supply zone detection, and comprehensive visualization components.

## Features

### 🚀 Core Features
- **Real-time 20-level market depth streaming** via WebSocket
- **Demand/supply zone detection** beyond standard 5-level depth
- **Trading signal generation** based on market microstructure
- **Market efficiency analysis** and liquidity scoring
- **Visual order book** with 20 levels of bid/ask data
- **Performance optimized** with throttled updates
- **Comprehensive error handling** and reconnection logic

### 📊 Analysis Features
- **Order Flow Imbalance** calculation
- **Market Microstructure** analysis
- **Liquidity Analysis** with optimal order sizing
- **Price Impact Estimation**
- **Volatility Estimation** from depth data
- **Fragmentation Scoring**

### 🎯 Trading Features
- **Automated Signal Generation** (BUY/SELL/HOLD)
- **Confidence Scoring** for signals
- **Target Level Identification**
- **Stop Loss Calculation**
- **Time Horizon Recommendations** (SCALP/INTRADAY/SWING)

## Architecture

### Backend Components

#### 1. Data Models (`src/dhan_trader/api/models.py`)
```python
@dataclass
class MarketDepthLevel:
    price: float
    quantity: int
    orders: int

@dataclass
class MarketDepth20Response:
    security_id: str
    exchange_segment: str
    bid_depth: MarketDepth20Level
    ask_depth: MarketDepth20Level
    timestamp: datetime
```

#### 2. Level 3 WebSocket Client (`src/dhan_trader/api/websocket_depth.py`)
- Dedicated WebSocket client for 20-level depth
- Binary message parsing for bid/ask packets
- Rate limiting and error handling
- Message queue processing for performance

#### 3. Market Depth Manager (`src/dhan_trader/market_data/depth_manager.py`)
- State management for 20-level data
- Subscription management (max 50 instruments)
- Real-time analysis caching
- Callback system for updates

#### 4. Depth Analyzer (`src/dhan_trader/analysis/depth_analyzer.py`)
- Advanced market microstructure analysis
- Trading signal generation
- Liquidity analysis
- Historical data tracking

### Frontend Components

#### 1. Market Depth Context (`frontend/src/contexts/MarketDepthContext.tsx`)
- React context for state management
- WebSocket integration
- Throttled updates for performance
- Subscription management

#### 2. Order Book Component (`frontend/src/components/MarketDepth/OrderBook20Level.tsx`)
- 20-level order book visualization
- Demand/supply zone highlighting
- Real-time price and quantity updates
- Compact and detailed view modes

#### 3. Trading Analysis Panel (`frontend/src/components/MarketDepth/TradingAnalysisPanel.tsx`)
- Market microstructure metrics
- Trading signal display
- Confidence indicators
- Target and stop loss levels

#### 4. Market Depth Dashboard (`frontend/src/components/MarketDepth/MarketDepthDashboard.tsx`)
- Multi-security subscription management
- Tabbed interface for order books and analysis
- Quick add functionality for popular instruments

## API Endpoints

### Subscription Management
```
POST /api/depth/subscribe
- Subscribe to 20-level market depth
- Parameters: security_id, exchange_segment

POST /api/depth/unsubscribe  
- Unsubscribe from market depth
- Parameters: security_id

GET /api/depth/subscriptions
- Get active subscriptions list
```

### Data Access
```
GET /api/depth/{security_id}
- Get current 20-level depth data
- Returns: Complete bid/ask levels with prices, quantities, orders

GET /api/depth/{security_id}/analysis
- Get market depth analysis
- Returns: Microstructure metrics, zones, price levels
```

## Usage

### Backend Usage

```python
from src.dhan_trader.market_data.depth_manager import MarketDepthManager
from src.dhan_trader.api.client import DhanAPIClient

# Initialize
client = DhanAPIClient()
depth_manager = MarketDepthManager(client)

# Connect and subscribe
depth_manager.connect()
depth_manager.subscribe_depth("1333", "NSE_EQ")  # RELIANCE

# Get data
depth_data = depth_manager.get_depth_data("1333")
analysis = depth_manager.get_depth_analysis("1333")
```

### Frontend Usage

```tsx
import { useMarketDepth } from '../contexts/MarketDepthContext';

function MyComponent() {
  const { subscribeToDepth, getDepthData, getAnalysis } = useMarketDepth();
  
  // Subscribe to depth
  subscribeToDepth("1333", "NSE_EQ");
  
  // Get current data
  const depthData = getDepthData("1333");
  const analysis = getAnalysis("1333");
  
  return <OrderBook20Level securityId="1333" exchangeSegment="NSE_EQ" />;
}
```

## Configuration

### Supported Exchanges
- **NSE_EQ**: NSE Equity
- **NSE_FNO**: NSE Futures & Options

### Limits
- **Maximum Subscriptions**: 50 instruments per connection
- **Update Throttle**: 100ms per security
- **Rate Limit**: 1000 messages/second
- **Buffer Timeout**: 1 second for bid/ask combination

### Performance Settings
```python
# WebSocket settings
max_messages_per_second = 1000
buffer_timeout = 1.0  # seconds
update_throttle = 100  # milliseconds

# Analysis settings
history_size = 100  # snapshots
cache_duration = 30  # seconds
```

## Error Handling

### WebSocket Errors
- Automatic reconnection with exponential backoff
- Error rate limiting (max 10 errors per 5 minutes)
- Message queue processing for reliability

### Data Validation
- Exchange segment validation
- Subscription limit enforcement
- Binary message format validation

### Frontend Error Handling
- Connection status monitoring
- Graceful degradation on errors
- User-friendly error messages

## Testing

Run the comprehensive test suite:

```bash
python test_market_depth.py
```

Tests cover:
- Data model validation
- Depth analyzer functionality
- WebSocket client structure
- Signal generation accuracy

## Integration Points

### Existing Dhan API Integration
- Uses existing authentication system
- Leverages current WebSocket infrastructure
- Integrates with options trading analysis
- Compatible with AI trading advisor

### Frontend Integration
- Added to main navigation menu
- Integrated with existing theme system
- Uses consistent UI components
- Follows established routing patterns

## Performance Optimizations

### Backend
- Message queue processing
- Throttled analysis calculations
- Efficient binary parsing
- Connection pooling

### Frontend
- React.memo for component optimization
- Throttled state updates
- Efficient re-rendering
- Lazy loading of analysis

## Security Considerations

- Uses existing Dhan API authentication
- Secure WebSocket connections (WSS)
- Rate limiting to prevent abuse
- Input validation and sanitization

## Future Enhancements

- Historical depth data storage
- Advanced pattern recognition
- Machine learning signal enhancement
- Cross-asset depth correlation
- Real-time alerts and notifications

## Support

For issues or questions:
1. Check the test results for validation
2. Review error logs for WebSocket issues
3. Verify authentication credentials
4. Ensure exchange segment compatibility

## License

This implementation is part of the Dhan AI Trader project and follows the same licensing terms.
