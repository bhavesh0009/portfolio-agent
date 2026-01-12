#!/usr/bin/env python3
"""
Standalone script to recalculate benchmark comparisons
Use this instead of running full portfolio manager
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import DatabaseService
from tools.performance_calculator import PerformanceCalculator
from utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("utils.recalculate_benchmarks")


def main():
    portfolio_id = 42  # Change this if needed

    logger.info("=" * 80)
    logger.info("BENCHMARK RECALCULATION SCRIPT")
    logger.info("=" * 80)

    db = DatabaseService()
    calc = PerformanceCalculator()

    # Step 1: Show current benchmark data
    logger.info(f"\nStep 1: Checking current benchmark data for portfolio {portfolio_id}...")
    current_data = db.client.table('benchmark_comparison')\
        .select('index_symbol, period, index_return, portfolio_return, alpha')\
        .eq('portfolio_id', portfolio_id)\
        .eq('period', 'ALL')\
        .execute()

    if current_data.data:
        logger.info(f"Found {len(current_data.data)} existing benchmark records:")
        for record in current_data.data:
            logger.info(
                f"  {record['index_symbol']}: "
                f"Portfolio {record['portfolio_return']:.2f}%, "
                f"Index {record['index_return']:.2f}%, "
                f"Alpha {record['alpha']:.2f}%"
            )
    else:
        logger.info("No existing benchmark data found")

    # Step 2: Delete existing data
    logger.info(f"\nStep 2: Deleting existing benchmark data for portfolio {portfolio_id}...")
    delete_result = db.client.table('benchmark_comparison')\
        .delete()\
        .eq('portfolio_id', portfolio_id)\
        .execute()
    logger.info(f"Deleted {len(delete_result.data) if delete_result.data else 0} records")

    # Step 3: Recalculate benchmarks
    logger.info(f"\nStep 3: Recalculating benchmarks...")
    try:
        results = calc.update_benchmark_comparisons(portfolio_id)

        if results:
            logger.info(f"\n✓ Successfully calculated {len(results)} benchmark comparisons")

            # Show results for ALL period
            logger.info("\nNew Benchmark Results (ALL period):")
            for result in results:
                if result.get('period') == 'ALL':
                    index_return = result.get('index_return')
                    if index_return is None:
                        logger.warning(
                            f"  ⚠️  {result['index_symbol']}: "
                            f"NO DATA - {result.get('error', 'Unknown error')}"
                        )
                    else:
                        logger.info(
                            f"  ✓ {result['index_symbol']}: "
                            f"Portfolio {result['portfolio_return']:.2f}%, "
                            f"Index {index_return:.2f}%, "
                            f"Alpha {result['alpha']:.2f}%"
                        )
        else:
            logger.warning("No benchmarks configured for this portfolio")

    except Exception as e:
        logger.error(f"Failed to recalculate benchmarks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    logger.info("\n" + "=" * 80)
    logger.info("✓ BENCHMARK RECALCULATION COMPLETE")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
