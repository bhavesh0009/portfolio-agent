# Portfolio Database Integration

Complete guide to the SQLite database storage system and SQL agent for portfolio management.

## Overview

The portfolio database system provides:

1. **Persistent Storage** - SQLite database for all portfolio, stock, and decision data
2. **Dual Format** - JSON files (legacy) + database (new)
3. **SQL Agent** - AI-powered natural language to SQL conversion
4. **Query Helper** - Convenience functions for common portfolio queries
5. **Audit Trail** - Complete history of transactions, events, and rebalancing decisions

## Architecture

```
Portfolio Builder Agent
        |
        v
    Build Portfolio (JSON)
        |
        +----> Save JSON (backward compatible)
        |
        +----> SQL Agent
                    |
                    v
            Generate INSERTs
                    |
                    v
            SQLite Database
                    |
                    +----> Schema: portfolios, stocks, investment_views, etc.
                    +----> Indices: For efficient querying
                    +----> Transactions: ACID compliance

Portfolio Manager Agent
        |
        v
    Portfolio Query Helper
        |
        +----> SQL Agent (natural language queries)
        |
        +----> Database Service (raw SQL)
        |
        v
    Decision Making
        |
        +----> Record Events
        +----> Track Performance
        +----> Plan Rebalancing
```

## Database Schema

### Core Tables

#### `portfolios`
Stores portfolio metadata.

```sql
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY,
    profile TEXT,              -- 'aggressive' or 'defensive'
    total_capital REAL,
    created_at TIMESTAMP,
    timestamp TEXT,            -- YYYYMMDD_HHMMSS
    json_path TEXT,           -- Path to JSON backup
    is_active BOOLEAN
);
```

#### `stocks`
Stores stock holdings with allocations and risk parameters.

```sql
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER FK,
    name TEXT,
    ticker TEXT,
    sector TEXT,
    entry_price REAL,
    allocation_pct REAL,
    allocation_amount REAL,
    stop_loss_pct REAL,
    stop_loss_price REAL,
    target_pct REAL,
    target_price REAL,
    rationale TEXT,
    news_sentiment TEXT
);
```

#### `investment_views`
Investment thesis and decision triggers per stock.

```sql
CREATE TABLE investment_views (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER FK,
    market_outlook TEXT,
    stock_rationale TEXT,
    holding_period TEXT,
    exit_triggers TEXT,       -- JSON array
    review_triggers TEXT      -- JSON array
);
```

#### `key_metrics`
Snapshot of fundamental metrics at portfolio creation.

```sql
CREATE TABLE key_metrics (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER FK,
    metrics_json TEXT         -- JSON object of all metrics
);
```

### Transaction & Event Tables

#### `transactions`
Buy/sell transaction history.

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER FK,
    stock_id INTEGER FK,
    transaction_type TEXT,    -- 'BUY' or 'SELL'
    quantity INTEGER,
    price REAL,
    total_amount REAL,
    transaction_date TIMESTAMP
);
```

#### `performance_metrics`
Daily/periodic portfolio and stock performance.

```sql
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER FK,
    stock_id INTEGER FK,      -- NULL for portfolio-level
    metric_date DATE,
    portfolio_value REAL,
    stock_value REAL,
    daily_return_pct REAL,
    cumulative_return_pct REAL,
    status TEXT               -- 'HOLDING', 'TARGET_HIT', 'STOP_LOSS_HIT'
);
```

#### `rebalancing_history`
Rebalancing decisions and actions.

```sql
CREATE TABLE rebalancing_history (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER FK,
    rebalancing_date TIMESTAMP,
    reason TEXT,
    action_type TEXT,         -- 'ADJUSTMENT', 'ROTATION', 'EXIT'
    affected_stocks TEXT,     -- JSON array of tickers
    allocation_changes TEXT,  -- JSON object
    status TEXT               -- 'PENDING', 'EXECUTED', 'CANCELLED'
);
```

#### `market_events`
Significant market events and decision triggers.

```sql
CREATE TABLE market_events (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER FK,
    stock_id INTEGER FK,
    event_type TEXT,         -- 'NEWS', 'TRIGGER_HIT', 'EARNINGS', etc.
    title TEXT,
    description TEXT,
    impact TEXT,             -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    action_taken TEXT,
    event_date TIMESTAMP,
    source TEXT
);
```

## Components

### 1. Database Service (`utils/db_service.py`)

Provides low-level database operations:

```python
from utils.db_service import get_db_service

db = get_db_service()

# Save portfolio
portfolio_id = db.save_portfolio(
    portfolio_data={'stocks': [...]},
    profile='aggressive',
    timestamp='20250101_100000'
)

# Get portfolio stocks
stocks = db.get_portfolio_stocks(portfolio_id)

# Record transaction
db.record_transaction(
    portfolio_id=portfolio_id,
    stock_id=stock_id,
    transaction_type='BUY',
    quantity=100,
    price=100.0,
    transaction_date=datetime.now()
)

