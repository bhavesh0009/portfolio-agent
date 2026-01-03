"""
Supabase Data Import Script
Imports JSON-exported data from SQLite to Supabase PostgreSQL
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from supabase import create_client, Client

from utils.logger import get_logger

logger = get_logger("utils.import_to_supabase")


class SupabaseDataImporter:
    """Imports JSON data to Supabase"""

    # Tables in foreign key dependency order (same as export)
    TABLE_ORDER = [
        'portfolios',              # Base table
        'stocks',                  # FK → portfolios
        'investment_views',        # FK → stocks
        'key_metrics',            # FK → stocks
        'transactions',           # FK → portfolios, stocks
        'performance_metrics',    # FK → portfolios, stocks
        'rebalancing_history',    # FK → portfolios
        'market_events',          # FK → portfolios, stocks
        'daily_prices',           # FK → stocks
        'index_prices',           # Independent
        'portfolio_snapshots',    # FK → portfolios
        'benchmark_comparison',   # FK → portfolios
        'manager_updates',        # FK → portfolios
        'rebalancing_recommendations',  # FK → portfolios
        'user_benchmark_preferences'    # FK → portfolios
    ]

    def __init__(self, input_dir: str, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize importer

        Args:
            input_dir: Directory containing JSON export files
            supabase_url: Supabase project URL (defaults to env var)
            supabase_key: Supabase API key (defaults to env var)
        """
        self.input_dir = Path(input_dir)

        if not self.input_dir.exists():
            raise FileNotFoundError(f"Import directory not found: {self.input_dir}")

        # Initialize Supabase client
        url = supabase_url or os.getenv('SUPABASE_URL')
        key = supabase_key or os.getenv('SUPABASE_API_KEY')

        if not url or not key:
            raise ValueError("Supabase credentials not found. Set SUPABASE_URL and SUPABASE_API_KEY env vars.")

        self.client: Client = create_client(url, key)
        logger.info(f"Connected to Supabase: {url}")

    def import_table(self, table_name: str, batch_size: int = 100) -> Dict[str, Any]:
        """
        Import single table from JSON file

        Args:
            table_name: Name of table to import
            batch_size: Number of rows to insert per batch

        Returns:
            Import result: {'table': str, 'rows': int, 'batches': int}
        """
        logger.info(f"Importing table: {table_name}")

        json_file = self.input_dir / f"{table_name}.json"

        if not json_file.exists():
            logger.warning(f"JSON file not found: {json_file.name}, skipping")
            return {'table': table_name, 'rows': 0, 'batches': 0, 'skipped': True}

        try:
            # Load JSON data
            with open(json_file, 'r') as f:
                rows = json.load(f)

            if not rows:
                logger.info(f"✓ Table {table_name} is empty, skipping")
                return {'table': table_name, 'rows': 0, 'batches': 0, 'skipped': True}

            # Import in batches
            total_rows = len(rows)
            num_batches = (total_rows + batch_size - 1) // batch_size  # Ceiling division

            logger.info(f"  Importing {total_rows} rows in {num_batches} batches...")

            for batch_num in range(num_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_rows)
                batch = rows[start_idx:end_idx]

                # Insert batch
                response = self.client.table(table_name).insert(batch).execute()

                # Check for errors
                if hasattr(response, 'error') and response.error:
                    raise Exception(f"Supabase error: {response.error}")

                logger.debug(f"  Batch {batch_num + 1}/{num_batches}: Inserted {len(batch)} rows")

            logger.info(f"✓ Imported {total_rows} rows to {table_name}")

            return {
                'table': table_name,
                'rows': total_rows,
                'batches': num_batches,
                'skipped': False
            }

        except Exception as e:
            logger.error(f"Failed to import {table_name}: {e}")
            raise

    def import_all(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Import all tables in dependency order

        Args:
            batch_size: Number of rows to insert per batch

        Returns:
            Import summary: {
                'total_tables': int,
                'total_rows': int,
                'tables': List[Dict],
                'timestamp': str
            }
        """
        logger.info("="*60)
        logger.info("Supabase Data Import from JSON")
        logger.info("="*60)
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Batch size: {batch_size}")

        results = []
        total_rows = 0

        for table_name in self.TABLE_ORDER:
            try:
                result = self.import_table(table_name, batch_size)
                results.append(result)
                if not result.get('skipped'):
                    total_rows += result['rows']
            except Exception as e:
                logger.error(f"Import failed for {table_name}: {e}")
                results.append({
                    'table': table_name,
                    'rows': 0,
                    'batches': 0,
                    'error': str(e)
                })
                # Stop on first error to prevent FK violations
                logger.error("Stopping import due to error (FK dependency order)")
                break

        summary = {
            'total_tables': len([r for r in results if not r.get('skipped')]),
            'total_rows': total_rows,
            'tables': results,
            'input_dir': str(self.input_dir),
            'timestamp': datetime.now().isoformat()
        }

        # Save summary
        summary_file = self.input_dir / '_import_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        # Print summary
        logger.info("="*60)
        logger.info("IMPORT SUMMARY")
        logger.info("="*60)
        logger.info(f"Total tables imported: {summary['total_tables']}")
        logger.info(f"Total rows imported: {summary['total_rows']}")
        logger.info(f"\nTable breakdown:")
        for result in results:
            if result.get('skipped'):
                logger.info(f"  {result['table']}: SKIPPED (empty or missing)")
            elif result.get('error'):
                logger.warning(f"  {result['table']}: ERROR - {result['error']}")
            else:
                logger.info(f"  {result['table']}: {result['rows']} rows ({result['batches']} batches)")
        logger.info(f"\nSummary saved to: {summary_file}")
        logger.info("="*60)

        return summary


def main():
    """CLI entry point"""
    import sys

    # Default path
    input_dir = Path(__file__).parent.parent / ".cache" / "migration_export"

    # Allow custom path via CLI arg
    if len(sys.argv) > 1:
        input_dir = Path(sys.argv[1])

    print("\n" + "="*60)
    print("Supabase Data Import from JSON")
    print("="*60)
    print(f"Input directory: {input_dir}")
    print(f"Supabase URL: {os.getenv('SUPABASE_URL')}")

    if not input_dir.exists():
        print(f"\n❌ Error: Input directory not found at {input_dir}")
        print("Run export_sqlite_data.py first!")
        sys.exit(1)

    # Check for export summary
    summary_file = input_dir / '_export_summary.json'
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            export_summary = json.load(f)
        print(f"\nExport summary found:")
        print(f"  Tables: {export_summary['total_tables']}")
        print(f"  Rows: {export_summary['total_rows']}")
    else:
        print("\n⚠️  Warning: No export summary found")

    # Confirm import
    response = input("\nProceed with import to Supabase? (yes/no): ")
    if response.lower() != 'yes':
        print("Import cancelled.")
        sys.exit(0)

    # Run import
    try:
        importer = SupabaseDataImporter(str(input_dir))
        summary = importer.import_all(batch_size=100)

        print(f"\n✓ Import complete!")
        print(f"  Tables: {summary['total_tables']}")
        print(f"  Rows: {summary['total_rows']}")
        print("\n" + "="*60)

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
