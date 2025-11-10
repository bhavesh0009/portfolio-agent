# Portfolio Manager Agent - Quick Start Guide

Fast reference for implementing the Portfolio Manager Agent using the database and SQL agent.

## 5-Minute Setup

### Import Required Modules
```python
from utils.portfolio_query_helper import get_portfolio_helper
from agents.sql_agent import SQLAgent
from datetime import datetime, date
```

### Load Latest Portfolio
```python
helper = get_portfolio_helper()
portfolio_data = helper.load_latest_portfolio('aggressive')

if portfolio_data:
    portfolio = portfolio_data['portfolio']
    stocks = portfolio_data['stocks']
    print(f"Loaded {len(stocks)} stocks")
else:
    print("No active portfolio found")
```

## Common Manager Tasks

### 1. Monitor Risk - Check Stop-Loss Hits

```python
# Get current prices from your data source
current_prices = {
    'TECH': 95.0,      # Example prices
    'FIN': 185.0,
    'PHARMA': 92.0
}

# Check for stop-loss hits
stops_hit = helper.check_stop_loss_hits(
    portfolio['id'],
    current_prices
)

if stops_hit:
    for stock in stops_hit:
        print(f"ALERT: {stock['ticker']} hit stop-loss!")
        print(f"  Price: {stock['current_price']}")
        print(f"  Stop-loss: {stock['stop_loss_price']}")
        print(f"  Loss: {stock['loss_pct']:.1f}%")

        # Record the event
        sql_agent = SQLAgent()
        sql_agent.record_market_event_from_manager(
            portfolio_id=portfolio['id'],
            event_type='TRIGGER_HIT',
            title=f'Stop-Loss Hit: {stock["name"]}',
            description=f'Stock price {stock["current_price"]} <= {stock["stop_loss_price"]}',
            impact='NEGATIVE',
            stock_ticker=stock['ticker'],
            action_taken='Recommend exit'
        )
```

### 2. Monitor Gains - Check Target Hits

```python
targets_hit = helper.check_target_hits(
    portfolio['id'],
    current_prices
)

if targets_hit:
    for stock in targets_hit:
        print(f"INFO: {stock['ticker']} reached target!")
        print(f"  Price: {stock['current_price']}")
        print(f"  Target: {stock['target_price']}")
        print(f"  Gain: {stock['gain_pct']:.1f}%")

        # Record achievement
        sql_agent = SQLAgent()
        sql_agent.record_market_event_from_manager(
            portfolio_id=portfolio['id'],
            event_type='TRIGGER_HIT',
            title=f'Target Hit: {stock["name"]}',
            description=f'Stock price {stock["current_price"]} >= {stock["target_price"]}',
            impact='POSITIVE',
            stock_ticker=stock['ticker'],
            action_taken='Consider profit booking'
        )
```

### 3. Calculate Current Performance

```python
performance = helper.get_current_performance(
    portfolio['id'],
    current_prices
)

print(f"\nPortfolio Performance Summary")
print(f"=" * 50)
print(f"Total Invested: Rs. {performance['total_invested']:,.0f}")
print(f"Current Value: Rs. {performance['total_current_value']:,.0f}")
print(f"Total P&L: Rs. {performance['total_gain_loss']:,.0f}")
print(f"Return %: {performance['total_gain_loss_pct']:.2f}%")

print(f"\nStock-wise Performance:")
for stock in performance['stocks'][:5]:  # Top 5
    print(f"{stock['ticker']:8} {stock['gain_loss_pct']:>7.2f}%  Rs. {stock['gain_loss']:>10,.0f}")
```

### 4. Check for Allocation Drift (Rebalancing)

```python
recommendation = helper.generate_rebalancing_recommendation(
    portfolio['id'],
    current_prices,
    allocation_drift_threshold=5.0  # Trigger if drift > 5%
)

if recommendation:
    print(f"\nRebalancing Recommended!")
    print(f"Reason: {recommendation['reason']}")
    print(f"\nDrifted Stocks:")

    for drift in recommendation['drifts']:
        print(f"{drift['ticker']:8} {drift['direction']}allocated")
        print(f"  Target: {drift['target_pct']:.1f}%  Current: {drift['current_pct']:.1f}%")

    # Record rebalancing plan
    from agents.sql_agent import SQLAgent
    sql_agent = SQLAgent()

    affected_tickers = [d['ticker'] for d in recommendation['drifts']]
    allocation_changes = {}

    # Build allocation changes from current vs target
    for drift in recommendation['drifts']:
        allocation_changes[drift['ticker']] = (
            drift['current_pct'],
            drift['target_pct']
        )

    db = get_db_service()
    db.record_rebalancing(
        portfolio_id=portfolio['id'],
        rebalancing_date=datetime.now(),
        reason=f"Allocation drift: {recommendation['reason']}",
        action_type='ADJUSTMENT',
        affected_stocks=affected_tickers,
        allocation_changes=allocation_changes,
        expected_result='Realign to target allocations'
    )
```

