import sqlite3
import json

conn = sqlite3.connect('.cache/portfolio.db')
cursor = conn.cursor()

print("=" * 80)
print("DATABASE TABLES")
print("=" * 80)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
for table in tables:
    print(f"  - {table}")

print("\n" + "=" * 80)
print("PORTFOLIOS TABLE")
print("=" * 80)
cursor.execute("SELECT * FROM portfolios")
cols = [desc[0] for desc in cursor.description]
print(f"Columns: {', '.join(cols)}\n")
for row in cursor.fetchall():
    for col, val in zip(cols, row):
        print(f"  {col}: {val}")
    print()

print("=" * 80)
print("STOCKS TABLE")
print("=" * 80)
cursor.execute("SELECT id, portfolio_id, name, ticker, sector, entry_price, allocation_pct, allocation_amount, stop_loss_price, target_price FROM stocks")
cols = [desc[0] for desc in cursor.description]
print(f"\n{cols[0]:<4} {cols[1]:<4} {cols[2]:<25} {cols[3]:<15} {cols[4]:<20} {cols[5]:<12} {cols[6]:<8} {cols[7]:<12} {cols[8]:<12} {cols[9]:<12}")
print("-" * 150)
for row in cursor.fetchall():
    print(f"{row[0]:<4} {row[1]:<4} {row[2]:<25} {row[3]:<15} {row[4]:<20} {row[5]:<12.2f} {row[6]:<8.1f} {row[7]:<12.0f} {row[8]:<12.2f} {row[9]:<12.2f}")

print("\n" + "=" * 80)
print("INVESTMENT VIEWS TABLE")
print("=" * 80)
cursor.execute("SELECT COUNT(*) FROM investment_views")
count = cursor.fetchone()[0]
print(f"Total investment views: {count}")

print("\n" + "=" * 80)
print("KEY METRICS TABLE")
print("=" * 80)
cursor.execute("SELECT COUNT(*) FROM key_metrics")
count = cursor.fetchone()[0]
print(f"Total key metrics records: {count}")

print("\n" + "=" * 80)
print("OTHER TABLES (EMPTY)")
print("=" * 80)
for table in ['transactions', 'performance_metrics', 'rebalancing_history', 'market_events']:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} records")

conn.close()
