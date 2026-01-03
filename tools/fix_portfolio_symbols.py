"""
Fix Portfolio Symbols - Migrate incorrect symbols in database to correct Yahoo Finance symbols
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import get_db_service
from tools.price_fetcher import get_price_fetcher
from utils.logger import get_logger

logger = get_logger("tools.fix_portfolio_symbols")


# Known symbol corrections from user feedback
KNOWN_CORRECTIONS = {
    '544291': ('RAJESH', 'BSE'),           # Rajesh Power
    'ORIANA': ('ORIANA-SM', 'NSE'),        # Oriana Power - SME
    '543709': ('GARGI', 'BSE'),            # PNGS Gargi
    'APS': ('APS-SM', 'NSE'),              # Australian Premium Solar - SME
    '543787': ('ROBU', 'BSE'),             # Macfos
}


def fix_portfolio_symbols(portfolio_id: int, dry_run: bool = True) -> dict:
    """
    Fix incorrect symbols in portfolio by validating against Yahoo Finance

    Args:
        portfolio_id: Portfolio to fix
        dry_run: If True, only report changes without updating database

    Returns:
        Dict with correction statistics
    """
    db = get_db_service()
    fetcher = get_price_fetcher()

    # Get all stocks in portfolio
    stocks = db.get_portfolio_stocks(portfolio_id)

    corrections = []
    failed_validations = []
    already_valid = []

    logger.info(f"Validating {len(stocks)} stocks in portfolio {portfolio_id}")

    for stock in stocks:
        ticker = stock['ticker']
        exchange = stock.get('exchange', 'NSE')
        stock_id = stock['id']
        name = stock['name']

        # Try to fetch current price with existing ticker
        price = fetcher.get_current_price(ticker, exchange, use_cache=False)

        if price is not None:
            # Symbol is valid
            already_valid.append({'ticker': ticker, 'name': name, 'price': price})
            logger.debug(f"✓ {ticker} ({name}) is valid: Rs. {price:.2f}")
            continue

        # Symbol failed - try to find correction
        logger.warning(f"✗ {ticker} ({name}) failed validation")

        # Check known corrections first
        if ticker in KNOWN_CORRECTIONS:
            corrected_ticker, corrected_exchange = KNOWN_CORRECTIONS[ticker]
            logger.info(f"Using known correction: {ticker} → {corrected_ticker} ({corrected_exchange})")
        else:
            # Try Yahoo search fallback
            logger.info(f"Searching Yahoo for: {name}")
            yf_symbol = fetcher._search_yahoo_symbol(name)

            if yf_symbol:
                corrected_ticker = yf_symbol.replace('.NS', '').replace('.BO', '')
                corrected_exchange = 'NSE' if '.NS' in yf_symbol else 'BSE'
                logger.info(f"Yahoo search found: {name} → {corrected_ticker}")
            else:
                failed_validations.append({
                    'ticker': ticker,
                    'name': name,
                    'stock_id': stock_id
                })
                logger.error(f"No correction found for {ticker} ({name})")
                continue

        # Validate corrected symbol
        corrected_price = fetcher.get_current_price(corrected_ticker, corrected_exchange, use_cache=False)

        if corrected_price is not None:
            corrections.append({
                'stock_id': stock_id,
                'name': name,
                'old_ticker': ticker,
                'old_exchange': exchange,
                'new_ticker': corrected_ticker,
                'new_exchange': corrected_exchange,
                'price': corrected_price
            })

            logger.info(f"✓ Correction validated: {ticker} → {corrected_ticker} = Rs. {corrected_price:.2f}")

            if not dry_run:
                # Update database
                db.update_stock_ticker(stock_id, corrected_ticker, corrected_exchange)
                logger.info(f"Database updated: stock_id={stock_id}")
        else:
            failed_validations.append({
                'ticker': ticker,
                'name': name,
                'stock_id': stock_id,
                'attempted_correction': corrected_ticker
            })
            logger.error(f"Correction failed validation: {corrected_ticker}")

    # Summary
    summary = {
        'total': len(stocks),
        'already_valid': len(already_valid),
        'corrections': len(corrections),
        'failed': len(failed_validations),
        'dry_run': dry_run,
        'correction_details': corrections,
        'valid_stocks': already_valid,
        'failed_stocks': failed_validations
    }

    logger.info("\n" + "="*60)
    logger.info("SYMBOL VALIDATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total stocks: {summary['total']}")
    logger.info(f"Already valid: {summary['already_valid']}")
    logger.info(f"Corrections needed: {summary['corrections']}")
    logger.info(f"Failed to fix: {summary['failed']}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")

    if corrections:
        logger.info("\nCORRECTIONS:")
        for c in corrections:
            logger.info(f"  {c['name']}: {c['old_ticker']} → {c['new_ticker']} (Rs. {c['price']:.2f})")

    if failed_validations:
        logger.warning("\nFAILED VALIDATIONS:")
        for f in failed_validations:
            logger.warning(f"  {f['name']} ({f['ticker']})")

    return summary


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fix portfolio symbols')
    parser.add_argument('--portfolio-id', type=int, default=4, help='Portfolio ID to fix')
    parser.add_argument('--live', action='store_true', help='Actually update database (default is dry-run)')

    args = parser.parse_args()

    dry_run = not args.live

    print(f"\n{'='*60}")
    print(f"FIXING PORTFOLIO {args.portfolio_id} SYMBOLS")
    print(f"Mode: {'LIVE UPDATE' if not dry_run else 'DRY RUN (no changes)'}")
    print(f"{'='*60}\n")

    result = fix_portfolio_symbols(args.portfolio_id, dry_run=dry_run)

    if dry_run and result['corrections']:
        print(f"\n⚠️  This was a dry run. To apply changes, run with --live flag:")
        print(f"   python tools/fix_portfolio_symbols.py --portfolio-id {args.portfolio_id} --live")
