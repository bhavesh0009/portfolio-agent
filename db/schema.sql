-- Portfolio Database Schema
-- Stores all portfolio data from portfolio builder with full audit trail

-- Main portfolios table
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile TEXT NOT NULL,  -- 'aggressive' or 'defensive'
    total_capital REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp TEXT UNIQUE NOT NULL,  -- YYYYMMDD_HHMMSS format
    json_path TEXT,  -- Path to JSON file for reference
    notes TEXT,  -- Optional notes about the portfolio
    is_active BOOLEAN DEFAULT 1  -- Whether this is the current active portfolio
);

-- Stocks in portfolio
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    sector TEXT,
    entry_price REAL NOT NULL,
    allocation_pct REAL NOT NULL,
    allocation_amount REAL NOT NULL,
    stop_loss_pct REAL NOT NULL,
    stop_loss_price REAL NOT NULL,
    target_pct REAL NOT NULL,
    target_price REAL NOT NULL,
    rationale TEXT,  -- Selection reasoning
    news_sentiment TEXT,  -- Latest news sentiment
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    UNIQUE(portfolio_id, ticker)
);

-- Investment view/thesis for each stock
CREATE TABLE IF NOT EXISTS investment_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL UNIQUE,
    market_outlook TEXT NOT NULL,  -- Market conditions at selection
    stock_rationale TEXT NOT NULL,  -- Why stock fits profile
    holding_period TEXT NOT NULL,  -- Recommended duration
    exit_triggers TEXT NOT NULL,  -- JSON array of conditions
    review_triggers TEXT NOT NULL,  -- JSON array of conditions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Key metrics snapshot at time of selection
CREATE TABLE IF NOT EXISTS key_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL UNIQUE,
    metrics_json TEXT NOT NULL,  -- JSON object of all metrics
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Transaction history (buys/sells)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,  -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    total_amount REAL NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Performance metrics over time
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    stock_id INTEGER,  -- NULL for portfolio-level metrics
    metric_date DATE NOT NULL,
    portfolio_value REAL,  -- Total portfolio value on this date
    stock_value REAL,  -- Value of individual stock holding
    daily_return_pct REAL,  -- Day-over-day return percentage
    cumulative_return_pct REAL,  -- Return since entry
    status TEXT,  -- 'HOLDING', 'TARGET_HIT', 'STOP_LOSS_HIT', 'SOLD'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(portfolio_id, stock_id, metric_date)
);

-- Rebalancing decisions and actions
CREATE TABLE IF NOT EXISTS rebalancing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    rebalancing_date TIMESTAMP NOT NULL,
    reason TEXT NOT NULL,  -- Why rebalancing was triggered
    action_type TEXT NOT NULL,  -- 'ADJUSTMENT', 'ROTATION', 'EXIT'
    affected_stocks TEXT NOT NULL,  -- JSON array of affected tickers
    allocation_changes TEXT NOT NULL,  -- JSON object of old->new allocations
    expected_result TEXT,  -- Expected outcome of rebalancing
    actual_result TEXT,  -- Actual outcome (filled later)
    status TEXT DEFAULT 'PENDING',  -- 'PENDING', 'EXECUTED', 'CANCELLED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

-- Market events and decision triggers
CREATE TABLE IF NOT EXISTS market_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER,  -- NULL for general market events
    stock_id INTEGER,  -- NULL for portfolio/general events
    event_type TEXT NOT NULL,  -- 'TRIGGER_HIT', 'NEWS', 'EARNINGS', 'ECONOMIC', 'REGULATORY', 'INTERNAL'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    impact TEXT,  -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    action_taken TEXT,  -- Action triggered by this event
    event_date TIMESTAMP NOT NULL,
    source TEXT,  -- Where the event came from
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Create indices for common queries
CREATE INDEX IF NOT EXISTS idx_portfolios_profile ON portfolios(profile);
CREATE INDEX IF NOT EXISTS idx_portfolios_created ON portfolios(created_at);
CREATE INDEX IF NOT EXISTS idx_stocks_portfolio ON stocks(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_stocks_ticker ON stocks(ticker);
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON transactions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_performance_portfolio ON performance_metrics(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_performance_date ON performance_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_rebalancing_portfolio ON rebalancing_history(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_market_events_portfolio ON market_events(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_market_events_date ON market_events(event_date);

-- View for dynamic benchmark comparisons
CREATE VIEW IF NOT EXISTS portfolio_benchmark_history AS
WITH portfolio_starts AS (
    SELECT portfolio_id, MIN(snapshot_date) as start_date
    FROM portfolio_snapshots
    GROUP BY portfolio_id
),
benchmark_initials AS (
    SELECT
        ps.portfolio_id,
        idx.index_symbol,
        ip.close_price as initial_index_price
    FROM
        portfolio_starts ps
    CROSS JOIN
        (SELECT DISTINCT index_symbol FROM index_prices) idx
    JOIN LATERAL (
        SELECT close_price
        FROM index_prices
        WHERE index_symbol = idx.index_symbol
        AND price_date <= ps.start_date
        ORDER BY price_date DESC
        LIMIT 1
    ) ip ON TRUE
)
SELECT
    ps.portfolio_id,
    ip.index_symbol,
    ps.snapshot_date as comparison_date,
    ps.total_return_pct as portfolio_return,
    ((ip.close_price - bi.initial_index_price) / bi.initial_index_price * 100) as index_return
FROM
    portfolio_snapshots ps
JOIN
    index_prices ip ON ps.snapshot_date = ip.price_date
JOIN
    benchmark_initials bi ON ps.portfolio_id = bi.portfolio_id AND ip.index_symbol = bi.index_symbol;
