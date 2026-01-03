-- Migration: Add share quantities and cash balance
-- Date: 2025-12-27
-- Description: Adds shares column to stocks table and cash_balance to portfolios table
--              for whole-share based portfolio management

-- Add shares column to stocks table
ALTER TABLE stocks ADD COLUMN shares INTEGER DEFAULT NULL;

-- Add cash_balance to portfolios table
ALTER TABLE portfolios ADD COLUMN cash_balance DOUBLE PRECISION DEFAULT 0;

-- Create index for share-based queries
CREATE INDEX IF NOT EXISTS idx_stocks_shares ON stocks(shares);

-- Add comments for documentation
COMMENT ON COLUMN stocks.shares IS 'Number of whole shares purchased (NULL for legacy allocation-only portfolios)';
COMMENT ON COLUMN portfolios.cash_balance IS 'Unallocated cash remaining after share purchases';
