# Database Migrations

This directory contains SQL migration scripts for the Portfolio Agent database (Supabase PostgreSQL).

## Running Migrations

### Option 1: Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of the migration file
4. Paste and run the SQL

### Option 2: Supabase CLI

```bash
# If you have Supabase CLI installed
supabase db push
```

### Option 3: psql Command Line

```bash
# Connect to your Supabase database
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run the migration
\i db/migrations/001_add_exit_and_pnl_fields.sql
```

## Migration History

### 001_add_exit_and_pnl_fields.sql
**Date**: 2026-01-06
**Purpose**: Add exit tracking and P&L fields to improve queryability

**Changes**:
- Added `realized_pnl_pct`, `realized_pnl_absolute`, `trigger_type` to `transactions` table
- Added `exit_date`, `exit_price`, `exit_type`, `shares` to `stocks` table
- Added `cash_balance` to `portfolios` table
- Added indexes for query performance
- Added check constraints for data validation

**Impact**:
- Exit data now queryable by P&L range and trigger type
- Rebalancing history includes execution status
- Full audit trail of all portfolio actions

## Verifying Migrations

After running a migration, verify the changes:

```sql
-- Check new columns in transactions table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'transactions'
AND column_name IN ('realized_pnl_pct', 'realized_pnl_absolute', 'trigger_type');

-- Check new columns in stocks table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'stocks'
AND column_name IN ('exit_date', 'exit_price', 'exit_type', 'shares');

-- Check new column in portfolios table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'portfolios'
AND column_name = 'cash_balance';
```

## Rollback

If you need to rollback a migration, you can drop the added columns:

```sql
-- WARNING: This will delete data!
ALTER TABLE transactions
DROP COLUMN IF EXISTS realized_pnl_pct,
DROP COLUMN IF EXISTS realized_pnl_absolute,
DROP COLUMN IF EXISTS trigger_type;

ALTER TABLE stocks
DROP COLUMN IF EXISTS exit_date,
DROP COLUMN IF EXISTS exit_price,
DROP COLUMN IF EXISTS exit_type,
DROP COLUMN IF EXISTS shares;

ALTER TABLE portfolios
DROP COLUMN IF EXISTS cash_balance;
```

## Testing Queries

After migration, you can test these new query capabilities:

```sql
-- Query all exits with P&L > 10%
SELECT t.*, s.ticker, s.name
FROM transactions t
JOIN stocks s ON t.stock_id = s.id
WHERE t.transaction_type = 'SELL'
AND t.realized_pnl_pct > 10
ORDER BY t.transaction_date DESC;

-- Query exits by trigger type
SELECT trigger_type, COUNT(*), AVG(realized_pnl_pct) as avg_pnl
FROM transactions
WHERE transaction_type = 'SELL'
GROUP BY trigger_type;

-- Query stocks with exit information
SELECT ticker, name, entry_price, exit_price, exit_date, exit_type,
       ((exit_price - entry_price) / entry_price * 100) as pnl_pct
FROM stocks
WHERE exit_date IS NOT NULL
ORDER BY exit_date DESC;

-- Query executed rebalancing actions
SELECT * FROM rebalancing_history
WHERE status = 'EXECUTED'
ORDER BY executed_at DESC;
```
