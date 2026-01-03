# Quick Portfolio Manager Testing Guide

## Overview

Portfolio manager now automatically handles multiple runs per day using UPSERT. No cleanup needed between runs!

## Key Changes

✅ **ALWAYS uses latest portfolio** - No profile parameter needed
✅ **UPSERT for daily data** - Can run multiple times per day without errors
✅ **Auto-activates newest portfolio** - Latest portfolio is always active

## Quick Commands

### 1. Run Portfolio Manager (Anytime)

```bash
python examples/run_portfolio_manager.py
```

**What it does:**
- Loads latest portfolio (ID 42 with INFY, HDFCAMC, etc.)
- Fetches current prices
- **Updates** today's prices (upsert - no duplicates!)
- **Updates** today's portfolio snapshot
- Analyzes news and generates recommendations

**Can run multiple times per day** - Each run updates the same records for today.

### 2. Check Current Portfolio Status

```bash
python scripts/check_portfolios.py
```

**Shows:**
- All portfolios in database
- Which one is active (✅)
- Stock counts and sample tickers

### 3. Ensure Latest is Active (Optional - Auto-runs)

```bash
python scripts/ensure_latest_portfolio_active.py
```

**Use this if:**
- You created a new portfolio
- Want to verify latest is active
- Need to switch active portfolio

### 4. Reset Data for Fresh Testing (Optional)

Only needed if you want to **clear all historical data** for clean testing:

```bash
# Reset all manager data (keeps portfolio)
python scripts/reset_manager_data.py --confirm

# Keep last 7 days
python scripts/reset_manager_data.py --keep-days 7 --confirm
```

**Deletes:**
- Manager updates
- Performance metrics
- Daily prices
- Snapshots

**Preserves:**
- Portfolio configuration
- Stock holdings
- Investment views

## Typical Testing Workflow

### Normal Daily Run (No cleanup needed)

```bash
# Run once or multiple times - no errors!
python examples/run_portfolio_manager.py
```

### Testing with Fresh State

```bash
# 1. Clear historical data
python scripts/reset_manager_data.py --confirm

# 2. Run portfolio manager
python examples/run_portfolio_manager.py

# 3. Run again (updates same records)
python examples/run_portfolio_manager.py
```

## Expected Output

```
================================================================================
PORTFOLIO MANAGER AGENT - Daily Portfolio Analysis
================================================================================

[1/9] Loading latest portfolio...
[INFO] Loading latest active portfolio from database
[INFO] Managing portfolio ID: 42 (Profile: aggressive)
[INFO] Portfolio loaded: 15 stocks, Rs. 500,000 capital

[2/9] Fetching current prices...
[INFO] Fetched prices for 15 stocks

[3/9] Persisting daily prices...
[INFO] Saved 15/15 price records  ← UPDATES if already exists

[4/9] Calculating portfolio snapshot...
[INFO] Portfolio snapshot saved   ← UPDATES if already exists
[INFO]   Total Value: Rs. 525,000
[INFO]   Total Return: +5.0%
[INFO]   Day Return: +0.5%

[5/9] Checking stop-loss and target triggers...
[INFO] Stop-loss breaches: 0
[INFO] Targets reached: 0

[6/9] Analyzing news for portfolio stocks...
[INFO] Analyzed news for 15 stocks

[7/9] Researching current market conditions...
[INFO] Market research complete

[8/9] Generating performance context...
[INFO] Performance context generated

[9/9] Generating portfolio recommendation...
[INFO] Recommendation: HOLD
[INFO] Confidence: 85%
[INFO] Priority: MEDIUM
```

## Troubleshooting

### Issue: "No active portfolio found"

**Solution:**
```bash
python scripts/ensure_latest_portfolio_active.py
```

### Issue: Old test stocks appearing

**Check which portfolio is active:**
```bash
python scripts/check_portfolios.py
```

**Fix if wrong portfolio is active:**
```bash
# Make portfolio 42 active
python scripts/fix_active_portfolio.py --set-active 42 --profile aggressive
```

### Issue: Want to start fresh for the day

**Reset today's data:**
```bash
python scripts/reset_manager_data.py --confirm
```

## Production Schedule

### Recommended: Daily at Market Close

```bash
# Add to crontab (3:30 PM IST daily)
30 15 * * 1-5 cd /path/to/portfolio-agent && python examples/run_portfolio_manager.py >> logs/cron.log 2>&1
```

### With Auto-activation

```bash
# Ensure latest portfolio is always active
0 9 * * * cd /path/to/portfolio-agent && python scripts/ensure_latest_portfolio_active.py
```

## Key Differences from Before

| Before | Now |
|--------|-----|
| `--profile aggressive` required | No parameter needed |
| `load_portfolio(profile)` | `load_portfolio()` - always latest |
| Errors on duplicate prices | UPSERT - updates existing |
| Manual portfolio activation | Auto-activates latest |
| Profile-based selection | Time-based (latest created_at) |

## Files Reference

- `examples/run_portfolio_manager.py` - Main script (no args needed)
- `scripts/check_portfolios.py` - List all portfolios
- `scripts/ensure_latest_portfolio_active.py` - Auto-activate latest
- `scripts/reset_manager_data.py` - Clear testing data
- `scripts/auto_activate_latest.py` - Hook for portfolio builder

## Success Indicators

✅ Loads portfolio 42 (with INFY, HDFCAMC)
✅ No duplicate key errors
✅ Prices update successfully (15/15)
✅ Snapshot updates successfully
✅ Generates recommendation
✅ Stores manager update in database

## Next Steps

After successful portfolio manager run:

1. **View on Dashboard:**
   ```bash
   cd frontend && npm run dev
   # Open http://localhost:3000
   ```

2. **Check Database:**
   - View latest manager update
   - See portfolio performance
   - Track price history

3. **Schedule Daily Runs:**
   - Add to crontab
   - Monitor logs
   - Set up alerts for critical recommendations

---

**Questions?** Check logs in `logs/` directory for detailed execution trace.
