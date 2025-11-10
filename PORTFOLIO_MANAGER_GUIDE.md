# Portfolio Manager Agent - Complete Guide

The Portfolio Manager Agent is an AI-powered autonomous agent that monitors your existing portfolio daily, analyzes market conditions, and generates actionable recommendations.

## Overview

**Purpose**: Daily portfolio monitoring and management

**Key Features**:
- Monitors current prices vs stop-loss/targets
- Analyzes recent news for portfolio holdings
- Researches market conditions
- Evaluates investment view triggers
- Generates AI-powered recommendations
- Stores updates in database for dashboard display

**Tool Access**: Same tools as Portfolio Builder
- Stock News Agent (`stock_news_agent.py`)
- Market Research Agent (`market_research_agent.py`)
- Stock Screening Agent (`stock_screening_agent.py`)
- Price Fetcher (Yahoo Finance)
- Performance Calculator

## How It Works

### 1. Portfolio Loading

Loads the latest portfolio from `.cache/portfolios/latest_{profile}.json`

```python
portfolio = {
    'profile': 'aggressive',
    'total_capital': 500000,
    'stocks': [
        {
            'ticker': 'RELIANCE',
            'entry_price': 2500,
            'stop_loss_price': 2125,
            'target_price': 3750,
            'investment_view': {
                'exit_triggers': [...],
                'review_triggers': [...]
            }
        },
        ...
    ]
}
```

### 2. Price Monitoring

Fetches current prices for all holdings and checks against thresholds:

**Stop-Loss Breach**: Current price ≤ stop-loss price
- **Action**: Consider exiting position
- **Priority**: CRITICAL or HIGH
- **Recommendation**: SELL

**Target Reached**: Current price ≥ target price
- **Action**: Consider booking profits
- **Priority**: HIGH
- **Recommendation**: SELL or HOLD with trailing stop

**Approaching Target**: Current price ≥ 95% of target
- **Action**: Monitor closely
- **Priority**: MEDIUM
- **Recommendation**: HOLD

### 3. News Analysis

For each stock, analyzes recent news using `stock_news_agent`:

```python
news_analysis = {
    'RELIANCE': {
        'sentiment': 'positive',
        'summary': 'Strong Q4 earnings, retail growth...',
        'full_analysis': '...'
    }
}
```

Checks if news matches investment view triggers:
- **Exit Triggers**: Conditions that invalidate investment thesis
- **Review Triggers**: Conditions requiring reassessment

### 4. Market Research

Analyzes overall market conditions using `market_research_agent`:

```python
query = "Current Indian stock market trends, Nifty outlook, sector performance"
market_outlook = run_market_research(query)
```

### 5. AI Recommendation Generation

LLM analyzes all data and generates structured recommendation:

```json
{
  "assessment": "Portfolio showing strong performance with 2 targets reached...",
  "immediate_actions": [
    "Book partial profits in RELIANCE (target reached)",
    "Monitor TATASTEEL closely (approaching stop-loss)"
  ],
  "stocks_to_review": ["TATASTEEL", "BAJAJFINSV"],
  "rebalancing_needed": false,
  "confidence_level": 85,
  "recommendation": "HOLD",
  "reasoning": "Despite market volatility, portfolio fundamentals remain strong..."
}
```

### 6. Database Storage

Stores update in `manager_updates` table:

```sql
INSERT INTO manager_updates (
    portfolio_id,
    update_date,
    update_type,
    title,
    description,
    affected_stocks,
    recommendation,
    reasoning,
    confidence_score,
    priority,
    status
) VALUES (...)
```

Update is then visible on dashboard.

## Running the Portfolio Manager

### Method 1: Direct Execution

```bash
# Run for aggressive portfolio
python examples/run_portfolio_manager.py

# Run programmatically
python -c "from agents.portfolio_manager_agent import run_portfolio_manager; run_portfolio_manager('aggressive')"
```

### Method 2: Via Scheduler (Automated Daily)

```bash
# Test mode (runs immediately)
python scheduler.py --test

# Daemon mode (runs daily at 4:00 PM IST)
python scheduler.py --daemon
```

Scheduled tasks:
- **3:45 PM IST**: Price updates
- **4:00 PM IST**: Portfolio Manager analysis
- **Sunday 12 AM IST**: Cache cleanup

### Method 3: Standalone Script

```python
from agents.portfolio_manager_agent import PortfolioManagerAgent

# Create agent
manager = PortfolioManagerAgent(model_name='high')

# Run analysis
result = manager.run(profile='aggressive')

if result['success']:
    recommendation = result['recommendation']
    print(f"Recommendation: {recommendation['recommendation']}")
    print(f"Confidence: {recommendation['confidence_level']}%")
```

## Output Structure

The agent returns a comprehensive results dict:

```python
{
    'success': True,
    'portfolio': {...},           # Full portfolio data
    'current_prices': {...},      # Ticker → price mapping
    'price_triggers': {           # Breaches detected
        'stop_loss_breached': [...],
        'target_reached': [...],
        'approaching_target': [...]
    },
    'news_analysis': {...},       # Per-stock news sentiment
    'market_outlook': '...',      # General market analysis
    'recommendation': {...},      # AI recommendation
    'priority': 'HIGH'            # Update priority
}
```

