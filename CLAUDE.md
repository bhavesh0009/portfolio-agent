# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Portfolio Agent is a highly autonomous multi-agent system for building and maintaining equity portfolios in Indian markets. The system leverages screener.in (335+ financial ratios), Google News for market analysis, and Gemini-powered AI agents that autonomously plan and execute investment decisions.

### Core Agent Architecture

**Portfolio Builder Agent** - Initial portfolio construction (one-time execution)
- Builds initial portfolio based on user inputs: investor profile (aggressive/defensive), deployed capital, risk tolerance
- Conducts comprehensive market research and stock screening
- Allocates capital across selected stocks according to profile-specific strategies

**Portfolio Manager Agent** - Ongoing portfolio management (daily/scheduled execution)
- Monitors existing portfolio performance and market conditions
- Executes timely rebalancing based on position drift and allocation targets
- Manages entry signals for new positions and exit signals for existing holdings
- Adapts to changing market dynamics while maintaining risk parameters

## Setup Commands

```bash
# Install dependencies
uv pip sync requirements.txt

# Install Playwright browsers (required for web automation)
playwright install chromium

# Configure credentials (required before first run)
copy .env.example .env  # Then edit .env with your screener.in credentials and Gemini API key

# Required environment variables:
# - SCREENER_EMAIL, SCREENER_PASSWORD: screener.in credentials
# - GEMINI_API_KEY: Google AI Studio API key
# - GEMINI_HIGH_MODEL: Most capable model for complex reasoning (e.g., gemini-2.5-pro)
# - GEMINI_MID_MODEL: Balanced model, default for most agents (e.g., gemini-2.5-flash)
# - GEMINI_LOW_MODEL: Lightweight model for simple tasks (e.g., gemini-2.5-flash-lite)
# - LOG_LEVEL: Logging verbosity (TRACE, DEBUG, INFO, WARNING, ERROR) - Default: TRACE
# - LOG_TO_CONSOLE: Enable console output (true/false) - Default: true
# - LOG_DIR: Directory for log files - Default: logs
```

## Logging System

The project uses a comprehensive logging system that writes detailed logs to timestamped files while maintaining dual output (console + file).

### Log Files

- **Location**: `logs/` directory
- **Naming**: `portfolio_agent_YYYYMMDD_HHMMSS.log` (unique per run)
- **Purpose**: Complete execution trace for debugging and auditing

### Log Levels

The system uses five log levels (from most to least verbose):
- **TRACE**: Very detailed output including full API responses, iteration details, internal state
- **DEBUG**: Detailed diagnostic information, parameter values, intermediate results
- **INFO**: General informational messages about program execution and progress
- **WARNING**: Warning messages for recoverable issues
- **ERROR**: Error messages for failures and exceptions

### Configuration

Set logging behavior via environment variables in `.env`:
```bash
LOG_LEVEL=TRACE          # TRACE | DEBUG | INFO | WARNING | ERROR
LOG_TO_CONSOLE=true      # true | false
LOG_DIR=logs             # Directory path
```

### Smart Preview Handling

Long text content (API responses, article content, etc.) is handled intelligently:
- **Console**: Shows truncated preview (e.g., first 300 characters)
- **Log File**: Contains full untruncated content

This allows clean console output while preserving complete data for debugging.

### Finding Logs

Each run creates a new log file in chronological order:
```bash
logs/portfolio_agent_20250126_143022.log
logs/portfolio_agent_20250126_151545.log
logs/portfolio_agent_20250126_162301.log
```

Latest logs appear at the bottom when sorted alphabetically.

## Running Examples

