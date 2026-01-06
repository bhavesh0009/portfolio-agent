-- Migration: Add exit tracking and P&L fields
-- Date: 2026-01-06
-- Description: Adds fields to track exits, P&L, and improve queryability

-- Add P&L and trigger type columns to transactions table
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS realized_pnl_pct DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS realized_pnl_absolute DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS trigger_type TEXT;

-- Add exit tracking columns to stocks table
ALTER TABLE stocks
ADD COLUMN IF NOT EXISTS exit_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS exit_price DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS exit_type TEXT,
ADD COLUMN IF NOT EXISTS shares INTEGER;

-- Add cash balance to portfolios table
ALTER TABLE portfolios
ADD COLUMN IF NOT EXISTS cash_balance DOUBLE PRECISION DEFAULT 0;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_transactions_trigger_type ON transactions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_transactions_pnl ON transactions(realized_pnl_pct) WHERE transaction_type = 'SELL';
CREATE INDEX IF NOT EXISTS idx_stocks_exit_date ON stocks(exit_date);
CREATE INDEX IF NOT EXISTS idx_stocks_exit_type ON stocks(exit_type);

-- Add check constraint for trigger_type
ALTER TABLE transactions
DROP CONSTRAINT IF EXISTS transactions_trigger_type_check;

ALTER TABLE transactions
ADD CONSTRAINT transactions_trigger_type_check
CHECK (trigger_type IS NULL OR trigger_type IN ('STOP_LOSS', 'TARGET_HIT', 'NEWS_DRIVEN', 'LLM_RECOMMENDATION', 'MANUAL'));

-- Comments for documentation
COMMENT ON COLUMN transactions.realized_pnl_pct IS 'Percentage profit/loss for SELL transactions';
COMMENT ON COLUMN transactions.realized_pnl_absolute IS 'Absolute profit/loss amount for SELL transactions';
COMMENT ON COLUMN transactions.trigger_type IS 'What triggered this transaction: STOP_LOSS, TARGET_HIT, NEWS_DRIVEN, LLM_RECOMMENDATION, or MANUAL';

COMMENT ON COLUMN stocks.exit_date IS 'Timestamp when position was exited';
COMMENT ON COLUMN stocks.exit_price IS 'Price at which position was exited';
COMMENT ON COLUMN stocks.exit_type IS 'Type of exit: STOP_LOSS, TARGET_HIT, NEWS_DRIVEN, LLM_RECOMMENDATION, or MANUAL';
COMMENT ON COLUMN stocks.shares IS 'Number of shares held';

COMMENT ON COLUMN portfolios.cash_balance IS 'Available cash after investments (updated on exits/entries)';
