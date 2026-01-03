# Phase 5 Complete: Portfolio Manager Agent

## Summary

Successfully implemented the Portfolio Manager Agent - an AI-powered autonomous agent that monitors existing portfolios daily, analyzes market conditions, and generates actionable recommendations.

**Status**: COMPLETE
**Completion Date**: January 8, 2025
**Implementation Time**: ~3 hours

---

## What Was Built

### 1. Portfolio Manager Agent Core

**File**: `agents/portfolio_manager_agent.py` (600+ lines)

**Key Features**:
- Portfolio state loading from JSON
- Real-time price monitoring
- Stop-loss and target detection
- News analysis for holdings
- Market research integration
- AI-powered recommendation generation
- Database integration for updates

**Class Structure**:
```python
class PortfolioManagerAgent:
    def load_portfolio(profile) -> Dict
    def get_current_prices(stocks) -> Dict[str, float]
    def check_price_triggers(stocks, prices) -> Dict
    def analyze_portfolio_news(stocks) -> Dict
    def check_investment_triggers(stock, news) -> Dict
    def generate_recommendation(...) -> Dict
    def store_manager_update(...) -> int
    def run(profile) -> Dict
```

### 2. Tool Integration

**Same Tools as Portfolio Builder**:

1. **Stock News Agent** (`stock_news_agent.py`)
   - Analyzes recent news for each holding
   - Extracts sentiment and key events
   - Cached to avoid redundant fetches

2. **Market Research Agent** (`market_research_agent.py`)
   - Researches current market conditions
   - Nifty/Sensex outlook
   - Sector performance analysis

3. **Stock Screening Agent** (`stock_screening_agent.py`)
   - Available for finding new opportunities
   - Can re-screen existing holdings
   - Compare fundamentals over time

4. **Price Fetcher** (`tools/price_fetcher.py`)
   - Real-time price fetching
   - Yahoo Finance integration
   - Caching for efficiency

5. **Performance Calculator** (`tools/performance_calculator.py`)
   - Portfolio metrics
   - Risk calculations
   - Benchmark comparisons

### 3. Analysis Workflow

**Step 1: Portfolio Loading**
```python
portfolio = load_portfolio('aggressive')
# Loads from .cache/portfolios/latest_aggressive.json
```

**Step 2: Price Monitoring**
```python
current_prices = get_current_prices(stocks)
price_triggers = check_price_triggers(stocks, current_prices)

# Returns:
{
    'stop_loss_breached': [
        {
            'stock': {...},
            'current_price': 125.0,
            'stop_loss_price': 127.5,
            'breach_pct': -1.96,
            'current_pnl_pct': -16.67
        }
    ],
    'target_reached': [...],
    'approaching_target': [...]
}
```

**Step 3: News Analysis**
```python
news_analysis = analyze_portfolio_news(stocks)

# For each stock:
{
    'RELIANCE': {
        'sentiment': 'positive',
        'summary': 'Strong Q4 earnings...',
        'full_analysis': '...'
    }
}
```

**Step 4: Market Research**
```python
market_outlook = run_market_research(
    "Current Indian stock market trends, Nifty outlook, sector performance"
)
```

**Step 5: AI Recommendation**
```python
recommendation = generate_recommendation(
    portfolio,
    current_prices,
    price_triggers,
    news_analysis,
    market_outlook
)

# Returns structured JSON:
{
    "assessment": "Portfolio showing strong performance...",
    "immediate_actions": ["Book profits in RELIANCE", "Monitor TATASTEEL"],
    "stocks_to_review": ["TATASTEEL", "BAJAJFINSV"],
    "rebalancing_needed": false,
    "confidence_level": 85,
    "recommendation": "HOLD",
    "reasoning": "Despite market volatility..."
}
```

**Step 6: Database Storage**
```python
update_id = store_manager_update(
    portfolio_id,
    recommendation,
    price_triggers,
    priority='HIGH'
)
```

### 4. Example Runner Script

