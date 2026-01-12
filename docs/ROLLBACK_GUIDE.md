# Rollback Guide - Portfolio Manager Multiple Runs

## Problem: Running Portfolio Manager Multiple Times

When portfolio manager runs multiple times on the same day, it creates duplicate and compounding data issues.

### Evidence from Your Database (2026-01-10)

Portfolio manager ran **3 times**:
- Run 1: 06:24:13 AM IST
- Run 2: 12:13:06 PM IST
- Run 3: 12:25:01 PM IST

**Result**: Portfolio value shows Rs. 489K instead of expected Rs. 2.37M

---

## Understanding the Duplicate Impact

### 1. INSERT Tables - Create Duplicates

**What happens:** Each run creates NEW records

| Table | Your Case | Risk |
|-------|-----------|------|
| `manager_updates` | **3 duplicates** ✅ Found | Cluttered history |
| `transactions` | 0 (market holiday) | **CRITICAL** - Inflates trading activity, wrong P&L |
| `rebalancing_history` | 0 (no rebalances) | Confusing audit trail |
| `market_events` | 0 (no events) | Inflated event count |

**Example Problem:**
If stock exits on run 1, then runs 2 & 3 may try to exit again → 3 SELL transactions for 1 stock!

### 2. UPSERT Tables - Overwrite (Last Run Wins)

**What happens:** Later runs OVERWRITE earlier data

| Table | Your Case | Impact |
|-------|-----------|--------|
| `daily_prices` | 15 records (correct) | Last price overwrites earlier |
| `portfolio_snapshots` | 1 snapshot (correct) | **Latest snapshot kept** |
| `benchmark_comparison` | Not checked | Latest comparison kept |

**Why this is OK:** UPSERT has unique constraints, so only latest data survives. No duplicates.

### 3. UPDATE Tables - Compounding Changes

**What happens:** Each run MODIFIES the same records

| Table | Field | Your Case | Risk Level |
|-------|-------|-----------|------------|
| `portfolios` | `cash_balance` | Unknown | **CRITICAL** - May be 3x inflated/deflated |
| `stocks` | `allocation_pct` | Unknown | **CRITICAL** - Wrong allocations |
| `stocks` | `allocation_amount` | Unknown | **CRITICAL** - Wrong amounts |
| `stocks` | `exit_date`, `exit_price` | Unknown | Latest overwrites |

**This is likely your Rs. 489K bug!**

If each run:
1. Updates cash balance (e.g., adds/removes cash)
2. Updates stock allocations
3. Recalculates portfolio value

Then 3 runs = 3x the changes = wrong total value.

---

## Quick Diagnosis

### Check Your Specific Issue

```bash
# Analyze what happened on 2026-01-10
python utils/rollback_by_date.py --date 2026-01-10 --analyze-only
```

**Expected output:**
```
📊 MANAGER UPDATES: 3 runs detected
  Run 1: 2026-01-10 06:24:13 (ID: 34)
  Run 2: 2026-01-10 12:13:06 (ID: 35)
  Run 3: 2026-01-10 12:25:01 (ID: 36)

💰 TRANSACTIONS: 0
⚖️  REBALANCING HISTORY: 0
📰 MARKET EVENTS: 0
📸 PORTFOLIO SNAPSHOTS: 1
💵 DAILY PRICES: 15 stocks
```

---

## Rollback Solution

### Option 1: Rollback Manager Updates Only (Safe, Limited)

**What it does:** Deletes duplicate `manager_updates` records only

**Limitations:**
- Does NOT fix cash_balance issues
- Does NOT fix stock allocation issues
- Only cleans up duplicate update records

```bash
# Dry run first (safe)
python utils/rollback_by_date.py --date 2026-01-10 --keep first --dry-run

# Execute rollback
python utils/rollback_by_date.py --date 2026-01-10 --keep first --execute
```

**Choose `--keep first` or `--keep last`:**
- `first` = Keep earliest run (06:24), delete later runs
- `last` = Keep latest run (12:25), delete earlier runs

### Option 2: Manual Database Restoration (Complete, Complex)

Since we don't have `run_id` tracking yet, you need to manually restore:

#### Step 1: Find Backup Data

Check if you have a backup from before the 3 runs:
```bash
# Check for JSON backups
ls -la .cache/portfolios/ | grep "2026-01-09"
```

#### Step 2: Identify Correct Values

