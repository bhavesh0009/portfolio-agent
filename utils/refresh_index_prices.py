#!/usr/bin/env python3
"""
Standalone script to refresh index prices
Fetches latest prices for all benchmark indices and stores in database
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import DatabaseService
from tools.price_fetcher import PriceFetcher, INDIAN_INDICES
from utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("utils.refresh_index_prices")

# Benchmark indices to update
BENCHMARK_INDICES = [
    '^NSEI',                    # Nifty 50
    '^BSESN',                   # Sensex
    'NIFTY_MIDCAP_100.NS',      # Nifty Midcap 100
    '^NSEMDCP50',               # Nifty Midcap 50
    'NIFTYSMLCAP250.NS',        # Nifty Smallcap 250
    'NIFTYIT.NS',               # Nifty IT
]


def refresh_index_prices(days_back: int = 7):
    """
    Refresh index prices for last N days

    Args:
        days_back: Number of days to fetch (default 7 to cover weekends)
    """
    logger.info("=" * 80)
    logger.info("INDEX PRICES REFRESH SCRIPT")
    logger.info("=" * 80)

    db = DatabaseService()
    fetcher = PriceFetcher()

    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    logger.info(f"\nFetching index prices from {start_date} to {end_date}")
    logger.info(f"Indices: {len(BENCHMARK_INDICES)}")

    results = {
        'success': [],
        'failed': [],
        'no_data': []
    }

    for index_symbol in BENCHMARK_INDICES:
        index_name = INDIAN_INDICES.get(index_symbol, index_symbol)
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing: {index_symbol} ({index_name})")
        logger.info(f"{'=' * 60}")

        try:
            # Fetch historical data from Yahoo Finance
            hist_data = fetcher.get_index_history(
                index_symbol,
                start=start_date,
                end=end_date + timedelta(days=1)  # Include end date
            )

            if not hist_data or not hist_data.get('dates'):
                logger.warning(f"No data returned for {index_symbol}")
                results['no_data'].append(index_symbol)
                continue

            if len(hist_data['dates']) == 0:
                logger.warning(f"Empty data returned for {index_symbol}")
                results['no_data'].append(index_symbol)
                continue

            # Store each day's data
            stored_count = 0
            for i, price_date in enumerate(hist_data['dates']):
                # Convert pandas Timestamp to date
                if hasattr(price_date, 'date'):
                    price_date = price_date.date()

                try:
                    db.store_index_price(
                        index_symbol=index_symbol,
                        index_name=index_name,
                        price_date=price_date,
                        open_price=float(hist_data['open'][i]),
                        high_price=float(hist_data['high'][i]),
                        low_price=float(hist_data['low'][i]),
                        close_price=float(hist_data['close'][i]),
                        volume=int(hist_data['volume'][i]) if hist_data['volume'][i] else None
                    )
                    stored_count += 1
                    logger.debug(f"  Stored {price_date}: close={hist_data['close'][i]:.2f}")
                except Exception as e:
                    logger.debug(f"  Skip {price_date}: {e} (likely duplicate)")

            logger.info(f"✓ Stored {stored_count} days of data for {index_symbol}")
            results['success'].append({
                'symbol': index_symbol,
                'name': index_name,
                'days': stored_count
            })

        except Exception as e:
            logger.error(f"✗ Failed to fetch {index_symbol}: {e}")
            results['failed'].append({
                'symbol': index_symbol,
                'name': index_name,
                'error': str(e)
            })

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("REFRESH SUMMARY")
    logger.info("=" * 80)

    if results['success']:
        logger.info(f"\n✓ Successfully updated {len(results['success'])} indices:")
        for item in results['success']:
            logger.info(f"  • {item['symbol']}: {item['days']} days")

    if results['no_data']:
        logger.warning(f"\n⚠ No data available for {len(results['no_data'])} indices:")
        for symbol in results['no_data']:
            logger.warning(f"  • {symbol}")

    if results['failed']:
        logger.error(f"\n✗ Failed to update {len(results['failed'])} indices:")
        for item in results['failed']:
            logger.error(f"  • {item['symbol']}: {item['error']}")

    logger.info("\n" + "=" * 80)
    logger.info("✓ INDEX PRICES REFRESH COMPLETE")
    logger.info("=" * 80)

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Refresh index prices from Yahoo Finance')
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to fetch (default: 7)'
    )

    args = parser.parse_args()

    try:
        results = refresh_index_prices(days_back=args.days)

        # Exit with error if all failed
        if results['failed'] and not results['success']:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
