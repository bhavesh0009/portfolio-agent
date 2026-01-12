"""
FastAPI Backend Service for Portfolio Dashboard
Provides REST API endpoints for performance metrics, benchmarks, and manager updates
"""

from fastapi import FastAPI, HTTPException, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    allow_origins=["*"],  # Allow all origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Disable caching middleware - prevents browser from caching API responses
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Add cache-control headers to prevent browser caching of API responses"""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

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


@app.get("/api/portfolios")
async def get_all_portfolios() -> List[Dict[str, Any]]:
    """
    Get list of all portfolios

    Returns:
        List of all portfolios ordered by created_at (newest first)
    """
    try:
        logger.info("Fetching all portfolios")

        portfolios = db.get_all_portfolios()

        logger.info(f"Found {len(portfolios)} portfolios")
        return portfolios

    except Exception as e:
        logger.error(f"Error fetching portfolios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolios/active")
async def get_active_portfolio(
    profile: str = Query(None, pattern="^(aggressive|moderate|defensive)$")
) -> Dict[str, Any]:
    """
    Get active portfolio (always returns latest active portfolio)

    Args:
        profile: DEPRECATED - Ignored, always returns latest active portfolio

    Returns:
        Active portfolio data or 404 if not found
    """
    try:
        if profile:
            logger.warning(f"Profile parameter '{profile}' is deprecated. Returning latest active portfolio.")

        logger.info("Fetching latest active portfolio")

        # Get all portfolios and find the active one (should be latest)
        all_portfolios = db.get_all_portfolios()

        if not all_portfolios:
            raise HTTPException(
                status_code=404,
                detail="No portfolios found in database"
            )

        # Find active portfolio
        portfolio = next((p for p in all_portfolios if p.get('is_active')), None)

        if not portfolio:
            # Fallback: Use latest by created_at
            logger.warning("No active portfolio found, using latest by created_at")
            all_portfolios.sort(key=lambda p: p.get('created_at', ''), reverse=True)
            portfolio = all_portfolios[0]

        logger.info(f"Found active portfolio: ID={portfolio['id']}, Profile={portfolio.get('profile')}")
        return portfolio

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching active portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolios/{portfolio_id}/stocks")
async def get_portfolio_stocks(portfolio_id: int) -> List[Dict[str, Any]]:
    """
    Get all stocks for a specific portfolio

    Args:
        portfolio_id: Portfolio ID

    Returns:
        List of stocks with investment views and key metrics
    """
    try:
        logger.info(f"Fetching stocks for portfolio {portfolio_id}")

        stocks = db.get_portfolio_stocks(portfolio_id)

        if not stocks:
            logger.warning(f"No stocks found for portfolio {portfolio_id}")
            return []

        # Enrich each stock with properly structured data
        for stock in stocks:
            stock_id = stock['id']

            # Get investment view as nested object
            investment_view = db.get_investment_view(stock_id)
            if investment_view:
                stock['investment_view'] = investment_view

            # Get key metrics with transformed field name
            key_metrics = db.get_key_metrics(stock_id)
            if key_metrics:
                # Transform metrics_json -> metrics for frontend compatibility
                if 'metrics_json' in key_metrics:
                    key_metrics['metrics'] = key_metrics.pop('metrics_json')
                stock['key_metrics'] = key_metrics

        logger.info(f"Found {len(stocks)} stocks for portfolio {portfolio_id}")
        return stocks

    except Exception as e:
        logger.error(f"Error fetching portfolio stocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{stock_id}")
async def get_stock_detail(stock_id: int) -> Dict[str, Any]:
    """
    Get detailed information for a specific stock

    Args:
        stock_id: Stock ID

    Returns:
        Stock data with investment view and key metrics
    """
    try:
        logger.info(f"Fetching stock detail for stock {stock_id}")

        # Get stock data
        stock = db.get_stock_by_id(stock_id)

        if not stock:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {stock_id} not found"
            )

        # Get investment view
        investment_view = db.get_investment_view(stock_id)
        if investment_view:
            stock['investment_view'] = investment_view

        # Get key metrics
        key_metrics = db.get_key_metrics(stock_id)
        if key_metrics:
            # Transform metrics_json -> metrics for frontend compatibility
            if 'metrics_json' in key_metrics:
                key_metrics['metrics'] = key_metrics.pop('metrics_json')
            stock['key_metrics'] = key_metrics

        logger.info(f"Successfully fetched stock detail: {stock.get('name', 'Unknown')}")
        return stock

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolios/{portfolio_id}/stats")
async def get_portfolio_stats(portfolio_id: int) -> Dict[str, Any]:
    """
    Get portfolio statistics and aggregations

    Args:
        portfolio_id: Portfolio ID

    Returns:
        Portfolio stats including total allocation, stock count, sector distribution
    """
    try:
        logger.info(f"Calculating portfolio stats for portfolio {portfolio_id}")

        # Get portfolio
        portfolio = db.get_portfolio_by_id(portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=404,
                detail=f"Portfolio {portfolio_id} not found"
            )

        # Get stocks
        stocks = db.get_portfolio_stocks(portfolio_id)

        if not stocks:
            return {
                'portfolio_id': portfolio_id,
                'total_allocated': 0,
                'stock_count': 0,
                'sector_distribution': {},
                'average_allocation': 0
            }

        # Filter to only active stocks (allocation > 0)
        active_stocks = [s for s in stocks if s.get('allocation_pct', 0) > 0]

        # Calculate stats
        total_allocated = sum(s.get('allocation_amount', 0) for s in active_stocks)
        stock_count = len(active_stocks)
        average_allocation = total_allocated / stock_count if stock_count > 0 else 0
        cash_balance = portfolio.get('cash_balance', 0.0)
        total_value = total_allocated + cash_balance

        # Sector distribution (only active stocks)
        sector_distribution = {}
        for stock in active_stocks:
            sector = stock.get('sector', 'Unknown')
            amount = stock.get('allocation_amount', 0)
            if sector in sector_distribution:
                sector_distribution[sector] += amount
            else:
                sector_distribution[sector] = amount

        response = {
            'portfolio_id': portfolio_id,
            'total_allocated': total_allocated,
            'cash_balance': cash_balance,
            'total_value': total_value,
            'stock_count': stock_count,
            'sector_distribution': sector_distribution,
            'average_allocation': average_allocation,
            'calculated_at': datetime.now().isoformat()
        }

        logger.info(f"Portfolio stats: {stock_count} stocks, Rs. {total_allocated:,.2f} allocated")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating portfolio stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
            'current_value': value_data['current_value'],  # Stock + Cash
            'stocks_value': value_data['stocks_value'],  # Stocks only
            'cash_balance': value_data['cash_balance'],  # Cash portion
            'initial_capital': value_data['initial_capital'],
            'pnl_absolute': value_data['pnl_absolute'],  # Now includes cash
            'pnl_pct': value_data['pnl_pct'],  # Now includes cash
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

        # Filter to only 3 benchmarks: Nifty 50, Sensex, Nifty Midcap 100
        ALLOWED_INDICES = ['^NSEI', '^BSESN', 'NIFTY_MIDCAP_100.NS']

        # Format benchmark data - FILTER to only allowed indices
        benchmark_list = [
            {
                'index_symbol': comp['index_symbol'],
                'index_name': comp['index_name'],
                'index_return': comp['index_return'],
                'alpha': comp['alpha'],
                'outperformance': comp['outperformance']
            }
            for comp in comparisons
            if comp['index_symbol'] in ALLOWED_INDICES
        ]

        # Sort by index order (Nifty 50, Sensex, Midcap) for consistent display
        index_order = {'^NSEI': 1, '^BSESN': 2, 'NIFTY_MIDCAP_100.NS': 3}
        benchmark_list.sort(key=lambda x: index_order.get(x['index_symbol'], 99))

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
            # Get all active portfolios using Supabase client
            portfolios = db.get_all_portfolios()
            portfolio_ids = [p['id'] for p in portfolios if p.get('is_active')]

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


@app.get("/api/portfolio-history/{portfolio_id}")
async def get_portfolio_history(
    portfolio_id: int,
    period: str = Query("ALL", pattern="^(1M|3M|6M|1Y|ALL)$")
) -> Dict[str, Any]:
    """
    Get historical portfolio value snapshots over time

    Args:
        portfolio_id: Portfolio ID
        period: Time period filter ('1M', '3M', '6M', '1Y', 'ALL')

    Returns:
        Array of portfolio snapshots with date, value, and P&L percentage
    """
    try:
        logger.info(f"Fetching portfolio history for portfolio {portfolio_id}, period={period}")

        # Get portfolio to verify it exists
        portfolio = db.get_portfolio_by_id(portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=404,
                detail=f"Portfolio {portfolio_id} not found"
            )

        # Get all snapshots (we'll filter by period if needed)
        snapshots = db.get_portfolio_snapshots(portfolio_id)

        if not snapshots:
            logger.info(f"No snapshot history found for portfolio {portfolio_id}")
            return {
                'portfolio_id': portfolio_id,
                'snapshots': [],
                'count': 0,
                'period': period,
                'fetched_at': datetime.now().isoformat()
            }

        # Transform data to match frontend expectations
        transformed_snapshots = [
            {
                'date': snapshot['snapshot_date'],
                'value': snapshot['total_value'],
                'pnl_pct': snapshot.get('total_return_pct', 0)
            }
            for snapshot in snapshots
        ]

        # Sort by date ascending (oldest first) for charting
        transformed_snapshots.sort(key=lambda x: x['date'])

        # Filter by period if not ALL
        if period != 'ALL':
            from datetime import timedelta

            now = date.today()
            period_map = {
                '1M': 30,
                '3M': 90,
                '6M': 180,
                '1Y': 365
            }
            days_back = period_map.get(period, 0)
            cutoff_date = (now - timedelta(days=days_back)).isoformat()

            transformed_snapshots = [
                s for s in transformed_snapshots
                if s['date'] >= cutoff_date
            ]

        response = {
            'portfolio_id': portfolio_id,
            'snapshots': transformed_snapshots,
            'count': len(transformed_snapshots),
            'period': period,
            'fetched_at': datetime.now().isoformat()
        }

        logger.info(f"Found {len(transformed_snapshots)} snapshots for period {period}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/api/benchmark-history/{portfolio_id}")
async def get_benchmark_history(
    portfolio_id: int,
    index_symbol: str = Query('^NSEI', description="Index symbol to compare against"),
    limit: int = Query(365, description="Number of days to fetch")
) -> Dict[str, Any]:
    """
    Get historical benchmark comparison data
    """
    try:
        history = db.get_benchmark_history(portfolio_id, index_symbol, limit)
        return {
            'portfolio_id': portfolio_id,
            'index_symbol': index_symbol,
            'history': history,
            'fetched_at': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching benchmark history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# Cloud Scheduler Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/scheduler/daily-update")
async def trigger_daily_update(background_tasks: BackgroundTasks):
    """
    Trigger daily price update (scheduled task)
    """
    from scheduler import daily_price_update
    
    logger.info("Received scheduler trigger for daily_price_update")
    background_tasks.add_task(daily_price_update)
    return {"status": "accepted", "message": "Daily price update started in background"}


@app.post("/api/scheduler/portfolio-manager")
async def trigger_portfolio_manager(background_tasks: BackgroundTasks):
    """
    Trigger portfolio manager analysis (scheduled task)
    """
    from scheduler import daily_portfolio_manager
    
    logger.info("Received scheduler trigger for daily_portfolio_manager")
    background_tasks.add_task(daily_portfolio_manager)
    return {"status": "accepted", "message": "Portfolio manager analysis started in background"}


@app.post("/api/scheduler/cleanup")
async def trigger_cleanup(background_tasks: BackgroundTasks):
    """
    Trigger weekly cleanup (scheduled task)
    """
    from scheduler import weekly_cache_cleanup
    
    logger.info("Received scheduler trigger for weekly_cache_cleanup")
    background_tasks.add_task(weekly_cache_cleanup)
    return {"status": "accepted", "message": "Weekly cleanup started in background"}


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
