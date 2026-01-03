"""
Symbol Validator - Validate NSE/BSE symbols against Yahoo Finance

This tool validates stock symbols to ensure they work with yfinance for price fetching.
Used during portfolio finalization to catch invalid symbols early.

Author: Portfolio Agent System
Created: 2025-01-09
"""

from typing import Dict, List, Optional, Tuple
import yfinance as yf
from utils.logger import get_logger

logger = get_logger(__name__)


def validate_yfinance_symbol(symbol: str, exchange: str = 'NSE') -> Tuple[bool, Optional[str]]:
    """
    Validate a single symbol against Yahoo Finance API.

    Args:
        symbol: Stock symbol (e.g., "WAAREEENER", "539337")
        exchange: Exchange code ("NSE" or "BSE")

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Examples:
        >>> validate_yfinance_symbol("WAAREEENER", "NSE")
        (True, None)

        >>> validate_yfinance_symbol("INVALIDXYZ", "NSE")
        (False, "Symbol not found on Yahoo Finance")
    """
    # Construct Yahoo Finance symbol
    suffix = '.NS' if exchange == 'NSE' else '.BO'
    yf_symbol = f"{symbol}{suffix}"

    try:
        logger.debug(f"Validating symbol: {yf_symbol}")

        # Try to fetch basic info
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        # Check if we got valid data
        # yfinance returns a dict even for invalid symbols, but it's mostly empty
        if not info or len(info) <= 3:
            # Empty or near-empty response indicates invalid symbol
            return False, f"Symbol {yf_symbol} not found on Yahoo Finance"

        # Check for explicit error fields
        if 'symbol' not in info:
            return False, f"Symbol {yf_symbol} has incomplete data"

        # Try to get a recent price as final validation
        # This catches symbols that exist but have no trading data
        history = ticker.history(period='5d')

        if history.empty:
            return False, f"Symbol {yf_symbol} has no recent trading data (possibly delisted)"

        logger.debug(f"Symbol {yf_symbol} validated successfully")
        return True, None

    except Exception as e:
        error_msg = f"Validation failed for {yf_symbol}: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg


def validate_portfolio_symbols(stocks: List[Dict]) -> Dict:
    """
    Validate symbols for all stocks in a portfolio list.

    Args:
        stocks: List of stock dicts with 'ticker', 'exchange', and 'name' fields

    Returns:
        Validation report dict with:
        - total: Total stocks checked
        - valid: Number of valid symbols
        - invalid: Number of invalid symbols
        - success_rate: Percentage of valid symbols
        - failures: List of failed stocks with details
        - warnings: List of warnings for manual review

    Example:
        >>> stocks = [
        ...     {"name": "Waaree Energies", "ticker": "WAAREEENER", "exchange": "NSE"},
        ...     {"name": "Invalid Stock", "ticker": "BADSTOCK", "exchange": "NSE"}
        ... ]
        >>> report = validate_portfolio_symbols(stocks)
        >>> print(f"Valid: {report['valid']}/{report['total']}")
        Valid: 1/2
    """
    logger.info(f"[SYMBOL VALIDATION] Validating {len(stocks)} stock symbols against Yahoo Finance")
    logger.info("[NOTE] Symbols should have been auto-corrected from screening data if needed")
    logger.separator()

    report = {
        'total': len(stocks),
        'valid': 0,
        'invalid': 0,
        'success_rate': 0.0,
        'failures': [],
        'warnings': []
    }

    for stock in stocks:
        name = stock.get('name', 'Unknown')
        ticker = stock.get('ticker', '').strip()
        exchange = stock.get('exchange', 'NSE').strip()

        # Check for missing fields
        if not ticker or ticker == 'Unknown':
            report['invalid'] += 1
            report['failures'].append({
                'name': name,
                'ticker': ticker or 'MISSING',
                'exchange': exchange,
                'error': 'Missing or unknown ticker symbol'
            })
            logger.warning(f"  [{name}] Missing ticker symbol")
            continue

        if not exchange or exchange == 'Unknown':
            report['warnings'].append({
                'name': name,
                'ticker': ticker,
                'exchange': exchange or 'MISSING',
                'warning': 'Missing exchange, assuming NSE'
            })
            exchange = 'NSE'  # Default to NSE

        # Validate symbol
        is_valid, error_msg = validate_yfinance_symbol(ticker, exchange)

        if is_valid:
            report['valid'] += 1
            logger.info(f"  [{name}] {ticker}.{exchange[:2]} - Valid")
        else:
            report['invalid'] += 1
            report['failures'].append({
                'name': name,
                'ticker': ticker,
                'exchange': exchange,
                'error': error_msg
            })
            logger.warning(f"  [{name}] {ticker}.{exchange[:2]} - INVALID: {error_msg}")

    # Calculate success rate
    if report['total'] > 0:
        report['success_rate'] = (report['valid'] / report['total']) * 100

    logger.separator()
    logger.info(f"[VALIDATION COMPLETE] {report['valid']}/{report['total']} symbols valid ({report['success_rate']:.1f}%)")

    if report['invalid'] > 0:
        logger.warning(f"[VALIDATION WARNINGS] {report['invalid']} invalid symbols found!")
        logger.warning("Portfolio will use fallback prices (entry price) for invalid symbols")
        logger.warning("Consider reviewing these stocks manually")

    return report


