-- Portfolio Database Schema - PostgreSQL Version
-- Migrated from SQLite to Supabase PostgreSQL

-- Main portfolios table
CREATE TABLE IF NOT EXISTS portfolios (
    id BIGSERIAL PRIMARY KEY,
    profile TEXT NOT NULL,  -- 'aggressive', 'moderate', or 'defensive'
    total_capital DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    timestamp TEXT UNIQUE NOT NULL,  -- YYYYMMDD_HHMMSS format
    json_path TEXT,  -- Path to JSON file for reference
    notes TEXT,  -- Optional notes about the portfolio
    is_active BOOLEAN DEFAULT TRUE,  -- Whether this is the current active portfolio
    cash_balance DOUBLE PRECISION DEFAULT 0  -- Available cash after investments
);

-- Stocks in portfolio
CREATE TABLE IF NOT EXISTS stocks (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    sector TEXT,
    entry_price DOUBLE PRECISION NOT NULL,
    allocation_pct DOUBLE PRECISION NOT NULL,
    allocation_amount DOUBLE PRECISION NOT NULL,
    stop_loss_pct DOUBLE PRECISION NOT NULL,
    stop_loss_price DOUBLE PRECISION NOT NULL,
    target_pct DOUBLE PRECISION NOT NULL,
    target_price DOUBLE PRECISION NOT NULL,
    rationale TEXT,  -- Selection reasoning
    news_sentiment TEXT,  -- Latest news sentiment
    added_at TIMESTAMP DEFAULT NOW(),
    exchange TEXT DEFAULT 'NSE',
    exit_date TIMESTAMP,  -- When position was exited
    exit_price DOUBLE PRECISION,  -- Exit price
    exit_type TEXT,  -- 'STOP_LOSS', 'TARGET_HIT', 'NEWS_DRIVEN', 'LLM_RECOMMENDATION', 'MANUAL'
    shares INTEGER,  -- Number of shares held
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    UNIQUE(portfolio_id, ticker)
);