### 5. Record Market Events (News, Regulatory, etc.)

```python
sql_agent = SQLAgent()

# Example: Earnings announcement
sql_agent.record_market_event_from_manager(
    portfolio_id=portfolio['id'],
    event_type='EARNINGS',
    title='Q3 Earnings Beat',
    description='TECH company exceeded revenue estimates by 12%',
    impact='POSITIVE',
    stock_ticker='TECH',
    action_taken='Increased conviction, hold position'
)

# Example: Regulatory change
sql_agent.record_market_event_from_manager(
    portfolio_id=portfolio['id'],
    event_type='REGULATORY',
    title='New Tax Policy',
    description='Government announced higher corporate tax on tech sector',
    impact='NEGATIVE',
    action_taken='Monitor earnings impact'
)

# Example: Market event
sql_agent.record_market_event_from_manager(
    portfolio_id=portfolio['id'],
    event_type='ECONOMIC',
    title='Rate Hike Expected',
    description='RBI signals potential rate increase at next meeting',
    impact='NEGATIVE',
    action_taken='Reduce leverage, prepare for volatility'
)
```

### 6. Query Investment Views (Decision Triggers)

```python
for stock in stocks:
    view = helper.db_service.get_investment_view(stock['id'])

    if view:
        print(f"\n{stock['name']} ({stock['ticker']})")
        print(f"Investment Thesis:")
        print(f"  Market Outlook: {view['market_outlook']}")
        print(f"  Rationale: {view['stock_rationale']}")
        print(f"  Holding Period: {view['holding_period']}")
        print(f"  Exit Triggers: {', '.join(view['exit_triggers'])}")
        print(f"  Review Triggers: {', '.join(view['review_triggers'])}")
```

### 7. Check Transaction History

```python
from datetime import timedelta

recent_tx = helper.get_recent_transactions(
    portfolio['id'],
    days=30  # Last 30 days
)

print(f"\nRecent Transactions (Last 30 days)")
for tx in recent_tx[:10]:
    print(f"{tx['transaction_date']}: {tx['transaction_type']:4} {tx['quantity']:3} @ {tx['price']:7.2f}")
```

### 8. Check Rebalancing History

```python
history = helper.get_rebalancing_history(
    portfolio['id'],
    limit=5  # Last 5 rebalancing events
)

print(f"\nRebalancing History")
for event in history:
    print(f"{event['rebalancing_date']}: {event['reason']}")
    print(f"  Type: {event['action_type']}")
    print(f"  Status: {event['status']}")
```

### 9. Get Recent Market Events

```python
recent_events = helper.get_recent_market_events(
    portfolio['id'],
    days=7  # Last 7 days
)

print(f"\nRecent Market Events")
for event in recent_events:
    print(f"{event['event_date']}: [{event['event_type']}] {event['title']}")
    print(f"  Impact: {event['impact']}")
    if event['action_taken']:
        print(f"  Action: {event['action_taken']}")
```

### 10. Natural Language Portfolio Queries

```python
sql_agent = SQLAgent()

# Example 1: Find high-conviction stocks
result = sql_agent.natural_language_to_sql(
    query="Show me stocks with allocation > 20% and positive sentiment",
    portfolio_id=portfolio['id']
)

if result['action'] == 'query_success':
    print(f"Found {result['row_count']} matching stocks")
    for row in result['results']:
        print(f"  {row['ticker']}: {row['allocation_pct']:.1f}%")

# Example 2: Get fundamental strength
result = sql_agent.natural_language_to_sql(
    query="Which stocks have ROE > 25% and growth > 30%?",
    portfolio_id=portfolio['id']
)

# Example 3: Sector composition
result = sql_agent.natural_language_to_sql(
    query="Show me portfolio composition by sector with total allocation",
    portfolio_id=portfolio['id']
)
```

## Complete Manager Loop

