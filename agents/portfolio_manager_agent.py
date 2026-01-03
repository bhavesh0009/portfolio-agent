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

        # Load news lookback period from config (default 5d for daily execution)
        config = configparser.ConfigParser()
        config_path = Path(__file__).parent.parent / 'config.ini'
        if config_path.exists():
            config.read(config_path)
            self.news_lookback_period = config.get('NEWS', 'news_lookback_period', fallback='5d')
        else:
            self.news_lookback_period = '5d'
        logger.debug(f"Portfolio manager news lookback period: {self.news_lookback_period}")

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

        Args:
            stocks: List of stock dicts
            current_prices: Dict of current prices

        Returns:
            Dict with 'stop_loss_breached', 'target_reached', 'approaching_target'
        """
        triggers = {
            'stop_loss_breached': [],
            'target_reached': [],
            'approaching_target': []  # Within 5% of target
        }

        for stock in stocks:
            ticker = stock['ticker']
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

        return triggers

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
            quantity = stock['allocation_amount'] / entry_price

            # Calculate P&L
            gain_loss_pct = (exit_price - entry_price) / entry_price * 100

            # Record sell transaction
            self.db.record_transaction(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                transaction_type='SELL',
                quantity=int(quantity),
                price=exit_price,
                transaction_date=datetime.now(),
                notes=f"{exit_type}: {exit_reason} (P&L: {gain_loss_pct:+.2f}%)"
            )

            # Mark stock as inactive (don't delete for audit trail)
            sql = "UPDATE stocks SET allocation_pct = 0, allocation_amount = 0 WHERE id = ?"
            self.db.execute_update(sql, (stock_id,))

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

        # Step 2: Get current prices
        logger.info("\n[2/10] Fetching current prices...")
        current_prices = self.get_current_prices(stocks)
        logger.info(f"Fetched prices for {len(current_prices)} stocks")

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

        # Step 6: Check price triggers
        logger.info("\n[6/10] Checking stop-loss and target triggers...")
        price_triggers = self.check_price_triggers(stocks, current_prices)

        logger.info(f"Stop-loss breaches: {len(price_triggers['stop_loss_breached'])}")
        logger.info(f"Targets reached: {len(price_triggers['target_reached'])}")
        logger.info(f"Approaching targets: {len(price_triggers['approaching_target'])}")

        # Step 7: Analyze news
        logger.info("\n[7/10] Analyzing news for portfolio stocks...")
        news_analysis = self.analyze_portfolio_news(stocks)
        logger.info(f"Analyzed news for {len(news_analysis)} stocks")

        # Step 8: Market research
        logger.info("\n[8/10] Researching current market conditions...")
        try:
            market_query = f"Indian stock market trends, Nifty outlook, and sector performance. Focus on developments from the last {self.news_lookback_period} only."
            market_outlook = run_market_research(market_query)
            logger.info("Market research complete")
        except Exception as e:
            logger.error(f"Market research failed: {e}")
            market_outlook = "Market data unavailable"

        # Step 9: Generate performance context
        logger.info("\n[9/10] Generating performance context...")
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
        logger.info("\n[10/10] Generating portfolio recommendation...")
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

        # Store update in database
        logger.info("\nStoring manager update in database...")
        update_id = self.store_manager_update(
            portfolio_id,
            recommendation,
            price_triggers,
            priority
        )
        logger.info(f"Manager update stored (ID: {update_id})")

        # Summary
        logger.info("\n" + "="*80)
        logger.info("PORTFOLIO MANAGER - Analysis Complete")
        logger.info("="*80)
        logger.info(f"Recommendation: {recommendation.get('recommendation', 'UNKNOWN')}")
        logger.info(f"Confidence: {recommendation.get('confidence_level', 0)}%")
        logger.info(f"Priority: {priority}")
        logger.info("="*80)

        return {
            'success': True,
            'portfolio': portfolio,
            'current_prices': current_prices,
            'price_triggers': price_triggers,
            'news_analysis': news_analysis,
            'market_outlook': market_outlook,
            'recommendation': recommendation,
            'priority': priority
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
