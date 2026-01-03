"""
Portfolio Symbol Migration Script

Fixes incorrect symbols in existing portfolio JSON files by looking up
correct NSE/BSE symbols from screener.in company hrefs.

Usage:
    python tools/migrate_portfolio_symbols.py --portfolio latest_aggressive.json
    python tools/migrate_portfolio_symbols.py --all
    python tools/migrate_portfolio_symbols.py --dry-run

Author: Portfolio Agent System
Created: 2025-01-09
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional
import shutil
from datetime import datetime
import sys
import yfinance as yf

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.yfinance_enricher import get_enricher
from tools.symbol_validator import validate_yfinance_symbol
from utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioSymbolMigrator:
    """Migrates portfolio symbols from incorrect to correct NSE/BSE symbols"""

    def __init__(self, portfolio_dir: Path = None, cache_dir: Path = None):
        """
        Initialize migrator.

        Args:
            portfolio_dir: Directory containing portfolio JSON files
            cache_dir: Directory containing screening results cache
        """
        # Default paths
        if portfolio_dir is None:
            portfolio_dir = Path(__file__).parent.parent / ".cache" / "portfolios"
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / ".cache" / "screening_results"

        self.portfolio_dir = portfolio_dir
        self.cache_dir = cache_dir
        self.enricher = get_enricher()

        # Load symbol overrides if exists
        self.overrides_file = Path(__file__).parent.parent / ".cache" / "symbol_overrides.json"
        self.symbol_overrides = {}

        if self.overrides_file.exists():
            with open(self.overrides_file, 'r') as f:
                self.symbol_overrides = json.load(f)
            logger.info(f"Loaded {len(self.symbol_overrides)} symbol overrides")

        logger.info(f"Portfolio directory: {self.portfolio_dir}")
        logger.info(f"Cache directory: {self.cache_dir}")

    def search_symbol_by_name(self, company_name: str) -> Optional[tuple]:
        """
        Search for correct symbol using yfinance search.

        Args:
            company_name: Company name to search for

        Returns:
            Tuple of (symbol, exchange) or None if not found
        """
        try:
            # Try direct yfinance search
            search_results = yf.Ticker(company_name).info

            if search_results and 'symbol' in search_results:
                symbol = search_results['symbol']

                # Determine exchange from suffix
                if symbol.endswith('.NS'):
                    return (symbol[:-3], 'NSE')
                elif symbol.endswith('.BO'):
                    return (symbol[:-3], 'BSE')

            logger.debug(f"No yfinance search results for: {company_name}")
            return None

        except Exception as e:
            logger.debug(f"yfinance search failed for {company_name}: {e}")
            return None

    def find_symbol_in_cache(self, stock_name: str) -> Optional[tuple]:
        """
        Find correct symbol by searching in screening results cache and overrides.

        Args:
            stock_name: Name of the stock to find

        Returns:
            Tuple of (symbol, exchange) or None if not found
        """
        # Check overrides first
        if stock_name in self.symbol_overrides:
            override = self.symbol_overrides[stock_name]
            symbol = override['ticker']
            exchange = override['exchange']
            logger.info(f"Found symbol in overrides: {stock_name} -> {symbol} ({exchange})")
            return (symbol, exchange)

        logger.debug(f"Searching cache for: {stock_name}")

        # Search all JSON files in cache directory
        if not self.cache_dir.exists():
            logger.warning(f"Cache directory not found: {self.cache_dir}")
            return None

        cache_files = list(self.cache_dir.glob("*.json"))
        logger.debug(f"Found {len(cache_files)} cache files to search")

        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)

                stocks = cache_data.get('stocks', [])

                # Search for matching stock name
                for stock in stocks:
                    if stock.get('Name', '').lower().strip() == stock_name.lower().strip():
                        # Found matching stock, extract symbol from _company_href
                        href = stock.get('_company_href')

                        if href:
                            extracted = self.enricher.extract_symbol_from_href(href)
                            if extracted:
                                symbol, exchange = extracted
                                logger.info(f"Found symbol in cache: {stock_name} -> {symbol} ({exchange})")
                                return (symbol, exchange)

            except Exception as e:
                logger.debug(f"Error reading cache file {cache_file}: {e}")
                continue

        logger.warning(f"Symbol not found in cache for: {stock_name}")
        return None

    def migrate_stock_symbol(self, stock: Dict, dry_run: bool = False) -> Dict:
        """
        Migrate a single stock's symbol.

        Args:
            stock: Stock dictionary with name, ticker, etc.
            dry_run: If True, don't make changes, just report

        Returns:
            Dict with migration result
        """
        name = stock.get('name', 'Unknown')
        old_ticker = stock.get('ticker', '')
        old_exchange = stock.get('exchange', 'NSE')

        result = {
            'name': name,
            'old_ticker': old_ticker,
            'old_exchange': old_exchange,
            'new_ticker': None,
            'new_exchange': None,
            'status': 'unchanged',
            'reason': None
        }

        # First, validate current symbol
        is_valid, error = validate_yfinance_symbol(old_ticker, old_exchange)

        if is_valid:
            result['status'] = 'valid'
            result['reason'] = 'Current symbol is valid'
            result['new_ticker'] = old_ticker
            result['new_exchange'] = old_exchange
            logger.info(f"  [{name}] Current symbol {old_ticker} is valid, no migration needed")
            return result

        # Symbol is invalid, try to find correct one
        logger.warning(f"  [{name}] Invalid symbol '{old_ticker}', searching for correct symbol...")

        # Try to find in cache first
        found = self.find_symbol_in_cache(name)

        # If not found in cache, try yfinance search
        if not found:
            logger.debug(f"  [{name}] Not found in cache, trying yfinance search...")
            found = self.search_symbol_by_name(name)

        if found:
            new_symbol, new_exchange = found

            # Validate new symbol
            is_valid, error = validate_yfinance_symbol(new_symbol, new_exchange)

            if is_valid:
                result['new_ticker'] = new_symbol
                result['new_exchange'] = new_exchange
                result['status'] = 'migrated'
                result['reason'] = f'Found correct symbol: {new_symbol}'

                if not dry_run:
                    stock['ticker'] = new_symbol
                    stock['exchange'] = new_exchange

                logger.info(f"  [{name}] Migrated: {old_ticker} -> {new_symbol} ({new_exchange})")
            else:
                result['status'] = 'failed'
                result['reason'] = f'Found symbol {new_symbol} but validation failed: {error}'
                logger.error(f"  [{name}] Found symbol {new_symbol} but it's invalid!")
        else:
            result['status'] = 'failed'
            result['reason'] = 'Could not find correct symbol'
            logger.error(f"  [{name}] Could not find correct symbol for '{name}'")

        return result

    def migrate_portfolio(self, portfolio_file: Path, dry_run: bool = False, backup: bool = True) -> Dict:
        """
        Migrate symbols in a portfolio file.

        Args:
            portfolio_file: Path to portfolio JSON file
            dry_run: If True, don't modify file, just report what would change
            backup: If True, create backup before modifying

        Returns:
            Migration report dict
        """
        logger.info(f"[MIGRATION] Processing portfolio: {portfolio_file.name}")
        logger.separator()

        # Load portfolio
        with open(portfolio_file, 'r') as f:
            portfolio_data = json.load(f)

        stocks = portfolio_data.get('portfolio', {}).get('stocks', [])

        if not stocks:
            logger.warning("No stocks found in portfolio")
            return {'status': 'error', 'reason': 'No stocks found'}

        # Migrate each stock
        results = []
        for stock in stocks:
            result = self.migrate_stock_symbol(stock, dry_run=dry_run)
            results.append(result)

        # Generate report
        report = {
            'portfolio_file': str(portfolio_file),
            'total_stocks': len(stocks),
            'valid_count': sum(1 for r in results if r['status'] == 'valid'),
            'migrated_count': sum(1 for r in results if r['status'] == 'migrated'),
            'failed_count': sum(1 for r in results if r['status'] == 'failed'),
            'results': results,
            'dry_run': dry_run
        }

        # Save changes if not dry run
        if not dry_run and report['migrated_count'] > 0:
            # Create backup
            if backup:
                backup_file = portfolio_file.with_suffix('.json.bak')
                shutil.copy2(portfolio_file, backup_file)
                logger.info(f"Backup created: {backup_file}")

            # Save migrated portfolio
            with open(portfolio_file, 'w') as f:
                json.dump(portfolio_data, f, indent=2)

            logger.info(f"Portfolio saved with corrected symbols")

        logger.separator()
        logger.info(f"[MIGRATION COMPLETE]")
        logger.info(f"  Total stocks: {report['total_stocks']}")
        logger.info(f"  Already valid: {report['valid_count']}")
        logger.info(f"  Migrated: {report['migrated_count']}")
        logger.info(f"  Failed: {report['failed_count']}")

        return report

    def migrate_all_portfolios(self, dry_run: bool = False) -> List[Dict]:
        """
        Migrate all portfolio files in the portfolio directory.

        Args:
            dry_run: If True, don't modify files, just report

        Returns:
            List of migration reports
        """
        if not self.portfolio_dir.exists():
            logger.error(f"Portfolio directory not found: {self.portfolio_dir}")
            return []

        portfolio_files = list(self.portfolio_dir.glob("*.json"))
        # Exclude backup files
        portfolio_files = [f for f in portfolio_files if not f.name.endswith('.bak')]

        logger.info(f"Found {len(portfolio_files)} portfolio files to migrate")
        logger.separator()

        reports = []
        for portfolio_file in portfolio_files:
            report = self.migrate_portfolio(portfolio_file, dry_run=dry_run)
            reports.append(report)
            print("\n")  # Add spacing between portfolios

        return reports


def print_summary_report(reports: List[Dict]) -> None:
    """Print summary of all migration reports"""
    print("\n" + "="*70)
    print("MIGRATION SUMMARY")
    print("="*70)

    total_stocks = sum(r['total_stocks'] for r in reports)
    total_valid = sum(r['valid_count'] for r in reports)
    total_migrated = sum(r['migrated_count'] for r in reports)
    total_failed = sum(r['failed_count'] for r in reports)

    print(f"\nPortfolios processed: {len(reports)}")
    print(f"Total stocks:         {total_stocks}")
    print(f"Already valid:        {total_valid}")
    print(f"Successfully migrated: {total_migrated}")
    print(f"Failed migrations:    {total_failed}")

    if total_failed > 0:
        print(f"\nFailed migrations require manual intervention:")
        for report in reports:
            for result in report['results']:
                if result['status'] == 'failed':
                    print(f"  - {result['name']}: {result['reason']}")

    print("\n" + "="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Migrate portfolio symbols to correct NSE/BSE symbols")
    parser.add_argument('--portfolio', type=str, help='Specific portfolio file to migrate (e.g., latest_aggressive.json)')
    parser.add_argument('--all', action='store_true', help='Migrate all portfolio files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup files')

    args = parser.parse_args()

    # Initialize migrator
    migrator = PortfolioSymbolMigrator()

    # Determine what to migrate
    if args.all:
        print("Migrating all portfolio files...")
        if args.dry_run:
            print("[DRY RUN MODE - No files will be modified]\n")

        reports = migrator.migrate_all_portfolios(dry_run=args.dry_run)
        print_summary_report(reports)

    elif args.portfolio:
        portfolio_file = migrator.portfolio_dir / args.portfolio

        if not portfolio_file.exists():
            print(f"Error: Portfolio file not found: {portfolio_file}")
            return 1

        print(f"Migrating portfolio: {args.portfolio}...")
        if args.dry_run:
            print("[DRY RUN MODE - No files will be modified]\n")

        report = migrator.migrate_portfolio(
            portfolio_file,
            dry_run=args.dry_run,
            backup=not args.no_backup
        )

        print_summary_report([report])

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python tools/migrate_portfolio_symbols.py --portfolio latest_aggressive.json")
        print("  python tools/migrate_portfolio_symbols.py --all --dry-run")
        print("  python tools/migrate_portfolio_symbols.py --all")


if __name__ == "__main__":
    main()