**File**: `examples/run_portfolio_manager.py` (100 lines)

**Features**:
- User-friendly output
- Summary display
- Critical stock highlights
- Recommendation details

**Usage**:
```bash
python examples/run_portfolio_manager.py
```

**Output**:
```
================================================================================
PORTFOLIO MANAGER AGENT - Daily Portfolio Analysis
================================================================================

ANALYSIS SUMMARY
================================================================================

Portfolio: AGGRESSIVE
Total Capital: Rs. 5,00,000
Holdings: 7 stocks

--- Price Triggers ---
Stop-loss breached: 1
Targets reached: 2
Approaching targets: 1

CRITICAL - Stop-Loss Breached:
  - Tata Steel Ltd (TATASTEEL)
    Current: Rs. 125.00 | Stop-Loss: Rs. 127.50 | P&L: -16.67%

SUCCESS - Targets Reached:
  - Reliance Industries Ltd (RELIANCE)
    Current: Rs. 3800.00 | Target: Rs. 3750.00 | P&L: +52.00%

--- AI Recommendation ---
Action: SELL
Priority: HIGH
Confidence: 85%

Assessment:
Portfolio requires immediate attention. One stop-loss breached (TATASTEEL),
two targets reached (RELIANCE, BAJAJFINSV). Market conditions remain favorable
but risk management suggests booking profits and limiting losses.

Immediate Actions:
  - Exit TATASTEEL position to limit losses
  - Book partial profits in RELIANCE (50-75% of position)
  - Set trailing stop for remaining RELIANCE position

Reasoning:
Stop-loss breach in TATASTEEL signals sector weakness. Steel facing headwinds
from China demand concerns. RELIANCE target achievement presents opportunity
to lock in 52% gains. Recommend profit booking while maintaining exposure to
energy sector strength through reduced position.

================================================================================
Update stored in database - view on dashboard!
================================================================================
```

### 5. Scheduler Integration

**File**: `scheduler.py` (Extended)

**New Task**: Daily Portfolio Manager
- **Timing**: 4:00 PM IST (after price updates)
- **Frequency**: Daily (Mon-Fri)
- **Trigger**: Automatically after prices update

**Full Schedule**:
```
3:45 PM IST - Daily Price Update
  ↓
4:00 PM IST - Portfolio Manager Analysis
  ↓
  [Updates stored in database]
  ↓
  [Visible on dashboard]
```

**Test Mode**: Runs both tasks immediately
```bash
python scheduler.py --test
```

**Daemon Mode**: Runs continuously with schedule
```bash
python scheduler.py --daemon
```

### 6. Comprehensive Documentation

**File**: `PORTFOLIO_MANAGER_GUIDE.md` (500+ lines)

**Contents**:
- How It Works (detailed workflow)
- Running methods (3 options)
- Output structure
- Recommendation types (HOLD/BUY_MORE/SELL/REBALANCE)
- Priority levels (CRITICAL/HIGH/MEDIUM/LOW)
- Confidence scoring
- Dashboard integration
- Example scenarios (with inputs/outputs)
- Configuration options
- Extending the agent
- Troubleshooting
- Best practices

---

## Key Features

### 1. Stop-Loss Monitoring

Automatically detects when prices breach stop-loss levels:

**Detection**:
```python
if current_price <= stop_loss_price:
    # CRITICAL alert
    priority = 'CRITICAL'
    recommendation = 'SELL'
```

**Dashboard Display**:
- Red alert card
- CRITICAL priority badge
- Immediate action needed
- Affected stock prominently shown

### 2. Target Achievement Detection

Identifies when stocks reach profit targets:

**Detection**:
```python
if current_price >= target_price:
    # SUCCESS alert
    priority = 'HIGH'
    recommendation = 'SELL' or 'HOLD with trailing stop'
```

**Dashboard Display**:
- Green success card
- TARGET REACHED badge
- Profit booking suggestion
- P&L percentage shown

### 3. Approaching Target Alerts

