"""
Performance Calculator - Portfolio Metrics
Calculates portfolio performance, risk metrics, and benchmark comparisons
"""

import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.db_service import get_db_service
from tools.price_fetcher import get_price_fetcher

logger = get_logger("tools.performance_calculator")

# Constants
RISK_FREE_RATE = 6.5  # Indian government bond rate (~6.5% as of 2025)
TRADING_DAYS_PER_YEAR = 252


class PerformanceCalculator:
    """Calculate portfolio performance and risk metrics"""

    def __init__(self):
        self.db = get_db_service()
        self.price_fetcher = get_price_fetcher()

    def calculate_current_value(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Calculate current portfolio value using latest prices

        Returns:
            Dict with total_value, stock_details, and summary
        """
        logger.info(f"Calculating current value for portfolio {portfolio_id}")

        portfolio = self.db.get_portfolio_by_id(portfolio_id)
        stocks = self.db.get_portfolio_stocks(portfolio_id)

        if not portfolio or not stocks:
            logger.error(f"Portfolio {portfolio_id} not found or has no stocks")
            return None

        # Get cash balance (with fallback for legacy portfolios)
        cash_balance = portfolio.get('cash_balance', 0.0)
        if cash_balance is None:
            # Calculate on-the-fly for legacy portfolios
            total_allocated = sum(s.get('allocation_amount', 0) for s in stocks)
            cash_balance = portfolio['total_capital'] - total_allocated
            logger.info(f"Calculated cash_balance on-the-fly: Rs. {cash_balance:,.2f}")

        total_value = 0
        stock_details = []

        for stock in stocks:
            # Skip exited stocks (allocation = 0 or exit_date set)
            if stock.get('allocation_pct', 0) == 0 or stock.get('exit_date') is not None:
                logger.debug(f"Skipping exited stock {stock['ticker']} (allocation: {stock.get('allocation_pct')}%, exit_date: {stock.get('exit_date')})")
                continue

            # Get latest price from database
            latest_price_data = self.db.get_latest_stock_price(stock['id'])

            if latest_price_data:
                current_price = latest_price_data['close_price']
            else:
                # Fallback to live fetch if no cached price
                logger.debug(f"No cached price for {stock['ticker']}, fetching live...")
                current_price = self.price_fetcher.get_current_price(
                    stock['ticker'],
                    stock.get('exchange', 'NSE')
                )

            if not current_price:
                logger.warning(f"No price available for {stock['ticker']}, using entry price")
                current_price = stock['entry_price']

            # Calculate values using shares if available (new portfolios),
            # otherwise calculate from allocation_amount (legacy portfolios)
            if stock.get('shares') is not None:
                # Share-based portfolio (preferred)
                shares = stock['shares']
                entry_value = shares * stock['entry_price']
                stock_value = shares * current_price
            else:
                # Legacy allocation-based portfolio
                entry_value = stock['allocation_amount']
                shares = entry_value / stock['entry_price']
                stock_value = shares * current_price

            total_value += stock_value

            # Calculate P&L
            pnl_absolute = stock_value - entry_value
            pnl_pct = (pnl_absolute / entry_value) * 100 if entry_value > 0 else 0

            stock_details.append({
                'stock_id': stock['id'],
                'ticker': stock['ticker'],
                'name': stock['name'],
                'entry_price': stock['entry_price'],
                'current_price': current_price,
                'shares': shares,
                'initial_value': entry_value,
                'current_value': stock_value,
                'pnl_absolute': pnl_absolute,
                'pnl_pct': pnl_pct,
                'allocation_pct': (stock_value / total_value * 100) if total_value > 0 else 0
            })

        # Calculate total portfolio value (stocks + cash)
        total_stocks_value = total_value  # Stock holdings only
        total_value = total_stocks_value + cash_balance  # Portfolio value = Stocks + Cash

        # Portfolio-level P&L (now includes cash at face value)
        initial_capital = portfolio['total_capital'] or sum(s['allocation_amount'] for s in stocks)
        portfolio_pnl_absolute = total_value - initial_capital
        portfolio_pnl_pct = (portfolio_pnl_absolute / initial_capital) * 100 if initial_capital > 0 else 0

        return {
            'portfolio_id': portfolio_id,
            'current_value': total_value,  # Stock + Cash
            'stocks_value': total_stocks_value,  # Stocks only
            'cash_balance': cash_balance,  # Cash portion
            'initial_capital': initial_capital,
            'pnl_absolute': portfolio_pnl_absolute,  # Now includes cash
            'pnl_pct': portfolio_pnl_pct,  # Now includes cash
            'num_stocks': len(stock_details),  # Count only active stocks
            'stock_details': stock_details,
            'calculated_at': datetime.now().isoformat()
        }

    def calculate_returns(
        self,
        portfolio_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, float]:
        """
        Calculate portfolio returns for a period

        Args:
            portfolio_id: Portfolio ID
            start_date: Start date (defaults to portfolio creation)
            end_date: End date (defaults to today)

        Returns:
            Dict with various return metrics
        """
        if end_date is None:
            end_date = date.today()

        if start_date is None:
            portfolio = self.db.get_portfolio_by_id(portfolio_id)
            start_date = datetime.fromisoformat(portfolio['created_at']).date()

        # Get snapshots for the period
        snapshots = self.db.get_portfolio_snapshots(
            portfolio_id,
            start_date=start_date,
            end_date=end_date
        )

        if not snapshots:
            logger.warning(f"No snapshots found for portfolio {portfolio_id}")
            return {
                'total_return_pct': 0,
                'annualized_return': 0,
                'period_days': 0
            }

        # Calculate returns
        snapshots.sort(key=lambda x: x['snapshot_date'])
        start_value = snapshots[0]['total_value']
        end_value = snapshots[-1]['total_value']

        total_return = ((end_value - start_value) / start_value) * 100

        # Annualize if period > 1 year
        period_days = (end_date - start_date).days
        if period_days > 365:
            years = period_days / 365.25
            annualized_return = ((end_value / start_value) ** (1 / years) - 1) * 100
        else:
            annualized_return = total_return

        return {
            'total_return_pct': total_return,
            'annualized_return': annualized_return,
            'period_days': period_days,
            'start_value': start_value,
            'end_value': end_value
        }

    def calculate_volatility(
        self,
        portfolio_id: int,
        period_days: int = 90
    ) -> float:
        """
        Calculate annualized volatility (standard deviation of returns)

        Args:
            portfolio_id: Portfolio ID
            period_days: Number of days to look back

        Returns:
            Annualized volatility percentage
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        snapshots = self.db.get_portfolio_snapshots(
            portfolio_id,
            start_date=start_date,
            end_date=end_date
        )

        if len(snapshots) < 2:
            logger.warning(f"Insufficient data to calculate volatility (need at least 2 snapshots)")
            return 0.0

        # Sort by date
        snapshots.sort(key=lambda x: x['snapshot_date'])

        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i - 1]['total_value']
            curr_value = snapshots[i]['total_value']
            daily_return = (curr_value - prev_value) / prev_value
            daily_returns.append(daily_return)

        if not daily_returns:
            return 0.0

        # Calculate standard deviation and annualize
        daily_std = np.std(daily_returns)
        annualized_volatility = daily_std * np.sqrt(TRADING_DAYS_PER_YEAR) * 100

        logger.debug(f"Volatility for portfolio {portfolio_id}: {annualized_volatility:.2f}%")
        return annualized_volatility

    def calculate_sharpe_ratio(
        self,
        portfolio_id: int,
        period_days: int = 90,
        risk_free_rate: float = RISK_FREE_RATE
    ) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return)

        Formula: (Portfolio Return - Risk Free Rate) / Volatility

        Args:
            portfolio_id: Portfolio ID
            period_days: Period for calculation
            risk_free_rate: Annual risk-free rate (default: 6.5%)

        Returns:
            Sharpe ratio
        """
        # Get returns
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        returns = self.calculate_returns(portfolio_id, start_date, end_date)

        portfolio_return = returns['annualized_return']

        # Get volatility
        volatility = self.calculate_volatility(portfolio_id, period_days)

        if volatility == 0:
            logger.warning("Volatility is zero, cannot calculate Sharpe ratio")
            return 0.0

        # Calculate Sharpe ratio
        sharpe = (portfolio_return - risk_free_rate) / volatility

        logger.debug(f"Sharpe ratio for portfolio {portfolio_id}: {sharpe:.2f}")
        return sharpe

    def calculate_max_drawdown(
        self,
        portfolio_id: int,
        period_days: Optional[int] = None
    ) -> float:
        """
        Calculate maximum drawdown (largest peak-to-trough decline)

        Args:
            portfolio_id: Portfolio ID
            period_days: Period to analyze (None = all time)

        Returns:
            Maximum drawdown percentage (positive number)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days) if period_days else None

        snapshots = self.db.get_portfolio_snapshots(
            portfolio_id,
            start_date=start_date,
            end_date=end_date
        )

        if len(snapshots) < 2:
            return 0.0

        # Sort by date
        snapshots.sort(key=lambda x: x['snapshot_date'])
        values = [s['total_value'] for s in snapshots]

        # Calculate drawdown
        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value

            drawdown = ((peak - value) / peak) * 100
            if drawdown > max_dd:
                max_dd = drawdown

        logger.debug(f"Max drawdown for portfolio {portfolio_id}: {max_dd:.2f}%")
        return max_dd

    def calculate_benchmark_comparison(
        self,
        portfolio_id: int,
        index_symbol: str,
        period: str = 'ALL'
    ) -> Dict[str, Any]:
        """
        Compare portfolio performance against a benchmark index

        Args:
            portfolio_id: Portfolio ID
            index_symbol: Index symbol (e.g., '^NSEI')
            period: 'ALL', '1M', '3M', '6M', '1Y'

        Returns:
            Dict with portfolio_return, index_return, alpha, beta
        """
        logger.info(f"Comparing portfolio {portfolio_id} vs {index_symbol} ({period})")

        # Determine date range
        end_date = date.today()
        if period == '1M':
            start_date = end_date - timedelta(days=30)
        elif period == '3M':
            start_date = end_date - timedelta(days=90)
        elif period == '6M':
            start_date = end_date - timedelta(days=180)
        elif period == '1Y':
            start_date = end_date - timedelta(days=365)
        else:  # 'ALL'
            portfolio = self.db.get_portfolio_by_id(portfolio_id)
            start_date = datetime.fromisoformat(portfolio['created_at']).date()

        # Get portfolio returns - use latest snapshot for consistency with Performance Metrics
        # For 'ALL' period, use the latest snapshot's total_return_pct directly
        if period == 'ALL':
            latest_snapshot = self.db.get_latest_portfolio_snapshot(portfolio_id)
            if latest_snapshot:
                portfolio_return = latest_snapshot['total_return_pct']
                logger.debug(f"Using snapshot total_return_pct for ALL period: {portfolio_return:.2f}%")
            else:
                # Fallback to calculated returns
                portfolio_returns = self.calculate_returns(portfolio_id, start_date, end_date)
                portfolio_return = portfolio_returns['total_return_pct']
        else:
            # For other periods, calculate from snapshots
            portfolio_returns = self.calculate_returns(portfolio_id, start_date, end_date)
            portfolio_return = portfolio_returns['total_return_pct']

        # Get index prices from database
        index_history = self.db.get_index_price_history(
            index_symbol,
            start_date=start_date,
            end_date=end_date
        )

        # Check if we need to fetch fresh data from Yahoo Finance
        needs_fetch = False

        if not index_history or len(index_history) < 2:
            needs_fetch = True
            logger.debug(f"Need fetch: insufficient data (records={len(index_history) if index_history else 0})")
        else:
            # Check data freshness - sort by date to get latest
            sorted_history = sorted(index_history, key=lambda x: x['price_date'], reverse=True)
            latest_date_str = sorted_history[0]['price_date']

            # Convert to date object if it's a string
            if isinstance(latest_date_str, str):
                latest_date = datetime.fromisoformat(latest_date_str).date()
            else:
                latest_date = latest_date_str

            # Calculate staleness (days between latest data and end_date)
            staleness_days = (end_date - latest_date).days

            # Fetch if data is 3+ days old (accounts for weekends: Fri→Mon = 3 days)
            if staleness_days >= 3:
                needs_fetch = True
                logger.debug(f"Need fetch: data is stale (latest={latest_date}, end={end_date}, staleness={staleness_days} days)")

        # If not in database or stale, fetch from Yahoo Finance and store
        if needs_fetch:
            logger.info(f"Fetching index history from Yahoo Finance: {index_symbol} ({start_date} to {end_date})")

            try:
                # Fetch historical data from Yahoo Finance
                hist_data = self.price_fetcher.get_index_history(
                    index_symbol,
                    start=start_date,
                    end=end_date + timedelta(days=1)  # Include end date
                )

                if hist_data and len(hist_data['dates']) >= 2:
                    # Store in database for future use
                    from tools.price_fetcher import INDIAN_INDICES
                    index_name = INDIAN_INDICES.get(index_symbol, index_symbol)

                    for i, price_date in enumerate(hist_data['dates']):
                        # Convert pandas Timestamp to date
                        if hasattr(price_date, 'date'):
                            price_date = price_date.date()

                        self.db.store_index_price(
                            index_symbol=index_symbol,
                            index_name=index_name,
                            price_date=price_date,
                            open_price=float(hist_data['open'][i]),
                            high_price=float(hist_data['high'][i]),
                            low_price=float(hist_data['low'][i]),
                            close_price=float(hist_data['close'][i]),
                            volume=int(hist_data['volume'][i]) if hist_data['volume'][i] else None
                        )

                    logger.info(f"Stored {len(hist_data['dates'])} days of index history for {index_symbol}")

                    # Now fetch from database again
                    index_history = self.db.get_index_price_history(
                        index_symbol,
                        start_date=start_date,
                        end_date=end_date
                    )
                else:
                    logger.warning(f"No historical data returned from Yahoo Finance for {index_symbol}")

            except Exception as e:
                logger.error(f"Failed to fetch index history from Yahoo Finance: {e}")

        # Check again if we have data after attempting fetch
        if not index_history or len(index_history) < 2:
            logger.warning(f"Insufficient index data for {index_symbol}")
            return {
                'portfolio_return': portfolio_return,
                'index_return': 0,
                'alpha': portfolio_return,
                'beta': None,
                'error': 'Insufficient index data'
            }

        # Calculate index return using closest available dates
        # Get baseline: last trading day on or before start_date
        baseline_price_data = self.db.get_index_price_on_or_before(index_symbol, start_date)

        # Get end price: last trading day on or before end_date
        end_price_data = self.db.get_index_price_on_or_before(index_symbol, end_date)

        if not baseline_price_data:
            logger.error(f"No baseline data for {index_symbol} before {start_date}")
            return {
                'portfolio_return': portfolio_return,
                'index_return': None,
                'alpha': None,
                'beta': None,
                'error': f'No baseline data before {start_date}'
            }

        if not end_price_data:
            logger.error(f"No end data for {index_symbol} before {end_date}")
            return {
                'portfolio_return': portfolio_return,
                'index_return': None,
                'alpha': None,
                'beta': None,
                'error': f'No end data before {end_date}'
            }

        start_price = baseline_price_data['close_price']
        start_date_actual = baseline_price_data['price_date']
        end_price = end_price_data['close_price']
        end_date_actual = end_price_data['price_date']

        # Convert date strings if needed
        if isinstance(start_date_actual, str):
            start_date_actual = datetime.fromisoformat(start_date_actual).date()
        if isinstance(end_date_actual, str):
            end_date_actual = datetime.fromisoformat(end_date_actual).date()

        logger.info(
            f"Benchmark {index_symbol}: Baseline {start_date_actual} (target {start_date}) = {start_price:.2f}, "
            f"End {end_date_actual} (target {end_date}) = {end_price:.2f}"
        )

        index_return = ((end_price - start_price) / start_price) * 100

        # Calculate alpha
        alpha = portfolio_return - index_return

        # Calculate beta (simplified - would need daily returns for accurate beta)
        # For now, estimate based on volatility ratio
        beta = None  # TODO: Implement proper beta calculation with covariance

        return {
            'portfolio_return': portfolio_return,
            'index_return': index_return,
            'alpha': alpha,
            'beta': beta,
            'outperformance': alpha,
            'period': period
        }

    def generate_portfolio_snapshot(
        self,
        portfolio_id: int,
        snapshot_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive portfolio snapshot with all metrics

        Args:
            portfolio_id: Portfolio ID
            snapshot_date: Date for snapshot (defaults to today)

        Returns:
            Complete snapshot dict
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        logger.info(f"Generating portfolio snapshot for {portfolio_id} on {snapshot_date}")

        # Calculate current value
        value_data = self.calculate_current_value(portfolio_id)

        if not value_data:
            logger.error("Failed to calculate current value")
            return None

        # Calculate metrics
        volatility = self.calculate_volatility(portfolio_id)
        sharpe_ratio = self.calculate_sharpe_ratio(portfolio_id)
        max_drawdown = self.calculate_max_drawdown(portfolio_id)

        # Get previous snapshot for day return
        previous_snapshot = self.db.get_portfolio_snapshots(
            portfolio_id,
            end_date=snapshot_date - timedelta(days=1),
            limit=1
        )

        if previous_snapshot:
            # Normal case: compare vs previous trading day
            prev_value = previous_snapshot[0]['total_value']
            day_return_absolute = value_data['current_value'] - prev_value
            day_return_pct = (day_return_absolute / prev_value) * 100 if prev_value > 0 else 0
        else:
            # First trading day: use initial capital as baseline
            prev_value = value_data['initial_capital']
            day_return_absolute = value_data['current_value'] - prev_value
            day_return_pct = (day_return_absolute / prev_value) * 100 if prev_value > 0 else 0
            logger.info(f"First snapshot: Day Return = Total Return (baseline = initial capital)")

        # Compile metrics
        metrics = {
            'cash_balance': value_data['cash_balance'],  # Cash portion of portfolio
            'invested_value': value_data['initial_capital'],
            'total_return_pct': value_data['pnl_pct'],  # Now includes cash
            'total_return_absolute': value_data['pnl_absolute'],  # Now includes cash
            'day_return_pct': day_return_pct,
            'day_return_absolute': day_return_absolute,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'num_stocks': value_data['num_stocks'],
            'avg_allocation_pct': 100 / value_data['num_stocks'] if value_data['num_stocks'] > 0 else 0
        }

        # Store snapshot in database
        snapshot_id = self.db.store_portfolio_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            total_value=value_data['current_value'],
            metrics=metrics
        )

        logger.info(f"Stored portfolio snapshot (ID: {snapshot_id})")

        return {
            'snapshot_id': snapshot_id,
            'snapshot_date': snapshot_date,
            'total_value': value_data['current_value'],
            **metrics,
            'stock_details': value_data['stock_details']
        }

    def update_benchmark_comparisons(
        self,
        portfolio_id: int,
        comparison_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Update benchmark comparisons for all user-selected indices

        Args:
            portfolio_id: Portfolio ID
            comparison_date: Date for comparison (defaults to today)

        Returns:
            List of comparison results
        """
        if comparison_date is None:
            comparison_date = date.today()

        # Get user's benchmark preferences
        benchmarks = self.db.get_user_benchmarks(portfolio_id)

        if not benchmarks:
            logger.warning(f"No benchmarks configured for portfolio {portfolio_id}")
            return []

        results = []

        for benchmark in benchmarks:
            index_symbol = benchmark['index_symbol']
            index_name = benchmark['index_name']

            # Calculate comparison for different periods
            for period in ['1M', '3M', '6M', '1Y', 'ALL']:
                comparison = self.calculate_benchmark_comparison(
                    portfolio_id,
                    index_symbol,
                    period
                )

                # Skip if no index data available
                if comparison['index_return'] is None:
                    logger.warning(
                        f"Skipping {index_symbol} {period} benchmark - "
                        f"no index data: {comparison.get('error', 'Unknown error')}"
                    )
                    continue

                # Store in database
                self.db.store_benchmark_comparison(
                    portfolio_id=portfolio_id,
                    comparison_date=comparison_date,
                    index_symbol=index_symbol,
                    index_name=index_name,
                    portfolio_return=comparison['portfolio_return'],
                    index_return=comparison['index_return'],
                    period=period,
                    alpha=comparison['alpha'],
                    beta=comparison.get('beta')
                )

                results.append({
                    'index_symbol': index_symbol,
                    'index_name': index_name,
                    'period': period,
                    **comparison
                })

        logger.info(f"Updated {len(results)} benchmark comparisons")
        return results


# Singleton instance
_performance_calculator = None


def get_performance_calculator() -> PerformanceCalculator:
    """Get or create performance calculator singleton"""
    global _performance_calculator
    if _performance_calculator is None:
        _performance_calculator = PerformanceCalculator()
    return _performance_calculator


if __name__ == '__main__':
    # Test script
    calc = PerformanceCalculator()

    print("Testing performance calculator...")
    print("\n1. Calculating current value for portfolio 1:")
    value_data = calc.calculate_current_value(1)
    if value_data:
        print(f"   Current Value: Rs. {value_data['current_value']:,.2f}")
        print(f"   P&L: {value_data['pnl_pct']:.2f}% (Rs. {value_data['pnl_absolute']:,.2f})")
    else:
        print("   No data available")

    print("\nDone!")
