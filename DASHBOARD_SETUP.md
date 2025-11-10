# Portfolio Dashboard - Complete Setup Guide

This guide covers the complete setup and running of the Portfolio Dashboard system, including backend, frontend, and automated scheduler.

## Architecture Overview

The system consists of three main components:

1. **Python Backend (FastAPI)** - REST API serving performance data, benchmarks, and manager updates
2. **Next.js Frontend** - Beautiful dashboard UI with real-time portfolio tracking
3. **Scheduler** - Automated daily price updates and metric calculations

## Prerequisites

- Python 3.9+ with uv/pip
- Node.js 18+ with npm
- All project dependencies installed

## Quick Start

### 1. Backend API (Terminal 1)

```bash
# Navigate to project root
cd D:\Projects\portfolio-agent

# Start FastAPI server
python api/price_service.py
```

Server will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs

### 2. Frontend Dashboard (Terminal 2)

```bash
# Navigate to frontend
cd D:\Projects\portfolio-agent\frontend

# Start Next.js dev server
npm run dev
```

Dashboard will be available at: http://localhost:3000

### 3. Automated Scheduler (Terminal 3 - Optional)

```bash
# Run daily scheduler
python scheduler.py --daemon
```

This runs price updates automatically at 3:45 PM IST daily.

## API Endpoints

### Performance Metrics
```
GET /api/performance/{portfolio_id}
```
Returns:
- Current portfolio value
- P&L (absolute & percentage)
- Risk metrics (volatility, Sharpe ratio, max drawdown)
- Individual stock performance

### Benchmark Comparison
```
GET /api/benchmarks/{portfolio_id}?period={1M|3M|6M|1Y|ALL}
```
Returns:
- Portfolio return for period
- Top 3 benchmark indices comparison
- Alpha (outperformance/underperformance)

### Manager Updates
```
GET /api/manager-updates/{portfolio_id}?status={PENDING|EXECUTED|IGNORED}&priority={LOW|MEDIUM|HIGH|CRITICAL}&limit={number}
```
Returns:
- AI portfolio manager daily analysis
- Rebalancing recommendations
- Affected stocks and reasoning

### Manual Price Update
```
POST /api/prices/update?portfolio_id={id}
```
Triggers immediate price update and metric recalculation.

## Frontend Features

### Dashboard (/)

**Performance Metrics Section:**
- Current Value - Live portfolio worth
- Total P&L - Absolute and percentage returns
- Day Return - Today's performance
- Sharpe Ratio - Risk-adjusted returns
- Volatility - Portfolio risk measure
- Max Drawdown - Largest decline
- Holdings Count - Number of stocks

**Benchmark Comparison:**
- Interactive period selector (1M, 3M, 6M, 1Y, ALL)
- Line chart comparing portfolio vs top 3 indices
- Color-coded cards showing:
  - Index return
  - Alpha (portfolio vs index)
  - Outperformance/underperformance status

**Latest Manager Update:**
- AI agent's most recent analysis
- Priority badge (CRITICAL/HIGH/MEDIUM/LOW)
- Recommendation (BUY_MORE/SELL/HOLD/REBALANCE)
- Affected stocks
- Confidence score with progress bar
- Link to full updates timeline

**Portfolio Holdings:**
- Grid of stock cards with entry price, targets, stop-loss
- Click to view detailed investment thesis
- Full key metrics and news sentiment

### Updates Timeline (/updates)

**Features:**
- Complete history of manager updates
- Filters by status (PENDING/EXECUTED/IGNORED)
- Filters by priority (CRITICAL/HIGH/MEDIUM/LOW)
- Grouped by date
- Expandable reasoning/analysis
- Time-based ordering

## Database Schema

### New Tables (Phase 1)

1. **daily_prices** - Stock OHLCV data
2. **index_prices** - Benchmark index values
3. **portfolio_snapshots** - Daily portfolio metrics
4. **benchmark_comparison** - Portfolio vs index for multiple periods
5. **manager_updates** - AI agent decisions
6. **user_benchmark_preferences** - User's selected indices

See `db/migrations/002_add_performance_tables.sql` for full schema.

## Scheduler Details

### Daily Workflow (3:45 PM IST)

1. Fetch prices for all active portfolios
2. Update stock prices (OHLCV from Yahoo Finance)
3. Update index prices (10 Indian indices)
4. Generate portfolio snapshot:
   - Calculate current value
   - Compute P&L
   - Calculate volatility, Sharpe ratio, max drawdown
5. Update benchmark comparisons for 5 periods (1M, 3M, 6M, 1Y, ALL)

### Manual Execution

```bash
# Test run (execute immediately, then exit)
python scheduler.py --test

# Daemon mode (run continuously with scheduled jobs)
python scheduler.py --daemon
```

## Configuration

### Backend Configuration

Create `.env` file (if not exists):
```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Supported Indian Indices

- Nifty 50 (^NSEI)
- Sensex (^BSESN)
- Nifty Midcap 100 (NIFTY_MIDCAP_100.NS)
- Nifty Smallcap 250 (NIFTYSMLCAP250.NS)
- Nifty IT (NIFTYIT.NS)
- Nifty Pharma (NIFTYPHARMA.NS)
- Nifty Auto (NIFTYAUTO.NS)
- Nifty Energy (NIFTYENERGY.NS)
- Nifty Bank (NIFTYBANK.NS)
- Nifty FMCG (NIFTYFMCG.NS)

## Troubleshooting

### Backend Won't Start

**Error**: "Port 8000 already in use"
```bash
# Find and kill process on port 8000 (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Frontend Can't Connect to Backend