## Recommendation Types

### HOLD
**When**: Portfolio healthy, no immediate actions needed
- No stop-loss breaches
- Targets not yet reached
- Positive market outlook
- Fundamentals intact

**Dashboard Display**: Green badge, low priority

### BUY_MORE
**When**: Opportunity to add to positions
- Stock performing well
- Price dip presents entry
- Market conditions favorable
- Capital available for deployment

**Dashboard Display**: Blue badge, medium priority

### SELL
**When**: Exit positions
- Stop-loss breached
- Target reached (book profits)
- Investment thesis invalidated
- Deteriorating fundamentals

**Dashboard Display**: Red badge, high/critical priority

### REBALANCE
**When**: Allocation drift significant
- Some stocks overweight/underweight
- Need to restore target allocation
- Sector concentration too high
- Risk profile changed

**Dashboard Display**: Yellow badge, medium priority

## Priority Levels

### CRITICAL
- Multiple stop-loss breaches
- Significant portfolio deterioration
- Urgent action required within 24 hours

**Example**: "3 stocks breached stop-loss, portfolio down 8%"

### HIGH
- Single stop-loss breach
- Multiple targets reached
- Important news affecting holdings

**Example**: "RELIANCE breached stop-loss at Rs. 2100"

### MEDIUM
- Approaching targets
- Sector rotation recommended
- Moderate news impact

**Example**: "2 stocks approaching targets, monitor closely"

### LOW
- Regular daily review
- No significant changes
- Portfolio stable

**Example**: "Daily portfolio review - all positions healthy"

## Confidence Scoring

The LLM assigns confidence (0-100%) based on:

**High Confidence (75-100%)**:
- Clear price triggers
- Strong supporting news
- Aligned market outlook
- Consistent fundamental data

**Medium Confidence (50-74%)**:
- Mixed signals
- Moderate news impact
- Uncertain market conditions
- Partial data available

**Low Confidence (0-49%)**:
- Conflicting information
- Limited data
- High market volatility
- Unclear implications

Confidence score displayed as progress bar on dashboard.

## Dashboard Integration

Updates appear on dashboard in two places:

### 1. Main Dashboard - Latest Update Card

Shows most recent manager update:
- Title and priority badge
- Recommendation with icon
- Description
- Affected stocks
- Confidence score progress bar
- Link to full timeline

### 2. Updates Timeline Page (`/updates`)

Complete history with:
- Filters by status/priority
- Grouped by date
- Expandable reasoning
- Full analysis details

## Example Scenarios

### Scenario 1: Stop-Loss Breach

**Input**:
- TATASTEEL entry: Rs. 150
- Stop-loss: Rs. 127.50 (-15%)
- Current price: Rs. 125

**Analysis**:
- Breach detected: -16.67% from entry
- News check: "Steel sector facing headwinds"
- Market: "Metals underperforming amid China concerns"

**Recommendation**:
```json
{
  "recommendation": "SELL",
  "confidence_level": 90,
  "immediate_actions": [
    "Exit TATASTEEL position to limit losses",
    "Consider reallocating to defensive sectors"
  ],
  "reasoning": "Stop-loss breached with deteriorating sector outlook..."
}
```

**Priority**: HIGH

**Dashboard**: Red alert card, SELL badge

### Scenario 2: Target Achieved

**Input**:
- RELIANCE entry: Rs. 2500
- Target: Rs. 3750 (+50%)
- Current price: Rs. 3800

**Analysis**:
- Target exceeded: +52% gain
- News: "Record earnings, dividend announced"
- Market: "Energy sector strength continues"

**Recommendation**:
```json
{
  "recommendation": "SELL",
  "confidence_level": 75,
  "immediate_actions": [
    "Book partial profits (50-75% of position)",
    "Set trailing stop-loss for remaining position"
  ],
  "reasoning": "Target achieved, consider profit booking while market strong..."
}
```

**Priority**: HIGH

**Dashboard**: Green success card, TARGET REACHED badge

### Scenario 3: Routine Review

**Input**:
- All stocks within stop-loss and target range
- Portfolio up 15% overall
- No critical news

**Analysis**:
- No triggers breached
- News: Generally positive
- Market: "Nifty consolidating, sideways movement"

**Recommendation**:
```json
{
  "recommendation": "HOLD",
  "confidence_level": 70,
  "stocks_to_review": [],
  "immediate_actions": [],
  "reasoning": "Portfolio healthy, no changes needed. Continue monitoring..."
}
```

**Priority**: LOW

**Dashboard**: Gray info card, HOLD badge

## Configuration

### Model Selection

```python
# Use high-tier model for complex decisions (recommended)
manager = PortfolioManagerAgent(model_name='high')

# Use mid-tier for faster but simpler analysis
manager = PortfolioManagerAgent(model_name='mid')
```

Configured via environment variables:
- `GEMINI_HIGH_MODEL`: gemini-2.5-pro
- `GEMINI_MID_MODEL`: gemini-2.5-flash