```python
def run_portfolio_manager(portfolio_profile='aggressive'):
    """Complete portfolio manager loop"""

    helper = get_portfolio_helper()
    sql_agent = SQLAgent()

    # 1. Load portfolio
    portfolio_data = helper.load_latest_portfolio(portfolio_profile)
    if not portfolio_data:
        print("No portfolio found")
        return

    portfolio = portfolio_data['portfolio']
    portfolio_id = portfolio['id']

    # 2. Get current prices (from your data source)
    current_prices = get_current_prices()  # Your implementation

    # 3. Calculate performance
    performance = helper.get_current_performance(portfolio_id, current_prices)
    print(f"Portfolio Value: Rs. {performance['total_current_value']:,.0f}")
    print(f"Return: {performance['total_gain_loss_pct']:.2f}%")

    # 4. Check risk
    stops = helper.check_stop_loss_hits(portfolio_id, current_prices)
    if stops:
        for stock in stops:
            print(f"ACTION: Exit {stock['ticker']} (stop-loss hit)")
            sql_agent.record_market_event_from_manager(
                portfolio_id=portfolio_id,
                event_type='TRIGGER_HIT',
                title='Stop-Loss Hit',
                description=f"{stock['ticker']} hit {stock['stop_loss_price']}",
                impact='NEGATIVE',
                stock_ticker=stock['ticker'],
                action_taken='Exit position'
            )

    # 5. Check gains
    targets = helper.check_target_hits(portfolio_id, current_prices)
    if targets:
        for stock in targets:
            print(f"ACTION: Consider booking profit on {stock['ticker']}")
            sql_agent.record_market_event_from_manager(
                portfolio_id=portfolio_id,
                event_type='TRIGGER_HIT',
                title='Target Hit',
                description=f"{stock['ticker']} reached {stock['target_price']}",
                impact='POSITIVE',
                stock_ticker=stock['ticker'],
                action_taken='Book profit'
            )

    # 6. Check for rebalancing
    rebalancing = helper.generate_rebalancing_recommendation(
        portfolio_id, current_prices, threshold=5.0
    )
    if rebalancing:
        print(f"ACTION: Rebalance portfolio")
        # Record and execute rebalancing

    # 7. Log summary
    print("\nPortfolio Manager Review Complete")
    print(f"Timestamp: {datetime.now()}")
```

## Database Functions Reference

### Portfolio Query Helper (High-level)
```python
helper.load_latest_portfolio(profile)
helper.check_stop_loss_hits(portfolio_id, prices)
helper.check_target_hits(portfolio_id, prices)
helper.get_current_performance(portfolio_id, prices)
helper.check_investment_view_triggers(portfolio_id, changes)
helper.generate_rebalancing_recommendation(portfolio_id, prices, threshold)
helper.get_recent_transactions(portfolio_id, days)
helper.get_rebalancing_history(portfolio_id, limit)
helper.get_recent_market_events(portfolio_id, days)
```

### SQL Agent (Mid-level)
```python
sql_agent.query_portfolio_summary(portfolio_id)
sql_agent.query_stock_performance(portfolio_id, ticker, days)
sql_agent.query_trigger_hits(portfolio_id, trigger_type)
sql_agent.natural_language_to_sql(query, portfolio_id, context)
sql_agent.record_market_event_from_manager(portfolio_id, event_type, title, ...)
```

### Database Service (Low-level)
```python
db.get_active_portfolio(profile)
db.get_portfolio_stocks(portfolio_id)
db.get_investment_view(stock_id)
db.get_key_metrics(stock_id)
db.record_transaction(...)
db.record_performance(...)
db.record_rebalancing(...)
db.record_market_event(...)
db.portfolio_summary(portfolio_id)
db.execute_query(sql, params)
```

## Debugging Tips

### Check Database Connection
```python
from utils.db_service import get_db_service
db = get_db_service()
portfolio = db.get_active_portfolio('aggressive')
print(f"Active portfolio ID: {portfolio['id'] if portfolio else 'None'}")
```

### View Raw Data
```python
from utils.db_service import get_db_service
db = get_db_service()
stocks = db.get_portfolio_stocks(1)
for stock in stocks:
    print(f"{stock['ticker']}: {stock['name']}")
```

### Check Logs
```bash
# View latest logs
ls -lart logs/ | tail -1
tail -f logs/portfolio_agent_*.log
```

### Test SQL Queries
```python
from utils.db_service import get_db_service
db = get_db_service()
results = db.execute_query(
    "SELECT ticker, allocation_pct FROM stocks WHERE portfolio_id = ? ORDER BY allocation_pct DESC",
    (1,)
)
for row in results:
    print(f"{row['ticker']}: {row['allocation_pct']:.1f}%")
```

## Next Steps

1. **Implement Scheduled Execution**
   - Daily: Run manager at market close
   - Weekly: Send performance report
   - Monthly: Review and rebalance

2. **Add Data Integration**
   - Get current prices from yfinance or broker API
   - Fetch news from news API
   - Get fundamental changes from screener.in

3. **Build Decision Rules**
   - Define conditions for various actions
   - Implement automated triggers
   - Log all decisions

4. **Create Reporting**
   - Daily performance email
   - Weekly portfolio summary
   - Monthly returns and rebalancing report

5. **Monitor and Tune**
   - Track actual vs expected returns
   - Adjust allocation thresholds
   - Refine decision rules

---

**Database Location**: `.cache/portfolio.db`

**Configuration**: `config.ini [DATABASE]` section

**Documentation**: `docs/DATABASE_INTEGRATION.md`

**Examples**: `examples/run_database_integration.py`