def print_validation_report(report: Dict) -> None:
    """
    Pretty-print a validation report to console.

    Args:
        report: Validation report from validate_portfolio_symbols()
    """
    print("\n" + "="*60)
    print("SYMBOL VALIDATION REPORT")
    print("="*60)

    print(f"\nTotal Stocks:    {report['total']}")
    print(f"Valid Symbols:   {report['valid']} ({report['success_rate']:.1f}%)")
    print(f"Invalid Symbols: {report['invalid']}")

    if report['failures']:
        print(f"\nFAILED VALIDATIONS ({len(report['failures'])}):")
        print("-" * 60)
        for i, failure in enumerate(report['failures'], 1):
            print(f"{i}. {failure['name']}")
            print(f"   Ticker: {failure['ticker']} | Exchange: {failure['exchange']}")
            print(f"   Error:  {failure['error']}")

    if report['warnings']:
        print(f"\nWARNINGS ({len(report['warnings'])}):")
        print("-" * 60)
        for i, warning in enumerate(report['warnings'], 1):
            print(f"{i}. {warning['name']}")
            print(f"   Ticker: {warning['ticker']} | Exchange: {warning['exchange']}")
            print(f"   Warning: {warning['warning']}")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    # Example usage and testing
    print("Symbol Validator - Test Mode\n")

    # Test individual symbols
    print("Testing individual symbols:")
    test_symbols = [
        ("WAAREEENER", "NSE"),  # Should be valid
        ("RELIANCE", "NSE"),     # Should be valid
        ("WAREE", "NSE"),        # Should be INVALID (wrong symbol)
        ("INVALIDXYZ", "NSE"),   # Should be INVALID
    ]

    for symbol, exchange in test_symbols:
        is_valid, error = validate_yfinance_symbol(symbol, exchange)
        status = "VALID" if is_valid else f"INVALID ({error})"
        print(f"  {symbol}.{exchange[:2]}: {status}")

    print("\n" + "-"*60 + "\n")

    # Test portfolio validation
    print("Testing portfolio validation:")
    test_portfolio = [
        {"name": "Waaree Energies", "ticker": "WAAREEENER", "exchange": "NSE"},
        {"name": "Reliance Industries", "ticker": "RELIANCE", "exchange": "NSE"},
        {"name": "Wrong Symbol", "ticker": "WAREE", "exchange": "NSE"},
        {"name": "Missing Ticker", "ticker": "", "exchange": "NSE"},
    ]

    report = validate_portfolio_symbols(test_portfolio)
    print_validation_report(report)