```bash
# Portfolio builder agent (one-time initial build) - RECOMMENDED
python examples/run_portfolio_builder.py

# Portfolio manager agent (daily/scheduled management)
python examples/run_portfolio_manager.py

# Individual specialized agents (called by orchestrators)
python examples/run_stock_screening.py
python examples/run_stock_news.py
python -c "from agents.market_research_agent import run_market_research; run_market_research('Indian IT sector trends')"

# Direct tool usage
python examples/main.py
```

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
python tests/test_ai_agent_usage.py
```

## Architecture Overview

### Three-Tier Agent Hierarchy

**Tier 1: Portfolio Orchestrator Agents**
- `portfolio_builder_agent_simple.py` - Initial portfolio construction with minimal prompting for maximum flexibility (one-time execution) **[PRIMARY]**
- `portfolio_builder_agent.py` - DEPRECATED: Legacy detailed workflow version (use simple version instead)
- `portfolio_manager_agent.py` - Ongoing portfolio management for rebalancing, entry/exit decisions (scheduled/daily execution)

**Tier 2: Specialized Analysis Agents** (called by portfolio orchestrators)
- `stock_screening_agent.py` - Screens stocks from screener.in using fundamentals
- `stock_news_agent.py` - Analyzes news/sentiment for specific stocks/companies
- `market_research_agent.py` - Researches Indian market trends, sectors, economics

**Tier 3: Tools** (called by agents)
- Stock screening: `screen_stocks.py`, `screener_session.py`, `column_manager.py`, `result_manager.py`
- News analysis: `news_scraper.py`, `article_extractor.py`

### Data Flow

```
Initial Build (One-time):
User Input (profile, capital)
  → Portfolio Builder Agent
    → Market Research Agent → news_scraper.py (market trends, sector analysis)
    → Stock Screening Agent → screen_stocks.py → screener_session.py (Playwright automation)
                                               → column_manager.py (name mapping/validation)
                                               → result_manager.py (storage/analysis)
    → Stock News Agent → news_scraper.py (Google News API)
                       → article_extractor.py (newspaper4k)
    → Final Output: Initial portfolio allocation with stock recommendations

Ongoing Management (Daily/Scheduled):
Trigger (scheduled job)
  → Portfolio Manager Agent
    → Fetch current portfolio state (.cache/portfolio_state_*.json)
    → Stock Screening Agent → Re-screen existing holdings + new opportunities
    → Stock News Agent → Monitor news for portfolio positions
    → Market Research Agent → Track market/sector changes
    → Decision: Rebalance/Entry/Exit signals
    → Update portfolio state
