"""
Script to fix active portfolio issues

Usage:
  # Make portfolio ID 42 (with INFY) the active aggressive portfolio
  python scripts/fix_active_portfolio.py --set-active 42 --profile aggressive

  # Just deactivate old aggressive portfolio
  python scripts/fix_active_portfolio.py --deactivate 4
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import get_db_service
from utils.logger import get_logger

logger = get_logger("scripts.fix_active_portfolio")


def set_active_portfolio(portfolio_id: int, profile: str):
    """
    Set a portfolio as active and deactivate others with same profile

    Args:
        portfolio_id: Portfolio ID to activate
        profile: Portfolio profile (aggressive, moderate, defensive)
    """
    db = get_db_service()

    # Get the portfolio to activate
    portfolio = db.get_portfolio_by_id(portfolio_id)
    if not portfolio:
        logger.error(f"Portfolio {portfolio_id} not found")
        return False

    # Get stocks to verify it's a real portfolio
    stocks = db.get_portfolio_stocks(portfolio_id)
    print(f"\nPortfolio ID {portfolio_id}:")
    print(f"  Current Profile: {portfolio.get('profile')}")
    print(f"  Stocks: {len(stocks)}")
    if stocks:
        print(f"  Sample tickers: {', '.join([s.get('ticker', 'Unknown') for s in stocks[:5]])}")

    # Deactivate all other portfolios with the target profile
    logger.info(f"Deactivating all {profile} portfolios...")
    all_portfolios = db.get_all_portfolios()
    for p in all_portfolios:
        if p['profile'] == profile and p['id'] != portfolio_id:
            db.client.table('portfolios').update({'is_active': False}).eq('id', p['id']).execute()
            logger.info(f"  Deactivated portfolio {p['id']}")

    # Update the target portfolio
    logger.info(f"Activating portfolio {portfolio_id} as {profile}...")
    db.client.table('portfolios').update({
        'is_active': True,
        'profile': profile
    }).eq('id', portfolio_id).execute()

    print(f"\n✅ Portfolio {portfolio_id} is now the active {profile} portfolio")
    return True


def deactivate_portfolio(portfolio_id: int):
    """Deactivate a portfolio"""
    db = get_db_service()

    portfolio = db.get_portfolio_by_id(portfolio_id)
    if not portfolio:
        logger.error(f"Portfolio {portfolio_id} not found")
        return False

    db.client.table('portfolios').update({'is_active': False}).eq('id', portfolio_id).execute()

    print(f"\n✅ Portfolio {portfolio_id} ({portfolio.get('profile')}) deactivated")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fix active portfolio issues",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--set-active',
        type=int,
        help='Portfolio ID to set as active'
    )
    parser.add_argument(
        '--profile',
        type=str,
        choices=['aggressive', 'moderate', 'defensive'],
        help='Profile to assign (required with --set-active)'
    )
    parser.add_argument(
        '--deactivate',
        type=int,
        help='Portfolio ID to deactivate'
    )

    args = parser.parse_args()

    if args.set_active:
        if not args.profile:
            print("ERROR: --profile is required with --set-active")
            return 1

        success = set_active_portfolio(args.set_active, args.profile)
        return 0 if success else 1

    elif args.deactivate:
        success = deactivate_portfolio(args.deactivate)
        return 0 if success else 1

    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
