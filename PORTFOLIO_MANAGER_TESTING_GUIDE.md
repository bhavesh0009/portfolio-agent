# Portfolio Manager Testing Guide

## Overview

This guide explains the enhanced portfolio manager system and how to test it effectively.

## What's New

### 1. Data Reset Script (`scripts/reset_manager_data.py`)

An ad-hoc script that resets portfolio manager data for testing without affecting core portfolio holdings.

**Usage:**
```bash
# Reset all data for all portfolios
python scripts/reset_manager_data.py

# Reset only aggressive portfolio
python scripts/reset_manager_data.py --profile aggressive

# Keep last 7 days of data
python scripts/reset_manager_data.py --keep-days 7

# Skip confirmation prompt
python scripts/reset_manager_data.py --confirm
```

**What it resets:**
- Manager updates (recommendations, analysis)
- Rebalancing recommendations
- Performance metrics (daily returns, portfolio values)
- Portfolio snapshots
- Benchmark comparisons
- Daily price data
- Index price data
- Market events
- Transaction history

**What it preserves:**
- Portfolio configuration
- Stock holdings (allocation, entry price, targets, stop-loss)
- Investment views (rationale, triggers)
- Key metrics snapshots

### 2. Enhanced Portfolio Manager Agent

**New capabilities:**

#### Price Persistence (`persist_daily_prices`)
- Saves today's prices to `daily_prices` table
- Enables historical price tracking and charting
- Supports OHLC format (currently all same value)

#### Portfolio Snapshots (`calculate_portfolio_snapshot`)
- Calculates total portfolio value
- Tracks returns (daily and since inception)
- Stores snapshot in `portfolio_snapshots` table
- Enables performance charting over time

**Enhanced workflow (9 steps):**
1. Load portfolio from database
2. Fetch current prices for all holdings
3. **[NEW]** Persist prices to database
4. **[NEW]** Calculate and save portfolio snapshot
5. Check stop-loss and target triggers
6. Analyze news for portfolio stocks
7. Research current market conditions
8. Generate performance context with benchmarks
9. Generate AI-powered recommendation

## Testing Strategy

### Pre-Test Cleanup

Before each test run, reset the data:

```bash
python scripts/reset_manager_data.py --profile aggressive --confirm
```

### Run Portfolio Manager

```bash
python examples/run_portfolio_manager.py
```

### Expected Output

```
================================================================================
PORTFOLIO MANAGER AGENT - Daily Portfolio Analysis
================================================================================

[1/9] Loading portfolio...
[2/9] Fetching current prices...
[3/9] Persisting daily prices...        <-- NEW
[4/9] Calculating portfolio snapshot...  <-- NEW
[5/9] Checking stop-loss and target triggers...
[6/9] Analyzing news for portfolio stocks...
[7/9] Researching current market conditions...
[8/9] Generating performance context...
[9/9] Generating portfolio recommendation...

Recommendation: HOLD/BUY_MORE/SELL/REBALANCE
Confidence: XX%
Priority: LOW/MEDIUM/HIGH/CRITICAL
```

### Database Verification

After each run, verify data was saved:

```python
from utils.db_service import get_db_service

db = get_db_service()
portfolio = db.get_active_portfolio('aggressive')
portfolio_id = portfolio['id']

# Check daily prices
prices = db.get_stock_price_history(stock_id=1, days=7)
print(f"Price history: {len(prices)} records")

# Check portfolio snapshots
snapshots = db.get_portfolio_snapshots(portfolio_id, days=7)
print(f"Snapshots: {len(snapshots)} records")

# Check manager updates
updates = db.get_manager_updates(portfolio_id, limit=5)
print(f"Recent updates: {len(updates)} records")
```

## Known Issues

### Invalid Stock Tickers

The current database may contain test stocks with invalid tickers (e.g., "543709", "TEST"). These cause price fetching to fail.

**Solution:**

1. **Option A - Clean Database:**
   ```sql
   -- Remove test stocks
   DELETE FROM stocks WHERE ticker IN ('543709', '543787', 'TEST', 'SSEGL');
   ```

