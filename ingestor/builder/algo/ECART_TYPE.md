# Écart-type Glissant (Rolling Standard Deviation) Feature

## Overview

The Écart-type glissant (Rolling Standard Deviation) feature calculates the volatility of cryptocurrency price movements over a rolling time window. It helps identify periods of high and low volatility, extreme price movements, and market stability.

## What is Écart-type?

Écart-type (Standard Deviation) measures the dispersion of price changes from their mean. A rolling standard deviation calculates this metric over a sliding window, providing a dynamic view of volatility over time.

### Key Concepts

- **Volatility**: Measure of price variability
- **Rolling Window**: Fixed number of periods used for calculation
- **Z-Score**: Number of standard deviations a price change is from the mean
- **Extreme Movements**: Price changes that are statistically significant (>2 standard deviations)

## Implementation

### Backend

**Location**: `ingestor/scraper/api/routes/algo/ecart_Type.py`

**Core Function**: `build_ecart_type(df: pl.DataFrame, period: int = 14)`

#### Calculation Process

1. **Price Changes**: Calculate percentage price changes and log returns
2. **Rolling Statistics**: 
   - Rolling standard deviation of price changes
   - Rolling mean of price changes
   - Rolling standard deviation of log returns
3. **Z-Score Calculation**: 
   - `z-score = (price_change - mean) / standard_deviation`
   - Identifies extreme movements (>2 standard deviations)
4. **Volatility Categorization**:
   - **High**: Above 75th percentile
   - **Medium**: Between 25th and 75th percentile
   - **Low**: Below 25th percentile

#### Special Handling

- **Single Symbol Queries**: Optimized calculation without grouping overhead
- **Division by Zero Protection**: Handles cases where standard deviation is zero
- **Insufficient Data**: Graceful handling when data points < period
- **Quantile Calculation**: Fallback for edge cases with limited data

### API Endpoints

#### Get Écart-type Analysis for Symbol
```
GET /data/ecart-type/{symbol}
```