Early warning when near target (within 5%):

**Detection**:
```python
if current_price >= target_price * 0.95:
    # Monitor closely
    priority = 'MEDIUM'
    recommendation = 'HOLD'
```

**Dashboard Display**:
- Yellow info card
- APPROACHING TARGET badge
- Monitor suggestion

### 4. News-Based Triggers

Checks if news matches investment view triggers:

**Exit Triggers**:
- Conditions that invalidate thesis
- Example: "Revenue growth falls below 20%"
- Action: Consider selling

**Review Triggers**:
- Conditions requiring reassessment
- Example: "Regulatory challenges emerge"
- Action: Review position size

### 5. AI-Powered Recommendations

LLM analyzes all data points:

**Inputs**:
- Current prices vs entry/stop-loss/target
- News sentiment for each stock
- Market outlook (Nifty, sectors)
- Investment view triggers
- Portfolio profile (aggressive/defensive)

**Output**:
- Overall assessment
- Immediate actions list
- Stocks requiring review
- Rebalancing recommendation
- Confidence level (0-100%)
- Detailed reasoning

### 6. Priority-Based Alerting

Updates assigned priority based on urgency:

**CRITICAL**: Multiple stop-losses, urgent action
**HIGH**: Single stop-loss or target reached
**MEDIUM**: Approaching targets, routine signals
**LOW**: Regular review, no changes

### 7. Dashboard Integration

Updates visible in two places:

**Main Dashboard** (`/`):
- Latest update card
- Priority and recommendation badges
- Confidence score progress bar
- Link to full timeline

**Updates Timeline** (`/updates`):
- Complete history
- Filters by status/priority
- Grouped by date
- Expandable reasoning

---

## Technical Architecture

### Data Flow

```
Portfolio Manager Agent
  ↓
1. Load Portfolio (.cache/portfolios/latest_aggressive.json)
  ↓
2. Fetch Current Prices (Yahoo Finance via price_fetcher)
  ↓
3. Check Price Triggers (stop-loss, targets)
  ↓
4. Analyze News (stock_news_agent for each holding)
  ↓
5. Research Market (market_research_agent)
  ↓
6. Generate Recommendation (LLM with all context)
  ↓
7. Store Update (database: manager_updates table)
  ↓
8. Display on Dashboard (via FastAPI → Next.js)
```

### Agent Caching

Prevents redundant API calls:

```python
# Cache news analysis
cache_key = hashlib.md5(f"stock_news:{ticker}".encode()).hexdigest()
if cache_key in self._agent_cache:
    return self._agent_cache[cache_key]

# Fetch and cache
result = run_stock_news(query)
self._agent_cache[cache_key] = result
```

### Database Schema

**manager_updates table**:
```sql
CREATE TABLE manager_updates (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER,
    update_date DATE,
    update_type TEXT,  -- DAILY_REVIEW, SIGNAL_GENERATED, DECISION_MADE
    title TEXT,
    description TEXT,
    affected_stocks TEXT,  -- JSON array
    recommendation TEXT,  -- HOLD, BUY_MORE, SELL, REBALANCE
    reasoning TEXT,
    confidence_score REAL,
    priority TEXT,  -- LOW, MEDIUM, HIGH, CRITICAL
    status TEXT,  -- PENDING, EXECUTED, IGNORED
    created_at TIMESTAMP,
    executed_at TIMESTAMP
);
```

---

## Example Usage Scenarios

### Scenario 1: Aggressive Portfolio - Stop-Loss Breach

**Input State**:
- Profile: Aggressive
- Portfolio: 7 stocks, Rs. 5,00,000 capital
- TATASTEEL entry: Rs. 150, Stop-loss: Rs. 127.50
- Current price: Rs. 125 (-16.67%)

**Agent Analysis**:
1. **Price Check**: Stop-loss breached
2. **News**: "Steel sector headwinds, China demand concerns"
3. **Market**: "Metals underperforming"
4. **Investment View**: No specific exit triggers hit

