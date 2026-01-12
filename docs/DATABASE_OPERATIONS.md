# Database Operations Reference - Portfolio Agent

Quick reference for all database write operations (INSERT/UPDATE/DELETE) in portfolio builder and manager agents.

## Tables Overview

| Table | Primary Writer | Operations | Rollback Priority |
|-------|---------------|------------|-------------------|
| portfolios | Builder, Manager | INSERT, UPDATE | **CRITICAL** |
| stocks | Builder, Manager | INSERT, UPDATE | **CRITICAL** |
| investment_views | Builder | INSERT | HIGH |
| key_metrics | Builder | INSERT | HIGH |
| transactions | Manager | INSERT | **CRITICAL** |
| rebalancing_history | Manager | INSERT, UPDATE | HIGH |
| market_events | Manager | INSERT | MEDIUM |
| daily_prices | Manager | UPSERT | HIGH |
| portfolio_snapshots | Manager | UPSERT | MEDIUM |
| benchmark_comparison | Manager | UPSERT | MEDIUM |
| manager_updates | Manager | INSERT, UPDATE | LOW |
| performance_metrics | Manager | UPSERT | MEDIUM |
| index_prices | Price Service | UPSERT | MEDIUM |

---

## Portfolio Builder Operations

### 1. Create Portfolio (CRITICAL)

**File:** `portfolio_builder_agent_simple.py:705`
**Entry:** `sql_agent.generate_insert_from_portfolio(execute=True)`

**Deactivate Previous:**
```python
# Table: portfolios
client.table('portfolios')
  .update({'is_active': False})
  .eq('profile', profile)
  .eq('is_active', True)
  .execute()
```

**Insert New Portfolio:**
```python
# Table: portfolios
client.table('portfolios').insert({
  'profile': profile,
  'total_capital': total_capital,
  'timestamp': timestamp,
  'json_path': json_path,
  'is_active': True,
  'cash_balance': cash_balance
}).execute()
# Returns: portfolio_id
```

### 2. Add Stocks (CRITICAL)

**File:** `db_service.py:167-182`
**Entry:** `save_stocks(portfolio_id, stocks)`

```python
# Table: stocks (bulk insert)
client.table('stocks').insert({
  'portfolio_id': portfolio_id,
  'name': stock['name'],
  'ticker': stock['ticker'],
  'sector': stock['sector'],
  'entry_price': stock['entry_price'],
  'allocation_pct': stock['allocation_pct'],
  'allocation_amount': stock['allocation_amount'],
  'shares': stock['shares'],
  'stop_loss_pct': stock['stop_loss_pct'],
  'stop_loss_price': stock['stop_loss_price'],
  'target_pct': stock['target_pct'],
  'target_price': stock['target_price'],
  'rationale': stock['rationale'],
  'news_sentiment': stock['news_sentiment']
}).execute()
# Returns: stock_id (used below)
```

### 3. Investment Views

**File:** `db_service.py:287-294`

```python
# Table: investment_views (1 per stock)
client.table('investment_views').insert({
  'stock_id': stock_id,
  'market_outlook': investment_view['market_outlook'],
  'stock_rationale': investment_view['stock_rationale'],
  'holding_period': investment_view['holding_period'],
  'exit_triggers': json.dumps(investment_view['exit_triggers']),
  'review_triggers': json.dumps(investment_view['review_triggers'])
}).execute()
```

### 4. Key Metrics

**File:** `db_service.py:316-319`

```python
# Table: key_metrics (1 per stock)
client.table('key_metrics').insert({
  'stock_id': stock_id,
  'metrics_json': json.dumps(key_metrics)
}).execute()
```

### 5. Initial Snapshot

**File:** `db_service.py:788-803`

```python
# Table: portfolio_snapshots
client.table('portfolio_snapshots').upsert({
  'portfolio_id': portfolio_id,
  'snapshot_date': snapshot_date,
  'total_value': total_capital,
  'cash_balance': 0,
  'invested_value': total_capital,
  # ... 11 more metrics
}, on_conflict='portfolio_id,snapshot_date').execute()
```

---

## Portfolio Manager Operations

### 1. Store Daily Prices (CRITICAL)

**File:** `portfolio_manager_agent.py:320`
**Entry:** Step 1 - Price update loop

```python
# Table: daily_prices
client.table('daily_prices').upsert({
  'stock_id': stock_id,
  'price_date': today,
  'open_price': price,
  'high_price': price,
  'low_price': price,
  'close_price': price,
  'volume': 0
}, on_conflict='stock_id,price_date').execute()
```

### 2. Exit Position (CRITICAL)

**File:** `portfolio_manager_agent.py:1251-1293`
**Entry:** `record_position_exit()` - triggered by stop-loss/target/news

