# Portfolio Agent - Complete Quick Start Guide

## Overview

This system consists of two parts:
1. **Backend**: Python-based AI agents that build and manage portfolios
2. **Frontend**: Next.js dashboard to visualize and track portfolios

## Prerequisites

- Python 3.8+ with uv package manager
- Node.js 18+ and npm
- screener.in account (for stock screening)
- Google Gemini API key (for AI agents)

## Step 1: Backend Setup

### 1.1 Install Python Dependencies

```bash
# Install dependencies
uv pip sync requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 1.2 Configure Environment

```bash
# Copy example env file
copy .env.example .env

# Edit .env and add your credentials:
# SCREENER_EMAIL=your@email.com
# SCREENER_PASSWORD=yourpassword
# GEMINI_API_KEY=your-gemini-api-key
```

### 1.3 Build Your First Portfolio

```bash
# Run the portfolio builder agent
python agents/portfolio_builder_agent_simple.py
```

This will:
- Research Indian markets
- Screen stocks based on fundamentals
- Analyze news and sentiment
- Build a diversified portfolio
- Save to `.cache/portfolios/` (JSON) and `.cache/portfolio.db` (SQLite)

**Expected output:**
- Portfolio with 5-10 stocks
- Each stock with entry price, allocation, stop-loss, target
- Investment thesis and triggers
- Full financial metrics

**Duration**: 5-15 minutes depending on API speeds

## Step 2: Frontend Setup

### 2.1 Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 2.2 Test Database Connection

```bash
node test-db.js
```

You should see:
```
[SUCCESS] Database connection established!
Found 1 portfolio(s): ID 1: aggressive (20251108_100354)
Total stocks: 7
```

### 2.3 Start Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## What You'll See

### Portfolio Overview (Top)
- **Total Capital**: Rs. 5,00,000
- **Total Stocks**: 7 positions
- **Top Sector**: Renewable Energy (28%)
- **Sector Distribution**: Visual breakdown

### Stock Cards (Grid)
Each card shows:
- Stock name and ticker (e.g., "Waaree Energies - WAREE")
- Sector badge
- Allocation: 15% (Rs. 75,000)
- Entry Price: Rs. 3,500
- Target: Rs. 5,250 (+50%)
- Stop Loss: Rs. 2,975 (-15%)
- Key Metrics: ROCE 34.94%, ROE 27.42%, D/E 0.26

### Click Any Stock
Opens detailed modal with:
- Full investment thesis
- Market outlook
- Exit triggers (when to sell)
- Review triggers (when to reassess)
- All financial metrics
- News sentiment

## Project Structure

```
portfolio-agent/
├── agents/                          # AI agents
│   ├── portfolio_builder_agent_simple.py   # Main builder
│   ├── stock_screening_agent.py            # Stock screener
│   ├── stock_news_agent.py                 # News analyzer
│   └── market_research_agent.py            # Market researcher
├── tools/                           # Data tools
│   ├── screen_stocks.py             # screener.in integration
│   ├── news_scraper.py              # Google News scraper
│   └── industry_scraper.py          # Industry data
├── utils/                           # Utilities
│   ├── db_service.py                # Database operations
│   └── llm_service.py               # Gemini API client
├── .cache/                          # Data storage
│   ├── portfolio.db                 # SQLite database
│   └── portfolios/                  # JSON backups
├── frontend/                        # Web dashboard
│   ├── src/
│   │   ├── app/                     # Next.js app
│   │   ├── components/              # React components
│   │   ├── lib/                     # Database utilities
│   │   └── types/                   # TypeScript types
│   └── package.json
└── CLAUDE.md                        # Project documentation
```

## Common Workflows

### Build a New Portfolio

```bash
# 1. Run builder agent
python agents/portfolio_builder_agent_simple.py

# 2. Check the output
# JSON: .cache/portfolios/latest_aggressive.json
# Database: .cache/portfolio.db

