# YFinance Benchmark API - Findings and Implementation Guide

## Research Summary

Successfully researched and tested yfinance API for fetching Indian benchmark indices data.

## Working Ticker Symbols for Indian Indices

### Primary Benchmarks (Recommended)

| Index Name | Ticker Symbol | Data Availability | Notes |
|-----------|---------------|-------------------|-------|
| **NIFTY 50** | `^NSEI` | ✅ Excellent (273 days) | Primary large-cap index |
| **NIFTY Midcap 100** | `NIFTY_MIDCAP_100.NS` | ✅ Excellent (271 days) | Mid-cap index |
| **NIFTY Midcap 50** | `^NSEMDCP50` | ✅ Excellent (271 days) | Alternative mid-cap |
| **NIFTY Midcap 150** | `NIFTYMIDCAP150.NS` | ✅ Excellent (272 days) | Broader mid-cap |
| **NIFTY Smallcap 250** | `NIFTYSMLCAP250.NS` | ⚠️ Limited (1 day only) | Data issues, avoid |

### Recommended for Portfolio Agent

Use these 3 primary benchmarks:
1. **^NSEI** - NIFTY 50 (large-cap)
2. **NIFTY_MIDCAP_100.NS** - NIFTY Midcap 100 (mid-cap)
3. **^NSEMDCP50** - NIFTY Midcap 50 (alternative mid-cap)

## Test Results (Dec 29, 2025)

### 30-Day Returns
- NIFTY 50: **-0.89%**
- NIFTY Midcap 100: **-1.71%**
- NIFTY Midcap 50: **-1.87%**
- NIFTY Midcap 150: **-1.70%**

### Today's Returns (vs. Previous Trading Day)
- NIFTY 50: **-0.38%**
- NIFTY Midcap 100: **-0.52%**
- NIFTY Midcap 50: **-0.50%**
- NIFTY Midcap 150: **-0.40%**

### Portfolio Comparison (Your Portfolio: -1.15%)
- vs NIFTY 50: **Underperformed by 0.77%**
- vs NIFTY Midcap 100: **Underperformed by 0.63%**
- vs NIFTY Midcap 50: **Underperformed by 0.65%**
- vs NIFTY Midcap 150: **Underperformed by 0.75%**

## How to Use yfinance

### Method 1: Using yf.download() (Recommended)

```python
import yfinance as yf
from datetime import datetime, timedelta

# Fetch 30 days of data
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

data = yf.download('^NSEI', start=start_date, end=end_date, progress=False)

# Extract close prices (handle MultiIndex columns)
if isinstance(data.columns, pd.MultiIndex):
    close_prices = data[('Close', '^NSEI')]
else:
    close_prices = data['Close']

# Calculate return
latest = float(close_prices.iloc[-1])
first = float(close_prices.iloc[0])
return_pct = ((latest - first) / first) * 100
```

### Method 2: Using yf.Ticker() (Alternative)

```python
import yfinance as yf

ticker = yf.Ticker('^NSEI')
hist = ticker.history(period='30d')

# Get latest close price
latest_close = float(hist['Close'].iloc[-1])

# Get ticker info
info = ticker.info
print(f"Currency: {info['currency']}")  # INR
print(f"Exchange: {info['exchange']}")  # NSI
```

### Method 3: Fetch Multiple Periods

```python
import yfinance as yf

ticker = '^NSEI'
data = yf.download(ticker, period='1y', progress=False)

# Handle MultiIndex
if isinstance(data.columns, pd.MultiIndex):
    close_col = data[('Close', ticker)]
else:
    close_col = data['Close']

# Calculate different period returns
def calculate_return(close_col, days):
    if len(close_col) < days:
        return None
    end = float(close_col.iloc[-1])
    start = float(close_col.iloc[-days])
    return ((end - start) / start) * 100

daily = calculate_return(close_col, 1)
wtd = calculate_return(close_col, 7)
mtd = calculate_return(close_col, 30)
ytd = calculate_return(close_col, 252)  # Trading days in a year
```

## Key Findings

### 1. Data Format - MultiIndex Columns

yfinance returns data with **MultiIndex columns** in format:
```
[('Close', '^NSEI'), ('High', '^NSEI'), ('Low', '^NSEI'), ...]
```

**Must handle this properly:**
```python
if isinstance(data.columns, pd.MultiIndex):
    close_col = data[('Close', ticker)]
else:
    close_col = data['Close']
```

### 2. Data Type - Series to Float

Values are returned as pandas Series. **Always convert to float:**
```python
latest_close = float(close_col.iloc[-1])  # Not just close_col.iloc[-1]
```

### 3. Empty Data Check

**Do NOT use** `.empty` on Series from MultiIndex:
```python
# ❌ WRONG (causes ambiguous truth value error)
if data['Close'].empty:
    ...

# ✅ CORRECT
if len(data) == 0:
    ...
```

### 4. Ticker Symbol Format

- **NSE Stocks:** Add `.NS` suffix (e.g., `RELIANCE.NS`)
- **BSE Stocks:** Add `.BO` suffix (e.g., `RELIANCE.BO`)
- **NSE Indices (some):** Use `^` prefix (e.g., `^NSEI`, `^NSEMDCP50`)
- **NSE Indices (others):** Use `.NS` suffix (e.g., `NIFTY_MIDCAP_100.NS`)

### 5. Data Availability

- Most indices: **~270 days** (9 months) of historical data
- NIFTY Smallcap 250: **Only 1 day** (data quality issue, avoid)
- Trading days only (weekends/holidays excluded)

## Current Bug in performance_context_aggregator.py

**Location:** `tools/performance_context_aggregator.py`, line ~330

**Issue:** The code checks `if data.empty:` on a Series, which causes:
```
'dict' object has no attribute 'empty'
```

**Root Cause:** Line 333 in `_compare_with_benchmarks()`:
```python
benchmark_data = self._fetch_benchmark_data(index_symbol, inception_date)
```

The `_fetch_benchmark_data()` method likely returns wrong data structure.

## Implementation Checklist

- [x] Research yfinance Indian index ticker symbols
- [x] Create comprehensive test script
- [x] Test all major indices (NIFTY 50, Midcap, Smallcap)
- [x] Test period return calculations
- [x] Test benchmark comparison with portfolio
- [x] Add debug logging to portfolio manager
- [ ] Fix bug in `performance_context_aggregator.py`
- [ ] Update `BENCHMARK_INDICES` in `performance_context_aggregator.py`
- [ ] Test benchmark comparison in portfolio manager agent

## References

- [NIFTY 50 on Yahoo Finance](https://finance.yahoo.com/quote/%5ENSEI/)
- [NIFTY MIDCAP 100 on Yahoo Finance](https://finance.yahoo.com/quote/NIFTY_MIDCAP_100.NS/)
- [NSE Tickers & Yahoo Finance Codes](https://www.kaggle.com/datasets/ianalyticsgeek/nse-tickers-their-yahoo-finance-equivalent-codes)
- [Getting Indian Stock Prices Using Python](https://medium.com/@TejasEkawade/getting-indian-stock-prices-using-python-19f8c83d2015)
- [Initializing yFinance to get NSE stock price data](https://medium.com/@dhruvi31/initializing-yfinance-to-get-nse-stock-price-data-2d05b9c920f2)

## Next Steps

1. Fix the bug in `performance_context_aggregator.py`
2. Update benchmark ticker symbols to use verified working ones
3. Test portfolio manager with corrected benchmark fetching
4. Verify performance narrative appears in logs with DEBUG level