-- Investment view/thesis for each stock
CREATE TABLE IF NOT EXISTS investment_views (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL UNIQUE,
    market_outlook TEXT NOT NULL,  -- Market conditions at selection
    stock_rationale TEXT NOT NULL,  -- Why stock fits profile
    holding_period TEXT NOT NULL,  -- Recommended duration
    exit_triggers TEXT NOT NULL,  -- JSON array of conditions
    review_triggers TEXT NOT NULL,  -- JSON array of conditions
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Key metrics snapshot at time of selection
CREATE TABLE IF NOT EXISTS key_metrics (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL UNIQUE,
    metrics_json TEXT NOT NULL,  -- JSON object of all metrics
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Transaction history (buys/sells)
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    stock_id BIGINT NOT NULL,
    transaction_type TEXT NOT NULL,  -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    total_amount DOUBLE PRECISION NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    realized_pnl_pct DOUBLE PRECISION,  -- P&L percentage for SELL transactions
    realized_pnl_absolute DOUBLE PRECISION,  -- P&L absolute amount for SELL transactions
    trigger_type TEXT,  -- 'STOP_LOSS', 'TARGET_HIT', 'NEWS_DRIVEN', 'LLM_RECOMMENDATION', 'MANUAL'
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Performance metrics over time
CREATE TABLE IF NOT EXISTS performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    stock_id BIGINT,  -- NULL for portfolio-level metrics
    metric_date DATE NOT NULL,
    portfolio_value DOUBLE PRECISION,  -- Total portfolio value on this date
    stock_value DOUBLE PRECISION,  -- Value of individual stock holding
    daily_return_pct DOUBLE PRECISION,  -- Day-over-day return percentage
    cumulative_return_pct DOUBLE PRECISION,  -- Return since entry
    status TEXT,  -- 'HOLDING', 'TARGET_HIT', 'STOP_LOSS_HIT', 'SOLD'
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(portfolio_id, stock_id, metric_date)
);

-- Rebalancing decisions and actions
CREATE TABLE IF NOT EXISTS rebalancing_history (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    rebalancing_date TIMESTAMP NOT NULL,
    reason TEXT NOT NULL,  -- Why rebalancing was triggered
    action_type TEXT NOT NULL,  -- 'ADJUSTMENT', 'ROTATION', 'EXIT'
    affected_stocks TEXT NOT NULL,  -- JSON array of affected tickers
    allocation_changes TEXT NOT NULL,  -- JSON object of old->new allocations
    expected_result TEXT,  -- Expected outcome of rebalancing
    actual_result TEXT,  -- Actual outcome (filled later)
    status TEXT DEFAULT 'PENDING',  -- 'PENDING', 'EXECUTED', 'CANCELLED'
    created_at TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

-- Market events and decision triggers
CREATE TABLE IF NOT EXISTS market_events (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT,  -- NULL for general market events
    stock_id BIGINT,  -- NULL for portfolio/general events
    event_type TEXT NOT NULL,  -- 'TRIGGER_HIT', 'NEWS', 'EARNINGS', 'ECONOMIC', 'REGULATORY', 'INTERNAL'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    impact TEXT,  -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    action_taken TEXT,  -- Action triggered by this event
    event_date TIMESTAMP NOT NULL,
    source TEXT,  -- Where the event came from
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Daily price data for stocks
CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL,
    price_date DATE NOT NULL,
    open_price DOUBLE PRECISION NOT NULL,
    high_price DOUBLE PRECISION NOT NULL,
    low_price DOUBLE PRECISION NOT NULL,
    close_price DOUBLE PRECISION NOT NULL,
    volume INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
    UNIQUE(stock_id, price_date)
);

-- Index price data (Nifty, Sensex, etc.)
CREATE TABLE IF NOT EXISTS index_prices (
    id BIGSERIAL PRIMARY KEY,
    index_symbol TEXT NOT NULL,         -- '^NSEI', '^BSESN', 'NIFTYSMLCAP250.NS'
    index_name TEXT NOT NULL,           -- 'Nifty 50', 'Sensex', 'Nifty Smallcap 250'
    price_date DATE NOT NULL,
    open_price DOUBLE PRECISION NOT NULL,
    high_price DOUBLE PRECISION NOT NULL,
    low_price DOUBLE PRECISION NOT NULL,
    close_price DOUBLE PRECISION NOT NULL,
    volume INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(index_symbol, price_date)
);

-- Portfolio snapshots for historical tracking
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,

    -- Value metrics
    total_value DOUBLE PRECISION NOT NULL,
    cash_balance DOUBLE PRECISION DEFAULT 0,
    invested_value DOUBLE PRECISION NOT NULL,

    -- Return metrics
    total_return_pct DOUBLE PRECISION,              -- Since inception
    total_return_absolute DOUBLE PRECISION,
    day_return_pct DOUBLE PRECISION,                -- Today's change
    day_return_absolute DOUBLE PRECISION,

    -- Risk metrics
    volatility DOUBLE PRECISION,                    -- Annualized volatility
    sharpe_ratio DOUBLE PRECISION,                  -- Risk-adjusted return
    max_drawdown DOUBLE PRECISION,                  -- Maximum peak-to-trough decline

    -- Additional metrics
    num_stocks INTEGER,                 -- Number of holdings
    avg_allocation_pct DOUBLE PRECISION,            -- Average allocation per stock

    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, snapshot_date)
);

-- Benchmark comparison data
CREATE TABLE IF NOT EXISTS benchmark_comparison (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    comparison_date DATE NOT NULL,
    index_symbol TEXT NOT NULL,         -- '^NSEI', '^BSESN', etc.
    index_name TEXT NOT NULL,           -- 'Nifty 50', 'Sensex'

    -- Return comparison
    portfolio_return DOUBLE PRECISION NOT NULL,     -- Portfolio return %
    index_return DOUBLE PRECISION NOT NULL,         -- Index return %
    alpha DOUBLE PRECISION,                         -- portfolio_return - index_return

    -- Risk comparison
    beta DOUBLE PRECISION,                          -- Correlation with index (0-2, 1=market)
    outperformance DOUBLE PRECISION,                -- Positive if portfolio > index

    -- Time period
    period TEXT,                        -- '1M', '3M', '6M', '1Y', 'ALL'

    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, index_symbol, comparison_date, period)
);

