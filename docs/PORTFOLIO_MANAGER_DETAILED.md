# Portfolio Manager Agent - Detailed Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture & Components](#architecture--components)
3. [Workflow Sequence](#workflow-sequence)
4. [Implementation Analysis](#implementation-analysis)
5. [Issues & Limitations](#issues--limitations)
6. [Improvement Suggestions](#improvement-suggestions)
7. [Code Examples](#code-examples)
8. [Best Practices](#best-practices)

---

## Overview

### Purpose
The Portfolio Manager Agent is an AI-powered autonomous agent that performs **daily monitoring and management** of existing portfolios. Unlike the Portfolio Builder Agent (which creates portfolios), the Manager Agent:

- Monitors portfolio performance against benchmarks
- Tracks stop-loss and target price breaches
- Analyzes news sentiment for holdings
- Generates rebalancing recommendations
- Records all decisions and events in database

### Key Characteristics
- **Tier**: Portfolio Orchestrator Agent (Tier 1)
- **Model**: Uses `GEMINI_HIGH_MODEL` for complex strategic decisions
- **Execution**: Designed for scheduled/daily runs (not one-time)
- **State**: Stateful - loads portfolio from `.cache/portfolios/latest_{profile}.json`
- **Autonomy**: Semi-autonomous - generates recommendations but requires human approval

### Design Philosophy
The agent follows a **monitor-analyze-recommend** pattern:
1. Monitor: Collect current state (prices, news, market conditions)
2. Analyze: Process data against investment thesis and triggers
3. Recommend: Generate actionable insights with confidence levels

---

## Architecture & Components

### Core Components

```
Portfolio Manager Agent
│
├── Data Fetchers
│   ├── Price Fetcher (Yahoo Finance integration)
│   ├── News Agent (Google News analysis)
│   └── Market Research Agent (sector/economy trends)
│
├── Calculators
│   ├── Performance Calculator (returns, volatility, Sharpe)
│   ├── Performance Context Aggregator (benchmarks, sectors)
│   └── Price Trigger Checker (stop-loss, targets)
│
├── Decision Engine
│   └── LLM Recommendation Generator (Gemini)
│
└── Storage
    └── Database Service (SQLite)
```

### Dependencies

**External Services:**
- Yahoo Finance (via `yfinance`) - Stock/index prices
- Google News API (via `news_scraper.py`) - News analysis
- Gemini API (via `llm_service.py`) - AI reasoning

**Internal Agents:**
- `stock_news_agent.py` - Analyze news for specific stocks
- `market_research_agent.py` - Research market trends
- `stock_screening_agent.py` - Re-screen opportunities (future use)

**Data Sources:**
- Portfolio state: `.cache/portfolios/latest_{profile}.json`
- Database: `.cache/portfolio.db`
- Configuration: `config.ini`

---

## Workflow Sequence

### High-Level Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Load Portfolio                                      │
│ - Read latest_{profile}.json                                │
│ - Extract stocks, capital, guidance                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Fetch Current Prices                                │
│ - Call price_fetcher.get_current_price() for each stock     │
│ - Fallback to entry_price if fetch fails                    │
│ - Cache prices (5-min TTL)                                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Check Price Triggers                                │
│ - Compare current_price vs stop_loss_price                  │
│ - Compare current_price vs target_price                     │
│ - Identify "approaching target" (within 5%)                 │
│ - Calculate P&L for each position                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Analyze News                                        │
│ - For each stock: run_stock_news(ticker)                    │
│ - Extract sentiment and summary                             │
│ - Cache results (MD5 hash key)                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Research Market Conditions                          │
│ - run_market_research("Current Indian market trends...")    │
│ - Get Nifty outlook, sector performance                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5.5: Generate Performance Context                      │
│ - Query portfolio from database                             │
│ - performance_aggregator.generate_context()                 │
│ - Include benchmarks (Nifty, Sensex)                        │
│ - Include sector breakdown                                  │
│ - Include top/bottom performers                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Generate AI Recommendation                          │
│ - Build comprehensive prompt with:                          │
│   • Portfolio summary                                       │
│   • Performance metrics & benchmarks                        │
│   • Price triggers                                          │
│   • News highlights                                         │
│   • Market outlook                                          │
│ - Call LLM (Gemini high-tier model)                         │
│ - Parse JSON response with:                                 │
│   • assessment                                              │
│   • immediate_actions                                       │
│   • stocks_to_review                                        │
│   • rebalancing_needed                                      │
│   • confidence_level                                        │
│   • recommendation (HOLD/BUY_MORE/SELL/REBALANCE)           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Store Manager Update                                │
│ - Determine priority (CRITICAL/HIGH/MEDIUM/LOW)             │
│ - Create title based on triggers                            │
│ - Store in manager_updates table                            │
│ - Link affected stocks                                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT: Return Analysis Results                             │
│ - success flag                                              │
│ - portfolio state                                           │
│ - current prices                                            │
│ - price_triggers                                            │
│ - news_analysis                                             │
│ - market_outlook                                            │
│ - recommendation                                            │
│ - priority                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Step-by-Step Execution

#### Step 1: Load Portfolio
**File:** `portfolio_manager_agent.py:51-90`

```python
def load_portfolio(profile: str = "aggressive") -> Optional[Dict[str, Any]]
```

**What happens:**
1. Construct path: `.cache/portfolios/latest_{profile}.json`
2. Check if file exists
3. Read JSON file
4. Handle two possible structures:
   - Nested: `{metadata: {...}, portfolio: {...}}` - flatten it
   - Flat: `{profile: ..., total_capital: ..., stocks: [...]}`
5. Return flattened portfolio dict with stocks array

**Potential Issues:**
- No validation of portfolio schema
- Silent failure if stocks array is empty
- No version checking for portfolio format changes

---

#### Step 2: Fetch Current Prices
**File:** `portfolio_manager_agent.py:92-118`

```python
def get_current_prices(stocks: List[Dict]) -> Dict[str, float]
```

**What happens:**
1. For each stock in portfolio:
   - Extract ticker and exchange
   - Call `price_fetcher.get_current_price(ticker, exchange)`
   - If successful, store in `prices` dict
   - If fails, fallback to `entry_price` with WARNING log
2. Return dict mapping ticker → price

**Price Fetcher Details:**
- Uses Yahoo Finance API via `yfinance` library
- In-memory cache with 5-minute TTL
- Ticker variation generation for truncated symbols
- NSE → BSE fallback
- Yahoo search API as last resort

**Potential Issues:**
- No batch fetching (sequential API calls = slow)
- No rate limiting protection
- Fallback to entry_price masks stale data problem
- No retry logic for transient failures
- No validation if price is reasonable (outlier detection)

---

#### Step 3: Check Price Triggers
**File:** `portfolio_manager_agent.py:120-184`

```python
def check_price_triggers(
    stocks: List[Dict],
    current_prices: Dict[str, float]
) -> Dict[str, List[Dict]]
```

**What happens:**
1. Initialize trigger categories: `stop_loss_breached`, `target_reached`, `approaching_target`
2. For each stock:
   - Get current price (fallback to entry_price if missing)
   - Calculate P&L percentage: `((current - entry) / entry) * 100`
   - **Stop-loss check**: `if current_price <= stop_loss_price`
     - Add to `stop_loss_breached` with breach details
   - **Target check**: `elif current_price >= target_price`
     - Add to `target_reached` with excess gain
   - **Approaching target check**: `elif current_price >= target * 0.95`
     - Add to `approaching_target` (within 5% of target)
3. Return categorized triggers

**Trigger Data Structure:**
```python
{
    'stop_loss_breached': [
        {
            'stock': {...},
            'current_price': float,
            'stop_loss_price': float,
            'breach_pct': float,  # How far below stop-loss
            'current_pnl_pct': float
        }
    ],
    'target_reached': [...],
    'approaching_target': [...]
}
```

**Potential Issues:**
- `elif` logic means a stock can't be in both "stop-loss" AND "approaching target" (edge case)
- 5% threshold for "approaching" is hardcoded, not configurable
- No hysteresis/cooldown - same alert could fire daily
- No alert deduplication mechanism

---

#### Step 4: Analyze News
**File:** `portfolio_manager_agent.py:186-233`

```python
def analyze_portfolio_news(stocks: List[Dict]) -> Dict[str, Any]
```

**What happens:**
1. For each stock:
   - Generate cache key: `MD5("stock_news:{ticker}")`
   - Check if cached, if yes → use cached result
   - If not cached:
     - Call `run_stock_news(f"Recent news for {name} ({ticker})")`
     - Extract sentiment (currently hardcoded to 'neutral')
     - Store first 500 chars as summary
     - Cache result
2. Return dict: `{ticker: {sentiment, summary, full_analysis}}`

**Stock News Agent:**
- Uses Google News API via `news_scraper.py`
- Fetches recent articles (lookback period from config)
- Extracts article content with `article_extractor.py` (newspaper4k)
- AI analysis for sentiment (via Gemini)

**Potential Issues:**
- **CRITICAL**: Sentiment extraction is broken - always returns 'neutral'
  ```python
  'sentiment': 'neutral',  # Extract from result <- TODO not implemented!
  ```
- No structured sentiment parsing from LLM response
- Cache is in-memory only - lost on restart
- Sequential API calls (slow for 15 stocks)
- No error aggregation - individual stock failures are logged but not surfaced

---

#### Step 5: Market Research
**File:** `portfolio_manager_agent.py:547-555`

```python
market_query = "Current Indian stock market trends, Nifty outlook, and sector performance"
market_outlook = run_market_research(market_query)
```

**What happens:**
1. Call Market Research Agent with fixed query
2. Agent searches Google News for market-wide trends
3. Returns text summary of market conditions
4. If fails, fallback to "Market data unavailable"

**Potential Issues:**
- Query is hardcoded - doesn't adapt to portfolio composition
- No structured output - free-form text makes parsing hard
- No caching - same market research repeated for all portfolios
- Errors are swallowed silently (fallback to generic message)

---

#### Step 5.5: Generate Performance Context
**File:** `portfolio_manager_agent.py:557-578`

```python
performance_context = self.performance_aggregator.generate_context(
    portfolio_id,
    include_benchmarks=True,
    include_sector_breakdown=True,
    include_top_performers=True
)
```

**What happens:**
1. Query database to get portfolio ID
2. Call `performance_context_aggregator.generate_context()`
3. Aggregator compiles:
   - Daily/MTD/YTD returns
   - Benchmark comparisons (Nifty, Sensex, sector indices)
   - Alpha calculation (portfolio return - benchmark return)
   - Sector-wise performance breakdown
   - Top/bottom performing stocks
4. Generate narrative text summary

**Performance Context Structure:**
```python
{
    'narrative': str,  # Human-readable summary
    'benchmarks': [
        {
            'name': 'Nifty 50',
            'symbol': '^NSEI',
            'status': 'available',
            'alpha': {'daily': float, 'mtd': float}
        }
    ],
    'sectors': [
        {
            'sector': 'Technology',
            'weighted_return': float,
            'total_allocation_pct': float
        }
    ],
    'top_performers': [...],
    'bottom_performers': [...]
}
```

**Potential Issues:**
- Portfolio must exist in database (if not, skipped)
- No graceful degradation if benchmarks unavailable
- Sector indices might not be updated (stale data)

---

#### Step 6: Generate AI Recommendation
**File:** `portfolio_manager_agent.py:274-447`

```python
def generate_recommendation(
    portfolio,
    current_prices,
    price_triggers,
    news_analysis,
    market_outlook,
    performance_context
) -> Dict[str, Any]
```

**What happens:**

**6.1: Build Context**
```python
context = {
    'profile': portfolio['profile'],
    'total_capital': portfolio['total_capital'],
    'num_stocks': len(portfolio['stocks']),
    'price_triggers': {
        'stop_loss_breached': count,
        'target_reached': count,
        'approaching_target': count
    },
    'market_outlook': market_outlook
}
```

**6.2: Build Detailed Analysis Text**
- List all stop-loss breaches with prices and P&L
- List all targets reached with gains
- Extract news highlights (non-neutral sentiment only)

**6.3: Construct LLM Prompt**
```
You are an expert portfolio manager analyzing an {profile} portfolio.

PORTFOLIO SUMMARY:
- Profile: aggressive
- Total Capital: Rs. 5,00,000
- Holdings: 15 stocks
- Stop-loss breaches: 2
- Targets reached: 1

=== PERFORMANCE METRICS ===
{performance_context.narrative}

=== BENCHMARK COMPARISON ===
Nifty 50: Daily Alpha +0.5%, MTD Alpha +2.3%

=== SECTOR PERFORMANCE ===
Technology: +3.2% (30% allocation)
Finance: +1.5% (25% allocation)

MARKET OUTLOOK:
{market_outlook}

DETAILED ANALYSIS:
STOP-LOSS BREACHES:
- Stock A: Rs. 85 vs SL Rs. 85 (P&L: -15%)

TARGETS REACHED:
- Stock B: Rs. 150 vs Target Rs. 150 (P&L: +50%)

NEWS HIGHLIGHTS:
- TECH: Positive earnings beat

Based on this analysis, provide your recommendation:
1. **Overall Assessment**: Brief summary of portfolio health
2. **Immediate Actions**: Any urgent decisions needed
3. **Stocks to Review**: Which holdings need closer monitoring
4. **Rebalancing Needed**: Should portfolio be rebalanced?
5. **Confidence Level**: Your confidence (0-100%)
6. **Recommendation**: HOLD, BUY_MORE, SELL, or REBALANCE

Provide structured JSON output with keys: assessment, immediate_actions,
stocks_to_review, rebalancing_needed, confidence_level, recommendation, reasoning
```

**6.4: Call LLM**
```python
response = generate_content(
    contents=prompt,
    model=self.model_name,  # "high" tier
    temperature=0.7,
    verbose=True
)
```

**6.5: Parse JSON Response**
- Strip markdown code blocks (```json ... ```)
- Parse JSON
- Extract recommendation fields

**Expected Response Structure:**
```json
{
    "assessment": "Portfolio showing mixed signals...",
    "immediate_actions": [
        "Exit Stock A (stop-loss breached)",
        "Consider booking profit on Stock B"
    ],
    "stocks_to_review": ["Stock C", "Stock D"],
    "rebalancing_needed": true,
    "confidence_level": 85,
    "recommendation": "REBALANCE",
    "reasoning": "Stop-loss breach requires immediate action..."
}
```

**Potential Issues:**
- **JSON parsing fragility**: LLM might not always return valid JSON
- No schema validation on response
- No retry if parsing fails
- Temperature 0.7 might produce inconsistent outputs
- No structured reasoning chain (just free-form text)
- Confidence level is subjective - no calibration
- Recommendation types are limited (HOLD/BUY_MORE/SELL/REBALANCE) - lacks nuance

---

#### Step 7: Store Manager Update
**File:** `portfolio_manager_agent.py:449-502`

```python
def store_manager_update(
    portfolio_id,
    recommendation,
    price_triggers,
    priority
) -> int
```

**What happens:**
1. Determine affected stocks from triggers
2. Create title based on trigger severity:
   - Stop-loss breach → "Stop-Loss Alert: N stocks breached"
   - Target reached → "Target Achievement: N stocks reached targets"
   - Default → "Daily Portfolio Review"
3. Set priority:
   - `CRITICAL`: 3+ stop-losses
   - `HIGH`: 1-2 stop-losses OR targets reached
   - `MEDIUM`: Default
4. Call `db.store_manager_update()` with:
   - `portfolio_id`
   - `update_date` (today)
   - `update_type` = 'DAILY_REVIEW'
   - `title`, `description`, `affected_stocks`
   - `recommendation`, `reasoning`, `priority`
5. Return update ID

**Database Table: `manager_updates`**
```sql
CREATE TABLE manager_updates (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER NOT NULL,
    update_date TEXT NOT NULL,
    update_type TEXT,
    title TEXT,
    description TEXT,
    affected_stocks TEXT,  -- JSON array
    recommendation TEXT,
    reasoning TEXT,
    priority TEXT,
    created_at TEXT
)
```

**Potential Issues:**
- Title generation logic is simplistic
- `affected_stocks` only includes triggered stocks - misses stocks under review
- No deduplication - same alert could be stored daily
- Priority logic is hardcoded, not configurable

---

### Summary Output

**File:** `portfolio_manager_agent.py:629-638`

```python
return {
    'success': True,
    'portfolio': portfolio,
    'current_prices': current_prices,
    'price_triggers': price_triggers,
    'news_analysis': news_analysis,
    'market_outlook': market_outlook,
    'recommendation': recommendation,
    'priority': priority
}
```

---

## Implementation Analysis

### Strengths

**1. Modular Architecture**
- Clear separation of concerns (fetchers, calculators, decision engine)
- Singleton pattern for services (price_fetcher, db_service)
- Reusable components across different agents

**2. Comprehensive Data Collection**
- Multi-source data: prices, news, market research, performance metrics
- Benchmark comparison (Nifty, Sensex)
- Sector breakdown

**3. Intelligent Caching**
- MD5-based agent cache prevents redundant API calls
- Price cache with 5-minute TTL
- In-memory conversation history

**4. Database Integration**
- All decisions logged for audit trail
- Structured storage for analysis
- Support for historical queries

**5. LLM-Powered Reasoning**
- Uses high-tier model for strategic decisions
- Context-rich prompts with performance metrics
- Structured JSON output format

**6. Graceful Degradation**
- Fallback to entry_price if live price unavailable
- Default market outlook if research fails
- Error handling in news analysis

### Weaknesses

**1. Sequential Processing**
- Price fetching is sequential (slow for 15 stocks)
- News analysis is sequential
- No parallelization opportunities utilized

**2. Fragile JSON Parsing**
- LLM response parsing relies on string manipulation
- No schema validation
- Single point of failure

**3. Hardcoded Logic**
- "Approaching target" threshold (5%) is hardcoded
- Priority determination logic is not configurable
- Market research query is fixed

**4. Incomplete Features**
- Sentiment extraction is not implemented (always 'neutral')
- Beta calculation is TODO
- Investment view triggers are not checked

**5. No State Management**
- In-memory cache lost on restart
- No resume capability
- No checkpoint/recovery mechanism

**6. Limited Error Handling**
- Errors are logged but not aggregated
- No alert escalation
- Silent failures in news analysis

**7. No Validation**
- Portfolio schema not validated
- Price outlier detection missing
- Recommendation confidence not calibrated

---

## Issues & Limitations

### Critical Issues

#### 1. Sentiment Extraction Not Implemented
**Location:** `portfolio_manager_agent.py:216`

```python
news_analysis[ticker] = {
    'sentiment': 'neutral',  # Extract from result <- NOT IMPLEMENTED!
    'summary': result[:500] if result else 'No recent news',
    'full_analysis': result
}
```

**Impact:** News analysis is incomplete, LLM doesn't receive actual sentiment signals

**Fix Required:**
```python
# Parse sentiment from LLM response
sentiment = self._extract_sentiment(result)  # Implement this method
news_analysis[ticker] = {
    'sentiment': sentiment,  # 'positive', 'negative', 'neutral'
    'summary': result[:500],
    'full_analysis': result
}
```

---

#### 2. Investment View Triggers Not Checked
**Location:** `portfolio_manager_agent.py:235-272`

The `check_investment_triggers()` method exists but is **never called** in the main workflow.

**What's Missing:**
- Portfolio Builder provides exit_triggers and review_triggers for each stock
- Manager should check if news/events match these triggers
- No monitoring of thesis invalidation

**Example:**
```python
# From portfolio guidance:
"exit_triggers": ["Revenue growth < 15%", "Loss of market share"]

# Current implementation: Simple keyword matching (too simplistic)
# Better approach: Use LLM to evaluate if trigger condition met
```

**Impact:** Core portfolio guidance system is not utilized

---

#### 3. Performance Context Optional
**Location:** `portfolio_manager_agent.py:558-578`

If portfolio not found in database, performance context is skipped entirely.

**Impact:** LLM recommendation generated without benchmark data, alpha, sector performance

**Fix:** Make performance context mandatory, fail fast if unavailable

---

#### 4. No Rate Limiting Protection
**Location:** Multiple - price fetching, news analysis

Sequential API calls without rate limiting:
```python
for stock in stocks:
    price = self.price_fetcher.get_current_price(ticker)  # No delay
```

**Impact:**
- Risk of API throttling/blocking
- Poor performance (no parallelization)
- Yahoo Finance rate limits can cause failures

**Fix:**
```python
# Add rate limiting
time.sleep(0.1)  # 100ms delay between calls
# OR: Use batch fetching
prices = self.price_fetcher.batch_fetch_prices(stocks, delay=0.1)
```

---

#### 5. Brittle JSON Parsing
**Location:** `portfolio_manager_agent.py:421-432`

```python
# Fragile string manipulation
if response.startswith("```json"):
    response = response[7:]
if response.startswith("```"):
    response = response[3:]
if response.endswith("```"):
    response = response[:-3]

recommendation = json.loads(response)  # Can fail!
```

**Impact:** If LLM returns malformed JSON or unexpected format, entire recommendation fails

**Fix:** Use structured output format (Gemini's `response_schema` parameter) or implement robust parsing with fallback

---

### Major Limitations

#### 1. No Alert Deduplication
Same alert could be generated daily if trigger remains breached.

**Example:**
- Day 1: "Stop-Loss Alert: Stock A breached"
- Day 2: "Stop-Loss Alert: Stock A breached" ← Duplicate!

**Fix:** Track alert history, only create new alert if status changed

---

#### 2. No Confidence Calibration
LLM confidence level (0-100%) is subjective and not calibrated against actual outcomes.

**Fix:** Track recommendation accuracy over time, calibrate confidence scores

---

#### 3. Static Market Research Query
```python
market_query = "Current Indian stock market trends, Nifty outlook, and sector performance"
```

Should adapt to portfolio composition:
- If 50% tech → "Tech sector analysis"
- If defensive → "Defensive sector trends"

---

#### 4. No Portfolio Synchronization
Portfolio file and database can be out of sync.

**Example:**
- Portfolio updated in `.cache/portfolios/` but not in database
- Manager loads file but performance context queries database

**Fix:** Single source of truth - database is canonical, file is snapshot

---

#### 5. No Execution Capability
Manager only generates recommendations, cannot execute:
- No trade placement
- No rebalancing execution
- Manual intervention required

**Design Decision:** This is intentional (human-in-the-loop), but should be documented

---

### Minor Issues

#### 1. Hardcoded Constants
```python
MAX_ITERATIONS = 20  # Agent iterations (not used in Manager!)
CACHE_DIR = Path(__file__).parent.parent / ".cache"
PORTFOLIOS_DIR = CACHE_DIR / "portfolios"
```

`MAX_ITERATIONS` is defined but never used - Manager doesn't have iterative agent loop.

---

#### 2. Inconsistent Error Handling
Some errors return `None`, others return error dict, others raise exceptions.

---

#### 3. No Metrics Collection
No tracking of:
- Execution time
- API call counts
- Success/failure rates

---

#### 4. Limited Recommendation Types
Only 4 types: `HOLD`, `BUY_MORE`, `SELL`, `REBALANCE`

Missing:
- `TRIM` (reduce position)
- `ROTATE` (sell X, buy Y)
- `HOLD_AND_MONITOR` (with review date)

---

## Improvement Suggestions

### High Priority

#### 1. Implement Sentiment Extraction
```python
def _extract_sentiment(self, llm_response: str) -> str:
    """Parse sentiment from LLM news analysis response"""
    # Use regex or structured output
    # Look for keywords: positive, negative, neutral
    # Or: Use Gemini with structured output schema

    sentiment_prompt = f"""
    Analyze the following news summary and return ONLY ONE WORD:
    - "positive" if overall sentiment is bullish
    - "negative" if overall sentiment is bearish
    - "neutral" if mixed or no clear direction

    News: {llm_response}

    Sentiment:
    """

    result = generate_content(sentiment_prompt, model="low", temperature=0)
    return result.strip().lower()
```

---

#### 2. Implement Investment Trigger Checking
```python
def check_investment_triggers_ai(
    self,
    stock: Dict[str, Any],
    news_analysis: str,
    market_outlook: str,
    performance_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use LLM to evaluate if exit/review triggers have been hit

    More sophisticated than keyword matching
    """
    view = stock.get('investment_view', {})
    exit_triggers = view.get('exit_triggers', [])
    review_triggers = view.get('review_triggers', [])

    prompt = f"""
    You are evaluating investment triggers for {stock['name']}.

    INVESTMENT THESIS:
    - Market Outlook: {view.get('market_outlook')}
    - Stock Rationale: {view.get('stock_rationale')}
    - Holding Period: {view.get('holding_period')}

    EXIT TRIGGERS (invalidate thesis):
    {json.dumps(exit_triggers, indent=2)}

    REVIEW TRIGGERS (require reassessment):
    {json.dumps(review_triggers, indent=2)}

    CURRENT DATA:
    - News Analysis: {news_analysis[:500]}
    - Market Conditions: {market_outlook[:300]}
    - Performance: {performance_data.get('pnl_pct')}% P&L

    Evaluate:
    1. Which EXIT triggers (if any) have been hit?
    2. Which REVIEW triggers (if any) have been hit?

    Return JSON: {{"exit_triggers_hit": [...], "review_triggers_hit": [...]}}
    """

    response = generate_content(prompt, model="mid", temperature=0.3)
    return json.loads(response)
```

---

#### 3. Add Parallel Processing
```python
import concurrent.futures

def get_current_prices_parallel(self, stocks: List[Dict]) -> Dict[str, float]:
    """Fetch prices in parallel using ThreadPoolExecutor"""
    prices = {}

    def fetch_price(stock):
        ticker = stock['ticker']
        exchange = stock.get('exchange', 'NSE')
        price = self.price_fetcher.get_current_price(ticker, exchange)
        return (ticker, price or stock['entry_price'])

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_price, stocks)

    for ticker, price in results:
        prices[ticker] = price

    return prices
```

---

#### 4. Use Structured Output (Gemini)
```python
from google.ai.generativelanguage_v1beta.types import content

# Define response schema
response_schema = content.Schema(
    type=content.Type.OBJECT,
    properties={
        "assessment": content.Schema(type=content.Type.STRING),
        "immediate_actions": content.Schema(
            type=content.Type.ARRAY,
            items=content.Schema(type=content.Type.STRING)
        ),
        "stocks_to_review": content.Schema(
            type=content.Type.ARRAY,
            items=content.Schema(type=content.Type.STRING)
        ),
        "rebalancing_needed": content.Schema(type=content.Type.BOOLEAN),
        "confidence_level": content.Schema(type=content.Type.INTEGER),
        "recommendation": content.Schema(
            type=content.Type.STRING,
            enum=["HOLD", "BUY_MORE", "SELL", "REBALANCE"]
        ),
        "reasoning": content.Schema(type=content.Type.STRING)
    },
    required=["assessment", "recommendation", "confidence_level"]
)

# Generate with schema
response = generate_content(
    prompt,
    model="high",
    response_schema=response_schema,
    temperature=0.7
)

# Response is guaranteed to match schema
recommendation = json.loads(response)
```

---

#### 5. Add Alert Deduplication
```python
def store_manager_update_deduplicated(
    self,
    portfolio_id: int,
    recommendation: Dict[str, Any],
    price_triggers: Dict[str, List[Dict]],
    priority: str
) -> int:
    """Store update only if different from last update"""

    # Get last update
    last_update = self.db.execute_query(
        """
        SELECT * FROM manager_updates
        WHERE portfolio_id = ?
        ORDER BY update_date DESC
        LIMIT 1
        """,
        (portfolio_id,)
    )

    if last_update:
        last = last_update[0]

        # Check if same triggers
        last_affected = set(json.loads(last['affected_stocks'] or '[]'))
        current_affected = set([
            item['stock']['ticker']
            for item in price_triggers['stop_loss_breached'] + price_triggers['target_reached']
        ])

        if last_affected == current_affected and last['recommendation'] == recommendation['recommendation']:
            logger.info("Skipping duplicate update (same as last)")
            return last['id']

    # Store new update
    return self.store_manager_update(portfolio_id, recommendation, price_triggers, priority)
```

---

### Medium Priority

#### 6. Make Portfolio-Database Sync Mandatory
```python
def load_portfolio(self, profile: str) -> Optional[Dict[str, Any]]:
    """Load portfolio from database (single source of truth)"""

    # Query database
    db_portfolio = self.db.get_active_portfolio(profile)

    if not db_portfolio:
        logger.error(f"No active portfolio in database for {profile}")
        return None

    # Load stocks
    stocks = self.db.get_portfolio_stocks(db_portfolio['id'])

    # Construct portfolio dict
    return {
        'id': db_portfolio['id'],
        'profile': db_portfolio['profile'],
        'total_capital': db_portfolio['total_capital'],
        'created_at': db_portfolio['created_at'],
        'stocks': stocks
    }
```

---

#### 7. Add Execution Metrics
```python
import time
from contextlib import contextmanager

@contextmanager
def track_execution(step_name: str):
    """Context manager to track execution time and log metrics"""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        logger.info(f"[METRICS] {step_name}: {duration:.2f}s")
        # Could also store in database:
        # self.db.store_execution_metric(step_name, duration)

# Usage:
with track_execution("Fetch Prices"):
    current_prices = self.get_current_prices(stocks)
```

---

#### 8. Adaptive Market Research Query
```python
def generate_market_research_query(self, portfolio: Dict) -> str:
    """Generate market research query based on portfolio composition"""

    # Analyze sector allocation
    sector_allocation = {}
    for stock in portfolio['stocks']:
        sector = stock.get('sector', 'Unknown')
        sector_allocation[sector] = sector_allocation.get(sector, 0) + stock['allocation_pct']

    # Top 2 sectors
    top_sectors = sorted(sector_allocation.items(), key=lambda x: x[1], reverse=True)[:2]

    # Build adaptive query
    query_parts = ["Current Indian stock market trends"]

    for sector, allocation in top_sectors:
        if allocation > 20:
            query_parts.append(f"{sector} sector outlook")

    query_parts.append("Nifty 50 outlook")

    return ", ".join(query_parts)
```

---

#### 9. Add Recommendation Confidence Calibration
Track historical accuracy and calibrate confidence scores.

```python
def calibrate_confidence(
    self,
    recommendation: Dict[str, Any],
    portfolio_id: int
) -> Dict[str, Any]:
    """
    Adjust confidence based on historical accuracy

    Example:
    - If past recommendations with 90% confidence were only 70% accurate,
      adjust current 90% down to 70%
    """

    # Get historical accuracy
    accuracy_data = self.db.execute_query(
        """
        SELECT
            AVG(CASE WHEN outcome = 'correct' THEN 1 ELSE 0 END) as accuracy,
            COUNT(*) as count
        FROM manager_update_outcomes
        WHERE portfolio_id = ?
          AND confidence_level BETWEEN ? AND ?
        """,
        (portfolio_id, recommendation['confidence_level'] - 10, recommendation['confidence_level'] + 10)
    )

    if accuracy_data and accuracy_data[0]['count'] > 5:
        historical_accuracy = accuracy_data[0]['accuracy'] * 100
        calibrated_confidence = historical_accuracy

        recommendation['confidence_level_raw'] = recommendation['confidence_level']
        recommendation['confidence_level'] = calibrated_confidence
        recommendation['confidence_note'] = f"Calibrated from {recommendation['confidence_level_raw']}% based on {accuracy_data[0]['count']} past predictions"

    return recommendation
```

---

### Low Priority

#### 10. Add Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def fetch_price_with_retry(self, ticker: str, exchange: str) -> float:
    """Fetch price with exponential backoff retry"""
    price = self.price_fetcher.get_current_price(ticker, exchange)
    if price is None:
        raise ValueError(f"Failed to fetch price for {ticker}")
    return price
```

---

#### 11. Add Price Outlier Detection
```python
def validate_price(
    self,
    ticker: str,
    current_price: float,
    entry_price: float,
    max_change_pct: float = 50.0
) -> bool:
    """
    Detect price outliers (likely data errors)

    Returns False if price change exceeds threshold
    """
    change_pct = abs(((current_price - entry_price) / entry_price) * 100)

    if change_pct > max_change_pct:
        logger.warning(
            f"Price outlier detected for {ticker}: "
            f"{current_price} vs entry {entry_price} ({change_pct:.1f}% change)"
        )
        return False

    return True
```

---

#### 12. Enhanced Recommendation Types
```python
RECOMMENDATION_TYPES = {
    'HOLD': 'Maintain current positions',
    'BUY_MORE': 'Add to existing positions',
    'SELL': 'Exit positions completely',
    'REBALANCE': 'Adjust allocations to targets',
    'TRIM': 'Reduce position size (partial exit)',
    'ROTATE': 'Sell underperformers, buy new opportunities',
    'HOLD_AND_MONITOR': 'Hold with specific review date',
    'DEFENSIVE_SHIFT': 'Move to defensive positions',
    'TAKE_PROFIT': 'Book profits on winners',
    'AVERAGE_DOWN': 'Add to losing positions (careful!)'
}
```

---

## Code Examples

### Complete Manager Implementation with Improvements

```python
# examples/run_improved_portfolio_manager.py

from agents.portfolio_manager_agent import PortfolioManagerAgent
from utils.logger import get_logger
import concurrent.futures
import time

logger = get_logger("examples.improved_manager")


class ImprovedPortfolioManager(PortfolioManagerAgent):
    """Enhanced Portfolio Manager with improvements"""

    def get_current_prices_parallel(self, stocks):
        """Parallel price fetching"""
        prices = {}

        def fetch_with_validation(stock):
            ticker = stock['ticker']
            price = self.price_fetcher.get_current_price(ticker, stock.get('exchange', 'NSE'))

            # Validate price
            if price and self.validate_price(ticker, price, stock['entry_price']):
                return (ticker, price)
            else:
                logger.warning(f"Using entry price for {ticker}")
                return (ticker, stock['entry_price'])

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(fetch_with_validation, stocks)

        return dict(results)

    def validate_price(self, ticker, current_price, entry_price, max_change=50.0):
        """Detect price outliers"""
        change_pct = abs(((current_price - entry_price) / entry_price) * 100)
        return change_pct <= max_change

    def extract_sentiment(self, llm_response: str) -> str:
        """Extract sentiment from news analysis"""
        response_lower = llm_response.lower()

        # Simple keyword matching (could use LLM)
        if any(word in response_lower for word in ['positive', 'bullish', 'optimistic', 'strong']):
            return 'positive'
        elif any(word in response_lower for word in ['negative', 'bearish', 'pessimistic', 'weak']):
            return 'negative'
        else:
            return 'neutral'

    def analyze_portfolio_news_enhanced(self, stocks):
        """Enhanced news analysis with proper sentiment extraction"""
        news_analysis = {}

        for stock in stocks:
            ticker = stock['ticker']
            cache_key = hashlib.md5(f"stock_news:{ticker}".encode()).hexdigest()

            if cache_key in self._agent_cache:
                news_analysis[ticker] = self._agent_cache[cache_key]
                continue

            try:
                result = run_stock_news(f"Recent news for {stock['name']} ({ticker})")

                # Extract sentiment properly
                sentiment = self.extract_sentiment(result)

                news_analysis[ticker] = {
                    'sentiment': sentiment,
                    'summary': result[:500],
                    'full_analysis': result
                }

                self._agent_cache[cache_key] = news_analysis[ticker]

            except Exception as e:
                logger.error(f"Failed news analysis for {ticker}: {e}")
                news_analysis[ticker] = {
                    'sentiment': 'unknown',
                    'summary': f'Error: {e}',
                    'full_analysis': ''
                }

        return news_analysis

    def run_enhanced(self, profile: str = "aggressive"):
        """Run manager with enhancements"""
        logger.info("Starting ENHANCED Portfolio Manager")

        # Load portfolio
        portfolio = self.load_portfolio(profile)
        if not portfolio:
            return {'success': False, 'error': 'Portfolio not found'}

        # Parallel price fetching
        start = time.time()
        current_prices = self.get_current_prices_parallel(portfolio['stocks'])
        logger.info(f"Fetched prices in {time.time() - start:.2f}s (parallel)")

        # Check triggers
        price_triggers = self.check_price_triggers(portfolio['stocks'], current_prices)

        # Enhanced news analysis
        news_analysis = self.analyze_portfolio_news_enhanced(portfolio['stocks'])

        # Market research
        market_outlook = run_market_research("Current Indian market trends")

        # Performance context (mandatory)
        performance_context = self.performance_aggregator.generate_context(
            portfolio['id'],
            include_benchmarks=True
        )

        # Generate recommendation
        recommendation = self.generate_recommendation(
            portfolio,
            current_prices,
            price_triggers,
            news_analysis,
            market_outlook,
            performance_context
        )

        # Store update (with deduplication)
        self.store_manager_update_deduplicated(
            portfolio['id'],
            recommendation,
            price_triggers
        )

        return {
            'success': True,
            'portfolio': portfolio,
            'recommendation': recommendation
        }


if __name__ == '__main__':
    manager = ImprovedPortfolioManager()
    result = manager.run_enhanced('aggressive')
    print(f"Recommendation: {result['recommendation']['recommendation']}")
```

---

## Best Practices

### 1. Scheduling
Run Portfolio Manager daily at market close:

```bash
# crontab -e
# Run at 3:45 PM IST (after market closes at 3:30 PM)
45 15 * * 1-5 cd /path/to/project && python examples/run_portfolio_manager.py >> logs/cron.log 2>&1
```

### 2. Error Notification
Send alerts on critical failures:

```python
def run_with_alerts(profile: str):
    try:
        result = run_portfolio_manager(profile)

        # Check for stop-loss breaches
        if result['price_triggers']['stop_loss_breached']:
            send_email_alert(
                subject="URGENT: Stop-Loss Breach",
                body=format_trigger_alert(result)
            )

        return result

    except Exception as e:
        send_email_alert(
            subject="ERROR: Portfolio Manager Failed",
            body=f"Error: {str(e)}"
        )
        raise
```

### 3. Performance Tracking
Store execution metrics:

```python
def store_execution_metrics(self, execution_time: float, api_calls: int):
    """Track manager performance over time"""
    self.db.execute_query(
        """
        INSERT INTO execution_metrics (date, execution_time_sec, api_calls, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (date.today(), execution_time, api_calls, datetime.now())
    )
```

### 4. Backtesting Recommendations
Validate recommendation accuracy:

```python
def backtest_recommendation(
    recommendation_id: int,
    actual_outcome: str,
    outcome_date: date
):
    """
    Store actual outcome of recommendation for calibration

    Args:
        recommendation_id: Manager update ID
        actual_outcome: 'correct' | 'incorrect' | 'partially_correct'
        outcome_date: When outcome was observed
    """
    db.execute_query(
        """
        INSERT INTO recommendation_outcomes
        (recommendation_id, actual_outcome, outcome_date, notes)
        VALUES (?, ?, ?, ?)
        """,
        (recommendation_id, actual_outcome, outcome_date, "")
    )
```

### 5. Human-in-the-Loop
Manager recommends, human decides:

```python
def execute_with_approval(recommendation: Dict):
    """Present recommendation and wait for approval"""
    print(f"\n{'='*60}")
    print(f"RECOMMENDATION: {recommendation['recommendation']}")
    print(f"Confidence: {recommendation['confidence_level']}%")
    print(f"\nAssessment: {recommendation['assessment']}")
    print(f"\nImmediate Actions:")
    for action in recommendation['immediate_actions']:
        print(f"  - {action}")
    print(f"{'='*60}\n")

    approval = input("Execute this recommendation? (yes/no): ")

    if approval.lower() == 'yes':
        execute_recommendation(recommendation)
    else:
        logger.info("Recommendation rejected by user")
```

---

## Conclusion

The Portfolio Manager Agent is a well-architected system with strong foundations but needs improvements in:

**Critical:**
- Sentiment extraction implementation
- Investment trigger checking
- Parallel processing

**Important:**
- JSON parsing robustness
- Alert deduplication
- Performance context reliability

**Nice-to-have:**
- Confidence calibration
- Adaptive market research
- Enhanced recommendation types

With these improvements, the agent will be production-ready for daily portfolio management.

---

**Last Updated:** 2025-12-26
**Version:** 1.0
**Status:** Initial detailed analysis