```

### Key Architectural Patterns

**Agent Communication:** Agents use JSON-based tool calling with Gemini API. Each agent:
1. Receives natural language query
2. Plans actions using internal reasoning
3. Calls tools via JSON format: `{"action": "call_tool", "tool": "...", "parameters": {...}}`
4. Iterates up to max_iterations until producing: `{"action": "final_answer", "answer": "..."}`

**Result Management:** When `screen_stocks.py` returns >30 results (configurable):
- Full results saved to `.cache/screening_results/`
- Returns 30-stock sample + statistical analysis
- Agent receives `is_sampled: true` flag with analysis insights

**Column Name Mapping:** screener.in has two name types:
- Configuration names: "Sales growth 3Years", "Return on equity"
- Table headers: "Sales Var 3Yrs %", "ROE %"
- `column_manager.py` handles all mapping/validation with fuzzy search

**Session Management:**
- Playwright saves auth to `.playwright-mcp/auth.json`
- Sessions persist across runs
- Auto-relogin on expiration

## Configuration

### config.ini Settings

`config.ini` controls:
- Portfolio settings: `max_stocks`, `initial_capital`, `investor_profile` (aggressive/defensive)
- Allocation strategies: Different percentages for aggressive vs defensive
- News validation: `news_lookback_period`, `check_news_for_shortlisted`
- Screener pagination: `fetch_all_pages`, `max_pages`, `page_delay`
- Result management: `max_results_to_return`, `enable_result_storage`, `enable_data_analysis`

### Gemini Model Tiers

The system uses three Gemini model tiers for cost-performance optimization:

**GEMINI_HIGH_MODEL** (e.g., gemini-2.5-pro)
- Use case: Portfolio orchestrator agents requiring complex multi-step reasoning
- Agents: Portfolio Builder, Portfolio Manager (future)
- Characteristics: Most capable, highest cost, best for strategic decision-making

**GEMINI_MID_MODEL** (e.g., gemini-2.5-flash) - Default
- Use case: Specialized analysis agents with moderate complexity
- Agents: Stock Screening, Stock News, Market Research
- Characteristics: Balanced performance and cost, handles structured tasks well

**GEMINI_LOW_MODEL** (e.g., gemini-2.5-flash-lite)
- Use case: Simple repetitive tasks, data extraction, summary generation
- Agents: Future utility agents, batch processing tasks
- Characteristics: Fastest, lowest cost, suitable for high-volume operations

All agents default to `GEMINI_MID_MODEL` and can be overridden via constructor `model_name` parameter.

**Centralized LLM Service:** All agents delegate LLM calls to `utils/llm_service.py` (GeminiService singleton) for unified client management, retry logic, and error handling. Model resolution follows priority order: `GEMINI_TEST_MODEL` env var → agent tier → environment defaults. Easy model testing across all agents: `export GEMINI_TEST_MODEL=gemini-2.5-pro` then run agents. See `examples/test_llm_service.py` for testing and switching model scenarios.

## Important Implementation Details

### Column Names in Queries

**ALWAYS use exact configuration names in queries and column lists:**
- ✅ "Market Capitalization" (NOT "market capitalization" or "Market Cap")
- ✅ "Return on equity" (NOT "ROE" or "ROE %")
- ✅ "Sales growth 3Years" (NOT "Sales growth 3years")

Case-sensitive and spacing matters. See `data/column_name_mapping.json` for full mappings.

### Industry and Sector Enrichment

**Industry and Sector are enriched via yfinance, not screener.in:**

screener.in does not support "Industry" or "Sector" as queryable or configurable columns. However, the system automatically enriches stock results with industry and sector data from yfinance when:
- Industry or Sector is requested in the columns list
- Industry filters are present in the query

**How it works:**
1. **Query preprocessing**: Industry filter conditions are detected and removed from the query sent to screener.in
   - Example: `Market Cap > 5000 AND Industry = "Hotels"` becomes `Market Cap > 5000`
2. **Symbol extraction**: NSE/BSE symbols are extracted from company links in screener.in results
   - NSE symbols: Alphabetic (e.g., WAAREEENER → WAAREEENER.NS)
   - BSE symbols: Numeric (e.g., 539337 → 539337.BO)
3. **yfinance enrichment**: Industry and Sector data fetched for each stock
   - In-memory session caching prevents repeated API calls
   - Failures set industry/sector to 'Unknown' gracefully
4. **Post-filtering**: Results are filtered by industry criteria after enrichment

**Agent usage:**
```python
# This will work correctly - Industry filter is handled automatically
screen_stocks(
    query="Market Cap > 5000 AND Industry = 'Hotels'",
    columns=["Name", "Market Capitalization", "Industry", "Sector"]
)
```

**Log visibility:**
- Query transformation: "Cleaned query: Market Cap > 5000"
- Enrichment progress: "Enriching 293 stocks with industry and sector data"
- Post-filtering: "Post-filtered: 293 -> 15 stocks"
- Cache statistics: "yfinance cache stats: 50 hits, 243 misses (17.1% hit rate)"

### Agent Prompt Philosophy

**Portfolio Builder Agent (PRIMARY):**
- **portfolio_builder_agent_simple.py**: "Use your judgment" minimal prompting for maximum flexibility
- Provides high-level objectives and available tools
- Lets the agent autonomously decide research approach, query strategy, and allocation method
- Recommended for production use

**Legacy (DEPRECATED):**
- **portfolio_builder_agent.py**: Prescriptive, detailed workflow steps
- Kept for reference/backwards compatibility but no longer actively maintained
- Use simple version instead

### Portfolio Builder → Manager Guidance System

**Purpose:** Portfolio builder provides comprehensive per-stock guidance for the portfolio manager to use in ongoing portfolio management and rebalancing decisions.

**Per-Stock Guidance Fields:**

Each stock in the portfolio includes:

```json
{
  "name": "Stock Name",
  "ticker": "SYMBOL",
  "entry_price": float,          // CMP at time of selection
  "allocation_pct": float,       // Initial allocation percentage
  "allocation_amount": float,    // Initial allocation amount in INR
  "stop_loss_pct": float,        // Stop-loss as percentage decline (e.g., -15.0)
  "stop_loss_price": float,      // Stop-loss absolute price (entry_price * (1 - stop_loss_pct/100))
  "target_pct": float,           // Target as percentage gain (e.g., +50.0)
  "target_price": float,         // Target absolute price (entry_price * (1 + target_pct/100))
  "investment_view": {
    "market_outlook": "string",  // Market conditions at time of selection
    "stock_rationale": "string", // Why stock fits investor profile
    "holding_period": "string",  // Recommended duration (e.g., "6-12 months")
    "exit_triggers": ["..."],    // Conditions that invalidate thesis
    "review_triggers": ["..."]   // Conditions requiring reassessment
  },
  "rationale": "string",         // Selection reasoning
  "key_metrics": {},             // Fundamental metrics from screening
  "news_sentiment": "string",    // News sentiment at time of selection
  "sector": "string"             // Stock sector
}
```

**Calculation Methodology:**

Stop-loss and target values are calculated based on investor profile:

**Aggressive Profile:**
- Stop-loss: -15% (maximum acceptable loss)
- Target range: 40-60% (growth potential)

**Defensive Profile:**
- Stop-loss: -8% (capital preservation)
- Target range: 15-25% (steady gains)

**Configuration:**

Risk parameters are defined in `config.ini` [RISK_PARAMETERS] section:
```ini
[RISK_PARAMETERS]
aggressive_stop_loss_pct = 15
defensive_stop_loss_pct = 8
aggressive_target_min_pct = 40
aggressive_target_max_pct = 60
defensive_target_min_pct = 15
defensive_target_max_pct = 25
```

**Portfolio Persistence:**

Final portfolios are saved to `.cache/portfolios/` with:
- **Timestamped file**: `portfolio_{profile}_{timestamp}.json` - Historical record
- **Latest pointer**: `latest_{profile}.json` - Latest portfolio for quick access

Portfolio manager uses the latest pointer to load current holdings and guidance.

**Manager Usage:**

The Portfolio Manager Agent uses this guidance to:
1. Monitor positions against stop-loss/target prices
2. Evaluate if investment view triggers have been breached
3. Reassess positions based on exit/review triggers
4. Generate rebalancing recommendations
5. **Override capability**: Manager can override guidance with strong justification logged

**Example:**
```
Entry: Rs. 100
Stop-loss (-15%): Rs. 85
Target (+50%): Rs. 150
Action: Manager monitors current price vs these levels
         If price hits Rs. 85 or below → Consider stop-loss
         If price hits Rs. 150 → Consider profit booking
         If "quarterly revenue growth falls below 20%" → Review holding
