# Benchmark Fix Verification Guide

## What Was Fixed

Fixed benchmark comparison calculation to use **closest available date** when exact date has no index data (e.g., weekends/market holidays).

### Bugs Fixed:
1. ✅ **Silent failure**: Was returning 0% when no data on exact date → Now finds closest trading day within 15 days
2. ✅ **Missing data handling**: Added `get_index_price_on_or_before()` method to properly query "latest on or before" date

### Changes Made:
- `utils/db_service.py`: Added `get_index_price_on_or_before()` method
- `tools/performance_calculator.py`: Fixed lines 472-504 to use new method and handle dates correctly
- `utils/recalculate_benchmarks.py`: Created standalone script to regenerate benchmark data

---

## Step-by-Step Verification

### Step 1: Run Recalculation Script

```bash
cd /Users/bhaveshghodasara/Development/portfolio-agent

# Run the standalone recalculation script
python utils/recalculate_benchmarks.py
```

**Expected output:**
```
BENCHMARK RECALCULATION SCRIPT
================================

Step 1: Checking current benchmark data...
Found X existing benchmark records

Step 2: Deleting existing benchmark data...
Deleted X records

Step 3: Recalculating benchmarks...
✓ Successfully calculated Y benchmark comparisons

New Benchmark Results (ALL period):
  ✓ ^NSEI: Portfolio -2.13%, Index -1.38%, Alpha -0.75%
  ✓ ^BSESN: Portfolio -2.13%, Index -1.42%, Alpha -0.71%
  ...
```

---

### Step 2: Manual Verification for ^NSEI

Run this query in Supabase SQL Editor to verify the calculation is correct:

```sql
-- Calculate expected return from index_prices
WITH inception AS (
  SELECT close_price, price_date
  FROM index_prices
  WHERE index_symbol = '^NSEI'
    AND price_date <= '2025-12-27'  -- Portfolio inception
  ORDER BY price_date DESC
  LIMIT 1
),
latest AS (
  SELECT close_price, price_date
  FROM index_prices
  WHERE index_symbol = '^NSEI'
  ORDER BY price_date DESC
  LIMIT 1
)
SELECT
  'Expected from index_prices' as source,
  inception.price_date as inception_date,
  inception.close_price as inception_price,
  latest.price_date as latest_date,
  latest.close_price as latest_price,
  ROUND(((latest.close_price - inception.close_price) / inception.close_price * 100)::numeric, 2) as calculated_return_pct
FROM inception, latest;

-- Compare with stored value in benchmark_comparison
SELECT
  'Stored in benchmark_comparison' as source,
  comparison_date,
  ROUND(index_return::numeric, 2) as index_return_pct,
  ROUND(portfolio_return::numeric, 2) as portfolio_return_pct,
  ROUND(alpha::numeric, 2) as alpha_pct
FROM benchmark_comparison
WHERE portfolio_id = 42
  AND index_symbol = '^NSEI'
  AND period = 'ALL'
ORDER BY comparison_date DESC
LIMIT 1;
```

**Expected Result:**
- Both queries should show the same `index_return` value
- For ^NSEI: Should be around **-1.38%** (negative because market declined)
- **NOT** +0.52% (the old buggy value)

---

### Step 3: Check All Indices

Verify all indices show realistic returns (not 0% or null):

```sql
SELECT
  index_symbol,
  period,
  comparison_date,
  ROUND(portfolio_return::numeric, 2) as portfolio_pct,
  ROUND(index_return::numeric, 2) as index_pct,
  ROUND(alpha::numeric, 2) as alpha_pct,
  CASE
    WHEN index_return IS NULL THEN '❌ NULL (missing data)'
    WHEN index_return = 0 THEN '⚠️ ZERO (suspicious)'
    WHEN ABS(index_return) < 0.1 THEN '⚠️ NEAR ZERO (check if valid)'
    ELSE '✓ OK'
  END as status
FROM benchmark_comparison
WHERE portfolio_id = 42
  AND period = 'ALL'
ORDER BY index_symbol;
```

**Expected Result:**
- All indices should show '✓ OK' status
- Index returns should be realistic (not 0% unless market truly flat)
- No NULL values (unless index truly has no data)

---

### Step 4: Compare Before/After

If you captured the "before" state, compare:

```sql
-- Check what changed
SELECT
  bc.index_symbol,
  bc.period,
  ROUND(bc.portfolio_return::numeric, 2) as portfolio_return,
  ROUND(bc.index_return::numeric, 2) as NEW_index_return,
  -- If you saved old values, compare here
  ROUND(bc.alpha::numeric, 2) as NEW_alpha
FROM benchmark_comparison bc
WHERE bc.portfolio_id = 42
  AND bc.period = 'ALL'
ORDER BY bc.index_symbol;
```

**Expected Changes:**
- Index returns should change from unrealistic values to market-realistic values
- Alpha values will change accordingly (alpha = portfolio_return - index_return)

---

### Step 5: Check Logs

Review the script output logs to see which dates were actually used:

```
Benchmark ^NSEI: Baseline 2025-12-26 (target 2025-12-27) = 26042.30, End 2026-01-09 (target 2026-01-09) = 25683.30
```

**What to check:**
- "target" date is the portfolio inception/comparison date
- Actual date used might be 1-2 days before (for weekends/holidays)
- This is EXPECTED and CORRECT behavior

---

## Success Criteria

✅ Script runs without errors
✅ ^NSEI shows negative return (market declined)
✅ All indices show realistic returns (not 0%)
✅ Alpha values are reasonable
✅ Logs show actual dates used vs target dates
✅ Frontend dashboard displays updated benchmark data

---

## Troubleshooting

### Issue: Script fails with "No baseline data"

**Cause**: Index data doesn't exist within 15 days of portfolio inception

**Fix**: Check `index_prices` table:
```sql
SELECT MIN(price_date) as earliest_data
FROM index_prices
WHERE index_symbol = '^NSEI';
```

If portfolio inception is before earliest index data, you need to backfill index data.

### Issue: Index return is NULL

**Cause**: Index legitimately has no data (e.g., new sectoral index)

**Expected**: This is OK for indices without historical data. The error message will show which index and why.

### Issue: Index return is still 0%

**Cause**: Code changes not applied or script not run

**Fix**:
1. Check `utils/db_service.py` has `get_index_price_on_or_before()` method
2. Check `tools/performance_calculator.py` uses the new method
3. Re-run `python utils/recalculate_benchmarks.py`

---

## Rollback (If Needed)

If the fix causes issues:

```bash
# Revert code changes
cd /Users/bhaveshghodasara/Development/portfolio-agent
git checkout utils/db_service.py tools/performance_calculator.py

# Delete new benchmark data
# (via Supabase SQL Editor)
DELETE FROM benchmark_comparison WHERE comparison_date >= '2026-01-12';
```
