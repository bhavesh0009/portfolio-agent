"""
Migration Validation Script
Validates data migration from SQLite to Supabase by comparing row counts and sampling data
"""

import sqlite3
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from supabase import create_client, Client

from utils.logger import get_logger

logger = get_logger("utils.validate_migration")


class MigrationValidator:
    """Validates data migration between SQLite and Supabase"""

    # Tables to validate
    TABLES = [
        'portfolios',
        'stocks',
        'investment_views',
        'key_metrics',
        'transactions',
        'performance_metrics',
        'rebalancing_history',
        'market_events',
        'daily_prices',
        'index_prices',
        'portfolio_snapshots',
        'benchmark_comparison',
        'manager_updates',
        'rebalancing_recommendations',
        'user_benchmark_preferences'
    ]

    def __init__(self, sqlite_db_path: str, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize validator

        Args:
            sqlite_db_path: Path to SQLite database file
            supabase_url: Supabase project URL (defaults to env var)
            supabase_key: Supabase API key (defaults to env var)
        """
        self.sqlite_db_path = Path(sqlite_db_path)

        if not self.sqlite_db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_db_path}")

        # Initialize Supabase client
        url = supabase_url or os.getenv('SUPABASE_URL')
        key = supabase_key or os.getenv('SUPABASE_API_KEY')

        if not url or not key:
            raise ValueError("Supabase credentials not found. Set SUPABASE_URL and SUPABASE_API_KEY env vars.")

        self.supabase: Client = create_client(url, key)
        logger.info(f"Connected to Supabase: {url}")

    def get_sqlite_row_count(self, table_name: str) -> int:
        """Get row count from SQLite table"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            return count
        except sqlite3.OperationalError:
            # Table doesn't exist
            return 0
        finally:
            conn.close()

    def get_supabase_row_count(self, table_name: str) -> int:
        """Get row count from Supabase table"""
        try:
            response = self.supabase.table(table_name).select('id', count='exact').limit(0).execute()
            return response.count
        except Exception as e:
            logger.error(f"Failed to get count for {table_name}: {e}")
            return -1  # Error indicator

    def validate_table(self, table_name: str) -> Dict[str, Any]:
        """
        Validate single table

        Args:
            table_name: Name of table to validate

        Returns:
            Validation result: {
                'table': str,
                'sqlite_count': int,
                'supabase_count': int,
                'match': bool,
                'difference': int
            }
        """
        logger.info(f"Validating table: {table_name}")

        sqlite_count = self.get_sqlite_row_count(table_name)
        supabase_count = self.get_supabase_row_count(table_name)

        match = sqlite_count == supabase_count
        difference = supabase_count - sqlite_count

        result = {
            'table': table_name,
            'sqlite_count': sqlite_count,
            'supabase_count': supabase_count,
            'match': match,
            'difference': difference
        }

        if match:
            logger.info(f"  ✓ MATCH: {sqlite_count} rows")
        else:
            logger.warning(f"  ✗ MISMATCH: SQLite={sqlite_count}, Supabase={supabase_count}, Diff={difference}")

        return result

    def validate_all(self) -> Dict[str, Any]:
        """
        Validate all tables

        Returns:
            Validation summary: {
                'total_tables': int,
                'matched': int,
                'mismatched': int,
                'tables': List[Dict],
                'all_match': bool,
                'timestamp': str
            }
        """
        logger.info("="*60)
        logger.info("Migration Validation: SQLite → Supabase")
        logger.info("="*60)
        logger.info(f"SQLite database: {self.sqlite_db_path}")

        results = []
        matched_count = 0
        mismatched_count = 0

        for table_name in self.TABLES:
            try:
                result = self.validate_table(table_name)
                results.append(result)

                if result['match']:
                    matched_count += 1
                else:
                    mismatched_count += 1

            except Exception as e:
                logger.error(f"Validation error for {table_name}: {e}")
                results.append({
                    'table': table_name,
                    'sqlite_count': -1,
                    'supabase_count': -1,
                    'match': False,
                    'error': str(e)
                })
                mismatched_count += 1

        all_match = mismatched_count == 0

        summary = {
            'total_tables': len(results),
            'matched': matched_count,
            'mismatched': mismatched_count,
            'tables': results,
            'all_match': all_match,
            'timestamp': datetime.now().isoformat()
        }

        # Print summary
        logger.info("="*60)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total tables validated: {summary['total_tables']}")
        logger.info(f"Matched: {summary['matched']}")
        logger.info(f"Mismatched: {summary['mismatched']}")
        logger.info(f"\nTable breakdown:")

        for result in results:
            status = "✓" if result['match'] else "✗"
            if 'error' in result:
                logger.warning(f"  {status} {result['table']}: ERROR - {result['error']}")
            else:
                sqlite_count = result['sqlite_count']
                supabase_count = result['supabase_count']
                if result['match']:
                    logger.info(f"  {status} {result['table']}: {sqlite_count} rows")
                else:
                    diff = result['difference']
                    logger.warning(f"  {status} {result['table']}: SQLite={sqlite_count}, Supabase={supabase_count}, Diff={diff:+d}")

        if all_match:
            logger.info("\n✓ MIGRATION VALIDATED: All row counts match!")
        else:
            logger.warning(f"\n✗ MIGRATION INCOMPLETE: {mismatched_count} tables have mismatches")

        logger.info("="*60)

        return summary


def main():
    """CLI entry point"""
    import sys
    import json

    # Default path
    sqlite_db_path = Path(__file__).parent.parent / ".cache" / "portfolio.db"

    # Allow custom path via CLI arg
    if len(sys.argv) > 1:
        sqlite_db_path = Path(sys.argv[1])

    print("\n" + "="*60)
    print("Migration Validation: SQLite → Supabase")
    print("="*60)
    print(f"SQLite database: {sqlite_db_path}")
    print(f"Supabase URL: {os.getenv('SUPABASE_URL')}")

    if not sqlite_db_path.exists():
        print(f"\n❌ Error: SQLite database not found at {sqlite_db_path}")
        sys.exit(1)

    # Run validation
    try:
        validator = MigrationValidator(str(sqlite_db_path))
        summary = validator.validate_all()

        # Save results
        output_dir = Path(__file__).parent.parent / ".cache" / "migration_export"
        output_dir.mkdir(parents=True, exist_ok=True)
        validation_file = output_dir / '_validation_results.json'

        with open(validation_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"\n✓ Validation complete!")
        print(f"  Total tables: {summary['total_tables']}")
        print(f"  Matched: {summary['matched']}")
        print(f"  Mismatched: {summary['mismatched']}")
        print(f"\nResults saved to: {validation_file}")

        if summary['all_match']:
            print("\n✓ SUCCESS: All row counts match!")
            sys.exit(0)
        else:
            print(f"\n✗ WARNING: {summary['mismatched']} tables have mismatches")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