# 3. View in dashboard
cd frontend
npm run dev
```

### View Existing Portfolio

```bash
# 1. Start frontend
cd frontend
npm run dev

# 2. Open browser
# http://localhost:3000

# 3. Click any stock for details
```

### Test Individual Agents

```bash
# Stock screening
python examples/run_stock_screening.py

# Stock news
python examples/run_stock_news.py

# Market research
python -c "from agents.market_research_agent import run_market_research; run_market_research('Indian IT sector trends')"
```

## Data Storage

### Dual Storage System

**JSON Files** (`.cache/portfolios/`):
- Human-readable backup
- Easy to inspect
- Git-friendly (optional)

**SQLite Database** (`.cache/portfolio.db`):
- Queryable with SQL
- Used by frontend
- Relational structure

### Database Schema

```
portfolios          → Portfolio metadata
├── stocks          → Stock positions
├── investment_views → Investment thesis per stock
├── key_metrics     → Financial metrics
└── (future tables) → transactions, performance, rebalancing
```

## Troubleshooting

### "No active portfolio found"
**Cause**: Database is empty
**Fix**: Run `python agents/portfolio_builder_agent_simple.py`

### "Database connection failed"
**Cause**: Wrong path or missing database
**Fix**: Check `.cache/portfolio.db` exists, run `node frontend/test-db.js`

### "Import error: No module named..."
**Cause**: Missing Python dependencies
**Fix**: Run `uv pip sync requirements.txt`

### Frontend shows errors
**Cause**: Missing Node modules
**Fix**: Run `cd frontend && npm install`

### Playwright browser not found
**Cause**: Chromium not installed
**Fix**: Run `playwright install chromium`

## Configuration Files

### `.env` (Backend)
```
SCREENER_EMAIL=your@email.com
SCREENER_PASSWORD=yourpassword
GEMINI_API_KEY=your-api-key
GEMINI_HIGH_MODEL=gemini-2.5-pro
GEMINI_MID_MODEL=gemini-2.5-flash
LOG_LEVEL=INFO
```

### `config.ini` (Backend)
```
[PORTFOLIO]
max_stocks = 10
initial_capital = 500000
investor_profile = aggressive

[RISK_PARAMETERS]
aggressive_stop_loss_pct = 15
aggressive_target_min_pct = 40
```

## Next Steps

1. **Run Portfolio Manager** (when implemented):
   ```bash
   python agents/portfolio_manager_agent.py
   ```

2. **Add Real-time Prices**:
   - Integrate NSE/BSE API
   - Update frontend to show current prices
   - Calculate P&L

3. **Performance Tracking**:
   - Add daily snapshots
   - Build charts with Recharts
   - Track cumulative returns

4. **Alerts & Notifications**:
   - Email/SMS on stop-loss breach
   - Target achievement alerts
   - News sentiment changes

## Support

- **Documentation**: See `CLAUDE.md` for full details
- **Frontend Guide**: See `frontend/SETUP.md`
- **Features**: See `frontend/FEATURES.md`

## Example Output

### Portfolio Builder Log
```
[INFO] Starting portfolio builder for AGGRESSIVE profile
[INFO] Capital: Rs. 500,000
[INFO] Researching market trends...
[INFO] Screening stocks...
[INFO] Found 127 stocks matching criteria
[INFO] Analyzing news for shortlisted stocks...
[INFO] Building portfolio with 7 stocks
[INFO] Saved to: .cache/portfolios/portfolio_aggressive_20251108_100354.json
[INFO] Saved to database: Portfolio ID 1
```

### Frontend Dashboard
```
Total Capital: Rs. 5,00,000
Total Stocks: 7
Top Sector: Renewable Energy (28%)

Stocks:
1. Waaree Energies (WAREE) - 15% - Rs. 75,000
2. Zen Technologies (ZENTEC) - 15% - Rs. 75,000
3. KPIT Technologies (KPITTECH) - 15% - Rs. 75,000
... (4 more)
```

## License

MIT License - See main project for details.
