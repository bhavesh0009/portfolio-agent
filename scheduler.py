"""
Daily Portfolio Update Scheduler
Runs automated price updates and portfolio calculations
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import get_logger
from utils.db_service import get_db_service
from tools.price_fetcher import get_price_fetcher
from tools.performance_calculator import get_performance_calculator

logger = get_logger("scheduler")

# Services
db = get_db_service()
price_fetcher = get_price_fetcher()
perf_calculator = get_performance_calculator()

# Portfolio Manager (optional import)
try:
    from agents.portfolio_manager_agent import run_portfolio_manager
    PORTFOLIO_MANAGER_AVAILABLE = True
except ImportError:
    PORTFOLIO_MANAGER_AVAILABLE = False
    logger.warning("Portfolio Manager Agent not available")


def daily_price_update():
    """
    Daily task: Update stock prices and indices
    Runs after market close (3:45 PM IST)
    """
    logger.info("=" * 80)
    logger.info("Starting daily price update...")
    logger.info("=" * 80)

    try:
        today = date.today()

        # Get all active portfolios
        portfolios = db.execute_query(
            "SELECT id, profile FROM portfolios WHERE is_active = 1"
        )

        if not portfolios:
            logger.warning("No active portfolios found")
            return

        logger.info(f"Found {len(portfolios)} active portfolio(s)")

        for portfolio in portfolios:
            portfolio_id = portfolio['id']
            logger.info(f"Processing portfolio {portfolio_id} ({portfolio['profile']})")

            # 1. Update stock prices
            logger.info("  Updating stock prices...")
            stock_result = price_fetcher.update_portfolio_prices(portfolio_id, today)
            logger.info(f"  Stock prices: {stock_result['success']}/{stock_result['total']} updated")

            # 2. Update index prices
            logger.info("  Updating index prices...")
            index_result = price_fetcher.update_index_prices(price_date=today)
            logger.info(f"  Index prices: {index_result['success']}/{index_result['total']} updated")

            # 3. Generate portfolio snapshot
            logger.info("  Generating portfolio snapshot...")
            snapshot = perf_calculator.generate_portfolio_snapshot(portfolio_id, today)
            if snapshot:
                logger.info(f"  Snapshot created: Value = Rs. {snapshot['total_value']:,.2f}")
                logger.info(f"  P&L: {snapshot['total_return_pct']:.2f}%")
                logger.info(f"  Sharpe Ratio: {snapshot['sharpe_ratio']:.2f}")
            else:
                logger.error("  Failed to generate snapshot")

            # 4. Update benchmark comparisons
            logger.info("  Updating benchmark comparisons...")
            comparisons = perf_calculator.update_benchmark_comparisons(portfolio_id, today)
            logger.info(f"  Updated {len(comparisons)} benchmark comparisons")

            logger.info(f"Portfolio {portfolio_id} update complete")

        logger.info("=" * 80)
        logger.info("Daily price update completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Daily price update failed: {e}", exc_info=True)


def daily_portfolio_manager():
    """
    Daily task: Run Portfolio Manager Agent
    Analyzes portfolio and generates recommendations
    Runs after price updates (4:00 PM IST)
    """
    if not PORTFOLIO_MANAGER_AVAILABLE:
        logger.warning("Portfolio Manager Agent not available, skipping")
        return

    logger.info("=" * 80)
    logger.info("Starting Portfolio Manager analysis...")
    logger.info("=" * 80)

    try:
        # Get all active portfolios
        portfolios = db.execute_query(
            "SELECT id, profile FROM portfolios WHERE is_active = 1"
        )

        if not portfolios:
            logger.warning("No active portfolios found")
            return

        for portfolio in portfolios:
            profile = portfolio['profile']
            logger.info(f"Running Portfolio Manager for {profile} portfolio...")

            try:
                result = run_portfolio_manager(profile=profile)

                if result['success']:
                    rec = result['recommendation']
                    logger.info(f"Portfolio Manager complete for {profile}")
                    logger.info(f"  Recommendation: {rec.get('recommendation', 'UNKNOWN')}")
                    logger.info(f"  Confidence: {rec.get('confidence_level', 0)}%")
                    logger.info(f"  Priority: {result['priority']}")
                else:
                    logger.error(f"Portfolio Manager failed for {profile}: {result.get('error')}")

            except Exception as e:
                logger.error(f"Portfolio Manager error for {profile}: {e}", exc_info=True)

        logger.info("=" * 80)
        logger.info("Portfolio Manager analysis completed!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Portfolio Manager task failed: {e}", exc_info=True)


def weekly_cache_cleanup():
    """
    Weekly task: Clean up old data
    Runs Sunday at midnight
    """
    logger.info("Running weekly cache cleanup...")

    try:
        # Clear in-memory caches
        price_fetcher.clear_cache()

        # Could add: Delete old snapshots, compress historical data, etc.

        logger.info("Cache cleanup complete")

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")


def start_scheduler(test_mode: bool = False):
    """
    Start the background scheduler

    Args:
        test_mode: If True, runs tasks immediately for testing
    """
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')

    if test_mode:
        logger.info("Running in TEST MODE - executing tasks immediately")

        # Run once immediately
        daily_price_update()

        # Run portfolio manager if available
        if PORTFOLIO_MANAGER_AVAILABLE:
            logger.info("\nRunning Portfolio Manager...")
            daily_portfolio_manager()

    else:
        # Daily price update at 3:45 PM IST (after market close)
        scheduler.add_job(
            daily_price_update,
            trigger=CronTrigger(hour=15, minute=45, timezone='Asia/Kolkata'),
            id='daily_price_update',
            name='Daily Price Update',
            replace_existing=True
        )

        # Daily portfolio manager at 4:00 PM IST (after prices update)
        if PORTFOLIO_MANAGER_AVAILABLE:
            scheduler.add_job(
                daily_portfolio_manager,
                trigger=CronTrigger(hour=16, minute=0, timezone='Asia/Kolkata'),
                id='daily_portfolio_manager',
                name='Daily Portfolio Manager',
                replace_existing=True
            )

        # Weekly cleanup on Sunday at midnight
        scheduler.add_job(
            weekly_cache_cleanup,
            trigger=CronTrigger(day_of_week='sun', hour=0, minute=0, timezone='Asia/Kolkata'),
            id='weekly_cleanup',
            name='Weekly Cache Cleanup',
            replace_existing=True
        )

        scheduler.start()
        logger.info("Scheduler started successfully")
        logger.info("Scheduled jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  - {job.name} (ID: {job.id}): {job.trigger}")

    return scheduler


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Portfolio Update Scheduler')
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (execute tasks immediately)'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as background daemon'
    )

    args = parser.parse_args()

    if args.test:
        # Test mode: Run tasks once and exit
        logger.info("Starting scheduler in TEST mode...")
        start_scheduler(test_mode=True)
        logger.info("Test run complete")

    elif args.daemon:
        # Daemon mode: Run continuously
        logger.info("Starting scheduler as daemon...")
        scheduler = start_scheduler(test_mode=False)

        try:
            # Keep the script running
            import time
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler stopped")

    else:
        print("Usage:")
        print("  python scheduler.py --test      # Run tasks once for testing")
        print("  python scheduler.py --daemon    # Run as background service")
        print("\nScheduled tasks:")
        print("  - Daily Price Update: 3:45 PM IST (Mon-Fri)")
        print("  - Daily Portfolio Manager: 4:00 PM IST (Mon-Fri)")
        print("  - Weekly Cleanup: Sunday 12:00 AM IST")
