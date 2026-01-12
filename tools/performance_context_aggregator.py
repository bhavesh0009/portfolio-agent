"""
Performance Context Aggregator - Portfolio Performance Data for LLM
Generates comprehensive portfolio performance metrics for Portfolio Manager Agent
"""

import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.db_service import get_db_service
from tools.price_fetcher import get_price_fetcher, INDIAN_INDICES
from tools.performance_calculator import get_performance_calculator

logger = get_logger("tools.performance_context_aggregator")

# Benchmark indices for comparison
# Updated 2025-12-29: Verified working ticker symbols via yfinance
BENCHMARK_INDICES = [
    '^NSEI',                    # Nifty 50 (large-cap)
    'NIFTY_MIDCAP_100.NS',      # Nifty Midcap 100 (mid-cap)
    '^NSEMDCP50'                # Nifty Midcap 50 (alternative mid-cap, replacing Smallcap 250 due to data issues)
]

# Time periods for return calculation (in days)
PERIODS = {
    'daily': 1,
    'wtd': 7,       # Week-to-date
    'mtd': 30,      # Month-to-date
    'inception': None  # Since portfolio creation
}

# Number of top/bottom performers to identify
NUM_TOP_PERFORMERS = 3


class PerformanceContextAggregator:
    """Aggregates comprehensive portfolio performance data for LLM consumption"""

    def __init__(self):
        self.db = get_db_service()
        self.price_fetcher = get_price_fetcher()
        self.perf_calculator = get_performance_calculator()

    def generate_context(
        self,
        portfolio_id: int,
        include_benchmarks: bool = True,
        include_sector_breakdown: bool = True,
        include_top_performers: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance context for LLM

        Args:
            portfolio_id: Portfolio ID from database
            include_benchmarks: Include benchmark comparison
            include_sector_breakdown: Include sector performance analysis
            include_top_performers: Include top gainers/losers

        Returns:
            Dict with performance metrics, narrative summary, and data quality info
        """
        logger.info(f"Generating performance context for portfolio {portfolio_id}")

        # Step 1: Fetch portfolio data
        portfolio = self.db.get_portfolio_by_id(portfolio_id)
        if not portfolio:
            logger.error(f"Portfolio {portfolio_id} not found")
            return self._error_context("Portfolio not found")

        stocks = self.db.get_portfolio_stocks(portfolio_id)
        if not stocks:
            logger.warning(f"Portfolio {portfolio_id} has no stocks")
            return self._error_context("Portfolio has no stocks")

        logger.debug(f"Loaded portfolio with {len(stocks)} stocks")

        # Step 2: Fetch latest prices
        current_prices, missing_prices = self._fetch_prices_with_fallback(stocks)
        logger.info(f"Price coverage: {len(current_prices) - len(missing_prices)}/{len(current_prices)}")

        # Step 3: Calculate time-period returns
        returns = self._calculate_period_returns(portfolio, stocks, current_prices)
        logger.debug(f"Calculated returns for {len(returns)} periods")

        # Step 4: Fetch & compare benchmarks
        benchmarks = []
        if include_benchmarks:
            inception_date = datetime.strptime(portfolio['timestamp'], '%Y%m%d_%H%M%S').date()
            benchmarks = self._compare_with_benchmarks(returns, inception_date)
            logger.info(f"Benchmark comparison: {len([b for b in benchmarks if b.get('status') != 'unavailable'])}/{len(BENCHMARK_INDICES)} available")

        # Step 5: Calculate volatility & risk metrics
        risk = self._calculate_volatility_comparison(portfolio_id, benchmarks if include_benchmarks else [])
        logger.debug(f"Risk metrics calculated: volatility={risk.get('volatility')}")

        # Step 6: Identify top performers
        top_performers = {}
        if include_top_performers:
            top_performers = self._identify_top_performers(stocks, current_prices, NUM_TOP_PERFORMERS)
            logger.debug(f"Identified {len(top_performers.get('gainers', []))} gainers and {len(top_performers.get('losers', []))} losers")

        # Step 7: Sector performance breakdown
        sectors = []
        if include_sector_breakdown:
            sectors = self._calculate_sector_performance(stocks, current_prices)
            logger.debug(f"Calculated performance for {len(sectors)} sectors")

        # Calculate current portfolio value (stocks + cash)
        stocks_value = sum(
            (stock['allocation_amount'] / stock['entry_price']) * current_prices.get(stock['ticker'], stock['entry_price'])
            for stock in stocks
        )
        cash_balance = portfolio.get('cash_balance', 0)
        current_value = stocks_value + cash_balance

        # Step 8: Format for LLM
        context = {
            'portfolio': {
                'id': portfolio_id,
                'profile': portfolio['profile'],
                'total_capital': portfolio['total_capital'],
                'current_value': round(current_value, 2),
                'inception_date': datetime.strptime(portfolio['timestamp'], '%Y%m%d_%H%M%S').date().isoformat(),
                'num_stocks': len(stocks)
            },
            'returns': returns,
            'benchmarks': benchmarks,
            'risk': risk,
            'top_performers': top_performers,
            'sectors': sectors,
            'data_quality': {
                'price_coverage': f"{len(current_prices) - len(missing_prices)}/{len(current_prices)}",
                'missing_prices': missing_prices,
                'benchmarks_available': len([b for b in benchmarks if b.get('status') != 'unavailable'])
            }
        }

        # Generate narrative summary
        context['narrative'] = self._format_narrative_summary(context)

        logger.info("Performance context generated successfully")
        return context

    def _fetch_prices_with_fallback(self, stocks: List[Dict]) -> tuple[Dict[str, float], List[str]]:
        """
        Fetch prices with 3-tier fallback: DB → Live → Entry Price

        Args:
            stocks: List of stock dicts

        Returns:
            Tuple of (prices dict, missing_prices list)
        """
        prices = {}
        missing_prices = []

        for stock in stocks:
            ticker = stock['ticker']
            stock_id = stock['id']

            # Tier 1: Check database (today's price)
            db_price = self.db.get_latest_stock_price(stock_id)
            if db_price and db_price.get('price_date') == date.today():
                prices[ticker] = db_price['close_price']
                logger.trace(f"{ticker}: Using DB price Rs. {db_price['close_price']:.2f}")
                continue

            # Tier 2: Fetch live price
            try:
                live_price = self.price_fetcher.get_current_price(
                    ticker,
                    stock.get('exchange', 'NSE')
                )
                if live_price and live_price > 0:
                    prices[ticker] = live_price
                    logger.debug(f"{ticker}: Fetched live price Rs. {live_price:.2f}")
                    # Store in database for future use
                    try:
                        self.db.store_daily_price(
                            stock_id=stock_id,
                            price_date=date.today(),
                            open_price=live_price,
                            high_price=live_price,
                            low_price=live_price,
                            close_price=live_price,
                            volume=None
                        )
                    except Exception as e:
                        logger.debug(f"Failed to store price for {ticker}: {e}")
                    continue
            except Exception as e:
                logger.debug(f"Live fetch failed for {ticker}: {e}")

            # Tier 3: Fallback to entry price
            prices[ticker] = stock['entry_price']
            missing_prices.append(ticker)
            logger.warning(f"{ticker}: Using entry price Rs. {stock['entry_price']:.2f} (no live data)")

        return prices, missing_prices

    def _calculate_period_returns(
        self,
        portfolio: Dict,
        stocks: List[Dict],
        current_prices: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate returns for all time periods

        Returns:
            Dict with keys: daily, wtd, mtd, inception
            Each value: {'pct': float, 'absolute': float}
        """
        returns = {}

        # Calculate current portfolio value (stocks + cash)
        stocks_value = sum(
            (stock['allocation_amount'] / stock['entry_price']) * current_prices.get(stock['ticker'], stock['entry_price'])
            for stock in stocks
        )
        cash_balance = portfolio.get('cash_balance', 0)
        current_value = stocks_value + cash_balance

        initial_capital = portfolio['total_capital'] or sum(s['allocation_amount'] for s in stocks)

        # Inception return (always calculable)
        inception_pnl_pct = ((current_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0
        inception_pnl_abs = current_value - initial_capital

        returns['inception'] = {
            'pct': round(inception_pnl_pct, 2),
            'absolute': round(inception_pnl_abs, 2)
        }

        # Other periods: Try snapshot method first, then fallback
        for period_name, period_days in [('daily', 1), ('wtd', 7), ('mtd', 30)]:
            pct_return = self._calculate_returns_with_fallback(portfolio['id'], period_days, stocks, current_prices, current_value)

            if pct_return is not None:
                abs_return = (pct_return / 100) * current_value
                returns[period_name] = {
                    'pct': round(pct_return, 2),
                    'absolute': round(abs_return, 2)
                }
            else:
                # No data available
                returns[period_name] = {
                    'pct': 0.0,
                    'absolute': 0.0
                }
                logger.warning(f"Could not calculate {period_name} return - insufficient data")

        return returns

    def _calculate_returns_with_fallback(
        self,
        portfolio_id: int,
        period_days: int,
        stocks: List[Dict],
        current_prices: Dict[str, float],
        current_value: float
    ) -> Optional[float]:
        """
        Calculate period return with fallback from snapshots → daily_prices

        Returns:
            Return percentage or None if insufficient data
        """
        # Try 1: Use portfolio_snapshots
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days)

            snapshots = self.db.get_portfolio_snapshots(
                portfolio_id,
                start_date=start_date,
                end_date=end_date
            )

            if snapshots and len(snapshots) >= 2:
                snapshots_list = sorted(snapshots, key=lambda x: x['snapshot_date'])
                start_value = snapshots_list[0]['total_value']
                end_value = snapshots_list[-1]['total_value']
                return ((end_value - start_value) / start_value) * 100
        except Exception as e:
            logger.trace(f"Snapshot calculation failed for {period_days}-day period: {e}")

        # Try 2: Calculate from daily_prices
        try:
            target_date = date.today() - timedelta(days=period_days)
            start_stocks_value = 0

            for stock in stocks:
                # Get historical price on or before target date (last trading day)
                # Use end_date parameter to look backward, not forward
                price_history = self.db.get_stock_price_history(
                    stock['id'],
                    end_date=target_date,  # Changed: use end_date to look backward
                    limit=1
                )

                if price_history:
                    start_price = price_history[0]['close_price']
                    shares = stock['allocation_amount'] / stock['entry_price']
                    start_stocks_value += shares * start_price

            # Add cash balance to start_value (bug fix)
            portfolio = self.db.get_portfolio_by_id(portfolio_id)
            cash_balance = portfolio.get('cash_balance', 0) if portfolio else 0
            start_value = start_stocks_value + cash_balance

            if start_value > 0:
                return ((current_value - start_value) / start_value) * 100
        except Exception as e:
            logger.trace(f"Daily price calculation failed for {period_days}-day period: {e}")

        return None

    def _compare_with_benchmarks(
        self,
        portfolio_returns: Dict[str, Dict],
        inception_date: date
    ) -> List[Dict[str, Any]]:
        """
        Compare portfolio returns with benchmark indices

        Returns:
            List of benchmark dicts with returns and alpha
        """
        benchmarks = []

        for index_symbol in BENCHMARK_INDICES:
            try:
                benchmark_data = self._fetch_benchmark_data(index_symbol, inception_date)
                benchmarks.append(benchmark_data)
            except Exception as e:
                logger.warning(f"Benchmark {index_symbol} unavailable: {e}")
                benchmarks.append({
                    'symbol': index_symbol,
                    'name': INDIAN_INDICES.get(index_symbol, index_symbol),
                    'status': 'unavailable',
                    'error': str(e)
                })

        # Calculate alpha for each period
        for benchmark in benchmarks:
            if benchmark.get('status') == 'unavailable':
                continue

            alpha = {}
            for period in ['daily', 'wtd', 'mtd', 'inception']:
                port_return = portfolio_returns.get(period, {}).get('pct', 0)
                bench_return = benchmark['returns'].get(period, 0)
                alpha[period] = round(port_return - bench_return, 2)

            benchmark['alpha'] = alpha

        return benchmarks

    def _fetch_benchmark_data(self, index_symbol: str, inception_date: date) -> Dict[str, Any]:
        """
        Fetch historical data for benchmark index and calculate returns

        Returns:
            Dict with index info, returns for all periods
        """
        # Fetch historical data
        periods_needed = {
            'daily': 1,
            'wtd': 7,
            'mtd': 30,
            'inception': (date.today() - inception_date).days
        }

        max_days = max(v for v in periods_needed.values() if v is not None)
        history = self.price_fetcher.get_index_history(index_symbol, period=f'{max_days}d')

        # get_index_history returns a dict, not a DataFrame
        if not history or not history.get('close'):
            raise ValueError(f"No history data for {index_symbol}")

        close_prices = history['close']
        num_prices = len(close_prices)

        if num_prices == 0:
            raise ValueError(f"No close prices for {index_symbol}")

        logger.debug(f"{index_symbol}: Retrieved {num_prices} historical prices")

        # Calculate returns for each period
        returns = {}
        for period_name, days in periods_needed.items():
            if days == 0:
                returns[period_name] = 0.0
                continue

            try:
                if num_prices > days:
                    # Get prices from the end of the list
                    start_price = close_prices[-days-1]
                    end_price = close_prices[-1]
                    period_return = ((end_price - start_price) / start_price) * 100
                    returns[period_name] = round(period_return, 2)
                    logger.trace(f"{index_symbol} {period_name}: {start_price:.2f} -> {end_price:.2f} = {period_return:+.2f}%")
                else:
                    # Not enough data for this period
                    logger.debug(f"{index_symbol}: Insufficient data for {period_name} ({num_prices} <= {days})")
                    returns[period_name] = 0.0
            except Exception as e:
                logger.debug(f"Could not calculate {period_name} return for {index_symbol}: {e}")
                returns[period_name] = 0.0

        return {
            'symbol': index_symbol,
            'name': INDIAN_INDICES.get(index_symbol, index_symbol),
            'returns': returns,
            'status': 'available'
        }

    def _calculate_volatility_comparison(
        self,
        portfolio_id: int,
        benchmarks: List[Dict]
    ) -> Dict[str, Any]:
        """
        Calculate portfolio risk metrics and compare volatility with benchmarks

        Returns:
            Dict with volatility, sharpe_ratio, max_drawdown, benchmark_volatility
        """
        risk = {}

        try:
            # Portfolio volatility
            volatility = self.perf_calculator.calculate_volatility(portfolio_id)
            risk['volatility'] = round(volatility, 2) if volatility else None

            # Sharpe ratio
            sharpe = self.perf_calculator.calculate_sharpe_ratio(portfolio_id)
            risk['sharpe_ratio'] = round(sharpe, 2) if sharpe else None

            # Max drawdown
            max_dd = self.perf_calculator.calculate_max_drawdown(portfolio_id)
            risk['max_drawdown'] = round(max_dd, 2) if max_dd else None

        except Exception as e:
            logger.warning(f"Could not calculate portfolio risk metrics: {e}")
            risk['volatility'] = None
            risk['sharpe_ratio'] = None
            risk['max_drawdown'] = None

        # Benchmark volatility (simplified - would need historical data)
        benchmark_volatility = {}
        for bench in benchmarks:
            if bench.get('status') == 'available':
                # Placeholder - proper calculation would require daily returns
                benchmark_volatility[bench['symbol']] = None

        risk['benchmark_volatility'] = benchmark_volatility

        return risk

    def _identify_top_performers(
        self,
        stocks: List[Dict],
        current_prices: Dict[str, float],
        num_top: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        Identify top gainers and losers with allocation-weighted impact

        Returns:
            Dict with 'gainers' and 'losers' lists
        """
        performers = []

        for stock in stocks:
            ticker = stock['ticker']
            current_price = current_prices.get(ticker, stock['entry_price'])
            entry_price = stock['entry_price']
            allocation = stock['allocation_pct']

            # Calculate stock return
            return_pct = ((current_price - entry_price) / entry_price) * 100

            # Calculate portfolio impact
            portfolio_impact = (return_pct * allocation) / 100

            performers.append({
                'ticker': ticker,
                'name': stock['name'],
                'sector': stock.get('sector', 'Unknown'),
                'current_price': round(current_price, 2),
                'entry_price': round(entry_price, 2),
                'return_pct': round(return_pct, 2),
                'allocation_pct': round(allocation, 2),
                'portfolio_impact': round(portfolio_impact, 2)
            })

        # Sort by return percentage
        performers_sorted = sorted(performers, key=lambda x: x['return_pct'], reverse=True)

        return {
            'gainers': performers_sorted[:num_top],
            'losers': performers_sorted[-num_top:][::-1]  # Reverse to show worst first
        }

    def _calculate_sector_performance(
        self,
        stocks: List[Dict],
        current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate allocation-weighted sector returns

        Returns:
            List of sector dicts sorted by performance
        """
        sectors = defaultdict(lambda: {'stocks': [], 'total_allocation': 0})

        for stock in stocks:
            ticker = stock['ticker']
            sector = stock.get('sector', 'Unknown')
            allocation = stock['allocation_pct']

            # Calculate stock return
            current_price = current_prices.get(ticker, stock['entry_price'])
            stock_return = ((current_price - stock['entry_price']) / stock['entry_price']) * 100

            sectors[sector]['stocks'].append({
                'ticker': ticker,
                'name': stock['name'],
                'return_pct': round(stock_return, 2),
                'allocation_pct': round(allocation, 2),
                'weighted_contribution': stock_return * allocation
            })
            sectors[sector]['total_allocation'] += allocation

        # Calculate weighted sector returns
        sector_performance = []
        for sector, data in sectors.items():
            if data['total_allocation'] > 0:
                weighted_return = sum(s['weighted_contribution'] for s in data['stocks']) / data['total_allocation']
            else:
                weighted_return = 0

            sector_performance.append({
                'sector': sector,
                'total_allocation_pct': round(data['total_allocation'], 2),
                'weighted_return': round(weighted_return, 2),
                'num_stocks': len(data['stocks'])
            })

        # Sort by performance
        return sorted(sector_performance, key=lambda x: x['weighted_return'], reverse=True)

    def _format_narrative_summary(self, context: Dict[str, Any]) -> str:
        """
        Generate narrative summary for LLM consumption

        Args:
            context: Full context dict

        Returns:
            Formatted narrative string
        """
        portfolio = context['portfolio']
        returns = context['returns']
        benchmarks = context['benchmarks']
        risk = context['risk']
        top_performers = context['top_performers']
        sectors = context['sectors']
        data_quality = context['data_quality']

        lines = []

        # Header
        lines.append(f"PERFORMANCE SUMMARY (as of {date.today().isoformat()})")
        lines.append("")

        # Portfolio value
        inception_return = returns['inception']['pct']
        lines.append(f"Portfolio Value: Rs. {portfolio['current_value']:,.0f} "
                    f"({inception_return:+.2f}% since inception on {portfolio['inception_date']})")
        lines.append("")

        # Today's performance with benchmark comparison
        daily_return = returns['daily']['pct']
        lines.append(f"Today's Performance: {daily_return:+.2f}% (Rs. {returns['daily']['absolute']:,.0f})")

        available_benchmarks = [b for b in benchmarks if b.get('status') == 'available']
        if available_benchmarks:
            for bench in available_benchmarks:
                alpha = bench['alpha']['daily']
                bench_return = bench['returns']['daily']
                comparision = "Outperformed" if alpha > 0 else "Underperformed" if alpha < 0 else "Matched"
                lines.append(f"- {comparision} {bench['name']} ({bench_return:+.2f}%) by {alpha:+.2f}%")
        lines.append("")

        # Period returns
        wtd_return = returns.get('wtd', {}).get('pct', 0)
        mtd_return = returns.get('mtd', {}).get('pct', 0)
        lines.append(f"Week-to-Date: {wtd_return:+.2f}%, Month-to-Date: {mtd_return:+.2f}%")
        lines.append("")

        # Risk metrics
        if risk.get('volatility') is not None:
            lines.append("Risk Metrics:")
            lines.append(f"- Volatility: {risk['volatility']:.1f}% (annualized)")
            if risk.get('sharpe_ratio') is not None:
                lines.append(f"- Sharpe Ratio: {risk['sharpe_ratio']:.2f}")
            if risk.get('max_drawdown') is not None:
                lines.append(f"- Max Drawdown: {risk['max_drawdown']:.2f}%")
            lines.append("")

        # Top performers
        if top_performers.get('gainers'):
            lines.append("Top Performers Today:")
            for i, stock in enumerate(top_performers['gainers'], 1):
                lines.append(f"{i}. {stock['name']} ({stock['ticker']}): "
                           f"{stock['return_pct']:+.2f}%, contributed {stock['portfolio_impact']:+.2f}% to portfolio")
            lines.append("")

        if top_performers.get('losers'):
            lines.append("Underperformers Today:")
            for i, stock in enumerate(top_performers['losers'], 1):
                lines.append(f"{i}. {stock['name']} ({stock['ticker']}): "
                           f"{stock['return_pct']:+.2f}%, impacted portfolio by {stock['portfolio_impact']:+.2f}%")
            lines.append("")

        # Sector performance
        if sectors:
            lines.append("Sector Performance (Allocation-Weighted):")
            for i, sector in enumerate(sectors[:5], 1):  # Top 5 sectors
                lines.append(f"{i}. {sector['sector']}: {sector['weighted_return']:+.2f}% "
                           f"({sector['total_allocation_pct']:.1f}% allocation)")
            lines.append("")

        # Data quality
        lines.append(f"Data Quality: {data_quality['price_coverage']} stocks with live prices, "
                    f"{data_quality['benchmarks_available']}/{len(BENCHMARK_INDICES)} benchmarks available")

        return "\n".join(lines)

    def _error_context(self, error_msg: str) -> Dict[str, Any]:
        """
        Return minimal error context when generation fails

        Returns:
            Error context dict
        """
        return {
            'error': error_msg,
            'portfolio': {},
            'returns': {},
            'benchmarks': [],
            'risk': {},
            'top_performers': {},
            'sectors': [],
            'narrative': f"Error generating performance context: {error_msg}",
            'data_quality': {
                'price_coverage': '0/0',
                'missing_prices': [],
                'benchmarks_available': 0
            }
        }


# Singleton instance
_aggregator = None


def get_performance_context_aggregator() -> PerformanceContextAggregator:
    """Get singleton instance of PerformanceContextAggregator"""
    global _aggregator
    if _aggregator is None:
        _aggregator = PerformanceContextAggregator()
    return _aggregator
