"""
Ensure Latest Portfolio is Always Active

This script ensures that:
1. Only the LATEST portfolio (by created_at) is marked as active
2. All other portfolios are marked as inactive
3. Portfolio manager will always work with the latest portfolio

Usage:
    python scripts/ensure_latest_portfolio_active.py
    python scripts/ensure_latest_portfolio_active.py --dry-run  # Preview changes without applying
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import get_db_service
from utils.logger import get_logger

logger = get_logger("scripts.ensure_latest_active")


def ensure_latest_portfolio_active(dry_run: bool = False):
    """
    Set the latest portfolio as active and deactivate all others

    Args:
        dry_run: If True, only preview changes without applying

    Returns:
        Dict with results
    """
    db = get_db_service()

    # Get all portfolios sorted by created_at (newest first)
    all_portfolios = db.get_all_portfolios()

    if not all_portfolios:
        logger.warning("No portfolios found in database")
        return {'success': False, 'error': 'No portfolios found'}

    # Sort by created_at descending (newest first)
    all_portfolios.sort(key=lambda p: p.get('created_at', ''), reverse=True)

    latest_portfolio = all_portfolios[0]
    older_portfolios = all_portfolios[1:]

    print("\n" + "="*80)
    print("PORTFOLIO ACTIVE STATUS CHECK")
    print("="*80)

    # Show latest portfolio
    print(f"\n📌 LATEST PORTFOLIO (should be active):")
    print(f"   ID: {latest_portfolio['id']}")
    print(f"   Profile: {latest_portfolio.get('profile', 'Unknown')}")
    print(f"   Total Capital: Rs. {latest_portfolio.get('total_capital', 0):,.0f}")
    print(f"   Created: {latest_portfolio.get('created_at', 'Unknown')}")
    print(f"   Currently Active: {latest_portfolio.get('is_active', False)}")

    # Get stocks for latest portfolio
    latest_stocks = db.get_portfolio_stocks(latest_portfolio['id'])
    if latest_stocks:
        tickers = [s.get('ticker', 'Unknown') for s in latest_stocks[:5]]
        print(f"   Stocks ({len(latest_stocks)}): {', '.join(tickers)}")

    # Show older portfolios
    if older_portfolios:
        print(f"\n📋 OLDER PORTFOLIOS (should be inactive):")
        for i, portfolio in enumerate(older_portfolios, 1):
            status = "✅ Already inactive" if not portfolio.get('is_active') else "⚠️  Currently ACTIVE (will deactivate)"
            print(f"\n   {i}. Portfolio ID: {portfolio['id']}")
            print(f"      Profile: {portfolio.get('profile', 'Unknown')}")
            print(f"      Created: {portfolio.get('created_at', 'Unknown')}")
            print(f"      Status: {status}")

    print("\n" + "="*80)

    # Determine actions needed
    actions_needed = []

    if not latest_portfolio.get('is_active'):
        actions_needed.append(f"Activate portfolio {latest_portfolio['id']}")

    for portfolio in older_portfolios:
        if portfolio.get('is_active'):
            actions_needed.append(f"Deactivate portfolio {portfolio['id']}")

    if not actions_needed:
        print("✅ NO CHANGES NEEDED - Latest portfolio is already active, all others inactive")
        print("="*80)
        return {
            'success': True,
            'latest_portfolio_id': latest_portfolio['id'],
            'changes_made': 0
        }

    print("\n🔧 ACTIONS NEEDED:")
    for action in actions_needed:
        print(f"   - {action}")

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be applied")
        print("="*80)
        return {
            'success': True,
            'dry_run': True,
            'actions_planned': len(actions_needed)
        }

    # Apply changes
    print("\n🔄 APPLYING CHANGES...")

    changes_made = 0

    # Activate latest portfolio
    if not latest_portfolio.get('is_active'):
        logger.info(f"Activating portfolio {latest_portfolio['id']}")
        db.client.table('portfolios').update({'is_active': True}).eq('id', latest_portfolio['id']).execute()
        print(f"   ✅ Activated portfolio {latest_portfolio['id']}")
        changes_made += 1

    # Deactivate all older portfolios
    for portfolio in older_portfolios:
        if portfolio.get('is_active'):
            logger.info(f"Deactivating portfolio {portfolio['id']}")
            db.client.table('portfolios').update({'is_active': False}).eq('id', portfolio['id']).execute()
            print(f"   ✅ Deactivated portfolio {portfolio['id']}")
            changes_made += 1

    print(f"\n✅ COMPLETE - {changes_made} changes applied")
    print("="*80)

    return {
        'success': True,
        'latest_portfolio_id': latest_portfolio['id'],
        'changes_made': changes_made
    }


def main():
    parser = argparse.ArgumentParser(
        description="Ensure latest portfolio is always active",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply changes
  python scripts/ensure_latest_portfolio_active.py

  # Preview changes without applying
  python scripts/ensure_latest_portfolio_active.py --dry-run
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying'
    )

    args = parser.parse_args()

    result = ensure_latest_portfolio_active(dry_run=args.dry_run)

    if result['success']:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
