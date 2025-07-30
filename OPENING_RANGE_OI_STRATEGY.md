# Opening Range OI Strategy

## 🎯 Strategy Overview

The **Opening Range OI Strategy** analyzes Open Interest (OI) between two strike prices based on the day's opening price. 

### Example: Today's NIFTY Opening at 24619
- **Opening Price**: 24619
- **Range Interval**: 100 points
- **Analysis Range**: 24600 - 24700

## 🔧 How It Works

### 1. Range Calculation
```python
opening_price = 24619
range_interval = 100

# Calculate range bounds
lower_bound = (int(24619 / 100) * 100) = 24600
upper_bound = lower_bound + 100 = 24700

# Result: Analyze 24600-24700 range
```

### 2. OI Analysis Logic
- **PE > CE on both strikes** → **Bullish Signal** (Support levels)
- **CE > PE on both strikes** → **Bearish Signal** (Resistance levels)  
- **Mixed signals** → **Neutral/Range-bound**

## 🚀 API Endpoints

### 1. Opening Range Analysis
```bash
POST /api/strategy/opening-range-oi-analysis
```

**Parameters:**
- `opening_price`: Today's opening price (e.g., 24619)
- `range_interval`: Range interval in points (default: 100)
- `underlying_scrip`: Security ID (default: 13 for NIFTY)
- `expiry`: Option expiry date (optional)

**Example:**
```bash
curl -X POST 'http://localhost:8000/api/strategy/opening-range-oi-analysis?opening_price=24619&underlying_scrip=13&range_interval=100'
```

**Response:**
```json
{
  "current_price": 24619,
  "lower_strike": 24600,
  "upper_strike": 24700,
  "lower_strike_pe_oi": 150000,
  "lower_strike_ce_oi": 120000,
  "upper_strike_pe_oi": 180000,
  "upper_strike_ce_oi": 200000,
  "lower_strike_signal": "support",
  "upper_strike_signal": "resistance",
  "overall_signal": "neutral",
  "confidence": 0.75,
  "reasoning": "Mixed signals: 24600 shows support (PE>CE), 24700 shows resistance (CE>PE)",
  "timestamp": "2024-12-26T10:30:00"
}
```

### 2. Individual Strike OI
```bash
GET /api/strategy/individual-strike-oi/{strike_price}
```

**Example:**
```bash
curl -X GET 'http://localhost:8000/api/strategy/individual-strike-oi/24600?underlying_scrip=13'
```

**Response:**
```json
{
  "strike_price": 24600,
  "pe_oi": 150000,
  "ce_oi": 120000,
  "pe_volume": 25000,
  "ce_volume": 18000,
  "pe_ltp": 45.50,
  "ce_ltp": 12.25,
  "pe_ce_ratio": 1.25,
  "signal": "support",
  "timestamp": "2024-12-26T10:30:00"
}
```

## 🖥️ Frontend Usage

### 1. Access the Interface
1. Open http://localhost:3000
2. Navigate to "Range OI Strategy"
3. Select **"Opening Range"** mode

### 2. Configure Analysis
- **Opening Price**: 24619 (today's opening)
- **Range Interval**: 100 (for 24600-24700 range)
- Click **"Analyze"**

### 3. Analysis Modes
- **Opening Range**: Based on opening price (24619 → 24600-24700)
- **Auto Range**: System auto-detects nearest strikes
- **Custom Range**: Manually specify exact strikes

## 🐍 Python API Usage

```python
from dhan_trader.strategies.range_oi_strategy import RangeOIStrategy
from dhan_trader.market_data.manager import MarketDataManager
from dhan_trader.api.client import DhanAPIClient

# Initialize components
api_client = DhanAPIClient()
market_data_manager = MarketDataManager(api_client)
strategy = RangeOIStrategy(market_data_manager)

# Opening range analysis
analysis = strategy.analyze_opening_range_oi(
    opening_price=24619,
    underlying_scrip=13,
    range_interval=100
)

print(f"Range: {analysis.lower_strike} - {analysis.upper_strike}")
print(f"Signal: {analysis.overall_signal}")
print(f"Confidence: {analysis.confidence:.2%}")

# Individual strike analysis
strike_data = strategy.get_individual_strike_oi(
    strike_price=24600,
    underlying_scrip=13
)

print(f"24600 PE OI: {strike_data.pe_oi:,}")
print(f"24600 CE OI: {strike_data.ce_oi:,}")
```

## 📊 Range Interval Examples

| Opening Price | Interval | Lower Strike | Upper Strike | Range |
|---------------|----------|--------------|--------------|-------|
| 24619 | 50 | 24600 | 24650 | 24600-24650 |
| 24619 | 100 | 24600 | 24700 | 24600-24700 |
| 24619 | 200 | 24600 | 24800 | 24600-24800 |
| 25440 | 100 | 25400 | 25500 | 25400-25500 |
| 25550 | 100 | 25500 | 25600 | 25500-25600 |

## 🎯 Trading Signals

### Bullish Signal (Support)
- **24600 PE OI > CE OI** AND **24700 PE OI > CE OI**
- **Interpretation**: Both strikes acting as support
- **Action**: Consider bullish strategies

### Bearish Signal (Resistance)  
- **24600 CE OI > PE OI** AND **24700 CE OI > PE OI**
- **Interpretation**: Both strikes acting as resistance
- **Action**: Consider bearish strategies

### Neutral Signal (Range-bound)
- **Mixed signals** between the two strikes
- **Interpretation**: Market likely to trade in range
- **Action**: Consider range-bound strategies

## 🔄 Real-time Updates

The strategy supports:
- **Auto-refresh** every 30 seconds
- **WebSocket** real-time updates
- **Historical signal tracking**
- **Confidence scoring** (0-100%)

## 📈 Use Cases

1. **Intraday Trading**: Quick range identification for day trading
2. **Options Strategies**: Support/resistance for option selling
3. **Risk Management**: Range-bound position sizing
4. **Market Sentiment**: Overall bullish/bearish bias

## 🚨 Important Notes

- **Strike Availability**: Ensure strikes exist in option chain
- **Liquidity**: Check OI and volume before trading
- **Time Decay**: Consider time to expiry
- **Market Hours**: Strategy works best during active trading hours

## 📝 Summary

✅ **Opening-based Range OI Strategy** implemented  
✅ **24619 opening → 24600-24700** range analysis  
✅ **Individual strike analysis** for specific strikes  
✅ **Frontend interface** with multiple analysis modes  
✅ **API endpoints** ready for integration  
✅ **Real-time updates** and historical tracking
