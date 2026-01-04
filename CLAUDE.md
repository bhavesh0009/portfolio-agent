# Portfolio Agent - AI-Powered Equity Portfolio Management

Multi-agent system for building and maintaining equity portfolios in Indian markets using screener.in (335+ financial ratios), Google News, and Gemini AI agents.

## Setup Commands

```bash
# Install dependencies
uv pip sync requirements.txt
playwright install chromium

# Configure credentials
cp .env.example .env  # Edit with screener.in credentials and Gemini API key

# Required environment variables
SCREENER_EMAIL, SCREENER_PASSWORD     # screener.in credentials
GEMINI_API_KEY                        # Google AI Studio API key
GEMINI_HIGH_MODEL=gemini-2.5-pro      # Portfolio orchestrator (complex reasoning)
GEMINI_MID_MODEL=gemini-2.5-flash     # Analysis agents (default)
GEMINI_LOW_MODEL=gemini-2.5-flash-lite # Simple tasks
SUPABASE_URL, SUPABASE_API_KEY        # Database connection
LOG_LEVEL=TRACE                       # TRACE|DEBUG|INFO|WARNING|ERROR
```

## Running the System

```bash
# Portfolio builder (one-time initial build) - RECOMMENDED
python examples/run_portfolio_builder.py

# Portfolio manager (daily/scheduled management)
python examples/run_portfolio_manager.py

# Individual agents
python examples/run_stock_screening.py
python examples/run_stock_news.py

# Backend API (required for dashboard)
python api/price_service.py  # FastAPI server on http://localhost:8000

# Frontend dashboard (requires backend running)
cd frontend && npm install && npm run dev  # http://localhost:3000

# Testing
pytest tests/

# Deployment (Google Cloud Run)
./deploy.sh  # Automated deployment script
# Deploys backend (api/price_service.py) and frontend to Cloud Run
# Configure Cloud Scheduler for: daily price updates (3:45 PM IST), portfolio manager (5:30 PM IST), weekly cleanup
# See DEPLOYMENT.md for detailed setup
```

## Architecture

**Three-Tier Agent Hierarchy:**
- **Tier 1**: Portfolio orchestrators (`portfolio_builder_agent_simple.py`, `portfolio_manager_agent.py`)
- **Tier 2**: Analysis agents (`stock_screening_agent.py`, `stock_news_agent.py`, `market_research_agent.py`)
- **Tier 3**: Tools (`screen_stocks.py`, `news_scraper.py`, `article_extractor.py`)

**Database**: Frontend (Next.js) → FastAPI (port 8000) → Supabase PostgreSQL
- Key tables: `portfolios`, `stocks`, `investment_views`, `key_metrics`, `daily_prices`, `performance_metrics`

**Core Files:**
- `utils/llm_service.py` - GeminiService singleton for all LLM calls
- `column_manager.py` - screener.in column name mapping/validation
- `config.ini` - Portfolio settings, allocation strategies, risk parameters
- `api/price_service.py` - FastAPI backend server (port 8000)
- `deploy.sh` - Google Cloud Run deployment script
- `backend.Dockerfile`, `frontend.Dockerfile` - Container configs

**Frontend Dashboard:**
- Next.js 14 with TypeScript, Tailwind CSS
- Portfolio overview with sector distribution charts
- Interactive stock cards with detail modals
- Investment thesis, metrics, targets, and stop-loss levels
- API routes: `/api/portfolio`, `/api/stocks/[id]`

## IMPORTANT: Critical Implementation Rules

### Column Names & Industry/Sector
- ALWAYS use exact column names from `data/column_name_mapping.json` (case-sensitive)
- Example: "Market Capitalization" NOT "market cap", "Return on equity" NOT "ROE"
- Industry/Sector are enriched from Supabase (`v_company_industry`), NOT from screener.in
- System auto-removes Industry/Sector filters from screener.in query, then post-filters results

### Portfolio Guidance System
Portfolio builder creates per-stock guidance for manager:
- Entry price, allocation, stop-loss/target (profile-based: aggressive -15%/+40-60%, moderate -12%/+25-40%, defensive -8%/+15-25%)
- Investment view: market outlook, rationale, holding period, exit/review triggers
- Saved to `.cache/portfolios/portfolio_{profile}_{timestamp}.json`
- Latest pointer: `.cache/portfolios/latest_{profile}.json`

Risk parameters in `config.ini` [RISK_PARAMETERS] section.

### Agent Prompt Philosophy
- **PRIMARY**: `portfolio_builder_agent_simple.py` - Minimal prompting, maximum flexibility
- **DEPRECATED**: `portfolio_builder_agent.py` - Legacy prescriptive workflow (use simple version)

## File Locations

**Logs**: `logs/portfolio_agent_YYYYMMDD_HHMMSS.log` (full trace), console (truncated preview)
**Cache**: `.cache/portfolios/` (final portfolios), `.cache/screening_results/` (>30 results), `.cache/simple_portfolio_state_*.json` (resume state)
**Auth**: `.playwright-mcp/auth.json` (persistent screener.in session)

## Common Pitfalls

1. Missing credentials in `.env` - agents fail silently
2. Playwright not installed: `playwright install chromium` required after pip install
3. Column name case/spacing errors - use exact names from `data/column_name_mapping.json`
4. Result sampling: Check `is_sampled` flag when >30 results returned
5. Agent iteration limits: Default max_iterations=10-15, increase for complex queries

## Code Style

- File naming: `*_screening_agent.py` (fundamentals), `*_news_agent.py` (stock news), `*_research_agent.py` (market research)
- No "_simple" suffixes on tools
- Backward compatibility via deprecated aliases (e.g., `run_stock_agent()` → `run_stock_screening()`)
- Agents use MD5-based query caching: `hashlib.md5(f"{agent}:{query}".encode()).hexdigest()`