# Record performance
db.record_performance(
    portfolio_id=portfolio_id,
    metric_date=date.today(),
    portfolio_value=510000.0,
    daily_return_pct=2.0
)

# Record rebalancing
db.record_rebalancing(
    portfolio_id=portfolio_id,
    rebalancing_date=datetime.now(),
    reason='Allocation drift',
    action_type='ADJUSTMENT',
    affected_stocks=['TECH', 'FIN'],
    allocation_changes={'TECH': (30.0, 25.0), 'FIN': (40.0, 45.0)}
)

# Record market event
db.record_market_event(
    event_type='NEWS',
    title='Earnings Beat',
    description='Company exceeded expectations',
    event_date=datetime.now(),
    portfolio_id=portfolio_id,
    impact='POSITIVE'
)

# Get portfolio summary
summary = db.portfolio_summary(portfolio_id)
```

### 2. SQL Agent (`agents/sql_agent.py`)

AI-powered SQL generation and natural language queries:

```python
from agents.sql_agent import SQLAgent

agent = SQLAgent(model_name='mid')

# Generate INSERTs from portfolio JSON
result = agent.generate_insert_from_portfolio(
    portfolio_data=portfolio_dict,
    profile='aggressive',
    timestamp='20250101_100000',
    json_path='/path/to/portfolio.json',
    execute=True  # Auto-save to database
)

# Natural language queries
query_result = agent.natural_language_to_sql(
    query="Show me all stocks with allocation > 20%",
    portfolio_id=1
)

# Convenience query methods
summary = agent.query_portfolio_summary(portfolio_id)
performance = agent.query_stock_performance(portfolio_id, ticker='TECH')
triggers = agent.query_trigger_hits(portfolio_id)

# Record market events
event = agent.record_market_event_from_manager(
    portfolio_id=portfolio_id,
    event_type='NEWS',
    title='Positive News',
    description='Details here',
    impact='POSITIVE',
    stock_ticker='TECH',
    action_taken='Hold position'
)
```

### 3. Portfolio Query Helper (`utils/portfolio_query_helper.py`)

High-level portfolio management functions:

```python
from utils.portfolio_query_helper import get_portfolio_helper

helper = get_portfolio_helper()

# Load latest portfolio
portfolio = helper.load_latest_portfolio('aggressive')

# Check for stop-loss hits
stops_hit = helper.check_stop_loss_hits(
    portfolio_id=1,
    current_prices={'TECH': 95.0, 'FIN': 180.0}
)

# Check for target hits
targets_hit = helper.check_target_hits(
    portfolio_id=1,
    current_prices={'TECH': 150.0, 'FIN': 320.0}
)

# Calculate current performance
performance = helper.get_current_performance(
    portfolio_id=1,
    current_prices={'TECH': 105.0, 'FIN': 190.0}
)

# Check investment view triggers
triggered = helper.check_investment_view_triggers(
    portfolio_id=1,
    fundamental_changes={'TECH': {'revenue_growth': -5.0}}
)

# Get rebalancing recommendation
recommendation = helper.generate_rebalancing_recommendation(
    portfolio_id=1,
    current_prices={'TECH': 102.0, 'FIN': 195.0},
    allocation_drift_threshold=5.0
)

# Get recent transactions
transactions = helper.get_recent_transactions(portfolio_id=1, days=30)

# Get rebalancing history
history = helper.get_rebalancing_history(portfolio_id=1, limit=10)

# Get market events
events = helper.get_recent_market_events(portfolio_id=1, days=7)
```

## Integration Workflow

### 1. Portfolio Building

```python
from agents.portfolio_builder_agent_simple import build_simple_portfolio

# Build portfolio
portfolio = build_simple_portfolio(
    investor_profile='aggressive',
    capital=500000
)

# Automatically saves to:
# - JSON: .cache/portfolios/portfolio_aggressive_20250101_100000.json
# - Database: .cache/portfolio.db (via SQL Agent)
```

### 2. Portfolio Management

```python
from utils.portfolio_query_helper import get_portfolio_helper

helper = get_portfolio_helper()

# Load portfolio
portfolio = helper.load_latest_portfolio('aggressive')

# Check current state
performance = helper.get_current_performance(
    portfolio['portfolio']['id'],
    current_prices  # Dictionary of ticker: price
)

# Monitor for triggers
stops = helper.check_stop_loss_hits(
    portfolio['portfolio']['id'],
    current_prices
)

targets = helper.check_target_hits(
    portfolio['portfolio']['id'],
    current_prices
)

# Record decisions
from agents.sql_agent import SQLAgent
agent = SQLAgent()

if stops:
    agent.record_market_event_from_manager(
        portfolio_id=portfolio['portfolio']['id'],
        event_type='TRIGGER_HIT',
        title='Stop-Loss Hit',
        description=f"{stops[0]['ticker']} hit stop-loss",
        impact='NEGATIVE',
        stock_ticker=stops[0]['ticker'],
        action_taken='Exit position'
    )
```

### 3. Natural Language Queries

```python
from agents.sql_agent import SQLAgent

