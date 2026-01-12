#!/usr/bin/env python3
"""
Rollback Portfolio Manager changes by date/timestamp

Usage:
    python utils/rollback_by_date.py --date 2026-01-10 --dry-run
    python utils/rollback_by_date.py --date 2026-01-10 --keep-first  # Keep earliest run only
    python utils/rollback_by_date.py --date 2026-01-10 --keep-last   # Keep latest run only
"""

import os
import sys
from datetime import datetime, date
from pathlib import Path
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import DatabaseService
from dotenv import load_dotenv

load_dotenv()


class RollbackManager:
    """Manage rollback of portfolio manager runs by date"""

    def __init__(self):
        self.db = DatabaseService()
        self.client = self.db.client

    def analyze_date(self, target_date: str):
        """Analyze what was done on a specific date"""
        print(f"\n{'='*80}")
        print(f"ANALYSIS FOR DATE: {target_date}")
        print(f"{'='*80}\n")

        # Check manager_updates (shows number of runs)
        updates = self.client.table('manager_updates').select('id, created_at, title').eq('update_date', target_date).order('created_at').execute()

        print(f"📊 MANAGER UPDATES: {len(updates.data)} runs detected")
        for i, update in enumerate(updates.data, 1):
            print(f"  Run {i}: {update['created_at']} (ID: {update['id']})")

        # Check transactions
        transactions = self.client.table('transactions').select('id, transaction_type').gte('transaction_date', f'{target_date}T00:00:00').lte('transaction_date', f'{target_date}T23:59:59').execute()
        print(f"\n💰 TRANSACTIONS: {len(transactions.data)}")
        if transactions.data:
            for txn in transactions.data:
                print(f"  - {txn['transaction_type']} (ID: {txn['id']})")

        # Check rebalancing_history
        rebalances = self.client.table('rebalancing_history').select('id, action_type, reason').eq('rebalancing_date', target_date).execute()
        print(f"\n⚖️  REBALANCING HISTORY: {len(rebalances.data)}")
        if rebalances.data:
            for rb in rebalances.data:
                print(f"  - {rb['action_type']}: {rb['reason'][:50]}... (ID: {rb['id']})")

        # Check market_events
        events = self.client.table('market_events').select('id, event_type, title').gte('event_date', f'{target_date}T00:00:00').lte('event_date', f'{target_date}T23:59:59').execute()
        print(f"\n📰 MARKET EVENTS: {len(events.data)}")
        if events.data:
            for event in events.data:
                print(f"  - {event['event_type']}: {event['title']} (ID: {event['id']})")

        # Check portfolio_snapshots (UPSERT - should be 1)
        snapshots = self.client.table('portfolio_snapshots').select('portfolio_id, total_value, cash_balance').eq('snapshot_date', target_date).execute()
        print(f"\n📸 PORTFOLIO SNAPSHOTS: {len(snapshots.data)}")
        for snap in snapshots.data:
            print(f"  Portfolio {snap['portfolio_id']}: Value={snap['total_value']:,.2f}, Cash={snap['cash_balance']:,.2f}")

        # Check daily_prices (UPSERT)
        prices = self.client.table('daily_prices').select('stock_id').eq('price_date', target_date).execute()
        print(f"\n💵 DAILY PRICES: {len(prices.data)} stocks")

        print(f"\n{'='*80}\n")

        return {
            'runs': len(updates.data),
            'updates': updates.data,
            'transactions': transactions.data,
            'rebalances': rebalances.data,
            'events': events.data
        }

    def rollback_duplicates(self, target_date: str, keep: str = 'first', dry_run: bool = True):
        """
        Rollback duplicate runs, keeping only first or last run

        Args:
            target_date: Date to rollback (YYYY-MM-DD)
            keep: 'first' or 'last' - which run to keep
            dry_run: If True, only show what would be deleted
        """
        analysis = self.analyze_date(target_date)

        if analysis['runs'] <= 1:
            print("✅ Only 1 run detected. Nothing to rollback.")
            return

        print(f"\n{'='*80}")
        print(f"ROLLBACK PLAN: Keep {keep.upper()} run, delete {analysis['runs']-1} duplicate(s)")
        print(f"{'='*80}\n")

        # Determine which records to keep
        updates = analysis['updates']
        if keep == 'first':
            keep_record = updates[0]
            delete_records = updates[1:]
            print(f"✅ KEEPING: Run at {keep_record['created_at']} (ID: {keep_record['id']})")
        else:  # last
            keep_record = updates[-1]
            delete_records = updates[:-1]
            print(f"✅ KEEPING: Run at {keep_record['created_at']} (ID: {keep_record['id']})")

        print(f"🗑️  DELETING: {len(delete_records)} duplicate manager_updates")
        for record in delete_records:
            print(f"  - {record['created_at']} (ID: {record['id']})")

        # Also delete associated transactions, rebalances, events created in duplicate runs
        # Since we don't have run_id, we can only safely delete manager_updates duplicates

        if dry_run:
            print("\n⚠️  DRY RUN MODE - No changes made")
            print("\nTo execute, run without --dry-run flag")
            return

        # Confirm with user
        print(f"\n{'='*80}")
        response = input(f"❗ DELETE {len(delete_records)} manager_updates records? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Rollback cancelled")
            return

        # Execute deletion
        print("\n🔥 Executing rollback...\n")
        for record in delete_records:
            try:
                self.client.table('manager_updates').delete().eq('id', record['id']).execute()
                print(f"  ✅ Deleted manager_update ID {record['id']}")
            except Exception as e:
                print(f"  ❌ Failed to delete ID {record['id']}: {e}")

        print("\n✅ Rollback complete!")

        # Note about transactions/rebalances
        if analysis['transactions'] or analysis['rebalances'] or analysis['events']:
            print("\n⚠️  WARNING: This script only deleted manager_updates.")
            print("   Transactions, rebalancing_history, and market_events were NOT touched")
            print("   because we cannot determine which run created them without run_id tracking.")
            print("\n   To fully rollback, you need to:")
            print("   1. Implement run_id tracking (see docs/DATABASE_OPERATIONS.md)")
            print("   2. Or manually delete records by created_at timestamp")


def main():
    parser = argparse.ArgumentParser(description='Rollback portfolio manager runs by date')
    parser.add_argument('--date', required=True, help='Date to rollback (YYYY-MM-DD)')
    parser.add_argument('--keep', choices=['first', 'last'], default='first',
                       help='Which run to keep (default: first)')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Dry run mode (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually execute the rollback')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze, do not rollback')

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Invalid date format: {args.date}")
        print("   Use YYYY-MM-DD format (e.g., 2026-01-10)")
        sys.exit(1)

    rollback = RollbackManager()

    if args.analyze_only:
        rollback.analyze_date(args.date)
    else:
        dry_run = not args.execute
        rollback.rollback_duplicates(args.date, keep=args.keep, dry_run=dry_run)


if __name__ == '__main__':
    main()
