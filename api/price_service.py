"""
FastAPI Backend Service for Portfolio Dashboard
Provides REST API endpoints for performance metrics, benchmarks, and manager updates
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.db_service import get_db_service
from tools.price_fetcher import get_price_fetcher
from tools.performance_calculator import get_performance_calculator

logger = get_logger("api.price_service")

# Initialize FastAPI app
app = FastAPI(
    title="Portfolio Agent API",
    description="REST API for portfolio performance tracking and analysis",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service instances
db = get_db_service()
price_fetcher = get_price_fetcher()
perf_calculator = get_performance_calculator()


@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "Portfolio Agent API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/api/performance/{portfolio_id}")
async def get_portfolio_performance(portfolio_id: int) -> Dict[str, Any]:
    """
    Get comprehensive portfolio performance metrics

    Returns:
        - Current portfolio value
        - P&L (absolute and percentage)
        - Risk metrics (volatility, Sharpe ratio, max drawdown)
        - Individual stock details
    """
    try:
        logger.info(f"Fetching performance data for portfolio {portfolio_id}")

        # Get current value and P&L
        value_data = perf_calculator.calculate_current_value(portfolio_id)

        if not value_data:
            raise HTTPException(
                status_code=404,
                detail=f"Portfolio {portfolio_id} not found or has no stocks"
            )

        # Get latest snapshot for additional metrics
        snapshot = db.get_latest_portfolio_snapshot(portfolio_id)

        if snapshot:
            # Use snapshot metrics if available
            metrics = {
                'volatility': snapshot.get('volatility', 0),
                'sharpe_ratio': snapshot.get('sharpe_ratio', 0),
                'max_drawdown': snapshot.get('max_drawdown', 0),
                'day_return_pct': snapshot.get('day_return_pct', 0),
                'day_return_absolute': snapshot.get('day_return_absolute', 0)
            }
        else:
            # Calculate fresh if no snapshot
            logger.warning(f"No snapshot found for portfolio {portfolio_id}, calculating fresh metrics")
            metrics = {
                'volatility': perf_calculator.calculate_volatility(portfolio_id),
                'sharpe_ratio': perf_calculator.calculate_sharpe_ratio(portfolio_id),
                'max_drawdown': perf_calculator.calculate_max_drawdown(portfolio_id),
                'day_return_pct': 0,
                'day_return_absolute': 0
            }

        # Combine data
        response = {
            'portfolio_id': portfolio_id,
            'current_value': value_data['current_value'],
            'initial_capital': value_data['initial_capital'],
            'pnl_absolute': value_data['pnl_absolute'],
            'pnl_pct': value_data['pnl_pct'],
            'num_stocks': value_data['num_stocks'],
            'calculated_at': value_data['calculated_at'],
            **metrics,
            'stock_details': value_data['stock_details']
        }

        logger.info(f"Successfully fetched performance data: Value = Rs. {response['current_value']:,.2f}, P&L = {response['pnl_pct']:.2f}%")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching performance data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/benchmarks/{portfolio_id}")
async def get_benchmark_comparison(
    portfolio_id: int,
    period: str = Query("ALL", pattern="^(1M|3M|6M|1Y|ALL)$")
) -> Dict[str, Any]:
    """
    Compare portfolio performance against benchmark indices

    Args:
        portfolio_id: Portfolio ID
        period: Time period ('1M', '3M', '6M', '1Y', 'ALL')

    Returns:
        - Portfolio return for period
        - List of benchmark comparisons with alpha
    """
    try:
        logger.info(f"Fetching benchmark comparisons for portfolio {portfolio_id}, period={period}")

        # Get benchmark comparisons from database
        comparisons = db.get_benchmark_comparisons(portfolio_id, period=period)

        if not comparisons:
            logger.warning(f"No benchmark data found for portfolio {portfolio_id}")
            return {
                'portfolio_id': portfolio_id,
                'period': period,
                'benchmarks': [],
                'message': 'No benchmark data available. Run scheduler to generate comparisons.'
            }

        # Get portfolio return (should be same across all benchmarks for this period)
        portfolio_return = comparisons[0]['portfolio_return'] if comparisons else 0

        # Format benchmark data
        benchmark_list = [
            {
                'index_symbol': comp['index_symbol'],
                'index_name': comp['index_name'],
                'index_return': comp['index_return'],
                'alpha': comp['alpha'],
                'outperformance': comp['outperformance']
            }
            for comp in comparisons
        ]

        # Sort by alpha descending
        benchmark_list.sort(key=lambda x: x['alpha'], reverse=True)

        response = {
            'portfolio_id': portfolio_id,
            'period': period,
            'portfolio_return': portfolio_return,
            'benchmarks': benchmark_list,
            'fetched_at': datetime.now().isoformat()
        }

        logger.info(f"Found {len(benchmark_list)} benchmark comparisons for period {period}")
        return response

    except Exception as e:
        logger.error(f"Error fetching benchmark data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manager-updates/{portfolio_id}")
async def get_manager_updates(
    portfolio_id: int,
    status: Optional[str] = Query(None, pattern="^(PENDING|EXECUTED|IGNORED)$"),
    priority: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Get portfolio manager daily updates and recommendations

    Args:
        portfolio_id: Portfolio ID
        status: Filter by status (optional)
        priority: Filter by priority (optional)
        limit: Maximum number of updates to return

    Returns:
        List of manager updates with recommendations
    """
    try:
        logger.info(f"Fetching manager updates for portfolio {portfolio_id}")

        updates = db.get_manager_updates(
            portfolio_id=portfolio_id,
            status=status,
            priority=priority,
            limit=limit
        )

        if not updates:
            logger.info(f"No manager updates found for portfolio {portfolio_id}")
            return {
                'portfolio_id': portfolio_id,
                'updates': [],
                'message': 'No updates available. Manager updates will be generated during scheduled runs.'
            }

        # Group updates by date for easier display
        updates_by_date = {}
        for update in updates:
            update_date = update['update_date']
            if update_date not in updates_by_date:
                updates_by_date[update_date] = []
            updates_by_date[update_date].append(update)

        response = {
            'portfolio_id': portfolio_id,
            'total_updates': len(updates),
            'updates': updates,
            'updates_by_date': updates_by_date,
            'fetched_at': datetime.now().isoformat()
        }

        logger.info(f"Found {len(updates)} manager updates")
        return response

    except Exception as e:
        logger.error(f"Error fetching manager updates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prices/update")