### Scheduler Timing

Edit `scheduler.py` to change timing:

```python
# Portfolio Manager at 4:00 PM IST
scheduler.add_job(
    daily_portfolio_manager,
    trigger=CronTrigger(hour=16, minute=0, timezone='Asia/Kolkata'),
    ...
)
```

### News Analysis Depth

Modify `analyze_portfolio_news()` to change:
- Number of news sources
- Lookback period
- Sentiment extraction method

## Extending the Agent

### Add Custom Triggers

```python
def check_custom_triggers(self, stock, current_price):
    """Add your custom trigger logic"""
    # Example: Momentum-based trigger
    if stock['52_week_high'] and current_price > stock['52_week_high'] * 0.98:
        return {'type': 'MOMENTUM_BREAKOUT', 'action': 'BUY_MORE'}

    return None
```

### Add Technical Analysis

```python
from tools.technical_indicators import calculate_rsi, calculate_macd

def analyze_technicals(self, ticker):
    """Add technical analysis"""
    prices = self.price_fetcher.get_historical_prices(ticker, period='3mo')

    rsi = calculate_rsi(prices['close'])
    macd = calculate_macd(prices['close'])

    return {'rsi': rsi, 'macd': macd}
```

### Custom Recommendation Logic

Override `generate_recommendation()` to add custom logic:

```python
def generate_recommendation(self, ...):
    """Custom recommendation with additional factors"""

    # Get base recommendation from LLM
    base_rec = super().generate_recommendation(...)

    # Add custom logic
    if self.check_sector_concentration(portfolio) > 40:
        base_rec['rebalancing_needed'] = True

    return base_rec
```

## Troubleshooting

### Issue: Portfolio Not Found

**Error**: "Portfolio not found for profile: aggressive"

**Cause**: No portfolio file exists

**Solution**:
1. Run Portfolio Builder first to create portfolio
2. Check `.cache/portfolios/latest_aggressive.json` exists
3. Verify file has correct structure

### Issue: Price Fetch Failures

**Error**: "Failed to fetch price for TICKER"

**Cause**: Yahoo Finance API issues or invalid ticker

**Solution**:
- System uses fallback entry price automatically
- Check ticker format (should be TICKER.NS or TICKER.BO)
- Verify stock still trades
- Try manual price fetch test

### Issue: News Analysis Slow

**Issue**: Agent takes long time on news step

**Cause**: Fetching news for many stocks

**Solution**:
- Enable agent caching (already implemented)
- Reduce portfolio size
- Run during off-peak hours
- Use faster model tier for news agent

### Issue: LLM Recommendation Fails

**Error**: "Failed to generate recommendation"

**Cause**: LLM API error or invalid response

**Solution**:
- Check GEMINI_API_KEY in `.env`
- Verify model availability
- Check logs for detailed error
- Use fallback recommendation (HOLD)

## Best Practices

### 1. Run Daily After Market Close

Schedule after 4:00 PM IST when prices are final:
```bash
python scheduler.py --daemon
```

### 2. Review Updates Regularly

Check dashboard daily for:
- CRITICAL/HIGH priority updates
- Stop-loss breaches
- Target achievements

### 3. Act on Recommendations

Manager provides analysis, but you decide:
- Review reasoning carefully
- Consider confidence scores
- Use as guidance, not gospel
- Override with your judgment

### 4. Monitor False Positives

Track recommendation accuracy:
- Did stop-loss saves prevent losses?
- Were profit bookings timely?
- Adjust thresholds if needed

### 5. Combine with Fundamentals

Agent focuses on price/news/market:
- Still review quarterly results
- Monitor management changes
- Track industry trends
- Use screening for new ideas

## Performance Metrics

Track Portfolio Manager effectiveness:

**Accuracy**: % of recommendations that were correct
**Timeliness**: Days between trigger and action
**Loss Prevention**: Saved by stop-loss exits
**Profit Capture**: Gains from target exits
**False Alarms**: Incorrect trigger alerts

## Future Enhancements

Planned improvements:

1. **Technical Indicators**
   - RSI, MACD, moving averages
   - Support/resistance levels
   - Volume analysis

2. **Sentiment Scoring**
   - NLP-based news sentiment
   - Social media sentiment
   - Analyst rating changes

3. **Options Strategies**
   - Protective puts
   - Covered calls
   - Collar strategies

4. **Backtesting**
   - Test recommendations on historical data
   - Optimize thresholds
   - Measure performance

5. **Multi-Portfolio Support**
   - Manage multiple strategies
   - Cross-portfolio insights
   - Relative performance

## Summary

Portfolio Manager Agent provides:
- **Automated monitoring** of positions
- **AI-powered analysis** of news and market
- **Actionable recommendations** with reasoning
- **Dashboard integration** for easy access
- **Configurable triggers** for your strategy

Run daily via scheduler for hands-off portfolio management!

---

**Next Steps**: After running Portfolio Manager a few times, you'll have rich data on dashboard showing daily analysis, recommendations, and tracking your portfolio performance over time.
