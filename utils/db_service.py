"""
Database Service for Portfolio Storage
Manages Supabase PostgreSQL database connections and operations
"""

import json
import os
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
import sys

from supabase import create_client, Client

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger

logger = get_logger("utils.db_service")


class DatabaseService:
    """Manages Supabase PostgreSQL database for portfolio storage"""

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize database service

        Args:
            supabase_url: Supabase project URL (defaults to env var SUPABASE_URL)
            supabase_key: Supabase API key (defaults to env var SUPABASE_API_KEY)
        """
        # Get credentials from env if not provided
        url = supabase_url or os.getenv('SUPABASE_URL')
        key = supabase_key or os.getenv('SUPABASE_API_KEY')

        if not url or not key:
            raise ValueError(
                "Supabase credentials required. Set SUPABASE_URL and SUPABASE_API_KEY env vars "
                "or pass them to constructor."
            )

        self.client: Client = create_client(url, key)
        logger.info(f"Connected to Supabase database: {url}")

    # ==================== Portfolio Operations ====================

    def save_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        profile: str,
        timestamp: str,
        json_path: Optional[str] = None,
        cash_balance: float = 0.0
    ) -> int:
        """
        Save portfolio metadata to database

        Args:
            portfolio_data: Portfolio dict with 'stocks' and metadata
            profile: Investor profile ('aggressive', 'moderate', or 'defensive')
            timestamp: Timestamp string (YYYYMMDD_HHMMSS)
            json_path: Path to JSON file
            cash_balance: Unallocated cash remaining after share purchases

        Returns:
            portfolio_id
        """
        total_capital = portfolio_data.get('total_capital', 0)

        # Deactivate previous portfolios with same profile
        self.client.table('portfolios').update({'is_active': False}).eq('profile', profile).eq('is_active', True).execute()

        # Insert new portfolio
        response = self.client.table('portfolios').insert({
            'profile': profile,
            'total_capital': total_capital,
            'timestamp': timestamp,
            'json_path': json_path,
            'is_active': True,
            'cash_balance': cash_balance
        }).execute()

        portfolio_id = response.data[0]['id']
        logger.info(f"Saved portfolio {portfolio_id} ({profile}, {timestamp}, cash: Rs. {cash_balance:,.2f})")

        # Create initial snapshot
        try:
            # Parse timestamp to date
            creation_date = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").date()
            
            # Initial metrics (all zero except balance)
            initial_metrics = {
                'cash_balance': total_capital,
                'invested_value': 0.0,
                'total_return_pct': 0.0,
                'total_return_absolute': 0.0,
                'day_return_pct': 0.0,
                'day_return_absolute': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'num_stocks': 0,
                'avg_allocation_pct': 0.0
            }
            
            self.store_portfolio_snapshot(
                portfolio_id=portfolio_id,
                snapshot_date=creation_date,
                total_value=total_capital,
                metrics=initial_metrics
            )
            logger.info(f"Created initial snapshot for portfolio {portfolio_id} on {creation_date}")
            
        except Exception as e:
            logger.error(f"Failed to create initial snapshot: {e}")

        return portfolio_id

    def get_active_portfolio(self, profile: str) -> Optional[Dict[str, Any]]:
        """Get active portfolio for a profile"""
        response = self.client.table('portfolios')\
            .select('*')\
            .eq('profile', profile)\
            .eq('is_active', True)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()

        return response.data[0] if response.data else None

    def get_portfolio_by_id(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        """Get portfolio by ID"""
        response = self.client.table('portfolios')\
            .select('*')\
            .eq('id', portfolio_id)\
            .execute()

        return response.data[0] if response.data else None

    def get_all_portfolios(self) -> List[Dict[str, Any]]:
        """Get all portfolios ordered by creation date (newest first)"""
        response = self.client.table('portfolios')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()

        return response.data if response.data else []

    # ==================== Stock Operations ====================

    def save_stocks(self, portfolio_id: int, stocks_data: List[Dict[str, Any]]) -> List[int]:
        """
        Save stocks from portfolio

        Args:
            portfolio_id: Portfolio ID
            stocks_data: List of stock dicts from portfolio

        Returns:
            List of stock IDs
        """
        stock_ids = []

        for stock in stocks_data:
            # Insert stock
            response = self.client.table('stocks').insert({
                'portfolio_id': portfolio_id,
                'name': stock.get('name'),
                'ticker': stock.get('ticker'),
                'sector': stock.get('sector'),
                'entry_price': stock.get('entry_price'),
                'allocation_pct': stock.get('allocation_pct'),
                'allocation_amount': stock.get('allocation_amount'),
                'shares': stock.get('shares'),
                'stop_loss_pct': stock.get('stop_loss_pct'),
                'stop_loss_price': stock.get('stop_loss_price'),
                'target_pct': stock.get('target_pct'),
                'target_price': stock.get('target_price'),
                'rationale': stock.get('rationale'),
                'news_sentiment': stock.get('news_sentiment')
            }).execute()

            stock_id = response.data[0]['id']
            stock_ids.append(stock_id)

            # Save investment view
            investment_view = stock.get('investment_view', {})
            if investment_view:
                self._save_investment_view(stock_id, investment_view)

            # Save key metrics
            key_metrics = stock.get('key_metrics', {})
            if key_metrics:
                self._save_key_metrics(stock_id, key_metrics)

        logger.info(f"Saved {len(stock_ids)} stocks for portfolio {portfolio_id}")

        return stock_ids

    def get_portfolio_stocks(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """Get all stocks for a portfolio with investment views and current prices"""
        from datetime import date

        # Get stocks
        response = self.client.table('stocks')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)\
            .order('allocation_pct', desc=True)\
            .execute()

        stocks = response.data
        today = date.today().isoformat()

        # Enrich with investment views and current prices
        for stock in stocks:
            # Get investment view
            view_response = self.client.table('investment_views')\
                .select('*')\
                .eq('stock_id', stock['id'])\
                .execute()

            if view_response.data:
                view = view_response.data[0]
                stock['market_outlook'] = view.get('market_outlook')
                stock['stock_rationale'] = view.get('stock_rationale')
                stock['holding_period'] = view.get('holding_period')
                stock['exit_triggers'] = view.get('exit_triggers')
                stock['review_triggers'] = view.get('review_triggers')

            # Get current price from daily_prices (today's close price)
            price_response = self.client.table('daily_prices')\
                .select('close_price')\
                .eq('stock_id', stock['id'])\
                .eq('price_date', today)\
                .execute()

            if price_response.data:
                stock['current_price'] = price_response.data[0]['close_price']
            else:
                # Fallback to entry_price if no daily price available
                stock['current_price'] = stock.get('entry_price')

        return stocks

    def get_stock_by_id(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """Get stock by ID"""
        response = self.client.table('stocks')\
            .select('*')\
            .eq('id', stock_id)\
            .execute()

        return response.data[0] if response.data else None

    def get_stock_by_ticker(self, ticker: str, portfolio_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get stock by ticker"""
        query = self.client.table('stocks').select('*').eq('ticker', ticker)

        if portfolio_id:
            query = query.eq('portfolio_id', portfolio_id)
        else:
            query = query.order('added_at', desc=True).limit(1)

        response = query.execute()
        return response.data[0] if response.data else None

    def update_stock_ticker(self, stock_id: int, new_ticker: str, new_exchange: str) -> None:
        """
        Update ticker and exchange for a stock

        Args:
            stock_id: Stock ID to update
            new_ticker: Corrected ticker symbol
            new_exchange: Corrected exchange ('NSE' or 'BSE')
        """
        self.client.table('stocks').update({
            'ticker': new_ticker,
            'exchange': new_exchange
        }).eq('id', stock_id).execute()

        logger.info(f"Updated stock_id={stock_id}: ticker={new_ticker}, exchange={new_exchange}")

    # ==================== Investment View Operations ====================

    def _save_investment_view(self, stock_id: int, investment_view: Dict[str, Any]):
        """Save investment view for a stock"""
        self.client.table('investment_views').insert({
            'stock_id': stock_id,
            'market_outlook': investment_view.get('market_outlook'),
            'stock_rationale': investment_view.get('stock_rationale'),
            'holding_period': investment_view.get('holding_period'),
            'exit_triggers': json.dumps(investment_view.get('exit_triggers', [])),
            'review_triggers': json.dumps(investment_view.get('review_triggers', []))
        }).execute()

    def get_investment_view(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """Get investment view for a stock"""
        response = self.client.table('investment_views')\
            .select('*')\
            .eq('stock_id', stock_id)\
            .execute()

        if response.data:
            result = response.data[0]
            # Parse JSON arrays
            result['exit_triggers'] = json.loads(result['exit_triggers'])
            result['review_triggers'] = json.loads(result['review_triggers'])
            return result

        return None

    # ==================== Key Metrics Operations ====================

    def _save_key_metrics(self, stock_id: int, key_metrics: Dict[str, Any]):
        """Save key metrics for a stock"""
        self.client.table('key_metrics').insert({
            'stock_id': stock_id,
            'metrics_json': json.dumps(key_metrics)
        }).execute()

    def get_key_metrics(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """Get key metrics for a stock"""
        response = self.client.table('key_metrics')\
            .select('*')\
            .eq('stock_id', stock_id)\
            .execute()

        if response.data:
            result = response.data[0]
            result['metrics_json'] = json.loads(result['metrics_json'])
            return result

        return None

    # ==================== Transaction Operations ====================

    def record_transaction(
        self,
        portfolio_id: int,
        stock_id: int,
        transaction_type: str,  # 'BUY' or 'SELL'
        quantity: int,
        price: float,
        transaction_date: datetime,
        notes: Optional[str] = None,
        realized_pnl_pct: Optional[float] = None,
        realized_pnl_absolute: Optional[float] = None,
        trigger_type: Optional[str] = None
    ) -> int:
        """Record a buy/sell transaction"""
        total_amount = quantity * price

        transaction_data = {
            'portfolio_id': portfolio_id,
            'stock_id': stock_id,
            'transaction_type': transaction_type,
            'quantity': quantity,
            'price': price,
            'total_amount': total_amount,
            'transaction_date': transaction_date.isoformat(),
            'notes': notes
        }

        # Add optional fields if provided
        if realized_pnl_pct is not None:
            transaction_data['realized_pnl_pct'] = realized_pnl_pct
        if realized_pnl_absolute is not None:
            transaction_data['realized_pnl_absolute'] = realized_pnl_absolute
        if trigger_type is not None:
            transaction_data['trigger_type'] = trigger_type

        response = self.client.table('transactions').insert(transaction_data).execute()

        transaction_id = response.data[0]['id']
        logger.info(f"Recorded {transaction_type} transaction {transaction_id}")

        return transaction_id

    def get_transactions(
        self,
        portfolio_id: Optional[int] = None,
        stock_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get transactions with optional filters"""
        query = self.client.table('transactions').select('*')

        if portfolio_id:
            query = query.eq('portfolio_id', portfolio_id)

        if stock_id:
            query = query.eq('stock_id', stock_id)

        if start_date:
            query = query.gte('transaction_date', start_date.isoformat())

        if end_date:
            query = query.lte('transaction_date', end_date.isoformat())

        response = query.order('transaction_date', desc=True).execute()
        return response.data

    # ==================== Performance Metrics Operations ====================

    def record_performance(
        self,
        portfolio_id: int,
        metric_date: date,
        portfolio_value: Optional[float] = None,
        stock_id: Optional[int] = None,
        stock_value: Optional[float] = None,
        daily_return_pct: Optional[float] = None,
        cumulative_return_pct: Optional[float] = None,
        status: Optional[str] = None
    ) -> int:
        """Record performance metrics (upsert based on unique constraint)"""
        response = self.client.table('performance_metrics').upsert({
            'portfolio_id': portfolio_id,
            'stock_id': stock_id,
            'metric_date': metric_date.isoformat(),
            'portfolio_value': portfolio_value,
            'stock_value': stock_value,
            'daily_return_pct': daily_return_pct,
            'cumulative_return_pct': cumulative_return_pct,
            'status': status
        }).execute()

        return response.data[0]['id']

    def get_performance_history(
        self,
        portfolio_id: int,
        stock_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get performance history"""
        query = self.client.table('performance_metrics')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)

        if stock_id:
            query = query.eq('stock_id', stock_id)
        else:
            query = query.is_('stock_id', 'null')

        if start_date:
            query = query.gte('metric_date', start_date.isoformat())

        if end_date:
            query = query.lte('metric_date', end_date.isoformat())

        response = query.order('metric_date', desc=False).execute()
        return response.data

    # ==================== Rebalancing History Operations ====================

    def record_rebalancing(
        self,
        portfolio_id: int,
        rebalancing_date: datetime,
        reason: str,
        action_type: str,  # 'ADJUSTMENT', 'ROTATION', 'EXIT'
        affected_stocks: List[str],  # List of tickers
        allocation_changes: Dict[str, Tuple[float, float]],  # ticker -> (old_pct, new_pct)
        expected_result: Optional[str] = None
    ) -> int:
        """Record a rebalancing action"""
        response = self.client.table('rebalancing_history').insert({
            'portfolio_id': portfolio_id,
            'rebalancing_date': rebalancing_date.isoformat(),
            'reason': reason,
            'action_type': action_type,
            'affected_stocks': json.dumps(affected_stocks),
            'allocation_changes': json.dumps(allocation_changes),
            'expected_result': expected_result
        }).execute()

        rebalancing_id = response.data[0]['id']
        logger.info(f"Recorded rebalancing action {rebalancing_id}")

        return rebalancing_id

    def get_rebalancing_history(
        self,
        portfolio_id: int,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get rebalancing history"""
        query = self.client.table('rebalancing_history')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)

        if status:
            query = query.eq('status', status)

        query = query.order('rebalancing_date', desc=True)

        if limit:
            query = query.limit(limit)

        response = query.execute()
        result = response.data

        # Parse JSON fields
        for row in result:
            row['affected_stocks'] = json.loads(row['affected_stocks'])
            row['allocation_changes'] = json.loads(row['allocation_changes'])

        return result

    # ==================== Market Events Operations ====================

    def record_market_event(
        self,
        event_type: str,
        title: str,
        description: str,
        event_date: datetime,
        portfolio_id: Optional[int] = None,
        stock_id: Optional[int] = None,
        impact: Optional[str] = None,
        action_taken: Optional[str] = None,
        source: Optional[str] = None
    ) -> int:
        """Record a market event"""
        response = self.client.table('market_events').insert({
            'portfolio_id': portfolio_id,
            'stock_id': stock_id,
            'event_type': event_type,
            'title': title,
            'description': description,
            'impact': impact,
            'action_taken': action_taken,
            'event_date': event_date.isoformat(),
            'source': source
        }).execute()

        event_id = response.data[0]['id']
        logger.info(f"Recorded market event {event_id}")

        return event_id

    def get_market_events(
        self,
        portfolio_id: Optional[int] = None,
        stock_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get market events with optional filters"""
        query = self.client.table('market_events').select('*')

        if portfolio_id:
            query = query.eq('portfolio_id', portfolio_id)

        if stock_id:
            query = query.eq('stock_id', stock_id)

        if start_date:
            query = query.gte('event_date', start_date.isoformat())

        if end_date:
            query = query.lte('event_date', end_date.isoformat())

        if event_type:
            query = query.eq('event_type', event_type)

        response = query.order('event_date', desc=True).execute()
        return response.data

    # ==================== Query Helpers ====================

    def portfolio_summary(self, portfolio_id: int) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        # Portfolio info
        portfolio = self.get_portfolio_by_id(portfolio_id)

        # Stocks info
        stocks = self.get_portfolio_stocks(portfolio_id)

        # Recent transactions
        transactions_response = self.client.table('transactions')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)\
            .order('transaction_date', desc=True)\
            .limit(10)\
            .execute()
        recent_transactions = transactions_response.data

        # Rebalancing history
        rebalancing = self.get_rebalancing_history(portfolio_id, limit=5)

        return {
            'portfolio': portfolio,
            'stocks': stocks,
            'recent_transactions': recent_transactions,
            'rebalancing_history': rebalancing,
            'stock_count': len(stocks),
            'total_allocation': sum(s['allocation_pct'] for s in stocks)
        }

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query for custom queries

        Note: For Supabase, use postgrest client methods instead of raw SQL when possible.
        This method uses Supabase SQL RPC for complex queries not supported by PostgREST.
        """
        # For complex queries, we'd need to use Supabase's RPC function
        # For now, log a warning that this is not directly supported
        logger.warning("Raw SQL execution not directly supported in Supabase client. Use PostgREST methods instead.")
        raise NotImplementedError("Use PostgREST methods (.select(), .insert(), etc.) instead of raw SQL")

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """
        Execute raw SQL update/delete query

        Note: For Supabase, use postgrest client methods instead of raw SQL when possible.
        """
        logger.warning("Raw SQL execution not directly supported in Supabase client. Use PostgREST methods instead.")
        raise NotImplementedError("Use PostgREST methods (.update(), .delete(), etc.) instead of raw SQL")

    # ==================== Daily Price Operations ====================

    def store_daily_price(
        self,
        stock_id: int,
        price_date: date,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: Optional[int] = None
    ) -> int:
        """
        Store daily price snapshot for a stock (upsert based on unique constraint)

        Args:
            stock_id: Stock ID from stocks table
            price_date: Date of price data
            open_price, high_price, low_price, close_price: OHLC prices
            volume: Trading volume

        Returns:
            ID of inserted/updated record
        """
        response = self.client.table('daily_prices').upsert({
            'stock_id': stock_id,
            'price_date': price_date.isoformat(),
            'open_price': open_price,
            'high_price': high_price,
            'low_price': low_price,
            'close_price': close_price,
            'volume': volume
        }, on_conflict='stock_id,price_date').execute()

        logger.debug(f"Stored daily price for stock_id {stock_id} on {price_date}")
        return response.data[0]['id']

    def get_stock_price_history(
        self,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get price history for a stock

        Args:
            stock_id: Stock ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Optional limit on number of records

        Returns:
            List of price records ordered by date descending
        """
        query = self.client.table('daily_prices')\
            .select('*')\
            .eq('stock_id', stock_id)

        if start_date:
            query = query.gte('price_date', start_date.isoformat())

        if end_date:
            query = query.lte('price_date', end_date.isoformat())

        query = query.order('price_date', desc=True)

        if limit:
            query = query.limit(limit)

        response = query.execute()
        return response.data

    def get_latest_stock_price(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """Get most recent price for a stock"""
        prices = self.get_stock_price_history(stock_id, limit=1)
        return prices[0] if prices else None

    # ==================== Index Price Operations ====================

    def store_index_price(
        self,
        index_symbol: str,
        index_name: str,
        price_date: date,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: Optional[int] = None
    ) -> int:
        """Store daily price for a market index (upsert based on unique constraint)"""
        response = self.client.table('index_prices').upsert(
            {
                'index_symbol': index_symbol,
                'index_name': index_name,
                'price_date': price_date.isoformat(),
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': close_price,
                'volume': volume
            },
            on_conflict='index_symbol,price_date'  # Specify unique constraint columns
        ).execute()

        logger.debug(f"Stored index price for {index_symbol} on {price_date}")
        return response.data[0]['id']

    def get_index_price_history(
        self,
        index_symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get price history for an index"""
        query = self.client.table('index_prices')\
            .select('*')\
            .eq('index_symbol', index_symbol)

        if start_date:
            query = query.gte('price_date', start_date.isoformat())

        if end_date:
            query = query.lte('price_date', end_date.isoformat())

        query = query.order('price_date', desc=True)

        if limit:
            query = query.limit(limit)

        response = query.execute()
        return response.data

    def get_index_price_on_or_before(
        self,
        index_symbol: str,
        target_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest index price on or before target_date.
        Searches backward up to 15 days to handle weekends/holidays.

        Args:
            index_symbol: Index symbol (e.g., '^NSEI')
            target_date: Target date to search from

        Returns:
            Price record dict or None if no data within 15 days
        """
        from datetime import timedelta

        search_start = target_date - timedelta(days=15)

        response = self.client.table('index_prices')\
            .select('*')\
            .eq('index_symbol', index_symbol)\
            .gte('price_date', search_start.isoformat())\
            .lte('price_date', target_date.isoformat())\
            .order('price_date', desc=True)\
            .limit(1)\
            .execute()

        if response.data:
            found_date = response.data[0]['price_date']
            if isinstance(found_date, str):
                found_date = datetime.fromisoformat(found_date).date()

            days_diff = (target_date - found_date).days
            logger.debug(f"Found {index_symbol} on {found_date} ({days_diff}d before {target_date})")
            return response.data[0]
        else:
            logger.warning(f"No {index_symbol} data within 15 days before {target_date}")
            return None

    def get_latest_index_price(self, index_symbol: str) -> Optional[Dict[str, Any]]:
        """Get most recent price for an index"""
        prices = self.get_index_price_history(index_symbol, limit=1)
        return prices[0] if prices else None

    # ==================== Portfolio Snapshot Operations ====================

    def store_portfolio_snapshot(
        self,
        portfolio_id: int,
        snapshot_date: date,
        total_value: float,
        metrics: Dict[str, float]
    ) -> int:
        """
        Store daily portfolio snapshot (upsert based on unique constraint)

        Args:
            portfolio_id: Portfolio ID
            snapshot_date: Date of snapshot
            total_value: Current portfolio value
            metrics: Dict with keys: invested_value, total_return_pct, total_return_absolute,
                     day_return_pct, day_return_absolute, volatility, sharpe_ratio,
                     max_drawdown, num_stocks, avg_allocation_pct
        """
        response = self.client.table('portfolio_snapshots').upsert({
            'portfolio_id': portfolio_id,
            'snapshot_date': snapshot_date.isoformat(),
            'total_value': total_value,
            'cash_balance': metrics.get('cash_balance', 0),
            'invested_value': metrics.get('invested_value', 0),
            'total_return_pct': metrics.get('total_return_pct', 0),
            'total_return_absolute': metrics.get('total_return_absolute', 0),
            'day_return_pct': metrics.get('day_return_pct', 0),
            'day_return_absolute': metrics.get('day_return_absolute', 0),
            'volatility': metrics.get('volatility', 0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
            'num_stocks': metrics.get('num_stocks', 0),
            'avg_allocation_pct': metrics.get('avg_allocation_pct', 0)
        }, on_conflict='portfolio_id,snapshot_date').execute()

        logger.info(f"Stored portfolio snapshot for portfolio {portfolio_id} on {snapshot_date}")
        return response.data[0]['id']

    def get_portfolio_snapshots(
        self,
        portfolio_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get portfolio snapshots for a date range"""
        query = self.client.table('portfolio_snapshots')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)

        if start_date:
            query = query.gte('snapshot_date', start_date.isoformat())

        if end_date:
            query = query.lte('snapshot_date', end_date.isoformat())

        query = query.order('snapshot_date', desc=True)

        if limit:
            query = query.limit(limit)

        response = query.execute()
        return response.data

    def get_latest_portfolio_snapshot(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        """Get most recent portfolio snapshot"""
        snapshots = self.get_portfolio_snapshots(portfolio_id, limit=1)
        return snapshots[0] if snapshots else None

    # ==================== Benchmark Comparison Operations ====================

    def store_benchmark_comparison(
        self,
        portfolio_id: int,
        comparison_date: date,
        index_symbol: str,
        index_name: str,
        portfolio_return: float,
        index_return: float,
        period: str = 'ALL',
        alpha: Optional[float] = None,
        beta: Optional[float] = None
    ) -> int:
        """Store benchmark comparison data (upsert based on unique constraint)"""
        if alpha is None and index_return is not None:
            alpha = portfolio_return - index_return

        outperformance = alpha if alpha is not None else None

        response = self.client.table('benchmark_comparison').upsert(
            {
                'portfolio_id': portfolio_id,
                'comparison_date': comparison_date.isoformat(),
                'index_symbol': index_symbol,
                'index_name': index_name,
                'portfolio_return': portfolio_return,
                'index_return': index_return,
                'alpha': alpha,
                'beta': beta,
                'outperformance': outperformance,
                'period': period
            },
            on_conflict='portfolio_id,index_symbol,comparison_date,period'  # Specify unique constraint
        ).execute()

        logger.debug(f"Stored benchmark comparison: Portfolio {portfolio_id} vs {index_symbol}")
        return response.data[0]['id']

    def get_benchmark_comparisons(
        self,
        portfolio_id: int,
        comparison_date: Optional[date] = None,
        period: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get benchmark comparison data - returns only latest comparison_date"""

        # If no specific date provided, get the latest comparison_date
        if not comparison_date:
            latest_query = self.client.table('benchmark_comparison')\
                .select('comparison_date')\
                .eq('portfolio_id', portfolio_id)\
                .order('comparison_date', desc=True)\
                .limit(1)\
                .execute()

            if latest_query.data:
                comparison_date = latest_query.data[0]['comparison_date']

        # Now query with the specific date
        query = self.client.table('benchmark_comparison')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)

        if comparison_date:
            # Convert to string if it's a date object
            if isinstance(comparison_date, date):
                query = query.eq('comparison_date', comparison_date.isoformat())
            else:
                query = query.eq('comparison_date', comparison_date)

        if period:
            query = query.eq('period', period)

        response = query.order('index_symbol').execute()
        return response.data

    # ==================== Manager Update Operations ====================

    def store_manager_update(
        self,
        portfolio_id: int,
        update_date: date,
        update_type: str,
        title: str,
        description: str,
        affected_stocks: Optional[List[str]] = None,
        affected_sectors: Optional[List[str]] = None,
        recommendation: Optional[str] = None,
        reasoning: Optional[str] = None,
        priority: str = 'MEDIUM'
    ) -> int:
        """
        Store portfolio manager daily update

        Args:
            portfolio_id: Portfolio ID
            update_date: Date of update
            update_type: 'DAILY_REVIEW', 'SIGNAL_GENERATED', 'DECISION_MADE'
            title: Update title
            description: Detailed description
            affected_stocks: List of ticker symbols
            affected_sectors: List of sectors
            recommendation: 'HOLD', 'BUY_MORE', 'SELL', 'REBALANCE', None
            reasoning: AI agent reasoning
            priority: 'LOW', 'MEDIUM', 'HIGH', 'URGENT'
        """
        response = self.client.table('manager_updates').insert({
            'portfolio_id': portfolio_id,
            'update_date': update_date.isoformat(),
            'update_type': update_type,
            'title': title,
            'description': description,
            'affected_stocks': json.dumps(affected_stocks) if affected_stocks else None,
            'affected_sectors': json.dumps(affected_sectors) if affected_sectors else None,
            'recommendation': recommendation,
            'reasoning': reasoning,
            'priority': priority
        }).execute()

        logger.info(f"Stored manager update: {title} ({update_type})")
        return response.data[0]['id']

    def get_manager_updates(
        self,
        portfolio_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get manager updates with optional filters

        Args:
            portfolio_id: Portfolio ID
            status: Filter by status ('PENDING', 'ACKNOWLEDGED', 'EXECUTED', 'IGNORED')
            priority: Filter by priority
            limit: Maximum number of records
        """
        query = self.client.table('manager_updates')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)

        if status:
            query = query.eq('status', status)

        if priority:
            query = query.eq('priority', priority)

        response = query.order('update_date', desc=True).order('priority', desc=True).limit(limit).execute()
        results = response.data

        # Parse JSON fields
        for result in results:
            if result.get('affected_stocks'):
                result['affected_stocks'] = json.loads(result['affected_stocks'])
            if result.get('affected_sectors'):
                result['affected_sectors'] = json.loads(result['affected_sectors'])

        return results

    def update_manager_update_status(
        self,
        update_id: int,
        status: str,
        user_decision: Optional[str] = None,
        user_notes: Optional[str] = None
    ) -> int:
        """Update status of a manager update"""
        executed_at = datetime.now().isoformat() if status == 'EXECUTED' else None

        response = self.client.table('manager_updates').update({
            'status': status,
            'user_decision': user_decision,
            'user_notes': user_notes,
            'executed_at': executed_at
        }).eq('id', update_id).execute()

        logger.info(f"Updated manager update {update_id} status to {status}")
        return len(response.data)

    # ==================== User Preferences Operations ====================

    def get_user_benchmarks(self, portfolio_id: int, primary_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get user's selected benchmark indices

        Args:
            portfolio_id: Portfolio ID
            primary_only: If True, return only primary benchmarks (top 3 for dashboard)
        """
        query = self.client.table('user_benchmark_preferences')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)\
            .eq('enabled', True)

        if primary_only:
            query = query.eq('is_primary', True)

        response = query.order('display_order', desc=False).execute()
        return response.data

    def set_primary_benchmarks(
        self,
        portfolio_id: int,
        index_symbols: List[str]
    ) -> int:
        """
        Set primary benchmarks for dashboard display

        Args:
            portfolio_id: Portfolio ID
            index_symbols: List of up to 3 index symbols to set as primary
        """
        # Reset all to non-primary
        self.client.table('user_benchmark_preferences').update({
            'is_primary': False
        }).eq('portfolio_id', portfolio_id).execute()

        # Set selected as primary with display order
        updated_count = 0
        for idx, symbol in enumerate(index_symbols[:3], start=1):
            response = self.client.table('user_benchmark_preferences').update({
                'is_primary': True,
                'display_order': idx
            }).eq('portfolio_id', portfolio_id).eq('index_symbol', symbol).execute()

            updated_count += len(response.data)

        logger.info(f"Set primary benchmarks for portfolio {portfolio_id}: {index_symbols}")
        return updated_count


    def get_benchmark_history(
        self,
        portfolio_id: int,
        index_symbol: str = '^NSEI',
        limit: int = 365
    ) -> List[Dict[str, Any]]:
        """
        Get daily benchmark comparison history from the view

        Args:
            portfolio_id: Portfolio ID
            index_symbol: Index symbol (default '^NSEI')
            limit: Max days to return (default 365)
        """
        response = self.client.table('portfolio_benchmark_history')\
            .select('*')\
            .eq('portfolio_id', portfolio_id)\
            .eq('index_symbol', index_symbol)\
            .order('comparison_date', desc=False)\
            .limit(limit)\
            .execute()
        
        return response.data


# Singleton instance
_db_service = None


def get_db_service(supabase_url: str = None, supabase_key: str = None) -> DatabaseService:
    """
    Get or create database service singleton

    Args:
        supabase_url: Supabase project URL (defaults to env var)
        supabase_key: Supabase API key (defaults to env var)
    """
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService(supabase_url, supabase_key)
    return _db_service