2. **Option B - Run with Valid Portfolio:**
   ```bash
   # First, build a fresh portfolio with real stocks
   python examples/run_portfolio_builder.py

   # Then run manager
   python examples/run_portfolio_manager.py
   ```

### Migration Warning

You may see: `Use PostgREST methods instead of raw SQL`

This is harmless - the migration utility tries to run raw SQL which Supabase doesn't support. The portfolio loads correctly from PostgREST methods.

## Multi-Run Testing Schedule

Simulate end-of-day runs multiple times:

```bash
#!/bin/bash
# test_manager_schedule.sh

echo "=== Run 1: Morning (9:30 AM) ==="
python scripts/reset_manager_data.py --profile aggressive --confirm
python examples/run_portfolio_manager.py
sleep 5

echo "=== Run 2: Afternoon (2:30 PM) ==="
python scripts/reset_manager_data.py --profile aggressive --confirm
python examples/run_portfolio_manager.py
sleep 5

echo "=== Run 3: End of Day (3:30 PM) ==="
python scripts/reset_manager_data.py --profile aggressive --confirm
python examples/run_portfolio_manager.py
```

## Frontend Integration

After successful manager runs, view results on the dashboard:

```bash
cd frontend
npm run dev
```

Navigate to:
- **Portfolio Overview**: See current value, returns
- **Performance Charts**: View daily returns over time
- **Manager Updates**: See AI recommendations
- **Stock Cards**: Check stop-loss/target status

## Next Steps

### Frontend Enhancements

1. **Performance Charts:**
   - Line chart for portfolio value over time
   - Bar chart for daily returns
   - Sector allocation pie chart

2. **Manager Updates Feed:**
   - Timeline view of recommendations
   - Priority badges (LOW/MEDIUM/HIGH/CRITICAL)
   - Action buttons (Acknowledge/Execute/Ignore)

3. **Real-time Data:**
   - Live price updates every 5 minutes
   - Auto-refresh dashboard
   - WebSocket integration

### Backend Enhancements

1. **Benchmark Tracking:**
   - Fetch Nifty 50 daily prices
   - Calculate alpha, beta
   - Store in `benchmark_comparison` table

2. **Index Price Service:**
   - Automated index price fetching
   - Daily cron job integration

3. **Rebalancing Engine:**
   - Detect portfolio drift
   - Generate rebalancing recommendations
   - Calculate optimal allocation adjustments

## Configuration

### Testing Configuration (`config.ini`)

```ini
[PORTFOLIO]
max_stocks = 15
initial_capital = 500000
investor_profile = aggressive

[TESTING]
# Use shorter lookback for faster testing
news_lookback_period = 7

# Disable expensive operations during testing
check_news_for_shortlisted = false
fetch_all_pages = false
max_pages = 1
```

### Environment Variables

```bash
# Use faster models for testing
export GEMINI_TEST_MODEL=gemini-2.5-flash

# Increase log verbosity
export LOG_LEVEL=DEBUG
```

## Troubleshooting

### Issue: Portfolio not found

**Solution:**
```bash
# Check if portfolio exists
python -c "from utils.db_service import get_db_service; db = get_db_service(); print(db.get_active_portfolio('aggressive'))"

# If None, build a fresh portfolio
python examples/run_portfolio_builder.py
```

### Issue: Price fetching timeout

**Solution:**
- Reduce stock count in portfolio
- Use cached prices (add caching to price_fetcher)
- Fetch prices in parallel (add async support)

### Issue: Performance context generation fails

**Solution:**
- Ensure at least one daily_prices record exists
- Ensure at least one portfolio_snapshot exists
- Check index_prices table has data

## Success Criteria

Portfolio manager testing is successful when:

- ✅ All 9 steps complete without errors
- ✅ Daily prices saved for all stocks
- ✅ Portfolio snapshot created with correct values
- ✅ Manager update stored in database
- ✅ Recommendation is sensible and confident (>60%)
- ✅ Frontend displays updated data correctly
- ✅ Multiple runs show progression over time
- ✅ Database tables populated correctly

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review database tables in Supabase dashboard
- Consult `CLAUDE.md` for architecture details