**AI Recommendation**:
```json
{
  "assessment": "Critical: Stop-loss breached in TATASTEEL (-16.67%). Steel sector facing headwinds.",
  "immediate_actions": [
    "Exit TATASTEEL position immediately to limit losses",
    "Consider reallocating to defensive sectors"
  ],
  "stocks_to_review": ["TATAMOTORS (auto exposure)", "JSW (steel sector)"],
  "rebalancing_needed": true,
  "confidence_level": 90,
  "recommendation": "SELL",
  "reasoning": "Stop-loss breach with deteriorating sector fundamentals. China demand concerns impacting steel prices. Exit to preserve capital for better opportunities."
}
```

**Database Update**:
- Title: "Stop-Loss Alert: 1 stock breached"
- Priority: HIGH
- Affected stocks: ["TATASTEEL"]
- Status: PENDING

**Dashboard Display**:
- Red alert card
- "CRITICAL - Stop-Loss Breached: Tata Steel Ltd"
- SELL recommendation badge
- 90% confidence
- Link to full reasoning

### Scenario 2: Defensive Portfolio - Target Achieved

**Input State**:
- Profile: Defensive
- Portfolio: 5 stocks, Rs. 3,00,000 capital
- HDFCBANK entry: Rs. 1500, Target: Rs. 1725 (+15%)
- Current price: Rs. 1740 (+16%)

**Agent Analysis**:
1. **Price Check**: Target exceeded
2. **News**: "Record quarterly earnings, dividend announced"
3. **Market**: "Banking sector strength continues"
4. **Investment View**: No exit triggers

**AI Recommendation**:
```json
{
  "assessment": "Success: HDFCBANK target achieved (+16%). Strong earnings support further upside.",
  "immediate_actions": [
    "Book 50% profits to secure gains",
    "Set trailing stop-loss at 10% for remaining position"
  ],
  "stocks_to_review": [],
  "rebalancing_needed": false,
  "confidence_level": 75,
  "recommendation": "SELL",
  "reasoning": "Target achieved with strong fundamentals. Recommend partial profit booking (conservative approach for defensive profile) while maintaining exposure to banking sector strength via trailing stop."
}
```

**Database Update**:
- Title: "Target Achievement: 1 stock reached target"
- Priority: MEDIUM (defensive profile, smaller gains)
- Affected stocks: ["HDFCBANK"]
- Status: PENDING

**Dashboard Display**:
- Green success card
- "SUCCESS - Target Reached: HDFC Bank"
- SELL (partial) recommendation
- 75% confidence

### Scenario 3: Routine Daily Review

**Input State**:
- Profile: Aggressive
- Portfolio: 7 stocks, all within ranges
- Market: Sideways consolidation
- No critical news

**Agent Analysis**:
1. **Price Check**: All stocks within stop-loss and target
2. **News**: Generally positive, no red flags
3. **Market**: "Nifty consolidating, sideways movement"
4. **Investment View**: No triggers hit

**AI Recommendation**:
```json
{
  "assessment": "Portfolio healthy. All positions within acceptable ranges. No immediate action required.",
  "immediate_actions": [],
  "stocks_to_review": ["BAJAJFINSV (monitor credit growth trends)"],
  "rebalancing_needed": false,
  "confidence_level": 70,
  "recommendation": "HOLD",
  "reasoning": "Portfolio up 15% overall with strong fundamentals across holdings. Market consolidation presents opportunity to maintain positions and wait for next breakout. Monitor BAJAJFINSV sector trends."
}
```

**Database Update**:
- Title: "Daily Portfolio Review"
- Priority: LOW
- Affected stocks: null
- Status: PENDING

**Dashboard Display**:
- Gray/blue info card
- "Daily Review - All Positions Healthy"
- HOLD recommendation
- 70% confidence

---

## Configuration & Customization

### 1. Model Selection

```python
# High-tier model for complex decisions (recommended)
manager = PortfolioManagerAgent(model_name='high')

# Mid-tier for faster analysis
manager = PortfolioManagerAgent(model_name='mid')
```

