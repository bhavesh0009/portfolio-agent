"""
Database Service for Portfolio Storage
Manages SQLite database connections and operations
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
import sys
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger

logger = get_logger("utils.db_service")


class DatabaseService:
    """Manages SQLite database for portfolio storage"""

    def __init__(self, db_path: str = ".cache/portfolio.db"):
        """
        Initialize database service

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _initialize_schema(self):
        """Initialize database schema"""
        schema_file = Path(__file__).parent.parent / "db" / "schema.sql"

        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return

        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            logger.info("Database schema initialized")

    # ==================== Portfolio Operations ====================

    def save_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        profile: str,
        timestamp: str,
        json_path: Optional[str] = None
    ) -> int:
        """
        Save portfolio metadata to database

        Args:
            portfolio_data: Portfolio dict with 'stocks' and metadata
            profile: Investor profile ('aggressive' or 'defensive')
            timestamp: Timestamp string (YYYYMMDD_HHMMSS)
            json_path: Path to JSON file

        Returns:
            portfolio_id
        """
        total_capital = portfolio_data.get('total_capital', 0)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Deactivate previous portfolios with same profile
            cursor.execute(
                "UPDATE portfolios SET is_active = 0 WHERE profile = ? AND is_active = 1",
                (profile,)
            )

            # Insert new portfolio
            cursor.execute("""
                INSERT INTO portfolios (profile, total_capital, timestamp, json_path, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (profile, total_capital, timestamp, json_path))

            portfolio_id = cursor.lastrowid
            logger.info(f"Saved portfolio {portfolio_id} ({profile}, {timestamp})")

            return portfolio_id

    def get_active_portfolio(self, profile: str) -> Optional[Dict[str, Any]]:
        """Get active portfolio for a profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM portfolios
                WHERE profile = ? AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 1
            """, (profile,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_portfolio_by_id(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        """Get portfolio by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

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

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for stock in stocks_data:
                cursor.execute("""
                    INSERT INTO stocks (
                        portfolio_id, name, ticker, sector,
                        entry_price, allocation_pct, allocation_amount,
                        stop_loss_pct, stop_loss_price, target_pct, target_price,
                        rationale, news_sentiment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    portfolio_id,
                    stock.get('name'),
                    stock.get('ticker'),
                    stock.get('sector'),
                    stock.get('entry_price'),
                    stock.get('allocation_pct'),
                    stock.get('allocation_amount'),
                    stock.get('stop_loss_pct'),
                    stock.get('stop_loss_price'),
                    stock.get('target_pct'),
                    stock.get('target_price'),
                    stock.get('rationale'),
                    stock.get('news_sentiment')
                ))

                stock_id = cursor.lastrowid
                stock_ids.append(stock_id)

                # Save investment view
                investment_view = stock.get('investment_view', {})
                if investment_view:
                    self._save_investment_view(cursor, stock_id, investment_view)

                # Save key metrics
                key_metrics = stock.get('key_metrics', {})
                if key_metrics:
                    self._save_key_metrics(cursor, stock_id, key_metrics)

            logger.info(f"Saved {len(stock_ids)} stocks for portfolio {portfolio_id}")

        return stock_ids

    def get_portfolio_stocks(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """Get all stocks for a portfolio"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, iv.market_outlook, iv.stock_rationale, iv.holding_period,
                       iv.exit_triggers, iv.review_triggers
                FROM stocks s
                LEFT JOIN investment_views iv ON s.id = iv.stock_id
                WHERE s.portfolio_id = ?
                ORDER BY s.allocation_pct DESC
            """, (portfolio_id,))

            return [dict(row) for row in cursor.fetchall()]

    def get_stock_by_ticker(self, ticker: str, portfolio_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get stock by ticker"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if portfolio_id:
                cursor.execute(
                    "SELECT * FROM stocks WHERE ticker = ? AND portfolio_id = ?",
                    (ticker, portfolio_id)
                )
            else:
                cursor.execute(
                    "SELECT * FROM stocks WHERE ticker = ? ORDER BY added_at DESC LIMIT 1",
                    (ticker,)
                )

            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== Investment View Operations ====================

    def _save_investment_view(self, cursor, stock_id: int, investment_view: Dict[str, Any]):
        """Save investment view for a stock"""
        cursor.execute("""
            INSERT INTO investment_views (
                stock_id, market_outlook, stock_rationale, holding_period,
                exit_triggers, review_triggers
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            stock_id,
            investment_view.get('market_outlook'),
            investment_view.get('stock_rationale'),
            investment_view.get('holding_period'),
            json.dumps(investment_view.get('exit_triggers', [])),
            json.dumps(investment_view.get('review_triggers', []))
        ))

    def get_investment_view(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """Get investment view for a stock"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM investment_views WHERE stock_id = ?", (stock_id,))
            row = cursor.fetchone()

            if row:
                result = dict(row)
                # Parse JSON arrays
                result['exit_triggers'] = json.loads(result['exit_triggers'])
                result['review_triggers'] = json.loads(result['review_triggers'])
                return result

            return None

    # ==================== Key Metrics Operations ====================

    def _save_key_metrics(self, cursor, stock_id: int, key_metrics: Dict[str, Any]):
        """Save key metrics for a stock"""
        cursor.execute("""
            INSERT INTO key_metrics (stock_id, metrics_json)
            VALUES (?, ?)
        """, (stock_id, json.dumps(key_metrics)))

    def get_key_metrics(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """Get key metrics for a stock"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM key_metrics WHERE stock_id = ?", (stock_id,))
            row = cursor.fetchone()

            if row:
                result = dict(row)
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
        notes: Optional[str] = None
    ) -> int:
        """Record a buy/sell transaction"""
        total_amount = quantity * price

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (
                    portfolio_id, stock_id, transaction_type, quantity, price,
                    total_amount, transaction_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id, stock_id, transaction_type, quantity, price,
                total_amount, transaction_date, notes
            ))

            transaction_id = cursor.lastrowid
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
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM transactions WHERE 1=1"
            params = []

            if portfolio_id:
                query += " AND portfolio_id = ?"
                params.append(portfolio_id)

            if stock_id:
                query += " AND stock_id = ?"
                params.append(stock_id)

            if start_date:
                query += " AND transaction_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND transaction_date <= ?"
                params.append(end_date)

            query += " ORDER BY transaction_date DESC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

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
        """Record performance metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO performance_metrics (
                    portfolio_id, stock_id, metric_date, portfolio_value, stock_value,
                    daily_return_pct, cumulative_return_pct, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id, stock_id, metric_date, portfolio_value, stock_value,
                daily_return_pct, cumulative_return_pct, status
            ))

            metric_id = cursor.lastrowid
            return metric_id

    def get_performance_history(
        self,
        portfolio_id: int,
        stock_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get performance history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM performance_metrics WHERE portfolio_id = ?"
            params = [portfolio_id]

            if stock_id:
                query += " AND stock_id = ?"
                params.append(stock_id)
            else:
                query += " AND stock_id IS NULL"

            if start_date:
                query += " AND metric_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND metric_date <= ?"
                params.append(end_date)

            query += " ORDER BY metric_date ASC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rebalancing_history (
                    portfolio_id, rebalancing_date, reason, action_type,
                    affected_stocks, allocation_changes, expected_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id,
                rebalancing_date,
                reason,
                action_type,
                json.dumps(affected_stocks),
                json.dumps(allocation_changes),
                expected_result
            ))

            rebalancing_id = cursor.lastrowid
            logger.info(f"Recorded rebalancing action {rebalancing_id}")

            return rebalancing_id

    def get_rebalancing_history(
        self,
        portfolio_id: int,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get rebalancing history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM rebalancing_history WHERE portfolio_id = ?"
            params = [portfolio_id]

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY rebalancing_date DESC"

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, params)
            result = [dict(row) for row in cursor.fetchall()]

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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_events (
                    portfolio_id, stock_id, event_type, title, description,
                    impact, action_taken, event_date, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id, stock_id, event_type, title, description,
                impact, action_taken, event_date, source
            ))

            event_id = cursor.lastrowid
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
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM market_events WHERE 1=1"
            params = []

            if portfolio_id:
                query += " AND portfolio_id = ?"
                params.append(portfolio_id)

            if stock_id:
                query += " AND stock_id = ?"
                params.append(stock_id)

            if start_date:
                query += " AND event_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND event_date <= ?"
                params.append(end_date)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY event_date DESC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # ==================== Query Helpers ====================

    def portfolio_summary(self, portfolio_id: int) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Portfolio info
            cursor.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,))
            portfolio = dict(cursor.fetchone())

            # Stocks info
            cursor.execute("""
                SELECT * FROM stocks WHERE portfolio_id = ?
                ORDER BY allocation_pct DESC
            """, (portfolio_id,))
            stocks = [dict(row) for row in cursor.fetchall()]

            # Recent transactions
            cursor.execute("""
                SELECT * FROM transactions WHERE portfolio_id = ?
                ORDER BY transaction_date DESC LIMIT 10
            """, (portfolio_id,))
            recent_transactions = [dict(row) for row in cursor.fetchall()]

            # Rebalancing history
            cursor.execute("""
                SELECT * FROM rebalancing_history WHERE portfolio_id = ?
                ORDER BY rebalancing_date DESC LIMIT 5
            """, (portfolio_id,))
            rebalancing = [dict(row) for row in cursor.fetchall()]

            return {
                'portfolio': portfolio,
                'stocks': stocks,
                'recent_transactions': recent_transactions,
                'rebalancing_history': rebalancing,
                'stock_count': len(stocks),
                'total_allocation': sum(s['allocation_pct'] for s in stocks)
            }

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute raw SQL query for custom queries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """Execute raw SQL update/delete query"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.rowcount

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
        Store daily price snapshot for a stock

        Args:
            stock_id: Stock ID from stocks table
            price_date: Date of price data
            open_price, high_price, low_price, close_price: OHLC prices
            volume: Trading volume

        Returns:
            ID of inserted/updated record
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO daily_prices
                (stock_id, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (stock_id, price_date, open_price, high_price, low_price, close_price, volume))

            logger.debug(f"Stored daily price for stock_id {stock_id} on {price_date}")
            return cursor.lastrowid

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
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM daily_prices WHERE stock_id = ?"
            params = [stock_id]

            if start_date:
                query += " AND price_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND price_date <= ?"
                params.append(end_date)

            query += " ORDER BY price_date DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

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
        """Store daily price for a market index"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO index_prices
                (index_symbol, index_name, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (index_symbol, index_name, price_date, open_price, high_price, low_price, close_price, volume))

            logger.debug(f"Stored index price for {index_symbol} on {price_date}")
            return cursor.lastrowid

    def get_index_price_history(
        self,
        index_symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get price history for an index"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM index_prices WHERE index_symbol = ?"
            params = [index_symbol]

            if start_date:
                query += " AND price_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND price_date <= ?"
                params.append(end_date)

            query += " ORDER BY price_date DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

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
        Store daily portfolio snapshot

        Args:
            portfolio_id: Portfolio ID
            snapshot_date: Date of snapshot
            total_value: Current portfolio value
            metrics: Dict with keys: invested_value, total_return_pct, total_return_absolute,
                     day_return_pct, day_return_absolute, volatility, sharpe_ratio,
                     max_drawdown, num_stocks, avg_allocation_pct
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio_snapshots
                (portfolio_id, snapshot_date, total_value, cash_balance, invested_value,
                 total_return_pct, total_return_absolute, day_return_pct, day_return_absolute,
                 volatility, sharpe_ratio, max_drawdown, num_stocks, avg_allocation_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id,
                snapshot_date,
                total_value,
                metrics.get('cash_balance', 0),
                metrics.get('invested_value', 0),
                metrics.get('total_return_pct', 0),
                metrics.get('total_return_absolute', 0),
                metrics.get('day_return_pct', 0),
                metrics.get('day_return_absolute', 0),
                metrics.get('volatility', 0),
                metrics.get('sharpe_ratio', 0),
                metrics.get('max_drawdown', 0),
                metrics.get('num_stocks', 0),
                metrics.get('avg_allocation_pct', 0)
            ))

            logger.info(f"Stored portfolio snapshot for portfolio {portfolio_id} on {snapshot_date}")
            return cursor.lastrowid

    def get_portfolio_snapshots(
        self,
        portfolio_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get portfolio snapshots for a date range"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM portfolio_snapshots WHERE portfolio_id = ?"
            params = [portfolio_id]

            if start_date:
                query += " AND snapshot_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND snapshot_date <= ?"
                params.append(end_date)

            query += " ORDER BY snapshot_date DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

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
        """Store benchmark comparison data"""
        if alpha is None:
            alpha = portfolio_return - index_return

        outperformance = alpha

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO benchmark_comparison
                (portfolio_id, comparison_date, index_symbol, index_name,
                 portfolio_return, index_return, alpha, beta, outperformance, period)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id, comparison_date, index_symbol, index_name,
                portfolio_return, index_return, alpha, beta, outperformance, period
            ))

            logger.debug(f"Stored benchmark comparison: Portfolio {portfolio_id} vs {index_symbol}")
            return cursor.lastrowid

    def get_benchmark_comparisons(
        self,
        portfolio_id: int,
        comparison_date: Optional[date] = None,
        period: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get benchmark comparison data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM benchmark_comparison WHERE portfolio_id = ?"
            params = [portfolio_id]

            if comparison_date:
                query += " AND comparison_date = ?"
                params.append(comparison_date)

            if period:
                query += " AND period = ?"
                params.append(period)

            query += " ORDER BY comparison_date DESC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO manager_updates
                (portfolio_id, update_date, update_type, title, description,
                 affected_stocks, affected_sectors, recommendation, reasoning, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id,
                update_date,
                update_type,
                title,
                description,
                json.dumps(affected_stocks) if affected_stocks else None,
                json.dumps(affected_sectors) if affected_sectors else None,
                recommendation,
                reasoning,
                priority
            ))

            logger.info(f"Stored manager update: {title} ({update_type})")
            return cursor.lastrowid

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
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM manager_updates WHERE portfolio_id = ?"
            params = [portfolio_id]

            if status:
                query += " AND status = ?"
                params.append(status)

            if priority:
                query += " AND priority = ?"
                params.append(priority)

            query += " ORDER BY update_date DESC, priority DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

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
        with self.get_connection() as conn:
            cursor = conn.cursor()

            executed_at = datetime.now() if status == 'EXECUTED' else None

            cursor.execute("""
                UPDATE manager_updates
                SET status = ?, user_decision = ?, user_notes = ?, executed_at = ?
                WHERE id = ?
            """, (status, user_decision, user_notes, executed_at, update_id))

            logger.info(f"Updated manager update {update_id} status to {status}")
            return cursor.rowcount

    # ==================== User Preferences Operations ====================

    def get_user_benchmarks(self, portfolio_id: int, primary_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get user's selected benchmark indices

        Args:
            portfolio_id: Portfolio ID
            primary_only: If True, return only primary benchmarks (top 3 for dashboard)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM user_benchmark_preferences WHERE portfolio_id = ? AND enabled = 1"
            params = [portfolio_id]

            if primary_only:
                query += " AND is_primary = 1"

            query += " ORDER BY display_order ASC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

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
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Reset all to non-primary
            cursor.execute("""
                UPDATE user_benchmark_preferences
                SET is_primary = 0
                WHERE portfolio_id = ?
            """, (portfolio_id,))

            # Set selected as primary with display order
            for idx, symbol in enumerate(index_symbols[:3], start=1):
                cursor.execute("""
                    UPDATE user_benchmark_preferences
                    SET is_primary = 1, display_order = ?
                    WHERE portfolio_id = ? AND index_symbol = ?
                """, (idx, portfolio_id, symbol))

            logger.info(f"Set primary benchmarks for portfolio {portfolio_id}: {index_symbols}")
            return cursor.rowcount


# Singleton instance
_db_service = None


def get_db_service(db_path: str = ".cache/portfolio.db") -> DatabaseService:
    """Get or create database service singleton"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService(db_path)
    return _db_service
