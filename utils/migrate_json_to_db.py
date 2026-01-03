"""
JSON Portfolio Migration to Database
Automatically migrates existing JSON portfolios to SQLite database
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.db_service import get_db_service

logger = get_logger("utils.migrate_json_to_db")


class JSONPortfolioMigrator:
    """Migrates JSON portfolios to database"""

    def __init__(self):
        self.db = get_db_service()
        self.cache_dir = Path(__file__).parent.parent / ".cache" / "portfolios"

    def discover_json_portfolios(self) -> List[Dict[str, Any]]:
        """
        Find all JSON portfolios not yet in database

        Returns:
            List of dicts with json_path, profile, timestamp
        """
        if not self.cache_dir.exists():
            logger.warning(f"Portfolio directory not found: {self.cache_dir}")
            return []

        # Find all portfolio JSON files
        json_files = list(self.cache_dir.glob("portfolio_*.json"))

        logger.info(f"Found {len(json_files)} JSON portfolio files")

        unmigrated = []

        for json_file in json_files:
            # Parse filename: portfolio_{profile}_{timestamp}.json
            filename = json_file.stem  # Remove .json
            parts = filename.split('_')

            if len(parts) < 3:
                logger.warning(f"Invalid filename format: {json_file.name}")
                continue

            profile = parts[1]
            timestamp = '_'.join(parts[2:])  # Handle timestamps with underscores

            # Check if portfolio with this timestamp exists in database
            existing = self.db.execute_query(
                "SELECT id FROM portfolios WHERE timestamp = ?",
                (timestamp,)
            )

            if existing:
                logger.debug(f"Portfolio {timestamp} already in database (ID: {existing[0]['id']})")
                continue

            unmigrated.append({
                'json_path': json_file,
                'profile': profile,
                'timestamp': timestamp
            })

        logger.info(f"Found {len(unmigrated)} portfolios not yet in database")
        return unmigrated

    def migrate_portfolio(self, json_path: Path) -> Optional[int]:
        """
        Import single JSON portfolio to database

        Args:
            json_path: Path to JSON file

        Returns:
            portfolio_id if successful, None if failed
        """
        logger.info(f"Migrating portfolio from {json_path.name}")

        try:
            # Load JSON file
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Handle both nested and flat formats
            if 'metadata' in data and 'portfolio' in data:
                # Nested format: {metadata: {...}, portfolio: {...}}
                metadata = data['metadata']
                portfolio_data = data['portfolio']

                profile = metadata.get('profile', 'aggressive')
                total_capital = metadata.get('total_capital', 500000)
                created_at = metadata.get('created_at', datetime.now().isoformat())
                timestamp = metadata.get('timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))

                stocks = portfolio_data.get('stocks', [])
            else:
                # Flat format: {profile: ..., total_capital: ..., stocks: [...]}
                profile = data.get('profile', 'aggressive')
                total_capital = data.get('total_capital', 500000)
                created_at = data.get('created_at', datetime.now().isoformat())
                timestamp = data.get('timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))

                stocks = data.get('stocks', [])

            if not stocks:
                logger.warning(f"No stocks found in {json_path.name}, skipping")
                return None

            # Check for duplicate by timestamp
            existing = self.db.execute_query(
                "SELECT id FROM portfolios WHERE timestamp = ?",
                (timestamp,)
            )

            if existing:
                logger.warning(f"Portfolio with timestamp {timestamp} already exists (ID: {existing[0]['id']}), skipping")
                return existing[0]['id']

            # Save portfolio to database
            portfolio_id = self.db.save_portfolio(
                profile=profile,
                total_capital=total_capital,
                timestamp=timestamp,
                json_path=str(json_path),
                is_active=0  # Historical portfolio (only latest should be active)
            )

            logger.info(f"Saved portfolio to database (ID: {portfolio_id})")

            # Save stocks
            stock_ids = self.db.save_stocks(portfolio_id, stocks)

            logger.info(f"Saved {len(stock_ids)} stocks to database")

            return portfolio_id

        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON in {json_path.name}: {e}")
            return None
        except KeyError as e:
            logger.error(f"Missing required field in {json_path.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to migrate {json_path.name}: {e}")
            return None

    def migrate_all(self) -> Dict[str, Any]:
        """
        Migrate all unmigrated portfolios

        Returns:
            Migration summary: {
                'total_found': int,
                'migrated': int,
                'skipped': int,
                'failed': int,
                'errors': List[str]
            }
        """
        logger.info("Starting portfolio migration from JSON to database")

        # Discover unmigrated portfolios
        portfolios_to_migrate = self.discover_json_portfolios()

        summary = {
            'total_found': len(portfolios_to_migrate),
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }

        if not portfolios_to_migrate:
            logger.info("No portfolios to migrate")
            return summary

        # Migrate each portfolio
        for portfolio_info in portfolios_to_migrate:
            json_path = portfolio_info['json_path']

            try:
                portfolio_id = self.migrate_portfolio(json_path)

                if portfolio_id is not None:
                    summary['migrated'] += 1
                    logger.info(f"Successfully migrated {json_path.name} (ID: {portfolio_id})")
                else:
                    summary['failed'] += 1
                    error_msg = f"Migration failed for {json_path.name}"
                    summary['errors'].append(error_msg)
                    logger.warning(error_msg)

            except Exception as e:
                summary['failed'] += 1
                error_msg = f"Exception migrating {json_path.name}: {str(e)}"
                summary['errors'].append(error_msg)
                logger.error(error_msg)

        # Log summary
        logger.info("="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total portfolios found: {summary['total_found']}")
        logger.info(f"Successfully migrated: {summary['migrated']}")
        logger.info(f"Skipped (duplicates): {summary['skipped']}")
        logger.info(f"Failed: {summary['failed']}")

        if summary['errors']:
            logger.warning(f"\nErrors ({len(summary['errors'])}):")
            for error in summary['errors']:
                logger.warning(f"  - {error}")

        logger.info("="*60)

        return summary

    def mark_latest_as_active(self, profile: str) -> bool:
        """
        Mark the most recent portfolio for a profile as active

        Args:
            profile: Portfolio profile ('aggressive' or 'defensive')

        Returns:
            True if successful
        """
        try:
            # Deactivate all portfolios for this profile
            self.db.execute_update(
                "UPDATE portfolios SET is_active = 0 WHERE profile = ?",
                (profile,)
            )

            # Activate the most recent one
            latest = self.db.execute_query(
                """
                SELECT id FROM portfolios
                WHERE profile = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (profile,)
            )

            if latest:
                portfolio_id = latest[0]['id']
                self.db.execute_update(
                    "UPDATE portfolios SET is_active = 1 WHERE id = ?",
                    (portfolio_id,)
                )
                logger.info(f"Marked portfolio {portfolio_id} as active for {profile}")
                return True
            else:
                logger.warning(f"No portfolios found for profile: {profile}")
                return False

        except Exception as e:
            logger.error(f"Failed to mark latest portfolio as active: {e}")
            return False


def main():
    """CLI interface for migration"""
    migrator = JSONPortfolioMigrator()

    print("\n" + "="*60)
    print("JSON Portfolio Migration to Database")
    print("="*60)

    # Discover portfolios
    portfolios = migrator.discover_json_portfolios()

    if not portfolios:
        print("\nNo unmigrated portfolios found.")
        return

    print(f"\nFound {len(portfolios)} portfolios to migrate:")
    for p in portfolios:
        print(f"  - {p['json_path'].name} ({p['profile']})")

    # Confirm migration
    response = input("\nProceed with migration? (yes/no): ")

    if response.lower() != 'yes':
        print("Migration cancelled.")
        return

    # Run migration
    print("\nMigrating portfolios...")
    result = migrator.migrate_all()

    print(f"\n✓ Migration complete!")
    print(f"  Migrated: {result['migrated']}")
    print(f"  Failed: {result['failed']}")

    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")

    # Mark latest as active
    print("\nMarking latest portfolios as active...")
    for profile in ['aggressive', 'defensive']:
        migrator.mark_latest_as_active(profile)

    print("\n" + "="*60)


if __name__ == '__main__':
    main()