**Parameters**:
- `symbol` (path): Cryptocurrency symbol (e.g., BTC, ETH)
- `period` (query, default: 14): Rolling window period (5-100)
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
    "price_volatility_std": 2.5,
    "volatility_category": "medium",
    "extreme_movement": false,
    "price_change_zscore": 0.8
  },
  "time_series": [
    {
      "ts": "2024-01-01T00:00:00Z",
      "price_usd": 42000.00,
      "price_change_pct": 1.2,
      "price_volatility_std": 2.3,
      "volatility_category": "medium",
      "extreme_movement": false,
      "price_change_zscore": 0.5
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

**Warning Response** (Insufficient Data):
```json
{
  "level": "warning",
  "msg": "Insufficient data for symbol BTC. Need at least 14 data points, but only found 10.",
  "response": {
    "symbol": "BTC",
    "period": 14,
    "data_points_available": 10,
    "minimum_required": 14,
    "time_series": [],
    "latest_stats": {}
  }
}
```

#### Get General Écart-type Analysis
```
GET /data/ecart-type
```

Returns écart-type analysis for all available symbols with summary statistics.

### Frontend

**Location**: `web/src/app/component/analytics/components/ecart-type-glissant.ts`

**Features**:
- Symbol selector with search functionality
- Interactive volatility chart
- Statistics display (current, average, max, min)
- Period adjustment
- Date range filtering
- Error handling with informative messages

#### Component Features

1. **Symbol Selection**: 
   - Searchable dropdown
   - All available symbols
   - Real-time data loading

2. **Chart Visualization**: 
   - Line chart showing rolling standard deviation over time
   - Color-coded volatility zones
   - Interactive tooltips
   - Responsive design

3. **Statistics Panel**:
   - **Current**: Latest volatility value
   - **Average**: Mean volatility over period
   - **Maximum**: Peak volatility
   - **Minimum**: Lowest volatility

4. **Controls**:
   - Period selector (default: 14)
   - Date range picker
   - Symbol search/filter

5. **Error Handling**:
   - Informative warning messages
   - Graceful degradation
   - Retry functionality
   - No mock data fallback

#### Usage Example

```typescript
// In component
this.apiService.getEcartType('BTC', { 
  period: 14, 
  limit: 100 
}).subscribe({
  next: (response) => {
    if (response.msg && response.msg.includes('Insufficient')) {
      // Handle insufficient data warning
      this.errorMessage = response.msg;
      return;
    }
    
    if (response.time_series) {
      // Process time series data
      this.ecartTypeData = response.time_series.map(item => ({
        timestamp: item.ts,
        value: item.price_volatility_std
      }));
      this.updateStats(response.latest_stats);
    }
  },
  error: (error) => {
    // Handle error
    this.errorMessage = error.error?.msg || 'Error loading data';
  }
});
```

## Data Flow

1. **User selects symbol** → Frontend component
2. **API request** → `ApiService.getEcartType()`
3. **Backend query** → MySQL database for price data
4. **Écart-type calculation** → `build_ecart_type()` function:
   - Filters and sorts data
   - Calculates price changes
   - Computes rolling statistics
   - Categorizes volatility
5. **Response** → JSON with time series and statistics
6. **Chart rendering** → Chart.js visualizes volatility data

## Interpretation Guide

### Volatility Categories

- **High Volatility**: 
  - Above 75th percentile
  - Indicates unstable price movements
  - Higher risk/reward potential

- **Medium Volatility**:
  - Between 25th and 75th percentile
  - Normal market conditions
  - Balanced risk

- **Low Volatility**:
  - Below 25th percentile
  - Stable price movements
  - Lower risk, lower reward potential

### Z-Score Interpretation

- **|z-score| > 2**: Extreme movement (statistically significant)
- **|z-score| 1-2**: Moderate deviation
- **|z-score| < 1**: Normal variation

### Trading Applications

1. **Risk Management**: 
   - High volatility = higher position sizing risk
   - Low volatility = more stable trading environment

2. **Entry/Exit Timing**:
   - Extreme movements may indicate reversal points
   - Low volatility periods may precede breakouts

3. **Portfolio Diversification**:
   - Balance high and low volatility assets
   - Correlate volatility with other indicators

## Configuration

### Default Period
- **Standard**: 14 periods (matches RSI for consistency)
- **Short-term**: 7-10 periods (more responsive)
- **Long-term**: 21-28 periods (smoother trend)

### Adjustable Parameters

- **Period**: Rolling window size (5-100)
- **Limit**: Maximum data points to analyze (10-10000)
- **Date Range**: Filter data by time period
- **Symbol**: Select specific cryptocurrency

## Error Handling

The Écart-type feature implements comprehensive error handling:

1. **Insufficient Data**: 
   - Returns 200 status with warning message
   - Explains minimum data requirements
   - No 500 errors for data issues

2. **Calculation Errors**:
   - Division by zero protection
   - Quantile calculation fallbacks
   - Single symbol optimization

3. **Network Errors**:
   - Frontend displays user-friendly messages
   - Retry functionality
   - No mock data (as per requirements)

4. **Empty Results**:
   - Clear messaging about data availability
   - Suggests alternative symbols or periods

## Performance Optimizations

1. **Single Symbol Detection**: 
   - Skips unnecessary grouping for single-symbol queries
   - Faster calculations

2. **Data Filtering**:
   - Early filtering of null values
   - Efficient Polars operations

3. **Response Size**:
   - Configurable limit parameter
   - Efficient data serialization

## Technical Details

### Calculation Formula

```
price_change_pct = (price_t - price_{t-1}) / price_{t-1} * 100
rolling_std = std(price_change_pct[t-period:t])
rolling_mean = mean(price_change_pct[t-period:t])
z_score = (price_change_pct - rolling_mean) / rolling_std
```

### Data Requirements

- **Minimum**: `period` number of data points
- **Recommended**: 2-3x period for reliable statistics
- **Optimal**: 100+ data points for smooth charts

## Best Practices

1. **Period Selection**:
   - Match period to trading timeframe
   - Shorter periods = more sensitive
   - Longer periods = smoother trends

2. **Data Quality**:
   - Ensure sufficient historical data
   - Check for data gaps
   - Verify price data accuracy

3. **Combined Analysis**:
   - Use with RSI for comprehensive view
   - Correlate with price trends
   - Consider market context

## Future Enhancements

Potential improvements:
- Volatility forecasting
- Volatility clustering detection
- Multi-symbol volatility comparison
- Volatility-based alerts
- Historical volatility analysis
- Custom volatility bands

## Related Files

- Backend Algorithm: `ingestor/scraper/api/routes/algo/ecart_Type.py`
- Backend API: `ingestor/scraper/api/routes/data.py` (Écart-type endpoints)
- Frontend Component: `web/src/app/component/analytics/components/ecart-type-glissant.ts`
- Frontend Service: `web/src/app/services/api.service.ts` (Écart-type methods)

## Troubleshooting

### Common Issues

**No Data Displayed**:
- Check if symbol has sufficient data points (>= period)
- Verify date range includes data
- Check API response for warning messages

**Chart Not Rendering**:
- Ensure time_series array is not empty
- Verify data format matches expected structure
- Check browser console for errors

**500 Errors**:
- Should not occur with current implementation
- If seen, check backend logs for calculation errors
- Verify data quality in database