Query database for previous day's snapshot:
```sql
SELECT
  total_value,
  cash_balance,
  invested_value
FROM portfolio_snapshots
WHERE portfolio_id = 42
  AND snapshot_date = '2026-01-09'
ORDER BY snapshot_date DESC
LIMIT 1;
```

#### Step 3: Manual Correction

If you know the correct values, update directly:
```sql
BEGIN;

-- Update portfolio snapshot for 2026-01-10
UPDATE portfolio_snapshots
SET
  total_value = <correct_value>,
  cash_balance = <correct_cash>,
  invested_value = <correct_invested>
WHERE portfolio_id = 42
  AND snapshot_date = '2026-01-10';

-- Update portfolio cash balance
UPDATE portfolios
SET cash_balance = <correct_cash>
WHERE id = 42;

-- Delete duplicate manager updates
DELETE FROM manager_updates
WHERE id IN (35, 36);  -- Keep ID 34

COMMIT;
```

---

## Prevention: Implement run_id Tracking

To prevent this in future, implement `run_id` tracking as documented in `DATABASE_OPERATIONS.md`:

### 1. Add Migration

```sql
-- File: utils/migrations/add_run_id_tracking.sql

ALTER TABLE portfolios ADD COLUMN run_id UUID;
ALTER TABLE stocks ADD COLUMN run_id UUID;
ALTER TABLE transactions ADD COLUMN run_id UUID;
ALTER TABLE rebalancing_history ADD COLUMN run_id UUID;
ALTER TABLE daily_prices ADD COLUMN run_id UUID;
ALTER TABLE portfolio_snapshots ADD COLUMN run_id UUID;
ALTER TABLE manager_updates ADD COLUMN run_id UUID;
ALTER TABLE market_events ADD COLUMN run_id UUID;

CREATE TABLE run_log (
  run_id UUID PRIMARY KEY,
  agent_type TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  status TEXT,
  portfolio_id INTEGER,
  metadata JSONB
);
```

### 2. Update Agents

Add `run_id` generation at start of portfolio manager:
```python
import uuid

def run(self):
    # Generate unique run_id
    run_id = uuid.uuid4()

    # Log run start
    self.db.client.table('run_log').insert({
        'run_id': str(run_id),
        'agent_type': 'MANAGER',
        'start_time': datetime.now(),
        'status': 'RUNNING',
        'portfolio_id': self.portfolio_id
    }).execute()

    # Pass run_id to all database operations
    ...
```

### 3. Future Rollback

With `run_id`, rollback becomes simple:
```sql
-- Rollback entire run
DELETE FROM transactions WHERE run_id = '<bad_run_id>';
DELETE FROM rebalancing_history WHERE run_id = '<bad_run_id>';
DELETE FROM manager_updates WHERE run_id = '<bad_run_id>';
-- ... etc
```

---

## Recommended Actions for Your Case

1. **Immediate:** Clean up duplicate manager_updates
   ```bash
   python utils/rollback_by_date.py --date 2026-01-10 --keep first --execute
   ```

2. **Investigation:** Check if cash_balance and allocations are wrong
   ```sql
   -- Compare with previous day
   SELECT * FROM portfolio_snapshots
   WHERE portfolio_id = 42
     AND snapshot_date >= '2026-01-09'
   ORDER BY snapshot_date;
   ```

3. **Fix if needed:** Manually restore correct values (Option 2 above)

4. **Prevention:** Implement `run_id` tracking to prevent future issues

5. **Process:** Add check to portfolio manager to prevent same-day reruns:
   ```python
   # At start of portfolio_manager_agent.py run()
   today = date.today()
   existing_run = self.db.client.table('manager_updates') \
       .select('id') \
       .eq('portfolio_id', portfolio_id) \
       .eq('update_date', today) \
       .execute()

   if existing_run.data:
       print(f"⚠️  Portfolio manager already ran today at {existing_run.data[0]['created_at']}")
       response = input("Run again? (yes/no): ")
       if response.lower() != 'yes':
           sys.exit(0)
   ```

---

## Quick Reference

```bash
# Analyze a date
python utils/rollback_by_date.py --date YYYY-MM-DD --analyze-only

# Rollback (dry run)
python utils/rollback_by_date.py --date YYYY-MM-DD --keep first --dry-run

# Rollback (execute)
python utils/rollback_by_date.py --date YYYY-MM-DD --keep first --execute
```

**Safety:** Always use `--dry-run` first, then `--analyze-only`, then `--execute`
