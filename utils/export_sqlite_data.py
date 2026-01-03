"""
SQLite Data Export Script
Exports all portfolio tables from SQLite database to JSON files for Supabase migration
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("utils.export_sqlite_data")


class SQLiteDataExporter:
    """Exports SQLite data to JSON files"""

    # Tables in foreign key dependency order
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

    def __init__(self, db_path: str, output_dir: str):
        """
        Initialize exporter

        Args:
            db_path: Path to SQLite database file
            output_dir: Directory to save JSON export files
        """
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def export_table(self, table_name: str) -> Dict[str, Any]:
        """
        Export single table to JSON file

        Args:
            table_name: Name of table to export

        Returns:
            Export result: {'table': str, 'rows': int, 'file': Path}
        """
        logger.info(f"Exporting table: {table_name}")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        cursor = conn.cursor()

        try:
            # Check if table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            if not cursor.fetchone():
                logger.warning(f"Table {table_name} does not exist in database, skipping")
                return {'table': table_name, 'rows': 0, 'file': None, 'skipped': True}

            # Export all rows
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = [dict(row) for row in cursor.fetchall()]

            # Save to JSON file
            output_file = self.output_dir / f"{table_name}.json"
            with open(output_file, 'w') as f:
                json.dump(rows, f, indent=2, default=str)  # default=str handles dates

            logger.info(f"✓ Exported {len(rows)} rows from {table_name} to {output_file.name}")

            return {
                'table': table_name,
                'rows': len(rows),
                'file': output_file,
                'skipped': False
            }

        except Exception as e:
            logger.error(f"Failed to export {table_name}: {e}")
            raise
        finally:
            conn.close()

    def export_all(self) -> Dict[str, Any]:
        """
        Export all tables in dependency order

        Returns:
            Export summary: {
                'total_tables': int,
                'total_rows': int,
                'tables': List[Dict],
                'output_dir': Path,
                'timestamp': str
            }
        """
        logger.info("="*60)
        logger.info("SQLite Data Export to JSON")
        logger.info("="*60)
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Output directory: {self.output_dir}")

        results = []
        total_rows = 0

        for table_name in self.TABLE_ORDER:
            try:
                result = self.export_table(table_name)
                results.append(result)
                if not result.get('skipped'):
                    total_rows += result['rows']
            except Exception as e:
                logger.error(f"Export failed for {table_name}: {e}")
                results.append({
                    'table': table_name,
                    'rows': 0,
                    'file': None,
                    'error': str(e)
                })

        summary = {
            'total_tables': len([r for r in results if not r.get('skipped')]),
            'total_rows': total_rows,
            'tables': results,
            'output_dir': str(self.output_dir),
            'timestamp': datetime.now().isoformat()
        }

        # Save summary
        summary_file = self.output_dir / '_export_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        # Print summary
        logger.info("="*60)
        logger.info("EXPORT SUMMARY")
        logger.info("="*60)
        logger.info(f"Total tables exported: {summary['total_tables']}")
        logger.info(f"Total rows exported: {summary['total_rows']}")
        logger.info(f"\nTable breakdown:")
        for result in results:
            if result.get('skipped'):
                logger.info(f"  {result['table']}: SKIPPED (table does not exist)")
            elif result.get('error'):
                logger.warning(f"  {result['table']}: ERROR - {result['error']}")
            else:
                logger.info(f"  {result['table']}: {result['rows']} rows")
        logger.info(f"\nExport files saved to: {self.output_dir}")
        logger.info(f"Summary saved to: {summary_file}")
        logger.info("="*60)

        return summary


def main():
    """CLI entry point"""
    import sys

    # Default paths
    db_path = Path(__file__).parent.parent / ".cache" / "portfolio.db"
    output_dir = Path(__file__).parent.parent / ".cache" / "migration_export"

    # Allow custom paths via CLI args
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    print("\n" + "="*60)
    print("SQLite Data Export for Supabase Migration")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Output: {output_dir}")

    if not db_path.exists():
        print(f"\n❌ Error: Database not found at {db_path}")
        sys.exit(1)

    # Confirm export
    response = input("\nProceed with export? (yes/no): ")
    if response.lower() != 'yes':
        print("Export cancelled.")
        sys.exit(0)

    # Run export
    exporter = SQLiteDataExporter(str(db_path), str(output_dir))
    summary = exporter.export_all()

    print(f"\n✓ Export complete!")
    print(f"  Tables: {summary['total_tables']}")
    print(f"  Rows: {summary['total_rows']}")
    print(f"  Location: {summary['output_dir']}")
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
