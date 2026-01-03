"""
Portfolio Optimizer Tool
Converts AI-generated allocation percentages to whole share quantities
"""

from math import floor
from typing import List, Dict, Any, Tuple
from utils.logger import get_logger

logger = get_logger("tools.portfolio_optimizer")


def convert_to_whole_shares(
    stocks: List[Dict[str, Any]],
    total_capital: float
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Convert allocation amounts to whole share quantities

    Algorithm:
    1. Calculate shares = floor(allocation_amount / entry_price)
    2. Identify stocks with 0 shares (allocation < price)
    3. Remove 0-share stocks, redistribute their allocation proportionally
    4. Recalculate shares for remaining stocks
    5. Calculate cash_remainder = capital - sum(shares * price)

    Args:
        stocks: List of stock dictionaries with allocation_amount and entry_price
        total_capital: Total portfolio capital

    Returns:
        Tuple of (optimized_stocks, cash_balance)

    Example:
        >>> stocks = [
        ...     {'name': 'A', 'entry_price': 100.0, 'allocation_amount': 250000.0},
        ...     {'name': 'B', 'entry_price': 200.0, 'allocation_amount': 250000.0}
        ... ]
        >>> optimized, cash = convert_to_whole_shares(stocks, 500000.0)
        >>> optimized[0]['shares']
        2500
        >>> cash
        0.0
    """

    if not stocks:
        logger.warning("No stocks provided for optimization")
        return [], total_capital

    # Step 1: Calculate initial shares
    for stock in stocks:
        shares = floor(stock['allocation_amount'] / stock['entry_price'])
        stock['shares'] = shares
        logger.trace(f"{stock.get('name', 'Unknown')}: {shares} shares @ Rs. {stock['entry_price']:.2f}")

    # Step 2: Identify zero-share stocks
    zero_share_stocks = [s for s in stocks if s['shares'] == 0]
    valid_stocks = [s for s in stocks if s['shares'] > 0]

    # Step 3: Redistribute if needed (iterative to handle cascading removals)
    max_iterations = 5  # Prevent infinite loops
    iteration = 0

    while zero_share_stocks and valid_stocks and iteration < max_iterations:
        iteration += 1
        logger.warning(f"Iteration {iteration}: Removing {len(zero_share_stocks)} stock(s) with insufficient allocation")

        for stock in zero_share_stocks:
            logger.warning(f"  - {stock.get('name', 'Unknown')} ({stock.get('ticker', 'N/A')}): Rs. {stock['allocation_amount']:,.0f} < Rs. {stock['entry_price']:.2f}")

        total_to_redistribute = sum(s['allocation_amount'] for s in zero_share_stocks)
        total_valid_allocation = sum(s['allocation_amount'] for s in valid_stocks)

        if total_valid_allocation == 0:
            logger.error("All stocks have zero allocation - cannot redistribute")
            return [], total_capital

        # Redistribute proportionally
        for stock in valid_stocks:
            proportion = stock['allocation_amount'] / total_valid_allocation
            stock['allocation_amount'] += total_to_redistribute * proportion
            stock['shares'] = floor(stock['allocation_amount'] / stock['entry_price'])

        # Check for new zero-share stocks after redistribution
        zero_share_stocks = [s for s in valid_stocks if s['shares'] == 0]
        valid_stocks = [s for s in valid_stocks if s['shares'] > 0]

    if iteration >= max_iterations:
        logger.error(f"Maximum iterations ({max_iterations}) reached during redistribution")

    # Step 4: Calculate actual values
    total_actual_value = 0
    for stock in valid_stocks:
        actual_value = stock['shares'] * stock['entry_price']
        stock['allocation_amount'] = actual_value
        total_actual_value += actual_value
        logger.debug(f"{stock.get('name', 'Unknown')}: {stock['shares']} shares × Rs. {stock['entry_price']:.2f} = Rs. {actual_value:,.2f}")

    cash_balance = total_capital - total_actual_value

    # Step 5: Recalculate percentages
    for stock in valid_stocks:
        stock['allocation_pct'] = (stock['allocation_amount'] / total_capital) * 100

    logger.info(f"Optimization complete: {len(valid_stocks)} stocks, Rs. {cash_balance:,.2f} cash balance")

    return valid_stocks, cash_balance


def validate_portfolio(
    stocks: List[Dict[str, Any]],
    total_capital: float,
    cash_balance: float
) -> Dict[str, Any]:
    """
    Validate share-based portfolio integrity

    Checks:
    - Capital conservation: sum(shares * price) + cash = capital
    - All shares are positive integers
    - Cash balance warnings

    Args:
        stocks: List of stock dictionaries with shares and entry_price
        total_capital: Total portfolio capital
        cash_balance: Unallocated cash

    Returns:
        Validation report with status, warnings, and errors

    Example:
        >>> stocks = [{'name': 'A', 'shares': 100, 'entry_price': 1000.0}]
        >>> report = validate_portfolio(stocks, 100500.0, 500.0)
        >>> report['status']
        'valid'
    """

    validation_report = {
        'status': 'valid',
        'warnings': [],
        'errors': []
    }

    # Check 1: Capital conservation
    total_invested = sum(s['shares'] * s['entry_price'] for s in stocks)
    total_accounted = total_invested + cash_balance

    capital_diff = abs(total_accounted - total_capital)
    if capital_diff > 0.01:
        validation_report['errors'].append({
            'check': 'capital_conservation',
            'message': f'Capital mismatch: expected Rs. {total_capital:,.2f}, got Rs. {total_accounted:,.2f}',
            'expected': total_capital,
            'actual': total_accounted,
            'difference': capital_diff
        })
        validation_report['status'] = 'error'
        logger.error(f"Capital conservation failed: diff Rs. {capital_diff:.2f}")

    # Check 2: All shares positive integers
    for stock in stocks:
        if stock['shares'] <= 0:
            validation_report['errors'].append({
                'check': 'shares_positive',
                'message': f"{stock.get('name', 'Unknown')} has invalid share count: {stock['shares']}",
                'stock': stock.get('name', 'Unknown'),
                'shares': stock['shares']
            })
            validation_report['status'] = 'error'
            logger.error(f"Invalid shares for {stock.get('name', 'Unknown')}: {stock['shares']}")

        # Check if shares is actually an integer
        if not isinstance(stock['shares'], int) and stock['shares'] != int(stock['shares']):
            validation_report['errors'].append({
                'check': 'shares_integer',
                'message': f"{stock.get('name', 'Unknown')} has fractional shares: {stock['shares']}",
                'stock': stock.get('name', 'Unknown'),
                'shares': stock['shares']
            })
            validation_report['status'] = 'error'
            logger.error(f"Fractional shares for {stock.get('name', 'Unknown')}: {stock['shares']}")

    # Check 3: High cash balance warning
    cash_pct = (cash_balance / total_capital) * 100 if total_capital > 0 else 0
    if cash_pct > 10:
        validation_report['warnings'].append({
            'check': 'high_cash_balance',
            'message': f'Cash balance is {cash_pct:.1f}% of capital (Rs. {cash_balance:,.2f})',
            'cash_pct': cash_pct,
            'cash_balance': cash_balance
        })
        if validation_report['status'] == 'valid':
            validation_report['status'] = 'warning'
        logger.warning(f"High cash balance: {cash_pct:.1f}% (Rs. {cash_balance:,.2f})")

    # Check 4: Very low cash balance warning (might indicate rounding issues)
    if cash_balance < 0:
        validation_report['errors'].append({
            'check': 'negative_cash_balance',
            'message': f'Negative cash balance: Rs. {cash_balance:,.2f}',
            'cash_balance': cash_balance
        })
        validation_report['status'] = 'error'
        logger.error(f"Negative cash balance: Rs. {cash_balance:,.2f}")

    return validation_report


def adjust_allocation_to_match_shares(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recalculate allocation_amount and allocation_pct from shares

    Useful when shares are manually adjusted or loaded from database.

    Args:
        stocks: List of stock dictionaries with shares and entry_price

    Returns:
        Same stocks list with updated allocation_amount and allocation_pct
    """

    total_value = sum(s['shares'] * s['entry_price'] for s in stocks)

    for stock in stocks:
        stock['allocation_amount'] = stock['shares'] * stock['entry_price']
        stock['allocation_pct'] = (stock['allocation_amount'] / total_value * 100) if total_value > 0 else 0

    logger.debug(f"Adjusted allocations for {len(stocks)} stocks, total value: Rs. {total_value:,.2f}")

    return stocks


if __name__ == '__main__':
    # Example usage and testing
    import json

    print("Portfolio Optimizer - Example Usage")
    print("=" * 60)

    # Example 1: Clean conversion
    print("\nExample 1: Clean conversion (no removals)")
    stocks1 = [
        {'name': 'Stock A', 'ticker': 'A', 'entry_price': 100.0, 'allocation_amount': 250000.0, 'allocation_pct': 50.0},
        {'name': 'Stock B', 'ticker': 'B', 'entry_price': 200.0, 'allocation_amount': 250000.0, 'allocation_pct': 50.0}
    ]
    optimized1, cash1 = convert_to_whole_shares(stocks1, 500000.0)
    print(json.dumps({
        'stocks': len(optimized1),
        'cash': cash1,
        'shares': [{'name': s['name'], 'shares': s['shares'], 'value': s['allocation_amount']} for s in optimized1]
    }, indent=2))

    # Example 2: With removal
    print("\nExample 2: Stock removal (insufficient allocation)")
    stocks2 = [
        {'name': 'Stock A', 'ticker': 'A', 'entry_price': 100.0, 'allocation_amount': 300000.0, 'allocation_pct': 60.0},
        {'name': 'Stock B (expensive)', 'ticker': 'B', 'entry_price': 50000.0, 'allocation_amount': 200000.0, 'allocation_pct': 40.0}
    ]
    optimized2, cash2 = convert_to_whole_shares(stocks2, 500000.0)
    print(json.dumps({
        'stocks': len(optimized2),
        'cash': cash2,
        'removed': len(stocks2) - len(optimized2),
        'shares': [{'name': s['name'], 'shares': s['shares'], 'value': s['allocation_amount']} for s in optimized2]
    }, indent=2))

    # Example 3: Validation
    print("\nExample 3: Portfolio validation")
    validation = validate_portfolio(optimized1, 500000.0, cash1)
    print(json.dumps(validation, indent=2))
