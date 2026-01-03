"""
Auto-activate Latest Portfolio Hook

This script is designed to be called automatically after portfolio builder
to ensure the newly created portfolio becomes active.

Can also be run manually or via cron to ensure latest portfolio is always active.

Usage:
    # Run manually
    python scripts/auto_activate_latest.py

    # Run as post-build hook (add to portfolio builder)
    from scripts.auto_activate_latest import activate_latest_portfolio
    activate_latest_portfolio()
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import get_db_service
from utils.logger import get_logger

logger = get_logger("scripts.auto_activate_latest")


def activate_latest_portfolio(silent: bool = False) -> bool:
    """
    Automatically activate the latest portfolio and deactivate all others

    Args:
        silent: If True, suppress console output

    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_db_service()

        # Get all portfolios
        all_portfolios = db.get_all_portfolios()

        if not all_portfolios:
            logger.warning("No portfolios found")
            return False

        # Sort by created_at descending (newest first)
        all_portfolios.sort(key=lambda p: p.get('created_at', ''), reverse=True)

        latest_portfolio = all_portfolios[0]
        latest_id = latest_portfolio['id']

        # Check if already active
        if latest_portfolio.get('is_active'):
            if not silent:
                logger.info(f"Latest portfolio (ID {latest_id}) is already active")
            return True

        # Activate latest
        db.client.table('portfolios').update({'is_active': True}).eq('id', latest_id).execute()
        logger.info(f"✅ Activated latest portfolio (ID {latest_id})")

        # Deactivate all others
        deactivated_count = 0
        for portfolio in all_portfolios[1:]:
            if portfolio.get('is_active'):
                db.client.table('portfolios').update({'is_active': False}).eq('id', portfolio['id']).execute()
                deactivated_count += 1

        if deactivated_count > 0:
            logger.info(f"✅ Deactivated {deactivated_count} older portfolio(s)")

        if not silent:
            print(f"\n✅ Portfolio ID {latest_id} is now active")

        return True

    except Exception as e:
        logger.error(f"Failed to activate latest portfolio: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = activate_latest_portfolio()
    sys.exit(0 if success else 1)
