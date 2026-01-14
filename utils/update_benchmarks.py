#!/usr/bin/env python3
"""
Standalone script to update benchmark comparisons
Uses latest index prices to recalculate portfolio vs benchmark performance
"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import get_db_service
from tools.performance_calculator import get_performance_calculator
from utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("utils.update_benchmarks")


def update_benchmarks(portfolio_id: int = None):
    """
    Update benchmark comparisons for portfolio(s)

    Args:
        portfolio_id: Specific portfolio ID (if None, updates all active portfolios)
    """
    logger.info("=" * 80)
    logger.info("BENCHMARK COMPARISON UPDATE")
    logger.info("=" * 80)

    db = get_db_service()
    perf_calculator = get_performance_calculator()

    today = date.today()

    # Determine which portfolios to update
    if portfolio_id:
        portfolio_ids = [portfolio_id]
    else:
        # Get all active portfolios
        portfolios = db.get_all_portfolios()
        portfolio_ids = [p['id'] for p in portfolios if p.get('is_active')]

    if not portfolio_ids:
        logger.error("No active portfolios found")
        return False

    logger.info(f"Updating benchmarks for {len(portfolio_ids)} portfolio(s)")

    success_count = 0

    for pid in portfolio_ids:
        try:
            logger.info(f"\nUpdating portfolio {pid}...")

            # Update benchmark comparisons
            comparisons = perf_calculator.update_benchmark_comparisons(pid, today)

            if comparisons:
                logger.info(f"✓ Updated {len(comparisons)} benchmark comparisons")
                success_count += 1
            else:
                logger.warning(f"⚠ No benchmarks configured for portfolio {pid}")

        except Exception as e:
            logger.error(f"✗ Failed to update portfolio {pid}: {e}")

    logger.info("\n" + "=" * 80)
    logger.info(f"COMPLETE - {success_count}/{len(portfolio_ids)} portfolios updated")
    logger.info("=" * 80)

    return success_count > 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Update benchmark comparisons')
    parser.add_argument(
        '--portfolio-id',
        type=int,
        help='Portfolio ID (optional, defaults to all active portfolios)'
    )

    args = parser.parse_args()

    try:
        success = update_benchmarks(portfolio_id=args.portfolio_id)
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
