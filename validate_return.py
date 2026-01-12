#!/usr/bin/env python3
"""
Validate today's return calculation for dashboard
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

print("="*80)
print("VALIDATION: Today's Return Calculation")
print("="*80)
print(f"Portfolio ID: {portfolio_id}")
print(f"Today's Date: {date.today()}")
print()

# 1. Check portfolio_snapshots for today and yesterday
print("[1] Checking portfolio_snapshots...")
print("-"*80)
snapshots = supabase.table('portfolio_snapshots')\
    .select('*')\
    .eq('portfolio_id', portfolio_id)\
    .order('snapshot_date', desc=True)\
    .limit(5)\
    .execute()

if snapshots.data:
    print(f"Found {len(snapshots.data)} recent snapshots:")
    for snap in snapshots.data:
        print(f"  - {snap['snapshot_date']}: Total Value = ₹{snap['total_value']:,.2f}, Cash = ₹{snap['cash_balance']:,.2f}")

    latest_snapshot = snapshots.data[0]
    latest_date = latest_snapshot['snapshot_date']

    print(f"\nLatest snapshot date: {latest_date}")
    print(f"Today's date: {date.today()}")

    if str(latest_date) == str(date.today()):
        print("✓ Today's snapshot EXISTS")
    else:
        print(f"✗ Today's snapshot MISSING (latest is {latest_date})")
else:
    print("✗ No snapshots found!")

print()

# 2. Check stocks table for current holdings
print("[2] Checking current stock holdings...")
print("-"*80)
stocks = supabase.table('stocks')\
    .select('id, ticker, allocation_pct, entry_price, exit_date')\
    .eq('portfolio_id', portfolio_id)\
    .execute()

if stocks.data:
    active_stocks = [s for s in stocks.data if s.get('allocation_pct', 0) > 0 and s.get('exit_date') is None]
    exited_stocks = [s for s in stocks.data if s.get('allocation_pct', 0) == 0 or s.get('exit_date') is not None]

    print(f"Total stocks: {len(stocks.data)}")
    print(f"Active stocks: {len(active_stocks)}")
    print(f"Exited stocks: {len(exited_stocks)}")

    print("\nActive holdings:")
    for stock in active_stocks:
        print(f"  - {stock['ticker']}: {stock['allocation_pct']}%")

    if exited_stocks:
        print("\nExited stocks:")
        for stock in exited_stocks:
            print(f"  - {stock['ticker']}: exit_date={stock.get('exit_date')}")

print()

# 3. Check daily_prices for today
print("[3] Checking daily_prices for today...")
print("-"*80)
today_str = str(date.today())
for stock in active_stocks:
    stock_id = stock['id']
    ticker = stock['ticker']

    daily_price = supabase.table('daily_prices')\
        .select('*')\
        .eq('stock_id', stock_id)\
        .eq('price_date', today_str)\
        .execute()

    if daily_price.data:
        price_data = daily_price.data[0]
        print(f"  ✓ {ticker}: ₹{price_data['close_price']:.2f} (as of {price_data['price_date']})")
    else:
        print(f"  ✗ {ticker}: NO PRICE DATA FOR TODAY")

print()

# 4. Check today's snapshot for today's return
print("[4] Checking today's snapshot for today's return...")
print("-"*80)
if snapshots.data and len(snapshots.data) > 0:
    latest = snapshots.data[0]
    print(f"Latest snapshot date: {latest['snapshot_date']}")
    print(f"  - Total value: ₹{latest['total_value']:,.2f}")
    print(f"  - Cash balance: ₹{latest['cash_balance']:,.2f}")
    print(f"  - Total return: {latest.get('total_return_pct', 0):.2f}%")
    print(f"  - Day return: {latest.get('day_return_pct', 0):.2f}%")
    print(f"  - Max drawdown: {latest.get('max_drawdown', 0):.2f}%")
    print(f"  - Sharpe ratio: {latest.get('sharpe_ratio', 0):.2f}")
else:
    print("✗ No snapshots found")

print()

# 5. Manual calculation of today's return
print("[5] Manual calculation of today's return...")
print("-"*80)

if len(snapshots.data) >= 2:
    latest_snapshot = snapshots.data[0]
    previous_snapshot = snapshots.data[1]

    latest_value = latest_snapshot['total_value']
    previous_value = previous_snapshot['total_value']

    calculated_return = ((latest_value - previous_value) / previous_value) * 100

    print(f"Latest value: ₹{latest_value:,.2f} ({latest_snapshot['snapshot_date']})")
    print(f"Previous value: ₹{previous_value:,.2f} ({previous_snapshot['snapshot_date']})")
    print(f"Calculated return: {calculated_return:.2f}%")

    stored_return = latest_snapshot.get('day_return_pct', None)
    if stored_return is not None:
        print(f"Stored day_return_pct: {stored_return:.2f}%")

        if abs(calculated_return - stored_return) < 0.01:
            print(f"\n✓ VALIDATION PASSED: Returns match!")
        else:
            print(f"\n✗ VALIDATION FAILED: Mismatch!")
            print(f"   Calculated: {calculated_return:.2f}%")
            print(f"   Stored: {stored_return:.2f}%")
            print(f"   Difference: {abs(calculated_return - stored_return):.2f}%")
    else:
        print(f"\n⚠ day_return_pct is NULL in snapshot")
        print(f"   Calculated return should be: {calculated_return:.2f}%")
else:
    print("✗ Not enough snapshots to calculate today's return (need at least 2)")

print()
print("="*80)
print("VALIDATION COMPLETE")
print("="*80)
