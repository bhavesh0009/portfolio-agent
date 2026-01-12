#!/usr/bin/env python3
"""
Calculate today's portfolio value and return, then generate INSERT statement
for portfolio_snapshots table.
"""

import os
from datetime import datetime, date
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Connect to Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_API_KEY")
supabase: Client = create_client(url, key)

portfolio_id = 42
today = date.today()

print("="*80)
print("CALCULATE TODAY'S RETURN & GENERATE INSERT STATEMENT")
print("="*80)
print(f"Portfolio ID: {portfolio_id}")
print(f"Today's Date: {today}")
print()

# 1. Get yesterday's snapshot for comparison
print("[1] Fetching yesterday's snapshot...")
print("-"*80)
yesterday_snapshot = supabase.table('portfolio_snapshots')\
    .select('*')\
    .eq('portfolio_id', portfolio_id)\
    .order('snapshot_date', desc=True)\
    .limit(1)\
    .execute()

if not yesterday_snapshot.data:
    print("✗ ERROR: No previous snapshot found!")
    exit(1)

prev_snapshot = yesterday_snapshot.data[0]
prev_date = prev_snapshot['snapshot_date']
prev_total_value = prev_snapshot['total_value']
prev_cash_balance = prev_snapshot['cash_balance']

print(f"Previous snapshot date: {prev_date}")
print(f"Previous total value: ₹{prev_total_value:,.2f}")
print(f"Previous cash balance: ₹{prev_cash_balance:,.2f}")
print()

# 2. Get current portfolio info
print("[2] Fetching portfolio and cash balance...")
print("-"*80)
portfolio = supabase.table('portfolios')\
    .select('*')\
    .eq('id', portfolio_id)\
    .single()\
    .execute()

initial_capital = portfolio.data['total_capital']
cash_balance = portfolio.data.get('cash_balance', prev_cash_balance)

print(f"Initial capital: ₹{initial_capital:,.2f}")
print(f"Current cash balance: ₹{cash_balance:,.2f}")
print()

# 3. Get active stocks and calculate today's portfolio value
print("[3] Calculating today's portfolio value...")
print("-"*80)
stocks = supabase.table('stocks')\
    .select('id, ticker, allocation_pct, entry_price, shares')\
    .eq('portfolio_id', portfolio_id)\
    .execute()

active_stocks = [s for s in stocks.data if s.get('allocation_pct', 0) > 0]
print(f"Active stocks: {len(active_stocks)}")
print()

total_stock_value = 0.0

print("Stock-by-stock valuation:")
for stock in active_stocks:
    stock_id = stock['id']
    ticker = stock['ticker']
    shares = stock.get('shares')
    allocation_pct = stock.get('allocation_pct', 0)
    entry_price = stock.get('entry_price', 0)

    # Get today's price
    today_price = supabase.table('daily_prices')\
        .select('close_price')\
        .eq('stock_id', stock_id)\
        .eq('price_date', str(today))\
        .execute()

    if not today_price.data:
        print(f"  ✗ {ticker}: NO PRICE DATA FOR TODAY!")
        continue

    close_price = today_price.data[0]['close_price']

    # Calculate shares if not stored
    if shares is None or shares == 0:
        # Estimate shares from allocation and entry price
        allocation_amount = initial_capital * (allocation_pct / 100)
        shares = int(allocation_amount / entry_price)

    stock_value = shares * close_price
    total_stock_value += stock_value

    print(f"  {ticker}: {shares} shares × ₹{close_price:.2f} = ₹{stock_value:,.2f}")

print()
print(f"Total stock value: ₹{total_stock_value:,.2f}")
print(f"Cash balance: ₹{cash_balance:,.2f}")

today_total_value = total_stock_value + cash_balance
invested_value = total_stock_value

print(f"Today's total portfolio value: ₹{today_total_value:,.2f}")
print()

# 4. Calculate returns
print("[4] Calculating returns...")
print("-"*80)

# Day return
day_return_absolute = today_total_value - prev_total_value
day_return_pct = (day_return_absolute / prev_total_value) * 100

print(f"Previous value: ₹{prev_total_value:,.2f} ({prev_date})")
print(f"Today's value: ₹{today_total_value:,.2f} ({today})")
print(f"Day return: ₹{day_return_absolute:,.2f} ({day_return_pct:.2f}%)")
print()

