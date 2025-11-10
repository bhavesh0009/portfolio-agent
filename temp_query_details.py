import sqlite3
import json

conn = sqlite3.connect('.cache/portfolio.db')
cursor = conn.cursor()

print("=" * 80)
print("DETAILED STOCK RECORD: Waaree Energies")
print("=" * 80)

# Get stock details
cursor.execute("""
    SELECT s.*, iv.market_outlook, iv.stock_rationale, iv.holding_period,
           iv.exit_triggers, iv.review_triggers, km.metrics_json
    FROM stocks s
    LEFT JOIN investment_views iv ON s.id = iv.stock_id
    LEFT JOIN key_metrics km ON s.id = km.stock_id
    WHERE s.id = 1
""")

row = cursor.fetchone()
cols = [desc[0] for desc in cursor.description]

print("\nBASIC INFO:")
print(f"  ID: {row[0]}")
print(f"  Name: {row[2]}")
print(f"  Ticker: {row[3]}")
print(f"  Sector: {row[4]}")

print("\nPRICE & ALLOCATION:")
print(f"  Entry Price: Rs. {row[5]:,.2f}")
print(f"  Allocation %: {row[6]}%")
print(f"  Allocation Amount: Rs. {row[7]:,.0f}")
print(f"  Stop Loss: Rs. {row[8]:,.2f} ({row[7]} - {row[8]}%)")
print(f"  Target: Rs. {row[9]:,.2f} ({row[10]}%)")

print("\nRATIONALE:")
print(f"  {row[11]}")

print("\nINVESTMENT VIEW:")
print(f"  Market Outlook: {row[14][:150]}...")
print(f"  Stock Rationale: {row[15][:150]}...")
print(f"  Holding Period: {row[16]}")

print("\nEXIT TRIGGERS:")
exit_triggers = json.loads(row[17])
for i, trigger in enumerate(exit_triggers, 1):
    print(f"  {i}. {trigger}")

print("\nREVIEW TRIGGERS:")
review_triggers = json.loads(row[18])
for i, trigger in enumerate(review_triggers, 1):
    print(f"  {i}. {trigger}")

print("\nKEY METRICS:")
metrics = json.loads(row[19])
for key, value in metrics.items():
    print(f"  {key}: {value}")

conn.close()