```

### Caching Strategy

Agents use MD5-based query caching in `_agent_cache` dict:
```python
cache_key = hashlib.md5(f"{agent}:{query}".encode()).hexdigest()
```
Prevents redundant API calls during multi-turn conversations.

### State Persistence

**Intermediate State** (for resume capability):
- Portfolio builders save state to `.cache/simple_portfolio_state_*.json` during building
- Allows resume on API failures/timeouts without restarting
- Contains: agent cache, conversation history, iteration results

**Final Portfolio State** (for portfolio manager):
- Completed portfolios saved to `.cache/portfolios/portfolio_*.json`
- Contains: Complete stock list with guidance, entry prices, stop-loss/target levels
- Latest portfolio accessible via `.cache/portfolios/latest_{profile}.json` pointer
- Used by Portfolio Manager Agent for ongoing management and rebalancing

## Common Pitfalls

1. **Column name mismatches**: Always validate column names through `column_manager.py`
2. **Missing credentials**: Agents fail silently without `.env` - check SCREENER_EMAIL/PASSWORD and GEMINI_API_KEY
3. **Playwright not installed**: `playwright install chromium` must run after pip install
4. **Result sampling confusion**: Check `is_sampled` flag - you're seeing a sample, not full results
5. **Agent iteration limits**: Default max_iterations=10-15 - increase for complex multi-step queries

## File Naming Conventions

Recent refactoring established clear naming:
- `*_screening_agent.py` - Fundamental analysis
- `*_news_agent.py` - Stock-specific news
- `*_research_agent.py` - Market-wide research
- No "_simple" suffixes on tools (removed from screener_session.py)

Backward compatibility maintained via deprecated function aliases (e.g., `run_stock_agent()` → `run_stock_screening()`).

## Frontend Dashboard

A beautiful Next.js web dashboard for visualizing and tracking your AI-powered portfolio.

### Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view your portfolio.

### Features

**Portfolio Overview:**
- Total capital and allocation summary
- Sector distribution chart
- Profile badge (Aggressive/Defensive)
- Real-time portfolio statistics

**Interactive Stock Cards:**
- Entry price, target, and stop-loss
- Allocation percentages and amounts
- Key metrics (ROCE, ROE, D/E)
- Investment rationale preview
- Click to view full details

**Stock Detail Modal:**
- Complete investment thesis
- Market outlook and stock rationale
- Holding period recommendations
- Exit and review triggers
- Full financial metrics
- News sentiment analysis

### Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling with custom animations
- **better-sqlite3** - SQLite database access
- **Lucide React** - Beautiful icons

### Database Connection

The frontend reads from `../.cache/portfolio.db` using better-sqlite3.

API Routes:
- `GET /api/portfolio` - Active portfolio with stocks and stats
- `GET /api/portfolio/[id]` - Specific portfolio by ID
- `GET /api/stocks/[id]` - Detailed stock information

### File Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── page.tsx          # Main dashboard
│   │   └── layout.tsx        # Root layout
│   ├── components/
│   │   ├── PortfolioOverview.tsx
│   │   ├── StockCard.tsx
│   │   └── StockDetailModal.tsx
│   ├── lib/
│   │   ├── db.ts             # Database utilities
│   │   └── utils.ts          # Helper functions
│   └── types/
│       └── index.ts          # TypeScript types
├── package.json
├── SETUP.md                  # Setup guide
└── FEATURES.md               # Feature documentation
```

