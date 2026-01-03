# Benchmark Bug Fix - Performance Context Aggregator

## Problem Summary

**Error:** `'dict' object has no attribute 'empty'`

**Location:** `tools/performance_context_aggregator.py`, line 374 (old code)

**Impact:** Benchmark comparison feature was completely broken - all 3 benchmarks failed to load.

## Root Cause

The `get_index_history()` method in `price_fetcher.py` returns a **dict**, but the code in `performance_context_aggregator.py` was treating it as a **pandas DataFrame**.

### Data Structure Mismatch

**What get_index_history() returns:**
```python
{
    'dates': [...],
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [1644.70, 1653.50, ...],  # List of floats
    'volume': [...]
}
```

**What the code expected:**
```python
# A pandas DataFrame with methods like .empty, .iloc[], etc.
```

## Changes Made

### 1. Fixed Data Structure Handling

**File:** `tools/performance_context_aggregator.py`

**Before (Lines 374-389):**
```python
if not history or history.empty:  # ❌ dict has no .empty attribute
    raise ValueError(f"No history data for {index_symbol}")

# Calculate returns for each period
returns = {}
for period_name, days in periods_needed.items():
    if days == 0:
        returns[period_name] = 0.0
        continue

    try:
        if len(history) > days:  # ❌ len(dict) returns number of keys, not rows
            start_price = history.iloc[-days-1]['Close']  # ❌ dict has no .iloc
            end_price = history.iloc[-1]['Close']
            period_return = ((end_price - start_price) / start_price) * 100
            returns[period_name] = round(period_return, 2)
```

**After (Lines 374-408):**
```python
# get_index_history returns a dict, not a DataFrame
if not history or not history.get('close'):  # ✅ Check dict key
    raise ValueError(f"No history data for {index_symbol}")

close_prices = history['close']  # ✅ Extract close prices list
num_prices = len(close_prices)  # ✅ Correct length check

if num_prices == 0:
    raise ValueError(f"No close prices for {index_symbol}")

logger.debug(f"{index_symbol}: Retrieved {num_prices} historical prices")

# Calculate returns for each period
returns = {}
for period_name, days in periods_needed.items():
    if days == 0:
        returns[period_name] = 0.0
        continue

    try:
        if num_prices > days:  # ✅ Check list length
            # Get prices from the end of the list
            start_price = close_prices[-days-1]  # ✅ List indexing
            end_price = close_prices[-1]
            period_return = ((end_price - start_price) / start_price) * 100
            returns[period_name] = round(period_return, 2)
            logger.trace(f"{index_symbol} {period_name}: {start_price:.2f} -> {end_price:.2f} = {period_return:+.2f}%")
        else:
            # Not enough data for this period
            logger.debug(f"{index_symbol}: Insufficient data for {period_name} ({num_prices} <= {days})")
            returns[period_name] = 0.0
```

### 2. Updated Benchmark Indices

**File:** `tools/performance_context_aggregator.py`

**Before:**
```python
BENCHMARK_INDICES = [
    '^NSEI',                    # Nifty 50
    'NIFTY_MIDCAP_100.NS',      # Nifty Midcap 100
    'NIFTYSMLCAP250.NS'         # Nifty Smallcap 250  ❌ Only 1 day of data
]
```

**After:**
```python
# Updated 2025-12-29: Verified working ticker symbols via yfinance
BENCHMARK_INDICES = [
    '^NSEI',                    # Nifty 50 (large-cap)
    'NIFTY_MIDCAP_100.NS',      # Nifty Midcap 100 (mid-cap)
    '^NSEMDCP50'                # Nifty Midcap 50 (alternative mid-cap) ✅ 271 days of data
]
```

### 3. Added Missing Index to INDIAN_INDICES

**File:** `tools/price_fetcher.py`

**Added:**
```python
INDIAN_INDICES = {
    '^NSEI': 'Nifty 50',
    '^BSESN': 'Sensex',
    '^NSEMDCP50': 'Nifty Midcap 50',  # ✅ Added
    'NIFTY_MIDCAP_100.NS': 'Nifty Midcap 100',
    'NIFTYSMLCAP250.NS': 'Nifty Smallcap 250',
    'NIFTYMIDCAP150.NS': 'Nifty Midcap 150',  # ✅ Added
    # ... rest
}
```

## Verification

### Test Results (Dec 29, 2025)

All 3 benchmarks now working correctly:

```
Testing: Nifty 50 (^NSEI)
  ✅ 29 price points
  ✅ Daily return: -0.38%

Testing: Nifty Midcap 100 (NIFTY_MIDCAP_100.NS)
  ✅ 29 price points
  ✅ Daily return: -0.52%

Testing: Nifty Midcap 50 (^NSEMDCP50)
  ✅ 29 price points
  ✅ Daily return: -0.50%
```

### Expected Portfolio Manager Output

With `LOG_LEVEL=DEBUG` in `.env`, you should now see:

```
[8/9] Generating performance context...
[INFO] Generating performance context for portfolio 42
[DEBUG] ^NSEI: Retrieved 29 historical prices
[TRACE] ^NSEI daily: 26042.30 -> 25942.10 = -0.38%
[DEBUG] NIFTY_MIDCAP_100.NS: Retrieved 29 historical prices
[TRACE] NIFTY_MIDCAP_100.NS daily: 60314.45 -> 60001.30 = -0.52%
[DEBUG] ^NSEMDCP50: Retrieved 29 historical prices
[TRACE] ^NSEMDCP50 daily: 17183.30 -> 17096.90 = -0.50%
[INFO] Benchmark comparison: 3/3 available  ✅ All working!
[DEBUG] Performance narrative being sent to LLM:
PERFORMANCE SUMMARY (as of 2025-12-29)

Portfolio Value: Rs. 494,271 (-1.15% since inception on 2025-12-28)

Today's Performance: -1.15% (Rs. -5,729)
- Underperformed Nifty 50 (-0.38%) by -0.77%
- Underperformed Nifty Midcap 100 (-0.52%) by -0.63%
- Underperformed Nifty Midcap 50 (-0.50%) by -0.65%

Week-to-Date: -1.15%, Month-to-Date: -1.15%
...
```

## Files Modified

1. **tools/performance_context_aggregator.py**
   - Fixed `_fetch_benchmark_data()` method (lines 356-414)
   - Updated `BENCHMARK_INDICES` list (lines 23-28)
   - Added debug/trace logging for better visibility

2. **tools/price_fetcher.py**
   - Added `^NSEMDCP50` to `INDIAN_INDICES` mapping
   - Added `NIFTYMIDCAP150.NS` to `INDIAN_INDICES` mapping

3. **agents/portfolio_manager_agent.py**
   - Added debug logging for performance narrative (line 739-741)

## Related Documentation

- `YFINANCE_BENCHMARK_FINDINGS.md` - Complete yfinance research and usage guide
- `tests/test_yfinance_benchmarks.py` - Comprehensive benchmark testing script
- `tests/test_benchmark_fix_standalone.py` - Verification test for the fix

## Testing

Run the portfolio manager to verify:
```bash
python examples/run_portfolio_manager.py
```

Look for these in the logs:
- ✅ `Benchmark comparison: 3/3 available` (not 0/3)
- ✅ Performance narrative with benchmark comparisons
- ✅ Alpha calculations vs each benchmark

## Next Steps

The bug is now fixed. When you run the portfolio manager:
1. All 3 benchmarks will load successfully
2. Performance narrative will include benchmark comparisons
3. LLM will receive complete context with alpha calculations
4. Manager updates will mention portfolio performance vs market indices