# Total return (since inception)
total_return_absolute = today_total_value - initial_capital
total_return_pct = (total_return_absolute / initial_capital) * 100

print(f"Initial capital: ₹{initial_capital:,.2f}")
print(f"Current value: ₹{today_total_value:,.2f}")
print(f"Total return: ₹{total_return_absolute:,.2f} ({total_return_pct:.2f}%)")
print()

# 5. Calculate risk metrics (need historical data)
print("[5] Calculating risk metrics...")
print("-"*80)

# Get all snapshots to calculate volatility, sharpe, max_drawdown
all_snapshots = supabase.table('portfolio_snapshots')\
    .select('snapshot_date, total_value, day_return_pct')\
    .eq('portfolio_id', portfolio_id)\
    .order('snapshot_date', desc=False)\
    .execute()

snapshots_data = all_snapshots.data

# Calculate volatility (annualized standard deviation of daily returns)
import math
import statistics

daily_returns = [s['day_return_pct'] for s in snapshots_data if s.get('day_return_pct') is not None]
daily_returns.append(day_return_pct)  # Add today's return

if len(daily_returns) > 1:
    volatility_daily = statistics.stdev(daily_returns)
    volatility_annualized = volatility_daily * math.sqrt(252)  # 252 trading days
else:
    volatility_annualized = 0.0

print(f"Volatility (annualized): {volatility_annualized:.2f}%")

# Calculate Sharpe ratio (assuming 0% risk-free rate for simplicity)
avg_daily_return = statistics.mean(daily_returns) if daily_returns else 0
if volatility_daily > 0:
    sharpe_ratio = (avg_daily_return / volatility_daily) * math.sqrt(252)
else:
    sharpe_ratio = 0.0

print(f"Sharpe ratio: {sharpe_ratio:.2f}")

# Calculate max drawdown
peak_value = initial_capital
max_drawdown = 0.0

for snapshot in snapshots_data:
    value = snapshot['total_value']
    if value > peak_value:
        peak_value = value
    drawdown = ((peak_value - value) / peak_value) * 100
    if drawdown > max_drawdown:
        max_drawdown = drawdown

# Check if today creates a new peak or drawdown
if today_total_value > peak_value:
    peak_value = today_total_value
    current_drawdown = 0.0
else:
    current_drawdown = ((peak_value - today_total_value) / peak_value) * 100
    if current_drawdown > max_drawdown:
        max_drawdown = current_drawdown

print(f"Max drawdown: {max_drawdown:.2f}%")
print()

# 6. Generate INSERT statement
print("[6] Generating INSERT statement...")
print("-"*80)
print()

num_stocks = len(active_stocks)
avg_allocation_pct = 100.0 / num_stocks if num_stocks > 0 else 0.0

insert_statement = f"""-- Insert today's portfolio snapshot
INSERT INTO portfolio_snapshots (
    portfolio_id,
    snapshot_date,
    total_value,
    cash_balance,
    invested_value,
    total_return_pct,
    total_return_absolute,
    day_return_pct,
    day_return_absolute,
    volatility,
    sharpe_ratio,
    max_drawdown,
    num_stocks,
    avg_allocation_pct,
    created_at
) VALUES (
    {portfolio_id},
    '{today}',
    {today_total_value:.2f},
    {cash_balance:.2f},
    {invested_value:.2f},
    {total_return_pct:.2f},
    {total_return_absolute:.2f},
    {day_return_pct:.2f},
    {day_return_absolute:.2f},
    {volatility_annualized:.2f},
    {sharpe_ratio:.2f},
    {max_drawdown:.2f},
    {num_stocks},
    {avg_allocation_pct:.2f},
    NOW()
);"""

print(insert_statement)
print()

print("="*80)
print("SUMMARY")
print("="*80)
print(f"Today's Date: {today}")
print(f"Today's Total Value: ₹{today_total_value:,.2f}")
print(f"Day Return: {day_return_pct:.2f}% (₹{day_return_absolute:,.2f})")
print(f"Total Return: {total_return_pct:.2f}% (₹{total_return_absolute:,.2f})")
print()
print("Copy the INSERT statement above and execute it in Supabase SQL Editor")
print("="*80)