async def trigger_price_update(portfolio_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Manually trigger price update for portfolio(s)

    Args:
        portfolio_id: Specific portfolio ID (if None, updates all active portfolios)

    Returns:
        Update summary with success/failure counts
    """
    try:
        logger.info(f"Manual price update triggered for portfolio_id={portfolio_id or 'ALL'}")

        today = date.today()
        results = []

        # Determine which portfolios to update
        if portfolio_id:
            portfolio_ids = [portfolio_id]
        else:
            portfolios = db.execute_query("SELECT id FROM portfolios WHERE is_active = 1")
            portfolio_ids = [p['id'] for p in portfolios]

        if not portfolio_ids:
            return {
                'success': False,
                'message': 'No active portfolios found',
                'results': []
            }

        # Update each portfolio
        for pid in portfolio_ids:
            try:
                # Update stock prices
                stock_result = price_fetcher.update_portfolio_prices(pid, today)

                # Update index prices
                index_result = price_fetcher.update_index_prices(price_date=today)

                # Generate snapshot
                snapshot = perf_calculator.generate_portfolio_snapshot(pid, today)

                # Update benchmarks
                comparisons = perf_calculator.update_benchmark_comparisons(pid, today)

                results.append({
                    'portfolio_id': pid,
                    'success': True,
                    'stocks_updated': stock_result['success'],
                    'stocks_total': stock_result['total'],
                    'indices_updated': index_result['success'],
                    'indices_total': index_result['total'],
                    'snapshot_created': snapshot is not None,
                    'comparisons_updated': len(comparisons)
                })

            except Exception as e:
                logger.error(f"Failed to update portfolio {pid}: {e}")
                results.append({
                    'portfolio_id': pid,
                    'success': False,
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])

        response = {
            'success': success_count > 0,
            'portfolios_updated': success_count,
            'portfolios_total': len(portfolio_ids),
            'results': results,
            'updated_at': datetime.now().isoformat()
        }

        logger.info(f"Price update complete: {success_count}/{len(portfolio_ids)} portfolios updated")
        return response

    except Exception as e:
        logger.error(f"Error during price update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk-metrics/{portfolio_id}")
async def get_risk_metrics(
    portfolio_id: int,
    period_days: int = Query(90, ge=7, le=365)
) -> Dict[str, Any]:
    """
    Get detailed risk metrics for portfolio

    Args:
        portfolio_id: Portfolio ID
        period_days: Period for calculation (default 90 days)

    Returns:
        Volatility, Sharpe ratio, max drawdown, and other risk metrics
    """
    try:
        logger.info(f"Calculating risk metrics for portfolio {portfolio_id}, period={period_days} days")

        # Calculate metrics
        volatility = perf_calculator.calculate_volatility(portfolio_id, period_days)
        sharpe_ratio = perf_calculator.calculate_sharpe_ratio(portfolio_id, period_days)
        max_drawdown = perf_calculator.calculate_max_drawdown(portfolio_id, period_days)

        # Get returns for the period
        returns = perf_calculator.calculate_returns(portfolio_id)

        response = {
            'portfolio_id': portfolio_id,
            'period_days': period_days,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'annualized_return': returns.get('annualized_return', 0),
            'total_return_pct': returns.get('total_return_pct', 0),
            'calculated_at': datetime.now().isoformat()
        }

        logger.info(f"Risk metrics: Volatility={volatility:.2f}%, Sharpe={sharpe_ratio:.2f}, Drawdown={max_drawdown:.2f}%")
        return response

    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/price-history/{stock_id}")
async def get_stock_price_history(
    stock_id: int,
    days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """
    Get historical price data for a stock

    Args:
        stock_id: Stock ID
        days: Number of days of history (default 30)

    Returns:
        Array of OHLCV price data
    """
    try:
        logger.info(f"Fetching price history for stock {stock_id}, {days} days")

        prices = db.get_stock_price_history(stock_id, limit=days)

        if not prices:
            raise HTTPException(
                status_code=404,
                detail=f"No price history found for stock {stock_id}"
            )

        response = {
            'stock_id': stock_id,
            'prices': prices,
            'count': len(prices),
            'fetched_at': datetime.now().isoformat()
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn

    logger.info("Starting Portfolio Agent API server...")
    logger.info("API will be available at: http://localhost:8000")
    logger.info("API documentation: http://localhost:8000/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