### 2. Scheduler Timing

```python
# Change Portfolio Manager timing
scheduler.add_job(
    daily_portfolio_manager,
    trigger=CronTrigger(hour=16, minute=0, timezone='Asia/Kolkata'),
    ...
)
```

### 3. Custom Triggers

Add custom trigger logic:
```python
def check_momentum_trigger(self, stock, current_price):
    """Custom momentum-based trigger"""
    if current_price > stock['52_week_high'] * 0.98:
        return {
            'type': 'MOMENTUM_BREAKOUT',
            'action': 'BUY_MORE',
            'reasoning': 'Approaching 52-week high'
        }
    return None
```

### 4. Technical Indicators (Future)

```python
from tools.technical_indicators import calculate_rsi

def analyze_technicals(self, ticker):
    """Add technical analysis"""
    prices = self.price_fetcher.get_historical_prices(ticker, period='3mo')
    rsi = calculate_rsi(prices['close'])

    if rsi < 30:
        return {'signal': 'OVERSOLD', 'action': 'BUY_MORE'}
    elif rsi > 70:
        return {'signal': 'OVERBOUGHT', 'action': 'SELL'}

    return {'signal': 'NEUTRAL', 'action': 'HOLD'}
```

---

## File Structure

```
portfolio-agent/
├── agents/
│   ├── portfolio_builder_agent_simple.py    [Existing - Creates portfolio]
│   └── portfolio_manager_agent.py            [NEW - 600 lines - Manages portfolio]
├── examples/
│   ├── run_portfolio_builder.py             [Existing]
│   └── run_portfolio_manager.py              [NEW - 100 lines - Example runner]
├── scheduler.py                               [EXTENDED - +50 lines - Added manager task]
├── PORTFOLIO_MANAGER_GUIDE.md                 [NEW - 500+ lines - Complete guide]
├── PHASE5_COMPLETE.md                         [NEW - This file]
└── .cache/
    └── portfolios/
        └── latest_aggressive.json             [Loaded by manager]
```

**Total New Code**: ~750 lines
**Files Created**: 3
**Files Modified**: 1

---

## Integration with Existing System

### Portfolio Builder → Portfolio Manager Flow

```
1. User runs Portfolio Builder (one-time)
   ↓
2. Builder creates portfolio with guidance:
   - Entry prices
   - Stop-loss levels (profile-specific)
   - Target prices (profile-specific)
   - Investment views (exit/review triggers)
   ↓
3. Portfolio saved to .cache/portfolios/latest_aggressive.json
   ↓
4. Portfolio Manager runs daily (automated)
   ↓
5. Manager loads portfolio and monitors:
   - Current prices vs stop-loss/targets
   - News vs exit/review triggers
   - Market conditions
   ↓
6. Manager generates recommendations
   ↓
7. Updates stored in database
   ↓
8. Dashboard displays latest update
   ↓
9. User reviews and acts on recommendations
```

### Dashboard Integration Points

**Manager Update Card** (`/`):
- Fetches: `GET /api/manager-updates/1?limit=1`
- Displays: Latest update with priority/recommendation
- Shows: Confidence score, affected stocks
- Links: To full timeline

**Updates Timeline** (`/updates`):
- Fetches: `GET /api/manager-updates/1?status=...&priority=...&limit=50`
- Displays: Complete history with filters
- Groups: By date
- Allows: Expandable reasoning

---

## Testing & Verification

### Manual Test

```bash
# Run once
python examples/run_portfolio_manager.py
```

**Expected Output**:
1. Portfolio loaded
2. Prices fetched for all stocks
3. Triggers checked
4. News analyzed
5. Market researched
6. Recommendation generated
7. Update stored in database
8. Summary displayed

### Automated Test via Scheduler

```bash
# Test mode (runs immediately)
python scheduler.py --test
```