**Error**: "Failed to fetch performance data"

1. Ensure backend is running: http://localhost:8000
2. Check CORS settings in `api/price_service.py`
3. Verify NEXT_PUBLIC_BACKEND_URL in `.env`

### No Data Showing

**Issue**: Empty charts/metrics

**Solution**: Run scheduler to populate data:
```bash
python scheduler.py --test
```

This will:
- Fetch latest prices
- Generate portfolio snapshot
- Calculate benchmark comparisons

### Ticker Symbol Errors

**Error**: "Quote not found for symbol: TICKER.NS"

**Cause**: Stock may be delisted or ticker incorrect

**Solution**: System uses fallback entry price automatically. To fix:
1. Find correct Yahoo Finance symbol
2. Update database:
   ```sql
   UPDATE stocks SET ticker = 'CORRECT_TICKER' WHERE ticker = 'OLD_TICKER';
   ```

### Weekend/After-Hours Index Failures

**Issue**: Some sectoral indices not fetching

**Cause**: Market closed, Yahoo Finance not returning data

**Solution**: Normal behavior. Indices will update during weekday market hours.

## Performance Metrics Explained

### Sharpe Ratio
- Formula: (Portfolio Return - Risk Free Rate) / Volatility
- Risk-free rate: 6.5% (Indian govt bonds)
- Interpretation:
  - > 1.0 = Good risk-adjusted returns
  - > 2.0 = Very good
  - > 3.0 = Excellent

### Volatility
- Annualized standard deviation of returns
- Based on daily portfolio value changes
- Calculated over 90-day period by default

### Max Drawdown
- Largest peak-to-trough decline
- Measures worst-case loss scenario
- Important for risk management

### Alpha
- Portfolio return - Benchmark return
- Positive alpha = Outperforming
- Negative alpha = Underperforming

## Development

### Backend Development

```bash
# Run API with auto-reload
uvicorn api.price_service:app --reload --port 8000
```

### Frontend Development

```bash
cd frontend
npm run dev
```

Changes to `.tsx` files will hot-reload automatically.

### Database Migrations

```bash
# Apply new migration
python db/apply_migration.py

# Check applied migrations
sqlite3 .cache/portfolio.db "SELECT * FROM schema_migrations;"
```

## Production Deployment

### Backend (FastAPI)

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn api.price_service:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend (Next.js)

```bash
cd frontend
npm run build
npm start
```

### Scheduler (System Service)

**Windows Task Scheduler:**
1. Create task to run daily at 3:45 PM
2. Action: `python D:\Projects\portfolio-agent\scheduler.py --test`

**Linux/Mac (Cron):**
```bash
# Add to crontab
45 15 * * * cd /path/to/portfolio-agent && python scheduler.py --test
```

## Data Flow

```
User → Next.js Frontend (localhost:3000)
         ↓
    Next.js API Routes (/api/performance, /api/benchmarks, /api/manager-updates)
         ↓
    FastAPI Backend (localhost:8000)
         ↓
    Tools (price_fetcher.py, performance_calculator.py)
         ↓
    Database (.cache/portfolio.db)
         ↑
    Scheduler (daily 3:45 PM IST)
```

## File Structure

```
portfolio-agent/
├── api/
│   ├── price_service.py          # FastAPI backend
│   └── test_api.py                # API test suite
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Main dashboard
│   │   │   ├── updates/page.tsx   # Updates timeline
│   │   │   └── api/               # Next.js API routes
│   │   ├── components/
│   │   │   ├── PerformanceMetrics.tsx
│   │   │   ├── BenchmarkComparison.tsx
│   │   │   ├── ManagerUpdateCard.tsx
│   │   │   ├── StockCard.tsx
│   │   │   └── StockDetailModal.tsx
│   │   └── types/index.ts         # TypeScript types
│   └── package.json
├── tools/
│   ├── price_fetcher.py           # Yahoo Finance integration
│   └── performance_calculator.py  # Metrics calculations
├── db/
│   └── migrations/
│       └── 002_add_performance_tables.sql
├── scheduler.py                   # Automated daily updates
└── DASHBOARD_SETUP.md             # This file
```

## Next Steps

1. ✅ **Phase 1 Complete**: Backend infrastructure
2. ✅ **Phase 2 Complete**: FastAPI backend + Frontend components
3. **Phase 3 (Future)**:
   - Portfolio Manager Agent daily updates
   - Rebalancing recommendations
   - Entry/exit signal generation
4. **Phase 4 (Future)**:
   - Real-time price updates via WebSocket
   - Mobile responsive design enhancements
   - Dark mode toggle

## Support

For issues or questions:
1. Check logs: `logs/portfolio_agent_*.log`
2. Review backend logs: FastAPI console output
3. Check browser console: Frontend errors
4. Database queries: Use DB Browser for SQLite

## Credits

Built with:
- FastAPI (Python backend)
- Next.js 14 (React frontend)
- Recharts (Charts)
- Tailwind CSS (Styling)
- SQLite (Database)
- yfinance (Price data)
- APScheduler (Task scheduling)