agent = SQLAgent()

# Query with natural language
result = agent.natural_language_to_sql(
    query="Which stocks have positive sentiment and allocation > 15%?",
    portfolio_id=1
)

if result['action'] == 'query_success':
    for row in result['results']:
        print(f"{row['ticker']}: {row['news_sentiment']}")
```

## Configuration

Add to `config.ini`:

```ini
[DATABASE]
# SQLite database settings
db_path = .cache/portfolio.db

# SQL Agent model tier
sql_agent_model = mid

# Auto-initialize schema on startup
auto_initialize_schema = true

# Query timeout in seconds
query_timeout = 30
```

## Data Flow

### Portfolio Builder → Database

```
1. Portfolio Builder Agent generates portfolio JSON
2. Call _save_final_portfolio()
3. Save JSON to .cache/portfolios/
4. Create SQL Agent instance
5. Call generate_insert_from_portfolio()
6. SQL Agent creates database service
7. Database service executes INSERTS
8. Tables populated: portfolios, stocks, investment_views, key_metrics
```

### Portfolio Manager → Database

```
1. Load latest portfolio from database
2. Get current prices for all stocks
3. Check stop-loss/target hits
4. Calculate performance
5. Check investment view triggers
6. Record market events
7. Plan rebalancing
8. Record rebalancing history
```

## Examples

See `examples/run_database_integration.py` for complete examples:

```bash
python examples/run_database_integration.py
```

Examples include:
1. Building and storing portfolio
2. Querying with SQL agent
3. Monitoring portfolio performance
4. Recording market events
5. Natural language queries

## Testing

Run tests:

```bash
# Test database service
pytest tests/test_db_service.py -v

# Test SQL agent
pytest tests/test_sql_agent.py -v

# Test all
pytest tests/ -v
```

## Best Practices

### 1. Always Use Query Helper for Common Tasks
```python
# Good
helper = get_portfolio_helper()
performance = helper.get_current_performance(portfolio_id, prices)

# Less ideal (but valid)
db = get_db_service()
stocks = db.get_portfolio_stocks(portfolio_id)
# ... calculate performance manually
```

### 2. Natural Language Queries for Portfolio Manager
```python
# Good - clear intent
agent.natural_language_to_sql(
    "Show me all rebalancing events in the last 30 days",
    portfolio_id=1
)

# Less ideal - raw SQL requires SQL knowledge
db.execute_query(
    "SELECT * FROM rebalancing_history WHERE portfolio_id = ? ORDER BY rebalancing_date DESC LIMIT 30",
    (1,)
)
```

### 3. Record Events for Audit Trail
```python
# Always record decisions
agent.record_market_event_from_manager(
    portfolio_id=portfolio_id,
    event_type='DECISION',
    title='Rebalancing',
    description='Reduced TECH from 30% to 25% due to allocation drift',
    impact='NEUTRAL',
    action_taken='Sold 5% TECH, bought 5% FIN'
)
```

### 4. Use Transactions for Multiple Operations
```python
with db.get_connection() as conn:
    # Multiple operations in single transaction
    db.record_transaction(...)
    db.record_performance(...)
    db.record_market_event(...)
    # All committed together or rolled back on error
```

## Performance Considerations

### Indices
Database has indices on:
- `portfolios.profile`
- `portfolios.created_at`
- `stocks.portfolio_id`
- `stocks.ticker`
- `transactions.portfolio_id`
- `performance_metrics.portfolio_id`
- `rebalancing_history.portfolio_id`
- `market_events.portfolio_id`

### Queries
Use `portfolio_id` in WHERE clause when possible to leverage indices.

### JSON Fields
Investment views, key metrics, and allocation changes are stored as JSON. Use SQL JSON functions if querying specific fields:

```sql
-- Query specific metric
SELECT ticker, json_extract(metrics_json, '$.ROE') as roe
FROM stocks
JOIN key_metrics ON stocks.id = key_metrics.stock_id
WHERE portfolio_id = 1
```

## Troubleshooting

### Database Locked
If you get "database is locked":
- Ensure only one process is writing at a time
- Close all read connections before writing
- Increase `query_timeout` in config if needed

### Schema Not Initialized
If schema.sql is missing:
```python
from utils.db_service import DatabaseService
db = DatabaseService()
# Will attempt to initialize from schema.sql
```

### SQL Agent Not Working
- Verify GEMINI_API_KEY is set in .env
- Check internet connection
- Verify Gemini model tier in config.ini

## Future Enhancements

Potential additions:
1. **Caching** - Redis for frequent queries
2. **Analytics** - Portfolio analytics dashboard
3. **Alerts** - Email/SMS alerts for trigger hits
4. **Reporting** - PDF portfolio reports
5. **Backtesting** - Historical simulation engine
6. **Multi-Portfolio** - Support multiple active portfolios
7. **Permissions** - User authentication and authorization
8. **API** - REST API for external tools

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review test cases in `tests/`
3. See examples in `examples/`
4. Check CLAUDE.md for project guidelines