**Expected**:
1. Price update completes
2. Portfolio Manager runs
3. Recommendation logged
4. Database updated

**Verify**:
```bash
# Check database
sqlite3 .cache/portfolio.db "SELECT * FROM manager_updates ORDER BY created_at DESC LIMIT 1;"
```

### Dashboard Verification

1. Start backend: `python api/price_service.py`
2. Start frontend: `cd frontend && npm run dev`
3. Visit: http://localhost:3000
4. Check: Latest update card appears
5. Click: "View All Updates" → Full timeline
6. Verify: Filters work, details expandable

---

## Performance Considerations

### News Analysis Caching

- Agent caches news results per ticker
- Avoids redundant fetches in same run
- Clears on weekly cleanup

### Price Fetching

- Uses price_fetcher caching (5-min)
- Batch fetches where possible
- 100ms delay between requests

### LLM Calls

- Single recommendation call per run
- Structured JSON prompt for consistency
- High-tier model for quality

### Database

- Single insert per portfolio per day
- Indexed by (portfolio_id, update_date)
- Efficient queries for dashboard

---

## Troubleshooting

### Portfolio Not Found

**Error**: "No portfolio found for profile: aggressive"

**Solution**:
1. Run Portfolio Builder first
2. Verify `.cache/portfolios/latest_aggressive.json` exists
3. Check file has correct structure

### LLM Recommendation Fails

**Error**: "Failed to generate recommendation"

**Solution**:
1. Check GEMINI_API_KEY in `.env`
2. Verify model tier available
3. Check logs for detailed error
4. Agent returns fallback HOLD recommendation

### News Fetch Slow

**Issue**: Agent takes long time

**Solution**:
- News results are cached
- First run slower, subsequent runs faster
- Run during off-peak hours
- Consider using mid-tier model for news agent

---

## Future Enhancements

### Planned Features

1. **Technical Indicators**
   - RSI, MACD, moving averages
   - Support/resistance levels
   - Volume analysis integration

2. **Sentiment Scoring**
   - NLP-based news sentiment
   - Social media sentiment (Twitter/Reddit)
   - Analyst rating changes tracking

3. **Portfolio Rebalancing**
   - Automatic allocation adjustment
   - Sector rotation suggestions
   - Position sizing optimization

4. **Backtesting**
   - Test recommendations on historical data
   - Measure accuracy and profitability
   - Optimize thresholds

5. **Multi-Portfolio Management**
   - Manage multiple strategies
   - Cross-portfolio insights
   - Relative performance tracking

6. **Risk Management**
   - Portfolio-level stop-loss
   - Correlation analysis
   - Volatility-based position sizing

7. **Options Strategies**
   - Protective puts for downside
   - Covered calls for income
   - Collar strategies

---

## Best Practices

### 1. Run After Market Close

Schedule after prices are final (4:00 PM IST)

### 2. Review Daily

Check dashboard for CRITICAL/HIGH priority updates

### 3. Act on Recommendations

Use as guidance, apply judgment:
- Review reasoning carefully
- Consider confidence scores
- Override when appropriate

### 4. Track Performance

Monitor recommendation accuracy:
- Stop-loss saves
- Profit booking timing
- False alarm rate

### 5. Combine with Fundamentals

Agent focuses on price/news:
- Still review quarterly results
- Monitor management changes
- Track industry trends

---

## Conclusion

Portfolio Manager Agent is complete and provides:

**Autonomous Monitoring**:
- Daily price checks
- Automatic trigger detection
- News and market analysis

**AI-Powered Decisions**:
- LLM-based recommendations
- Confidence scoring
- Detailed reasoning

**Dashboard Integration**:
- Real-time updates
- Priority-based alerting
- Full history tracking

**Configurable & Extensible**:
- Custom triggers
- Model selection
- Scheduler integration

**Next Step**: Run daily via scheduler for automated portfolio management!

```bash
# Start automated daily management
python scheduler.py --daemon
```

---

**Portfolio Manager Agent is ready for production use! 🚀**