-- Manager updates and notifications
CREATE TABLE IF NOT EXISTS manager_updates (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    update_date DATE NOT NULL,

    -- Update classification
    update_type TEXT NOT NULL,          -- 'DAILY_REVIEW', 'SIGNAL_GENERATED', 'DECISION_MADE'
    title TEXT NOT NULL,
    description TEXT NOT NULL,

    -- Affected entities
    affected_stocks TEXT,               -- JSON array of tickers: ["WAREE", "ZENTEC"]
    affected_sectors TEXT,              -- JSON array: ["Renewable Energy"]

    -- Recommendation
    recommendation TEXT,                -- 'HOLD', 'BUY_MORE', 'SELL', 'REBALANCE', NULL
    reasoning TEXT,                     -- AI agent detailed reasoning

    -- Priority and status
    priority TEXT NOT NULL DEFAULT 'MEDIUM',  -- 'LOW', 'MEDIUM', 'HIGH', 'URGENT'
    status TEXT DEFAULT 'PENDING',      -- 'PENDING', 'ACKNOWLEDGED', 'EXECUTED', 'IGNORED'

    -- User interaction
    user_decision TEXT,                 -- 'APPROVED', 'REJECTED', 'MODIFIED', NULL
    user_notes TEXT,
    executed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

-- Rebalancing recommendations
CREATE TABLE IF NOT EXISTS rebalancing_recommendations (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    recommendation_date TIMESTAMP NOT NULL,

    -- Trigger information
    trigger_reason TEXT NOT NULL,       -- 'STOP_LOSS_HIT', 'TARGET_HIT', 'DRIFT_DETECTED', etc.
    action_type TEXT NOT NULL,          -- 'ADJUSTMENT', 'ROTATION', 'EXIT', 'ENTRY'

    -- Affected entities
    affected_stocks TEXT NOT NULL,      -- JSON array of tickers
    proposed_changes TEXT NOT NULL,     -- JSON: {ticker: {action, from_pct, to_pct, reason}}

    -- Impact analysis
    expected_impact TEXT,               -- Description of expected outcome
    risk_assessment TEXT,               -- Risk analysis
    confidence_score DOUBLE PRECISION,              -- 0-100 confidence level

    -- Status tracking
    status TEXT DEFAULT 'PENDING',      -- 'PENDING', 'APPROVED', 'REJECTED', 'EXECUTED'
    user_decision TEXT,                 -- 'APPROVED', 'REJECTED', 'MODIFIED'
    user_modifications TEXT,            -- JSON of user changes
    execution_notes TEXT,
    executed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

-- User benchmark preferences
CREATE TABLE IF NOT EXISTS user_benchmark_preferences (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL,
    index_symbol TEXT NOT NULL,
    index_name TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,       -- Top 3 shown in main dashboard
    display_order INTEGER,              -- Order in UI (1, 2, 3 for primary)
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, index_symbol)
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
CREATE INDEX IF NOT EXISTS idx_daily_prices_stock_date ON daily_prices(stock_id, price_date);
CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(price_date);
CREATE INDEX IF NOT EXISTS idx_index_prices_symbol_date ON index_prices(index_symbol, price_date);
CREATE INDEX IF NOT EXISTS idx_index_prices_date ON index_prices(price_date);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_portfolio_date ON portfolio_snapshots(portfolio_id, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_benchmark_comparison_portfolio_date ON benchmark_comparison(portfolio_id, comparison_date);
CREATE INDEX IF NOT EXISTS idx_benchmark_comparison_index ON benchmark_comparison(index_symbol, comparison_date);
CREATE INDEX IF NOT EXISTS idx_manager_updates_portfolio_date ON manager_updates(portfolio_id, update_date);
CREATE INDEX IF NOT EXISTS idx_manager_updates_status ON manager_updates(status);
CREATE INDEX IF NOT EXISTS idx_manager_updates_priority ON manager_updates(priority);
CREATE INDEX IF NOT EXISTS idx_rebalancing_recommendations_portfolio ON rebalancing_recommendations(portfolio_id, recommendation_date);
CREATE INDEX IF NOT EXISTS idx_rebalancing_recommendations_status ON rebalancing_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_user_benchmark_preferences_portfolio ON user_benchmark_preferences(portfolio_id);

-- View for dynamic benchmark comparisons
CREATE OR REPLACE VIEW portfolio_benchmark_history AS
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
