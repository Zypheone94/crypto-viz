# RSI (Relative Strength Index) Feature

The RSI (Relative Strength Index) is a momentum oscillator that measures the speed and magnitude of price movements. It helps identify overbought and oversold conditions in cryptocurrency markets.

## What is RSI?

RSI is a technical indicator that oscillates between 0 and 100:
- **RSI > 70**: Overbought condition (potential sell signal)
- **RSI < 30**: Oversold condition (potential buy signal)
- **RSI 30-70**: Neutral/momentum zone

## Implementation

### Backend

**Location**: `ingestor/builder/rsi.py`

**Core Function**: `build_rsi(df: pl.DataFrame, period: int = 14)`

#### Calculation Process

1. **Price Changes**: Calculate price differences and percentage changes
2. **Gains and Losses**: Separate positive (gains) and negative (losses) price movements
3. **Average Gains/Losses**: Calculate Simple Moving Average (SMA) over the period
4. **Relative Strength (RS)**: Ratio of average gains to average losses
5. **RSI Formula**: `RSI = 100 - (100 / (1 + RS))`

#### Additional Metrics

- **RSI Signal**: Categorizes as "overbought", "oversold", or "neutral"
- **RSI Strength**: Classifies momentum as "strong", "moderate", or "weak"
- **RSI Momentum**: Tracks direction of RSI change (increasing/decreasing)

### API Endpoints

#### Get RSI Analysis for Symbol
```
GET /data/rsi/{symbol}
```

**Parameters**:
- `symbol` (path): Cryptocurrency symbol (e.g., BTC, ETH)
- `period` (query, default: 14): RSI calculation period (5-100)
- `limit` (query, default: 1000): Maximum records to analyze (10-10000)
- `date_from` (query, optional): Start date filter (YYYY-MM-DD)
- `date_to` (query, optional): End date filter (YYYY-MM-DD)

**Response Structure**:
```json
{
  "success": true,
  "symbol": "BTC",
  "period": 14,
  "latest_stats": {
    "price_usd": 45000.00,
    "rsi": 65.5,
    "rsi_signal": "neutral",
    "rsi_strength": "moderate",
    "rsi_momentum": "increasing"
  },
  "time_series": [
    {
      "ts": "2024-01-01T00:00:00Z",
      "price_usd": 42000.00,
      "rsi": 58.2,
      "rsi_signal": "neutral",
      "avg_gain": 1.5,
      "avg_loss": 1.2
    }
  ],
  "metadata": {
    "total_points": 100,
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-15T00:00:00Z"
    }
  }
}
```

#### Get General RSI Analysis
```
GET /data/rsi
```

Returns RSI analysis for all available symbols with summary statistics.

### Frontend

**Location**: `web/src/app/component/analytics/components/rsi.ts`

**Features**:
- Symbol selector dropdown
- Real-time RSI chart visualization
- Current RSI value display with color coding
- Signal indicator (overbought/oversold/neutral)
- Price information
- Historical RSI trend visualization

#### Component Features

1. **Symbol Selection**: Dropdown with all available symbols
2. **Chart Visualization**: Line chart showing RSI over time with:
   - RSI line (0-100 scale)
   - Overbought threshold (70) - red zone
   - Oversold threshold (30) - green zone
   - Neutral zone (30-70) - orange zone
3. **Statistics Display**:
   - Current RSI value
   - Signal status (color-coded)
   - Current price
4. **Error Handling**: Graceful error messages and retry functionality

#### Usage Example

```typescript
// In component
this.apiService.getSymbolRsiAnalysis('BTC', { 
  period: 14, 
  limit: 100 
}).subscribe({
  next: (data) => {
    // Process RSI data
    this.data = data;
    this.createChart();
  },
  error: (error) => {
    // Handle error
  }
});
```

## Data Flow

1. **User selects symbol** → Frontend component
2. **API request** → `ApiService.getSymbolRsiAnalysis()`
3. **Backend query** → MySQL database for price data
4. **RSI calculation** → `build_rsi()` function processes data
5. **Response** → JSON with time series and statistics
6. **Chart rendering** → Chart.js visualizes RSI data

## Interpretation Guide

### RSI Values

- **0-30**: Oversold - Potential buying opportunity
- **30-70**: Neutral - Normal market conditions
- **70-100**: Overbought - Potential selling opportunity

### Trading Signals

**Buy Signal**:
- RSI crosses above 30 (exiting oversold)
- RSI is below 50 and increasing

**Sell Signal**:
- RSI crosses below 70 (exiting overbought)
- RSI is above 50 and decreasing

**Neutral**:
- RSI between 30-70 with stable trend

### Best Practices

1. **Use with other indicators**: RSI works best when combined with other technical analysis tools
2. **Consider timeframe**: Different periods (14, 21, 28) provide different insights
3. **Watch for divergences**: Price making new highs while RSI doesn't can indicate weakness
4. **Avoid extremes in trending markets**: In strong trends, RSI can stay overbought/oversold for extended periods

## Configuration

### Default Period
- **Standard**: 14 periods (most common)
- **Short-term**: 7-9 periods (more sensitive)
- **Long-term**: 21-28 periods (less sensitive)

### Adjustable Parameters

In the frontend component, users can:
- Select different symbols
- View historical data
- Adjust date ranges (via API parameters)

## Error Handling

The RSI feature handles various error scenarios:

1. **No Data Available**: Returns warning message with 200 status
2. **Insufficient Data**: Requires minimum data points equal to period
3. **Calculation Errors**: Graceful fallback with error messages
4. **Network Errors**: Frontend displays error with retry option

## Performance Considerations

- **Data Limit**: Default 1000 records, max 10000
- **Calculation Speed**: Optimized with Polars DataFrame operations
- **Chart Rendering**: Efficient Chart.js rendering with data sampling for large datasets

