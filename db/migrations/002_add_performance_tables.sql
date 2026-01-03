-- Migration: Add Performance Tracking Tables
-- Created: 2025-01-08
-- Purpose: Enable price tracking, benchmark comparison, and manager updates

-- =============================================================================
-- PRICE TRACKING TABLES
-- =============================================================================

-- Daily price snapshots for stocks
CREATE TABLE IF NOT EXISTS daily_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    price_date DATE NOT NULL,
    open_price REAL NOT NULL,
    high_price REAL NOT NULL,
    low_price REAL NOT NULL,
    close_price REAL NOT NULL,
    volume INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
    UNIQUE(stock_id, price_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_stock_date
    ON daily_prices(stock_id, price_date);

CREATE INDEX IF NOT EXISTS idx_daily_prices_date
    ON daily_prices(price_date);

-- Index/benchmark prices (Nifty, Sensex, etc.)
CREATE TABLE IF NOT EXISTS index_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    index_symbol TEXT NOT NULL,         -- '^NSEI', '^BSESN', 'NIFTYSMLCAP250.NS'
    index_name TEXT NOT NULL,           -- 'Nifty 50', 'Sensex', 'Nifty Smallcap 250'
    price_date DATE NOT NULL,
    open_price REAL NOT NULL,
    high_price REAL NOT NULL,
    low_price REAL NOT NULL,
    close_price REAL NOT NULL,
    volume INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(index_symbol, price_date)
);

CREATE INDEX IF NOT EXISTS idx_index_prices_symbol_date
    ON index_prices(index_symbol, price_date);

CREATE INDEX IF NOT EXISTS idx_index_prices_date
    ON index_prices(price_date);

-- =============================================================================
-- PORTFOLIO PERFORMANCE TABLES
-- =============================================================================

-- Portfolio snapshot (daily) - Extends existing performance_metrics table
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,

    -- Value metrics
    total_value REAL NOT NULL,
    cash_balance REAL DEFAULT 0,
    invested_value REAL NOT NULL,

    -- Return metrics
    total_return_pct REAL,              -- Since inception
    total_return_absolute REAL,
    day_return_pct REAL,                -- Today's change
    day_return_absolute REAL,

    -- Risk metrics
    volatility REAL,                    -- Annualized volatility
    sharpe_ratio REAL,                  -- Risk-adjusted return
    max_drawdown REAL,                  -- Maximum peak-to-trough decline

    -- Additional metrics
    num_stocks INTEGER,                 -- Number of holdings
    avg_allocation_pct REAL,            -- Average allocation per stock

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_portfolio_date
    ON portfolio_snapshots(portfolio_id, snapshot_date);

-- Benchmark comparison (portfolio vs indices)
CREATE TABLE IF NOT EXISTS benchmark_comparison (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    comparison_date DATE NOT NULL,
    index_symbol TEXT NOT NULL,         -- '^NSEI', '^BSESN', etc.
    index_name TEXT NOT NULL,           -- 'Nifty 50', 'Sensex'

    -- Return comparison
    portfolio_return REAL NOT NULL,     -- Portfolio return %
    index_return REAL NOT NULL,         -- Index return %
    alpha REAL,                         -- portfolio_return - index_return

    -- Risk comparison
    beta REAL,                          -- Correlation with index (0-2, 1=market)
    outperformance REAL,                -- Positive if portfolio > index

    -- Time period
    period TEXT,                        -- '1M', '3M', '6M', '1Y', 'ALL'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, index_symbol, comparison_date, period)
);

CREATE INDEX IF NOT EXISTS idx_benchmark_comparison_portfolio_date
    ON benchmark_comparison(portfolio_id, comparison_date);

CREATE INDEX IF NOT EXISTS idx_benchmark_comparison_index
    ON benchmark_comparison(index_symbol, comparison_date);

-- =============================================================================
-- MANAGER UPDATE TABLES
-- =============================================================================

-- Portfolio manager daily updates/decisions
CREATE TABLE IF NOT EXISTS manager_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
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

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_manager_updates_portfolio_date
    ON manager_updates(portfolio_id, update_date);

CREATE INDEX IF NOT EXISTS idx_manager_updates_status
    ON manager_updates(status);

CREATE INDEX IF NOT EXISTS idx_manager_updates_priority
    ON manager_updates(priority);

-- Enhanced rebalancing recommendations
CREATE TABLE IF NOT EXISTS rebalancing_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
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
    confidence_score REAL,              -- 0-100 confidence level

    -- Status tracking
    status TEXT DEFAULT 'PENDING',      -- 'PENDING', 'APPROVED', 'REJECTED', 'EXECUTED'
    user_decision TEXT,                 -- 'APPROVED', 'REJECTED', 'MODIFIED'
    user_modifications TEXT,            -- JSON of user changes
    execution_notes TEXT,
    executed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rebalancing_recommendations_portfolio
    ON rebalancing_recommendations(portfolio_id, recommendation_date);

CREATE INDEX IF NOT EXISTS idx_rebalancing_recommendations_status
    ON rebalancing_recommendations(status);

-- =============================================================================
-- USER PREFERENCES
-- =============================================================================

-- User benchmark preferences
CREATE TABLE IF NOT EXISTS user_benchmark_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    index_symbol TEXT NOT NULL,
    index_name TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT 0,       -- Top 3 shown in main dashboard
    display_order INTEGER,              -- Order in UI (1, 2, 3 for primary)
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, index_symbol)
);

CREATE INDEX IF NOT EXISTS idx_user_benchmark_preferences_portfolio
    ON user_benchmark_preferences(portfolio_id);

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

-- Insert default benchmark preferences for existing portfolios
-- (Assuming portfolio ID 1 exists from your current setup)
INSERT OR IGNORE INTO user_benchmark_preferences
    (portfolio_id, index_symbol, index_name, is_primary, display_order)
VALUES
    (1, '^NSEI', 'Nifty 50', 1, 1),
    (1, '^BSESN', 'Sensex', 0, 4),
    (1, 'NIFTY_MIDCAP_100.NS', 'Nifty Midcap 100', 1, 2),
    (1, 'NIFTYSMLCAP250.NS', 'Nifty Smallcap 250', 1, 3),
    (1, 'NIFTYIT.NS', 'Nifty IT', 0, 5),
    (1, 'NIFTYPHARMA.NS', 'Nifty Pharma', 0, 6),
    (1, 'NIFTYAUTO.NS', 'Nifty Auto', 0, 7),
    (1, 'NIFTYENERGY.NS', 'Nifty Energy', 0, 8);

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Verification queries (comment out for production)
/*
SELECT 'Tables created:' as message;
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%price%' OR name LIKE '%snapshot%' OR name LIKE '%manager%';

SELECT 'Indexes created:' as message;
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';

SELECT 'Default benchmarks:' as message;
SELECT * FROM user_benchmark_preferences;
*/