**2a. Record Transaction:**
```python
# Table: transactions
client.table('transactions').insert({
  'portfolio_id': portfolio_id,
  'stock_id': stock_id,
  'transaction_type': 'SELL',
  'quantity': quantity,
  'price': exit_price,
  'transaction_date': datetime.now(),
  'notes': f"{exit_type}: {exit_reason} (P&L: {gain_loss_pct:+.2f}%)",
  'realized_pnl_pct': gain_loss_pct,
  'realized_pnl_absolute': gain_loss_absolute,
  'trigger_type': exit_type
}).execute()
```

**2b. Mark Stock Exited:**
```python
# Table: stocks
client.table('stocks').update({
  'allocation_pct': 0,
  'allocation_amount': 0,
  'exit_date': datetime.now(),
  'exit_price': exit_price,
  'exit_type': exit_type
}).eq('id', stock_id).execute()
```

**2c. Update Cash Balance:**
```python
# Table: portfolios
client.table('portfolios')
  .update({'cash_balance': new_cash})
  .eq('id', portfolio_id)
  .execute()
```

**2d. Record Rebalancing:**
```python
# Table: rebalancing_history
client.table('rebalancing_history').insert({
  'portfolio_id': portfolio_id,
  'rebalancing_date': date,
  'reason': f"AUTO-EXECUTE: {reason}",
  'action_type': 'EXIT',
  'affected_stocks': [ticker],
  'allocation_changes': json.dumps({ticker: (old_pct, 0.0)}),
  'expected_result': f"Exit {ticker}, realized P&L {pnl:.2f}%"
}).execute()
# Returns: record_id
```

**2e. Update Rebalancing Status:**
```python
# Table: rebalancing_history
client.table('rebalancing_history').update({
  'status': 'EXECUTED',
  'executed_at': datetime.now(),
  'actual_result': f"Successfully exited {ticker}. Actual P&L: {pnl:.2f}%"
}).eq('id', record_id).execute()
```

**2f. Record Market Event:**
```python
# Table: market_events
client.table('market_events').insert({
  'event_type': 'TRIGGER_HIT',
  'title': f"{exit_type}: {ticker} exited",
  'description': f"Sold {ticker} at Rs. {exit_price:.2f} ({pnl:+.2f}%)",
  'event_date': datetime.now(),
  'portfolio_id': portfolio_id,
  'stock_id': stock_id,
  'impact': 'NEGATIVE' if exit_type == 'STOP_LOSS' else 'POSITIVE',
  'action_taken': 'POSITION_CLOSED'
}).execute()
```

### 3. Add Position (CRITICAL)

**File:** `portfolio_manager_agent.py:1295-1358`
**Entry:** `record_position_entry()` - replacement/cash deployment

**3a. Insert Stock:**
```python
# Table: stocks
client.table('stocks').insert({
  'portfolio_id': portfolio_id,
  'name': stock_data['name'],
  'ticker': stock_data['ticker'],
  'sector': stock_data['sector'],
  'entry_price': stock_data['entry_price'],
  'allocation_pct': allocation_pct,
  'allocation_amount': allocation_amount,
  'shares': quantity,
  'stop_loss_pct': stock_data['stop_loss_pct'],
  'stop_loss_price': stock_data['stop_loss_price'],
  'target_pct': stock_data['target_pct'],
  'target_price': stock_data['target_price'],
  'rationale': stock_data['rationale']
}).execute()
# Returns: stock_id
```

**3b. Record Transaction:**
```python
# Table: transactions
client.table('transactions').insert({
  'portfolio_id': portfolio_id,
  'stock_id': stock_id,
  'transaction_type': 'BUY',
  'quantity': quantity,
  'price': entry_price,
  'transaction_date': datetime.now(),
  'notes': f"New position: {rationale}"
}).execute()
```

**3c. Deduct Cash:**
```python
# Table: portfolios
client.table('portfolios')
  .update({'cash_balance': new_cash})
  .eq('id', portfolio_id)
  .execute()
```

**3d. Record Rebalancing:**
```python
# Table: rebalancing_history
client.table('rebalancing_history').insert({
  'portfolio_id': portfolio_id,
  'rebalancing_date': date,
  'reason': f"AUTO-EXECUTE: Replacement for {exited_ticker}",
  'action_type': 'ENTRY',
  'affected_stocks': [ticker],
  'allocation_changes': json.dumps({ticker: (0.0, allocation_pct)}),
  'expected_result': f"Added {ticker} with {allocation_pct:.1f}% allocation"
}).execute()
# Returns: record_id
```

**3e. Update Rebalancing Status:**
```python
# Table: rebalancing_history
client.table('rebalancing_history').update({
  'status': 'EXECUTED',
  'executed_at': datetime.now(),
  'actual_result': f"Successfully added {ticker}"
}).eq('id', record_id).execute()
```

### 4. Update Allocation