### Documentation

- `frontend/SETUP.md` - Installation and setup guide
- `frontend/FEATURES.md` - Detailed feature overview and design specs

## TODO / Future Scope

**Completed:**
- [x] Portfolio Builder → Manager Guidance System (stop-loss, target, investment views per stock)
- [x] Per-stock guidance fields in portfolio output
- [x] Portfolio persistence to `.cache/portfolios/`
- [x] SQLite database for portfolio storage
- [x] Frontend dashboard with Next.js and TypeScript
- [x] Beautiful UI with Tailwind CSS and animations
- [x] Interactive stock cards and detail modals
- [x] API routes for portfolio data access

**Explored but Deferred (Phase 2):**
- RSS Feed Integration (Nov 2, 2025): Investigated RSS feeds for Indian financial news as alternative to Google News. Found most major publishers (ET, Moneycontrol, Business Standard, Mint, etc.) have broken/malformed RSS feeds or are geographically blocked. Google News remains primary source with source reliability guidance in agent prompts.

**Near-term priorities:**
- [ ] Implement Portfolio Manager Agent for daily portfolio monitoring and management
  - Load latest portfolio from `.cache/portfolios/latest_{profile}.json`
  - Monitor stop-loss/target breaches with live price data
  - Evaluate investment view triggers and market changes
  - Generate rebalancing recommendations
  - Support manager overrides with justification logging
- [ ] Add scheduled execution framework (cron/task scheduler integration)
- [ ] Build rebalancing logic with position drift detection and allocation adjustment
- [ ] Implement entry/exit signal generation based on fundamental changes
- [ ] Real-time price updates in frontend dashboard
- [ ] Performance tracking charts (Recharts integration)
- [ ] Dark mode toggle for frontend
