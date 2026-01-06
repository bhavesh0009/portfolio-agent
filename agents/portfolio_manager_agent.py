"""
Portfolio Manager Agent
Monitors existing portfolio and generates daily analysis, recommendations, and rebalancing decisions
"""

import json
import hashlib
import configparser
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.llm_service import generate_content
from utils.db_service import get_db_service
from tools.price_fetcher import get_price_fetcher
from tools.performance_calculator import get_performance_calculator
from tools.performance_context_aggregator import get_performance_context_aggregator
from agents.stock_news_agent import run_stock_news
from agents.market_research_agent import run_market_research
from agents.stock_screening_agent import run_stock_screening
from agents.execution_engine import ExecutionEngine
from agents.replacement_finder import ReplacementStockFinder

logger = get_logger("agents.portfolio_manager")

# Constants
MAX_ITERATIONS = 20
CACHE_DIR = Path(__file__).parent.parent / ".cache"
PORTFOLIOS_DIR = CACHE_DIR / "portfolios"


class PortfolioManagerAgent:
    """AI-powered portfolio manager for daily monitoring and recommendations"""

    def __init__(self, model_name: str = None):
        """
        Initialize Portfolio Manager Agent

        Args:
            model_name: LLM model to use (defaults to GEMINI_HIGH_MODEL for complex reasoning)
        """
        self.db = get_db_service()
        self.price_fetcher = get_price_fetcher()
        self.perf_calculator = get_performance_calculator()
        self.performance_aggregator = get_performance_context_aggregator()
        self.model_name = model_name or "high"  # Use high-tier model for strategic decisions
        self._agent_cache: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, str]] = []

        # Load config
        config = configparser.ConfigParser()
        config_path = Path(__file__).parent.parent / 'config.ini'
        if config_path.exists():
            config.read(config_path)
            self.news_lookback_period = config.get('NEWS', 'news_lookback_period', fallback='5d')
            self.execution_mode = config.get('EXECUTION', 'execution_mode', fallback='manual')
        else:
            self.news_lookback_period = '5d'
            self.execution_mode = 'manual'

        self.config = config
        logger.debug(f"Portfolio manager news lookback period: {self.news_lookback_period}")
        logger.info(f"Execution mode: {self.execution_mode}")

        # Initialize execution components
        self.execution_engine = ExecutionEngine(config)
        self.replacement_finder = ReplacementStockFinder(config)

        # Track current portfolio ID for execution methods
        self.current_portfolio_id = None
        self.current_stocks = []

        # Auto-migrate JSON portfolios on first run
        self._check_and_migrate_json_portfolios()

    def _check_and_migrate_json_portfolios(self):
        """Run migration if JSON portfolios exist but not in database"""
        try:
            from utils.migrate_json_to_db import JSONPortfolioMigrator

            migrator = JSONPortfolioMigrator()
            portfolios_to_migrate = migrator.discover_json_portfolios()

            if portfolios_to_migrate:
                logger.info(f"Found {len(portfolios_to_migrate)} JSON portfolios to migrate")
                result = migrator.migrate_all()

                logger.info(
                    f"Migration complete: {result['migrated']} migrated, "
                    f"{result['skipped']} skipped, {result['failed']} failed"
                )

                if result['errors']:
                    for error in result['errors']:
                        logger.warning(f"Migration error: {error}")

                # Mark latest portfolios as active
                for profile in ['aggressive', 'defensive']:
                    migrator.mark_latest_as_active(profile)

        except Exception as e:
            logger.error(f"Failed to check/migrate portfolios: {e}")
            # Don't fail initialization if migration fails
            pass

    def load_portfolio(self, profile: str = None) -> Optional[Dict[str, Any]]:
        """
        Load active portfolio from database (always loads LATEST portfolio)

        Args:
            profile: DEPRECATED - Always loads latest portfolio regardless of profile

        Returns:
            Portfolio dict or None if not found
        """
        if profile:
            logger.warning(f"Profile parameter '{profile}' is deprecated. Loading latest portfolio instead.")

        logger.info("Loading latest active portfolio from database")

        try:
            # Get all portfolios and find the active one (should be latest)
            all_portfolios = self.db.get_all_portfolios()

            if not all_portfolios:
                logger.error("No portfolios found in database")
                return None

            # Find active portfolio (should be the latest one)
            db_portfolio = next((p for p in all_portfolios if p.get('is_active')), None)

            if not db_portfolio:
                # Fallback: Get latest portfolio by created_at
                logger.warning("No active portfolio found, using latest by created_at")
                all_portfolios.sort(key=lambda p: p.get('created_at', ''), reverse=True)
                db_portfolio = all_portfolios[0]

            # db_portfolio is guaranteed to exist here (either active or latest)

            portfolio_id = db_portfolio['id']
            logger.debug(f"Found portfolio ID: {portfolio_id}")

            # Get all stocks with investment views and metrics
            stocks = self.db.get_portfolio_stocks(portfolio_id)

            # Enrich each stock with investment views and key metrics
            for stock in stocks:
                # Parse JSON fields from database
                if stock.get('exit_triggers'):
                    try:
                        stock['exit_triggers'] = json.loads(stock['exit_triggers'])
                    except (json.JSONDecodeError, TypeError):
                        stock['exit_triggers'] = []

                if stock.get('review_triggers'):
                    try:
                        stock['review_triggers'] = json.loads(stock['review_triggers'])
                    except (json.JSONDecodeError, TypeError):
                        stock['review_triggers'] = []

                # Build investment_view dict from separate fields
                stock['investment_view'] = {
                    'market_outlook': stock.pop('market_outlook', ''),
                    'stock_rationale': stock.pop('stock_rationale', ''),
                    'holding_period': stock.pop('holding_period', ''),
                    'exit_triggers': stock.get('exit_triggers', []),
                    'review_triggers': stock.get('review_triggers', [])
                }

                # Get key metrics
                metrics = self.db.get_key_metrics(stock['id'])
                if metrics:
                    try:
                        stock['key_metrics'] = json.loads(metrics['metrics_json'])
                    except (json.JSONDecodeError, TypeError):
                        stock['key_metrics'] = {}

            # Return structure matching JSON format (backward compatibility)
            portfolio = {
                'profile': db_portfolio['profile'],
                'total_capital': db_portfolio['total_capital'],
                'created_at': db_portfolio['created_at'],
                'stocks': stocks,
                'diversification': '',  # Not stored in DB currently
                'risk_assessment': ''   # Not stored in DB currently
            }

            logger.info(f"Loaded portfolio from database: {len(stocks)} stocks, Rs. {db_portfolio['total_capital']:,.0f} capital")
            return portfolio

        except Exception as e:
            logger.error(f"Failed to load portfolio from database: {e}")
            # Fallback to JSON if database read fails
            return self._load_portfolio_from_json_fallback(profile)

    def _load_portfolio_from_json_fallback(self, profile: str) -> Optional[Dict[str, Any]]:
        """
        Fallback: Load from JSON if database is empty or corrupted

        This ensures graceful degradation if database has issues

        Args:
            profile: Portfolio profile

        Returns:
            Portfolio dict or None
        """
        latest_file = PORTFOLIOS_DIR / f"latest_{profile}.json"

        if not latest_file.exists():
            logger.error(f"No JSON fallback available for {profile}")
            return None

        logger.warning(f"Using JSON fallback for {profile} portfolio")

        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)

            # Handle nested structure
            if 'metadata' in data and 'portfolio' in data:
                portfolio = {
                    'profile': data['metadata']['profile'],
                    'total_capital': data['metadata']['total_capital'],
                    'created_at': data['metadata']['created_at'],
                    'stocks': data['portfolio']['stocks'],
                    'diversification': data['portfolio'].get('diversification', ''),
                    'risk_assessment': data['portfolio'].get('risk_assessment', '')
                }
            else:
                portfolio = data

            logger.info(f"Loaded portfolio from JSON: {len(portfolio.get('stocks', []))} stocks")
            return portfolio

        except Exception as e:
            logger.error(f"Failed to load portfolio from JSON: {e}")
            return None

    def get_current_prices(self, stocks: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Get current prices for all stocks in portfolio

        Args:
            stocks: List of stock dicts with ticker and exchange

        Returns:
            Dict mapping ticker to current price
        """
        logger.info(f"Fetching current prices for {len(stocks)} stocks...")
        prices = {}

        for stock in stocks:
            ticker = stock['ticker']
            exchange = stock.get('exchange', 'NSE')

            price = self.price_fetcher.get_current_price(ticker, exchange)
            if price:
                prices[ticker] = price
                logger.debug(f"{ticker}: Rs. {price:.2f}")
            else:
                # Fallback to entry price
                prices[ticker] = stock['entry_price']
                logger.warning(f"{ticker}: Using entry price Rs. {stock['entry_price']:.2f}")

        return prices

    def persist_daily_prices(
        self,
        stocks: List[Dict[str, Any]],
        current_prices: Dict[str, float]
    ) -> int:
        """
        Save today's prices to daily_prices table for historical tracking

        Args:
            stocks: List of stock dicts with stock IDs
            current_prices: Dict of current prices by ticker

        Returns:
            Number of price records saved
        """
        logger.info("Persisting daily prices to database...")
        saved_count = 0
        today = date.today()

        for stock in stocks:
            ticker = stock['ticker']
            stock_id = stock.get('id')

            if not stock_id:
                logger.warning(f"Skipping {ticker}: No stock ID")
                continue

            price = current_prices.get(ticker)
            if not price:
                logger.warning(f"Skipping {ticker}: No price available")
                continue

            try:
                # Save as OHLC (all same for current price)
                self.db.store_daily_price(
                    stock_id=stock_id,
                    price_date=today,
                    open_price=price,
                    high_price=price,
                    low_price=price,
                    close_price=price,
                    volume=0  # Not available from current price fetch
                )
                saved_count += 1
                logger.debug(f"Saved price for {ticker}: Rs. {price:.2f}")

            except Exception as e:
                logger.error(f"Failed to save price for {ticker}: {e}")

        logger.info(f"Saved {saved_count}/{len(stocks)} price records")
        return saved_count

    def check_price_triggers(
        self,
        stocks: List[Dict[str, Any]],
        current_prices: Dict[str, float]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Check which stocks have breached stop-loss or target prices
        and optionally execute exits

        Args:
            stocks: List of stock dicts
            current_prices: Dict of current prices

        Returns:
            Dict with 'stop_loss_breached', 'target_reached', 'approaching_target', 'executed_exits'
        """
        triggers = {
            'stop_loss_breached': [],
            'target_reached': [],
            'approaching_target': [],  # Within 5% of target
            'executed_exits': []  # Auto-executed exits
        }

        for stock in stocks:
            ticker = stock['ticker']

            # Skip stocks with 0% allocation (already exited)
            if stock.get('allocation_pct', 0) == 0:
                logger.debug(f"Skipping {ticker} - already exited (0% allocation)")
                continue

            current_price = current_prices.get(ticker, stock['entry_price'])
            stop_loss = stock['stop_loss_price']
            target = stock['target_price']
            entry_price = stock['entry_price']

            # Calculate current P&L
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Check stop-loss breach
            if current_price <= stop_loss:
                triggers['stop_loss_breached'].append({
                    'stock': stock,
                    'current_price': current_price,
                    'stop_loss_price': stop_loss,
                    'breach_pct': ((current_price - stop_loss) / stop_loss) * 100,
                    'current_pnl_pct': pnl_pct
                })
                logger.warning(f"STOP-LOSS BREACH: {ticker} at Rs. {current_price:.2f} (SL: Rs. {stop_loss:.2f})")

            # Check target reached
            elif current_price >= target:
                triggers['target_reached'].append({
                    'stock': stock,
                    'current_price': current_price,
                    'target_price': target,
                    'excess_pct': ((current_price - target) / target) * 100,
                    'current_pnl_pct': pnl_pct
                })
                logger.info(f"TARGET REACHED: {ticker} at Rs. {current_price:.2f} (Target: Rs. {target:.2f})")

            # Check approaching target (within 5%)
            elif current_price >= target * 0.95:
                triggers['approaching_target'].append({
                    'stock': stock,
                    'current_price': current_price,
                    'target_price': target,
                    'distance_pct': ((target - current_price) / target) * 100,
                    'current_pnl_pct': pnl_pct
                })
                logger.info(f"APPROACHING TARGET: {ticker} at Rs. {current_price:.2f} (95% of target)")

        # Auto-execute price-triggered exits if enabled
        if self.execution_mode in ['price-only', 'full']:
            logger.info("\nAuto-executing price-triggered exits...")

            for item in triggers['stop_loss_breached']:
                success = self._execute_triggered_exit(
                    stock=item['stock'],
                    current_price=item['current_price'],
                    trigger_type='STOP_LOSS',
                    reason=f"Stop-loss breach at Rs. {item['current_price']:.2f}"
                )
                if success:
                    triggers['executed_exits'].append({**item, 'exit_type': 'STOP_LOSS'})

            for item in triggers['target_reached']:
                success = self._execute_triggered_exit(
                    stock=item['stock'],
                    current_price=item['current_price'],
                    trigger_type='TARGET_HIT',
                    reason=f"Target achieved at Rs. {item['current_price']:.2f}"
                )
                if success:
                    triggers['executed_exits'].append({**item, 'exit_type': 'TARGET_HIT'})

            if triggers['executed_exits']:
                logger.info(f"✓ Auto-executed {len(triggers['executed_exits'])} price-triggered exits")

        return triggers

    def _execute_triggered_exit(
        self,
        stock: Dict[str, Any],
        current_price: float,
        trigger_type: str,
        reason: str
    ) -> bool:
        """
        Execute automatic position exit

        Args:
            stock: Stock dict
            current_price: Current price
            trigger_type: 'STOP_LOSS', 'TARGET_HIT', 'NEWS_DRIVEN', 'LLM_RECOMMENDATION'
            reason: Exit reason

        Returns:
            True if exit executed successfully
        """
        ticker = stock['ticker']
        portfolio_id = self.current_portfolio_id

        # Check with execution engine
        can_execute, decision_reason = self.execution_engine.should_execute_exit(
            portfolio_id=portfolio_id,
            stock=stock,
            trigger_type=trigger_type,
            confidence=100.0 if trigger_type in ['STOP_LOSS', 'TARGET_HIT'] else 80.0,
            reasoning=reason
        )

        if not can_execute:
            logger.warning(f"Cannot execute exit for {ticker}: {decision_reason}")
            return False

        try:
            # Validate current price
            if current_price <= 0:
                logger.error(f"Invalid price for {ticker}: {current_price}")
                # Fallback to last daily price
                current_price = self._get_last_known_price(stock.get('id'))
                if not current_price:
                    raise ValueError(f"Cannot determine price for {ticker}")

            # Execute position exit
            success = self.record_position_exit(
                portfolio_id=portfolio_id,
                ticker=ticker,
                exit_price=current_price,
                exit_reason=reason,
                exit_type=trigger_type
            )

            if not success:
                raise RuntimeError(f"Failed to record exit for {ticker}")

            # Update portfolio cash_balance
            exit_proceeds = stock['allocation_amount']  # Original investment
            exit_value = (current_price / stock['entry_price']) * exit_proceeds
            self._update_cash_balance(portfolio_id, exit_value)

            # Log to rebalancing_history
            rebalance_date = datetime.now()
            self.db.record_rebalancing(
                portfolio_id=portfolio_id,
                rebalancing_date=rebalance_date,
                reason=f"AUTO-EXECUTE: {reason}",
                action_type='EXIT',
                affected_stocks=[ticker],
                allocation_changes={ticker: (stock['allocation_pct'], 0.0)},
                expected_result=f"Exit {ticker}, realized P&L {((current_price/stock['entry_price'])-1)*100:.2f}%"
            )

            # Update rebalancing status to EXECUTED
            actual_pnl = ((current_price/stock['entry_price'])-1)*100
            try:
                # First, find the most recent EXIT rebalancing record for this stock today
                today_start = rebalance_date.date().isoformat()
                today_end = today_start + ' 23:59:59'

                recent_records = self.db.client.table('rebalancing_history')\
                    .select('id')\
                    .eq('portfolio_id', portfolio_id)\
                    .eq('action_type', 'EXIT')\
                    .gte('rebalancing_date', today_start)\
                    .lte('rebalancing_date', today_end)\
                    .order('created_at', desc=True)\
                    .limit(1)\
                    .execute()

                if recent_records.data:
                    record_id = recent_records.data[0]['id']
                    self.db.client.table('rebalancing_history')\
                        .update({
                            'status': 'EXECUTED',
                            'executed_at': rebalance_date.isoformat(),
                            'actual_result': f"Successfully exited {ticker}. Actual P&L: {actual_pnl:.2f}%"
                        })\
                        .eq('id', record_id)\
                        .execute()
                    logger.debug(f"Updated rebalancing status to EXECUTED for {ticker}")
            except Exception as e:
                logger.warning(f"Failed to update rebalancing status: {e}")

            logger.info(f"✓ AUTO-EXECUTED EXIT: {ticker} at Rs. {current_price:.2f}")
            return True

        except Exception as e:
            logger.error(f"Exit execution failed for {ticker}: {e}")

            # Log failure to market_events
            try:
                self.db.record_market_event(
                    event_type='INTERNAL',
                    title=f"EXECUTION FAILED: {ticker}",
                    description=f"Failed to execute {trigger_type} exit: {str(e)}",
                    event_date=datetime.now(),
                    portfolio_id=portfolio_id,
                    stock_id=stock.get('id'),
                    impact='NEGATIVE',
                    action_taken='ERROR_LOGGED'
                )
            except:
                pass  # Don't fail if event logging fails

            return False

    def _find_and_add_replacement(
        self,
        exited_stock: Dict[str, Any],
        portfolio_id: int,
        portfolio_profile: str
    ) -> Optional[int]:
        """
        Find and add replacement stock after exit

        Args:
            exited_stock: Stock that was exited
            portfolio_id: Portfolio ID
            portfolio_profile: Portfolio profile

        Returns:
            New stock ID or None
        """
        # Check if replacement search is enabled
        if not self.config.getboolean('EXECUTION', 'enable_replacement_search', fallback=True):
            logger.info("Replacement search disabled, keeping cash")
            return None

        # Get available cash
        available_cash = self._get_available_cash(portfolio_id)

        # Check minimum cash reserve
        min_reserve_pct = self.config.getfloat('EXECUTION', 'min_cash_balance_pct', fallback=5.0)
        portfolio_data = self.db.get_portfolio_by_id(portfolio_id)
        total_capital = portfolio_data['total_capital']
        min_reserve = total_capital * (min_reserve_pct / 100)

        if available_cash <= min_reserve:
            logger.warning(f"Insufficient cash for replacement (Rs. {available_cash:.2f})")
            return None

        # Get current holdings
        current_stocks = self.db.get_portfolio_stocks(portfolio_id)
        active_stocks = [s for s in current_stocks if s.get('allocation_pct', 0) > 0]

        # Find replacement
        try:
            replacement_data = self.replacement_finder.find_replacement(
                exited_stock=exited_stock,
                portfolio_profile=portfolio_profile,
                available_capital=available_cash - min_reserve,
                current_holdings=active_stocks
            )

            if not replacement_data:
                logger.warning("No suitable replacement found")
                return None

            # Calculate allocation (match exited stock's allocation)
            allocation_amount = min(
                exited_stock.get('allocation_amount', 0),
                available_cash - min_reserve
            )

            # Calculate allocation percentage
            total_invested = sum(s.get('allocation_amount', 0) for s in active_stocks)
            allocation_pct = (allocation_amount / (total_invested + allocation_amount)) * 100 if total_invested + allocation_amount > 0 else 0

            # Add allocation fields
            replacement_data['allocation_pct'] = allocation_pct
            replacement_data['allocation_amount'] = allocation_amount
            replacement_data['shares'] = int(allocation_amount / replacement_data['entry_price']) if replacement_data['entry_price'] > 0 else 0

            # Add investment view
            replacement_data['investment_view'] = {
                'market_outlook': f"Replacement for {exited_stock['ticker']}",
                'stock_rationale': replacement_data.get('rationale', 'Replacement stock'),
                'holding_period': exited_stock.get('investment_view', {}).get('holding_period', '3-6 months'),
                'exit_triggers': [],
                'review_triggers': []
            }

            # Check with execution engine
            can_execute, reason = self.execution_engine.should_execute_entry(
                portfolio_id=portfolio_id,
                stock_data=replacement_data,
                confidence=75.0,
                replacement_for=exited_stock['ticker']
            )

            if not can_execute:
                logger.warning(f"Cannot add replacement: {reason}")
                return None

            # Add to portfolio
            stock_id = self.record_position_entry(portfolio_id, replacement_data)

            if stock_id:
                # Deduct from cash balance
                self._update_cash_balance(portfolio_id, -allocation_amount)

                # Log rebalancing
                rebalance_date = datetime.now()
                self.db.record_rebalancing(
                    portfolio_id=portfolio_id,
                    rebalancing_date=rebalance_date,
                    reason=f"AUTO-EXECUTE: Replacement for {exited_stock['ticker']}",
                    action_type='ENTRY',
                    affected_stocks=[replacement_data['ticker']],
                    allocation_changes={replacement_data['ticker']: (0.0, allocation_pct)},
                    expected_result=f"Added {replacement_data['ticker']} with {allocation_pct:.1f}% allocation"
                )

                # Update rebalancing status to EXECUTED
                try:
                    # First, find the most recent ENTRY rebalancing record for this stock today
                    today_start = rebalance_date.date().isoformat()
                    today_end = today_start + ' 23:59:59'

                    recent_records = self.db.client.table('rebalancing_history')\
                        .select('id')\
                        .eq('portfolio_id', portfolio_id)\
                        .eq('action_type', 'ENTRY')\
                        .gte('rebalancing_date', today_start)\
                        .lte('rebalancing_date', today_end)\
                        .order('created_at', desc=True)\
                        .limit(1)\
                        .execute()

                    if recent_records.data:
                        record_id = recent_records.data[0]['id']
                        self.db.client.table('rebalancing_history')\
                            .update({
                                'status': 'EXECUTED',
                                'executed_at': rebalance_date.isoformat(),
                                'actual_result': f"Successfully added {replacement_data['ticker']} with {allocation_pct:.1f}% allocation"
                            })\
                            .eq('id', record_id)\
                            .execute()
                        logger.debug(f"Updated rebalancing status to EXECUTED for {replacement_data['ticker']}")
                except Exception as e:
                    logger.warning(f"Failed to update rebalancing status: {e}")

                logger.info(f"✓ AUTO-EXECUTED ENTRY: {replacement_data['ticker']} ({allocation_pct:.1f}%)")

            return stock_id

        except Exception as e:
            logger.error(f"Failed to find/add replacement: {e}")
            return None

    def _update_cash_balance(self, portfolio_id: int, amount: float) -> None:
        """
        Update portfolio cash balance

        Args:
            portfolio_id: Portfolio ID
            amount: Amount to add (positive for sell) or subtract (negative for buy)
        """
        try:
            portfolio = self.db.get_portfolio_by_id(portfolio_id)
            current_cash = portfolio.get('cash_balance', 0) or 0
            new_cash = current_cash + amount

            # Update in database
            self.db.client.table('portfolios')\
                .update({'cash_balance': new_cash})\
                .eq('id', portfolio_id)\
                .execute()

            logger.info(f"Updated cash balance: Rs. {current_cash:,.2f} → Rs. {new_cash:,.2f} (change: {amount:+,.2f})")

        except Exception as e:
            logger.error(f"Failed to update cash balance: {e}")

    def _get_available_cash(self, portfolio_id: int) -> float:
        """
        Get current available cash

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Available cash amount
        """
        try:
            portfolio = self.db.get_portfolio_by_id(portfolio_id)
            cash = portfolio.get('cash_balance', 0) or 0
            return float(cash)
        except Exception as e:
            logger.error(f"Failed to get cash balance: {e}")
            return 0.0

    def _get_last_known_price(self, stock_id: int) -> Optional[float]:
        """
        Get last known price from daily_prices table

        Args:
            stock_id: Stock ID

        Returns:
            Last known price or None
        """
        try:
            response = self.db.client.table('daily_prices')\
                .select('close_price')\
                .eq('stock_id', stock_id)\
                .order('price_date', desc=True)\
                .limit(1)\
                .execute()

            if response.data:
                return response.data[0]['close_price']

            return None

        except Exception as e:
            logger.error(f"Failed to get last known price: {e}")
            return None

    def _evaluate_news_exits(
        self,
        stocks: List[Dict[str, Any]],
        news_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to evaluate if news warrants exit

        Args:
            stocks: List of stocks
            news_analysis: News analysis dict

        Returns:
            List of exit recommendations
        """
        exit_recommendations = []

        for stock in stocks:
            ticker = stock['ticker']
            news = news_analysis.get(ticker, {})

            # Skip if news is neutral or positive
            sentiment = news.get('sentiment', 'neutral')
            if sentiment not in ['negative', 'very_negative']:
                continue

            # Ask LLM to evaluate exit necessity
            current_price = self.current_prices.get(ticker, stock['entry_price'])
            current_pnl = ((current_price / stock['entry_price']) - 1) * 100

            prompt = f"""
You are evaluating whether to exit a stock position based on recent news.

Stock: {stock['name']} ({ticker})
Sector: {stock.get('sector')}
Entry Price: Rs. {stock['entry_price']:.2f}
Current Price: Rs. {current_price:.2f}
Current P&L: {current_pnl:.2f}%

Recent News Summary:
{news.get('full_analysis', 'No detailed analysis available')}

Investment Thesis:
{stock.get('investment_view', {}).get('stock_rationale', 'N/A')}

Exit Triggers:
{stock.get('investment_view', {}).get('exit_triggers', [])}

Based on this information:
1. Does the news invalidate the investment thesis?
2. Are any exit triggers hit?
3. Is there fundamental deterioration or just temporary noise?
4. Should we exit this position NOW?

Respond in JSON format:
{{
    "should_exit": true/false,
    "confidence": 0-100,
    "reasoning": "detailed explanation",
    "urgency": "LOW/MEDIUM/HIGH"
}}
            """

            try:
                response = generate_content(
                    contents=prompt,
                    model=self.model_name,
                    temperature=0.3,
                    verbose=False,
                    agent_name="news_exit_evaluator"
                )

                # Parse response
                result = json.loads(response.strip().replace('```json', '').replace('```', ''))

                if result.get('should_exit') and result.get('confidence', 0) >= 80:
                    exit_recommendations.append({
                        'stock': stock,
                        'confidence': result['confidence'],
                        'reasoning': result['reasoning'],
                        'urgency': result.get('urgency', 'MEDIUM')
                    })
                    logger.warning(
                        f"NEWS EXIT CANDIDATE: {ticker} "
                        f"(confidence: {result['confidence']}%, urgency: {result['urgency']})"
                    )

            except Exception as e:
                logger.error(f"Failed to evaluate news exit for {ticker}: {e}")

        return exit_recommendations

    def _generate_execution_summary(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Generate summary of executed actions

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Execution summary dict
        """
        from datetime import date, datetime

        try:
            # Get today's transactions
            transactions = self.db.get_transactions(
                portfolio_id=portfolio_id,
                start_date=date.today(),
                end_date=date.today()
            )

            # Get today's rebalancing history
            rebalancing = self.db.get_rebalancing_history(portfolio_id, limit=10)
            # Parse rebalancing_date string to datetime before comparing
            today_rebalancing = []
            for r in rebalancing:
                rebal_date_str = r['rebalancing_date']
                # Handle both datetime strings with time and date-only strings
                if isinstance(rebal_date_str, str):
                    # Try parsing with time first, fall back to date-only
                    try:
                        rebal_date = datetime.fromisoformat(rebal_date_str.replace('Z', '+00:00')).date()
                    except ValueError:
                        rebal_date = datetime.strptime(rebal_date_str[:10], '%Y-%m-%d').date()
                else:
                    rebal_date = rebal_date_str.date() if hasattr(rebal_date_str, 'date') else rebal_date_str

                if rebal_date == date.today():
                    today_rebalancing.append(r)

            summary = {
                'transactions_count': len(transactions),
                'exits_count': len([t for t in transactions if t['transaction_type'] == 'SELL']),
                'entries_count': len([t for t in transactions if t['transaction_type'] == 'BUY']),
                'rebalancing_actions': len(today_rebalancing),
                'transactions': transactions,
                'rebalancing': today_rebalancing
            }

            logger.info(
                f"Execution summary: {summary['exits_count']} exits, "
                f"{summary['entries_count']} entries, "
                f"{summary['rebalancing_actions']} rebalancing actions"
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to generate execution summary: {e}")
            return {'error': str(e)}

    def analyze_portfolio_news(self, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze recent news for all stocks in portfolio

        Args:
            stocks: List of stock dicts

        Returns:
            Dict with news analysis for each stock
        """
        logger.info("Analyzing news for portfolio stocks...")
        news_analysis = {}

        for stock in stocks:
            ticker = stock['ticker']
            name = stock['name']

            # Check cache
            cache_key = hashlib.md5(f"stock_news:{ticker}".encode()).hexdigest()
            if cache_key in self._agent_cache:
                logger.debug(f"Using cached news for {ticker}")
                news_analysis[ticker] = self._agent_cache[cache_key]
                continue

            # Fetch news
            try:
                query = f"News and sentiment analysis for {name} ({ticker}). Focus on news from the last {self.news_lookback_period} only."
                result = run_stock_news(query)

                news_analysis[ticker] = {
                    'sentiment': 'neutral',  # Extract from result
                    'summary': result[:500] if result else 'No recent news',
                    'full_analysis': result
                }

                # Cache result
                self._agent_cache[cache_key] = news_analysis[ticker]
                logger.debug(f"Analyzed news for {ticker}")

            except Exception as e:
                logger.error(f"Failed to analyze news for {ticker}: {e}")
                news_analysis[ticker] = {
                    'sentiment': 'unknown',
                    'summary': f'Error analyzing news: {e}',
                    'full_analysis': ''
                }

        return news_analysis

    def check_investment_triggers(
        self,
        stock: Dict[str, Any],
        news_summary: str
    ) -> Dict[str, Any]:
        """
        Check if exit or review triggers have been hit

        Args:
            stock: Stock dict with investment_view
            news_summary: Recent news summary

        Returns:
            Dict with triggered exit_triggers and review_triggers
        """
        view = stock.get('investment_view', {})
        exit_triggers = view.get('exit_triggers', [])
        review_triggers = view.get('review_triggers', [])

        triggered = {
            'exit_triggers': [],
            'review_triggers': []
        }

        # Simple keyword matching in news (can be enhanced with LLM)
        news_lower = news_summary.lower()

        for trigger in exit_triggers:
            trigger_keywords = trigger.lower().split()
            if any(keyword in news_lower for keyword in trigger_keywords):
                triggered['exit_triggers'].append(trigger)

        for trigger in review_triggers:
            trigger_keywords = trigger.lower().split()
            if any(keyword in news_lower for keyword in trigger_keywords):
                triggered['review_triggers'].append(trigger)

        return triggered

    def update_stock_allocation(
        self,
        portfolio_id: int,
        ticker: str,
        new_allocation_pct: float,
        new_allocation_amount: float,
        reason: str
    ) -> bool:
        """
        Update stock allocation for rebalancing

        Args:
            portfolio_id: Portfolio ID
            ticker: Stock ticker symbol
            new_allocation_pct: New allocation percentage
            new_allocation_amount: New allocation amount in INR
            reason: Reason for change

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get stock record
            stocks = self.db.get_portfolio_stocks(portfolio_id)
            stock = next((s for s in stocks if s['ticker'] == ticker), None)

            if not stock:
                logger.error(f"Stock {ticker} not found in portfolio {portfolio_id}")
                return False

            old_allocation_pct = stock['allocation_pct']
            old_allocation_amount = stock['allocation_amount']

            # Update stock allocation
            sql = """
                UPDATE stocks
                SET allocation_pct = ?, allocation_amount = ?
                WHERE id = ?
            """
            self.db.execute_update(sql, (new_allocation_pct, new_allocation_amount, stock['id']))

            # Record rebalancing in history
            self.db.record_rebalancing(
                portfolio_id=portfolio_id,
                rebalancing_date=datetime.now(),
                reason=reason,
                action_type='ADJUSTMENT',
                affected_stocks=[ticker],
                allocation_changes={
                    ticker: (old_allocation_pct, new_allocation_pct)
                },
                expected_result=f"Adjusted {ticker} from {old_allocation_pct:.1f}% to {new_allocation_pct:.1f}%"
            )

            logger.info(f"Updated {ticker} allocation: {old_allocation_pct:.1f}% → {new_allocation_pct:.1f}%")
            return True

        except Exception as e:
            logger.error(f"Failed to update stock allocation: {e}")
            return False

    def record_position_exit(
        self,
        portfolio_id: int,
        ticker: str,
        exit_price: float,
        exit_reason: str,
        exit_type: str = 'MANUAL'  # 'STOP_LOSS', 'TARGET_HIT', 'MANUAL'
    ) -> bool:
        """
        Record stock exit/sale from portfolio

        Args:
            portfolio_id: Portfolio ID
            ticker: Stock ticker symbol
            exit_price: Price at which stock was sold
            exit_reason: Reason for exit
            exit_type: Type of exit

        Returns:
            True if successful
        """
        try:
            # Get stock record
            stocks = self.db.get_portfolio_stocks(portfolio_id)
            stock = next((s for s in stocks if s['ticker'] == ticker), None)

            if not stock:
                logger.error(f"Stock {ticker} not found in portfolio {portfolio_id}")
                return False

            stock_id = stock['id']
            entry_price = stock['entry_price']
            allocation_amount = stock['allocation_amount']
            quantity = allocation_amount / entry_price

            # Calculate P&L
            gain_loss_pct = (exit_price - entry_price) / entry_price * 100
            gain_loss_absolute = (exit_price - entry_price) * quantity

            # Record sell transaction with P&L and trigger type
            self.db.record_transaction(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                transaction_type='SELL',
                quantity=int(quantity),
                price=exit_price,
                transaction_date=datetime.now(),
                notes=f"{exit_type}: {exit_reason} (P&L: {gain_loss_pct:+.2f}%)",
                realized_pnl_pct=gain_loss_pct,
                realized_pnl_absolute=gain_loss_absolute,
                trigger_type=exit_type
            )

            # Mark stock as inactive and record exit details (don't delete for audit trail)
            self.db.client.table('stocks')\
                .update({
                    'allocation_pct': 0,
                    'allocation_amount': 0,
                    'exit_date': datetime.now().isoformat(),
                    'exit_price': exit_price,
                    'exit_type': exit_type
                })\
                .eq('id', stock_id)\
                .execute()

            # Record market event
            self.db.record_market_event(
                event_type='TRIGGER_HIT' if exit_type in ['STOP_LOSS', 'TARGET_HIT'] else 'INTERNAL',
                title=f"{exit_type}: {ticker} exited",
                description=f"Sold {ticker} at Rs. {exit_price:.2f} ({gain_loss_pct:+.2f}%). Reason: {exit_reason}",
                event_date=datetime.now(),
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                impact='NEGATIVE' if exit_type == 'STOP_LOSS' else 'POSITIVE',
                action_taken='POSITION_CLOSED'
            )

            logger.info(f"Recorded exit: {ticker} at Rs. {exit_price:.2f} ({gain_loss_pct:+.2f}%)")
            return True

        except Exception as e:
            logger.error(f"Failed to record position exit: {e}")
            return False

    def record_position_entry(
        self,
        portfolio_id: int,
        stock_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Add new stock position to portfolio

        Args:
            portfolio_id: Portfolio ID
            stock_data: Stock dict with all required fields (name, ticker, entry_price, etc.)

        Returns:
            stock_id if successful, None otherwise
        """
        try:
            # Validate required fields
            required = ['name', 'ticker', 'entry_price', 'allocation_pct', 'allocation_amount']
            for field in required:
                if field not in stock_data:
                    logger.error(f"Missing required field: {field}")
                    return None

            # Add default values for required fields if not provided
            entry_price = stock_data['entry_price']

            # Set default stop-loss and target if not provided
            if 'stop_loss_pct' not in stock_data:
                stock_data['stop_loss_pct'] = 15.0  # Default aggressive stop-loss
            if 'stop_loss_price' not in stock_data:
                stock_data['stop_loss_price'] = entry_price * (1 - stock_data['stop_loss_pct'] / 100)

            if 'target_pct' not in stock_data:
                stock_data['target_pct'] = 50.0  # Default aggressive target
            if 'target_price' not in stock_data:
                stock_data['target_price'] = entry_price * (1 + stock_data['target_pct'] / 100)

            # Save stock to database
            stock_ids = self.db.save_stocks(portfolio_id, [stock_data])

            if not stock_ids:
                logger.error("Failed to insert stock")
                return None

            stock_id = stock_ids[0]

            # Record buy transaction
            quantity = stock_data['allocation_amount'] / stock_data['entry_price']
            self.db.record_transaction(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                transaction_type='BUY',
                quantity=int(quantity),
                price=stock_data['entry_price'],
                transaction_date=datetime.now(),
                notes=f"New position added: {stock_data.get('rationale', 'No rationale')}"
            )

            logger.info(f"Added new position: {stock_data['ticker']} ({stock_data['allocation_pct']:.1f}%)")
            return stock_id

        except Exception as e:
            logger.error(f"Failed to record position entry: {e}")
            return None

    def generate_recommendation(
        self,
        portfolio: Dict[str, Any],
        current_prices: Dict[str, float],
        price_triggers: Dict[str, List[Dict[str, Any]]],
        news_analysis: Dict[str, Any],
        market_outlook: str,
        performance_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to generate portfolio management recommendation

        Args:
            portfolio: Full portfolio dict
            current_prices: Current prices for all stocks
            price_triggers: Stop-loss/target breaches
            news_analysis: News sentiment for stocks
            market_outlook: General market analysis
            performance_context: Comprehensive performance metrics and benchmark comparison

        Returns:
            Recommendation dict with actions and reasoning
        """
        logger.info("Generating portfolio recommendation using LLM...")

        # Prepare context for LLM
        context = {
            'profile': portfolio['profile'],
            'total_capital': portfolio['total_capital'],
            'num_stocks': len(portfolio['stocks']),
            'price_triggers': {
                'stop_loss_breached': len(price_triggers['stop_loss_breached']),
                'target_reached': len(price_triggers['target_reached']),
                'approaching_target': len(price_triggers['approaching_target'])
            },
            'market_outlook': market_outlook
        }

        # Build detailed analysis
        analysis_parts = []

        # Stop-loss breaches
        if price_triggers['stop_loss_breached']:
            analysis_parts.append("STOP-LOSS BREACHES:")
            for item in price_triggers['stop_loss_breached']:
                stock = item['stock']
                analysis_parts.append(
                    f"- {stock['name']} ({stock['ticker']}): "
                    f"Rs. {item['current_price']:.2f} vs SL Rs. {item['stop_loss_price']:.2f} "
                    f"(P&L: {item['current_pnl_pct']:.2f}%)"
                )

        # Target reached
        if price_triggers['target_reached']:
            analysis_parts.append("\nTARGETS REACHED:")
            for item in price_triggers['target_reached']:
                stock = item['stock']
                analysis_parts.append(
                    f"- {stock['name']} ({stock['ticker']}): "
                    f"Rs. {item['current_price']:.2f} vs Target Rs. {item['target_price']:.2f} "
                    f"(P&L: {item['current_pnl_pct']:.2f}%)"
                )

        # News highlights
        analysis_parts.append("\nNEWS HIGHLIGHTS:")
        for ticker, news in news_analysis.items():
            if news['sentiment'] != 'neutral':
                analysis_parts.append(f"- {ticker}: {news['summary'][:200]}")

        analysis_text = "\n".join(analysis_parts)

        # Build prompt parts
        prompt_parts = [
            f"You are an expert portfolio manager analyzing an {portfolio['profile']} portfolio.",
            "",
            "PORTFOLIO SUMMARY:",
            f"- Profile: {portfolio['profile']}",
            f"- Total Capital: Rs. {portfolio['total_capital']:,.0f}",
            f"- Holdings: {len(portfolio['stocks'])} stocks",
            f"- Stop-loss breaches: {len(price_triggers['stop_loss_breached'])}",
            f"- Targets reached: {len(price_triggers['target_reached'])}",
            f"- Approaching targets: {len(price_triggers['approaching_target'])}"
        ]

        # Add performance context if available
        if performance_context and not performance_context.get('error'):
            prompt_parts.append("")
            prompt_parts.append("=== PERFORMANCE METRICS ===")

            # Log the full performance narrative for debugging
            narrative = performance_context.get('narrative', '')
            if narrative:
                logger.debug(f"Performance narrative being sent to LLM:\n{narrative}")

            prompt_parts.append(narrative)

            # Add structured benchmark data
            benchmarks = performance_context.get('benchmarks', [])
            available_benchmarks = [b for b in benchmarks if b.get('status') == 'available']
            if available_benchmarks:
                prompt_parts.append("")
                prompt_parts.append("=== BENCHMARK COMPARISON ===")
                for bench in available_benchmarks:
                    daily_alpha = bench.get('alpha', {}).get('daily', 0)
                    mtd_alpha = bench.get('alpha', {}).get('mtd', 0)
                    prompt_parts.append(
                        f"{bench['name']}: Daily Alpha {daily_alpha:+.2f}%, MTD Alpha {mtd_alpha:+.2f}%"
                    )

            # Add sector performance
            sectors = performance_context.get('sectors', [])
            if sectors:
                prompt_parts.append("")
                prompt_parts.append("=== SECTOR PERFORMANCE ===")
                for sector in sectors[:5]:  # Top 5 sectors
                    prompt_parts.append(
                        f"{sector['sector']}: {sector['weighted_return']:+.2f}% "
                        f"({sector['total_allocation_pct']:.1f}% allocation)"
                    )

        prompt_parts.extend([
            "",
            "MARKET OUTLOOK:",
            market_outlook,
            "",
            "DETAILED ANALYSIS:",
            analysis_text,
            "",
            "Based on this analysis, provide your recommendation:"
        ])

        # LLM prompt
        prompt = "\n".join(prompt_parts) + """

1. **Overall Assessment**: Brief summary of portfolio health
2. **Immediate Actions**: Any urgent decisions needed (sell/book profits/hold)
3. **Stocks to Review**: Which holdings need closer monitoring
4. **Rebalancing Needed**: Should portfolio be rebalanced?
5. **Confidence Level**: Your confidence in this assessment (0-100%)
6. **Recommendation**: HOLD, BUY_MORE, SELL, or REBALANCE

Provide structured JSON output with keys: assessment, immediate_actions, stocks_to_review, rebalancing_needed, confidence_level, recommendation, reasoning
"""

        try:
            # Call LLM
            response = generate_content(
                contents=prompt,
                model=self.model_name,
                temperature=0.7,
                verbose=True,
                agent_name="portfolio_manager_agent"
            )

            # Parse JSON from response (handle markdown code blocks if present)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]  # Remove ```json
            if response.startswith("```"):
                response = response[3:]  # Remove ```
            if response.endswith("```"):
                response = response[:-3]  # Remove trailing ```
            response = response.strip()

            # Parse response
            recommendation = json.loads(response)
            logger.info(f"Generated recommendation: {recommendation.get('recommendation', 'UNKNOWN')}")

            return recommendation

        except Exception as e:
            logger.error(f"Failed to generate recommendation: {e}")
            return {
                'assessment': 'Error generating recommendation',
                'immediate_actions': [],
                'stocks_to_review': [],
                'rebalancing_needed': False,
                'confidence_level': 0,
                'recommendation': 'HOLD',
                'reasoning': f'Error: {e}'
            }

    def store_manager_update(
        self,
        portfolio_id: int,
        recommendation: Dict[str, Any],
        price_triggers: Dict[str, List[Dict[str, Any]]],
        priority: str = "MEDIUM"
    ) -> int:
        """
        Store manager update in database

        Args:
            portfolio_id: Portfolio ID
            recommendation: LLM recommendation dict
            price_triggers: Triggered stocks
            priority: Update priority

        Returns:
            Update ID
        """
        # Determine affected stocks
        affected_stocks = []

        for item in price_triggers['stop_loss_breached']:
            affected_stocks.append(item['stock']['ticker'])

        for item in price_triggers['target_reached']:
            affected_stocks.append(item['stock']['ticker'])

        # Create title
        if price_triggers['stop_loss_breached']:
            title = f"Stop-Loss Alert: {len(price_triggers['stop_loss_breached'])} stocks breached"
            priority = "HIGH"
        elif price_triggers['target_reached']:
            title = f"Target Achievement: {len(price_triggers['target_reached'])} stocks reached targets"
            priority = "MEDIUM"
        else:
            title = "Daily Portfolio Review"
            priority = "LOW"

        # Store in database
        update_id = self.db.store_manager_update(
            portfolio_id=portfolio_id,
            update_date=date.today(),
            update_type='DAILY_REVIEW',
            title=title,
            description=recommendation.get('assessment', 'Portfolio review completed'),
            affected_stocks=affected_stocks if affected_stocks else None,
            recommendation=recommendation.get('recommendation', 'HOLD'),
            reasoning=recommendation.get('reasoning', ''),
            priority=priority
        )

        logger.info(f"Stored manager update (ID: {update_id})")
        return update_id

    def run(self, profile: str = None) -> Dict[str, Any]:
        """
        Run daily portfolio management analysis

        Args:
            profile: DEPRECATED - Always analyzes latest portfolio

        Returns:
            Analysis results dict
        """
        logger.info("="*80)
        logger.info(f"PORTFOLIO MANAGER - Daily Analysis for LATEST portfolio")
        logger.info("="*80)

        # Step 1: Load portfolio (always latest)
        logger.info("\n[1/10] Loading latest portfolio...")
        portfolio = self.load_portfolio()

        if not portfolio:
            logger.error("Cannot proceed without portfolio")
            return {'success': False, 'error': 'Portfolio not found'}

        stocks = portfolio.get('stocks', [])
        logger.info(f"Portfolio loaded: {len(stocks)} stocks, Rs. {portfolio['total_capital']:,.0f} capital")

        # Get portfolio ID for database operations (find active portfolio)
        all_portfolios = self.db.get_all_portfolios()
        db_portfolio = next((p for p in all_portfolios if p.get('is_active')), None)

        if not db_portfolio:
            logger.error("No active portfolio found in database")
            return {'success': False, 'error': 'No active portfolio found in database'}

        portfolio_id = db_portfolio['id']
        logger.info(f"Managing portfolio ID: {portfolio_id} (Profile: {db_portfolio.get('profile')})")

        # Store portfolio info for execution methods
        self.current_portfolio_id = portfolio_id
        self.current_stocks = stocks

        # Step 2: Get current prices
        logger.info("\n[2/10] Fetching current prices...")
        current_prices = self.get_current_prices(stocks)
        logger.info(f"Fetched prices for {len(current_prices)} stocks")

        # Store for execution methods
        self.current_prices = current_prices

        # Step 3: Persist prices to database
        logger.info("\n[3/10] Persisting daily prices...")
        self.persist_daily_prices(stocks, current_prices)

        # Step 4: Calculate and save portfolio snapshot
        logger.info("\n[4/10] Calculating portfolio snapshot...")
        snapshot_result = self.perf_calculator.generate_portfolio_snapshot(portfolio_id)
        if snapshot_result:
            logger.info(f"Portfolio snapshot saved (ID: {snapshot_result['snapshot_id']})")
        else:
            logger.warning("Failed to generate portfolio snapshot")

        # Step 5: Update benchmark comparisons
        logger.info("\n[5/10] Updating benchmark comparisons...")
        try:
            benchmark_results = self.perf_calculator.update_benchmark_comparisons(portfolio_id)
            if benchmark_results:
                logger.info(f"Updated {len(benchmark_results)} benchmark comparisons")
            else:
                logger.warning("No benchmarks configured for this portfolio")
        except Exception as e:
            logger.error(f"Failed to update benchmark comparisons: {e}")
            # Don't fail entire run if benchmarks fail

        # Step 6: Check price triggers AND auto-execute exits
        logger.info("\n[6/13] Checking stop-loss and target triggers...")
        price_triggers = self.check_price_triggers(stocks, current_prices)

        logger.info(f"Stop-loss breaches: {len(price_triggers['stop_loss_breached'])}")
        logger.info(f"Targets reached: {len(price_triggers['target_reached'])}")
        logger.info(f"Approaching targets: {len(price_triggers['approaching_target'])}")
        logger.info(f"Executed exits: {len(price_triggers.get('executed_exits', []))}")

        # Step 6a: Find and add replacement stocks
        executed_exits = price_triggers.get('executed_exits', [])
        if executed_exits:
            logger.info(f"\n[6a/13] Finding replacement stocks for {len(executed_exits)} exited positions...")
            replacements_added = 0

            for exit_item in executed_exits:
                replacement_id = self._find_and_add_replacement(
                    exited_stock=exit_item['stock'],
                    portfolio_id=portfolio_id,
                    portfolio_profile=db_portfolio['profile']
                )
                if replacement_id:
                    replacements_added += 1

            logger.info(f"✓ Added {replacements_added}/{len(executed_exits)} replacement stocks")

            # Reload portfolio with updated positions
            portfolio = self.load_portfolio()
            stocks = portfolio.get('stocks', [])
            self.current_stocks = stocks

        # Step 7: Analyze news
        logger.info("\n[7/13] Analyzing news for portfolio stocks...")
        news_analysis = self.analyze_portfolio_news(stocks)
        logger.info(f"Analyzed news for {len(news_analysis)} stocks")

        # Step 7a: Evaluate news-driven exit opportunities
        if self.execution_mode == 'full':
            logger.info("\n[7a/13] Evaluating news-driven exit opportunities...")
            news_driven_exits = self._evaluate_news_exits(stocks, news_analysis)

            if news_driven_exits:
                logger.info(f"Found {len(news_driven_exits)} news-driven exit candidates")
                for exit_rec in news_driven_exits:
                    stock = exit_rec['stock']
                    current_price = current_prices.get(stock['ticker'], stock['entry_price'])

                    success = self._execute_triggered_exit(
                        stock=stock,
                        current_price=current_price,
                        trigger_type='NEWS_DRIVEN',
                        reason=f"News-driven exit: {exit_rec['reasoning'][:100]}"
                    )

                    if success:
                        # Add to executed exits for potential replacement
                        executed_exits.append({
                            'stock': stock,
                            'current_price': current_price,
                            'exit_type': 'NEWS_DRIVEN'
                        })

                # Find replacements for news-driven exits if any
                if executed_exits:
                    logger.info(f"\n[7a.1/13] Finding replacements for news-driven exits...")
                    for exit_item in executed_exits:
                        if exit_item.get('exit_type') == 'NEWS_DRIVEN':
                            replacement_id = self._find_and_add_replacement(
                                exited_stock=exit_item['stock'],
                                portfolio_id=portfolio_id,
                                portfolio_profile=db_portfolio['profile']
                            )

                    # Reload portfolio
                    portfolio = self.load_portfolio()
                    stocks = portfolio.get('stocks', [])
                    self.current_stocks = stocks

        # Step 8: Market research
        logger.info("\n[8/13] Researching current market conditions...")
        try:
            market_query = f"Indian stock market trends, Nifty outlook, and sector performance. Focus on developments from the last {self.news_lookback_period} only."
            market_outlook = run_market_research(market_query)
            logger.info("Market research complete")
        except Exception as e:
            logger.error(f"Market research failed: {e}")
            market_outlook = "Market data unavailable"

        # Step 9: Generate performance context
        logger.info("\n[9/13] Generating performance context...")
        performance_context = None
        try:
            performance_context = self.performance_aggregator.generate_context(
                portfolio_id,
                include_benchmarks=True,
                include_sector_breakdown=True,
                include_top_performers=True
            )
            logger.info("Performance context generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate performance context: {e}")
            performance_context = None

        # Step 10: Generate recommendation
        logger.info("\n[10/13] Generating portfolio recommendation...")
        recommendation = self.generate_recommendation(
            portfolio,
            current_prices,
            price_triggers,
            news_analysis,
            market_outlook,
            performance_context
        )

        # Determine priority
        if price_triggers['stop_loss_breached']:
            priority = "CRITICAL" if len(price_triggers['stop_loss_breached']) > 2 else "HIGH"
        elif price_triggers['target_reached']:
            priority = "HIGH"
        else:
            priority = "MEDIUM"

        # Step 11: Store manager update
        logger.info("\n[11/13] Storing manager update in database...")
        update_id = self.store_manager_update(
            portfolio_id,
            recommendation,
            price_triggers,
            priority
        )
        logger.info(f"Manager update stored (ID: {update_id})")

        # Step 12: Generate execution summary
        logger.info("\n[12/13] Generating execution summary...")
        execution_summary = self._generate_execution_summary(portfolio_id)

        # Step 13: Final summary
        logger.info("\n[13/13] PORTFOLIO MANAGER - Analysis Complete")
        logger.info("="*80)
        logger.info(f"Recommendation: {recommendation.get('recommendation', 'UNKNOWN')}")
        logger.info(f"Confidence: {recommendation.get('confidence_level', 0)}%")
        logger.info(f"Priority: {priority}")
        logger.info(f"Executions: {execution_summary.get('exits_count', 0)} exits, {execution_summary.get('entries_count', 0)} entries")
        logger.info("="*80)

        return {
            'success': True,
            'portfolio': portfolio,
            'current_prices': current_prices,
            'price_triggers': price_triggers,
            'news_analysis': news_analysis,
            'market_outlook': market_outlook,
            'recommendation': recommendation,
            'priority': priority,
            'execution_summary': execution_summary
        }


def run_portfolio_manager(profile: str = None, model_name: str = None) -> Dict[str, Any]:
    """
    Convenience function to run portfolio manager

    Args:
        profile: DEPRECATED - Always manages latest portfolio
        model_name: Optional model name override

    Returns:
        Analysis results dict
    """
    from utils.metrics_collector import get_metrics_collector

    if profile:
        logger.warning(f"Profile parameter '{profile}' is deprecated. Managing latest portfolio.")

    manager = PortfolioManagerAgent(model_name=model_name)
    result = manager.run()

    # Print metrics summary
    metrics_collector = get_metrics_collector()
    metrics_collector.print_summary()

    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Portfolio Manager Agent - Always manages LATEST portfolio',
        epilog='Note: Portfolio manager always works with the latest portfolio (by created_at). '
               'Use scripts/ensure_latest_portfolio_active.py to verify correct portfolio is active.'
    )
    parser.add_argument(
        '--profile',
        type=str,
        default=None,
        help='DEPRECATED - Portfolio manager always uses latest portfolio'
    )
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='LLM model to use (defaults to high-tier model)'
    )

    args = parser.parse_args()

    if args.profile:
        print(f"⚠️  Warning: --profile parameter is deprecated. Managing latest portfolio instead.\n")

    # Run manager (always uses latest portfolio)
    result = run_portfolio_manager(model_name=args.model)

    if result['success']:
        print("\n" + "="*80)
        print("RECOMMENDATION SUMMARY")
        print("="*80)
        rec = result['recommendation']
        print(f"Action: {rec.get('recommendation', 'UNKNOWN')}")
        print(f"Confidence: {rec.get('confidence_level', 0)}%")
        print(f"\nAssessment:\n{rec.get('assessment', 'N/A')}")
        print(f"\nReasoning:\n{rec.get('reasoning', 'N/A')}")
        print("="*80)
    else:
        print(f"\nError: {result.get('error', 'Unknown error')}")