**File:** `portfolio_manager_agent.py:1189`

```python
# Table: stocks
UPDATE stocks
SET allocation_pct = ?, allocation_amount = ?
WHERE id = ?
```

### 5. Daily Snapshot

**File:** `portfolio_manager_agent.py:1658`

```python
# Table: portfolio_snapshots
client.table('portfolio_snapshots').upsert({
  'portfolio_id': portfolio_id,
  'snapshot_date': date,
  'total_value': total_value,
  'cash_balance': cash,
  'invested_value': invested,
  'total_return_pct': return_pct,
  'total_return_absolute': return_abs,
  'day_return_pct': day_pct,
  'day_return_absolute': day_abs,
  'volatility': vol,
  'sharpe_ratio': sharpe,
  'max_drawdown': drawdown,
  'num_stocks': count,
  'avg_allocation_pct': avg_pct
}, on_conflict='portfolio_id,snapshot_date').execute()
```

### 6. Benchmark Comparison

**File:** `portfolio_manager_agent.py:1667`

```python
# Table: benchmark_comparison
client.table('benchmark_comparison').upsert({
  'portfolio_id': portfolio_id,
  'comparison_date': date,
  'index_symbol': symbol,
  'index_name': name,
  'portfolio_return': p_return,
  'index_return': i_return,
  'alpha': alpha,
  'beta': beta,
  'outperformance': outperf,
  'period': period
}, on_conflict='portfolio_id,index_symbol,comparison_date,period').execute()
```

### 7. Manager Update

**File:** `portfolio_manager_agent.py:1582-1592`

```python
# Table: manager_updates
client.table('manager_updates').insert({
  'portfolio_id': portfolio_id,
  'update_date': date,
  'update_type': 'DAILY_REVIEW',
  'title': title,
  'description': assessment,
  'affected_stocks': json.dumps(stocks),
  'recommendation': recommendation,
  'reasoning': reasoning,
  'priority': priority
}).execute()
```

---

## Rollback Design Considerations

### Critical Tables Requiring `run_id`

1. **portfolios** - Track which run created/updated portfolio
2. **stocks** - Track which run added/modified stocks
3. **transactions** - Track which run recorded trades
4. **rebalancing_history** - Track which run made changes
5. **daily_prices** - Track which run stored prices

### UPSERT Tables - Special Handling

Tables using UPSERT need different rollback strategy:
- `daily_prices` - Can rollback by date + run_id
- `portfolio_snapshots` - Can rollback by date + run_id
- `benchmark_comparison` - Can rollback by date + run_id

### Recommended `run_id` Schema

```sql
-- Add to all critical tables
ALTER TABLE portfolios ADD COLUMN run_id UUID;
ALTER TABLE stocks ADD COLUMN run_id UUID;
ALTER TABLE transactions ADD COLUMN run_id UUID;
ALTER TABLE rebalancing_history ADD COLUMN run_id UUID;
ALTER TABLE daily_prices ADD COLUMN run_id UUID;
ALTER TABLE portfolio_snapshots ADD COLUMN run_id UUID;
ALTER TABLE benchmark_comparison ADD COLUMN run_id UUID;
ALTER TABLE manager_updates ADD COLUMN run_id UUID;
ALTER TABLE market_events ADD COLUMN run_id UUID;

-- Create run_log table
CREATE TABLE run_log (
  run_id UUID PRIMARY KEY,
  agent_type TEXT NOT NULL, -- 'BUILDER' or 'MANAGER'
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  status TEXT, -- 'RUNNING', 'COMPLETED', 'ROLLED_BACK'
  portfolio_id INTEGER,
  metadata JSONB
);
```

### Rollback Procedure

```sql
-- Rollback a specific run
BEGIN;
  -- Mark run as rolled back
  UPDATE run_log SET status = 'ROLLED_BACK' WHERE run_id = ?;

  -- Delete/revert all changes
  DELETE FROM transactions WHERE run_id = ?;
  DELETE FROM rebalancing_history WHERE run_id = ?;
  DELETE FROM daily_prices WHERE run_id = ?;
  DELETE FROM portfolio_snapshots WHERE run_id = ?;
  DELETE FROM benchmark_comparison WHERE run_id = ?;
  DELETE FROM manager_updates WHERE run_id = ?;
  DELETE FROM market_events WHERE run_id = ?;

  -- Revert stock changes (UPDATE back to previous state or DELETE if new)
  DELETE FROM stocks WHERE run_id = ? AND entry_date::date = (SELECT start_time::date FROM run_log WHERE run_id = ?);
  UPDATE stocks SET allocation_pct = prev_allocation_pct, ... WHERE run_id = ?;

  -- Revert portfolio changes
  UPDATE portfolios SET cash_balance = prev_cash WHERE run_id = ?;
COMMIT;
```
