"""
Portfolio Manager Agent
Monitors existing portfolio and generates daily analysis, recommendations, and rebalancing decisions
"""

import json
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.llm_service import get_llm_service
from utils.db_service import get_db_service
from tools.price_fetcher import get_price_fetcher
from tools.performance_calculator import get_performance_calculator
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
        self.llm = get_llm_service()
        self.db = get_db_service()
        self.price_fetcher = get_price_fetcher()
        self.perf_calculator = get_performance_calculator()
        self.model_name = model_name or "high"  # Use high-tier model for strategic decisions
        self._agent_cache: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, str]] = []

    def load_portfolio(self, profile: str = "aggressive") -> Optional[Dict[str, Any]]:
        """
        Load latest portfolio for the given profile

        Args:
            profile: Portfolio profile ('aggressive' or 'defensive')

        Returns:
            Portfolio dict or None if not found
        """
        latest_file = PORTFOLIOS_DIR / f"latest_{profile}.json"

        if not latest_file.exists():
            logger.error(f"No portfolio found for profile: {profile}")
            return None

        try:
            with open(latest_file, 'r') as f:
                portfolio = json.load(f)
            logger.info(f"Loaded portfolio: {len(portfolio.get('stocks', []))} stocks")
            return portfolio
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
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
                query = f"Recent news and sentiment analysis for {name} ({ticker})"
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

    def generate_recommendation(
        self,
        portfolio: Dict[str, Any],
        current_prices: Dict[str, float],
        price_triggers: Dict[str, List[Dict[str, Any]]],
        news_analysis: Dict[str, Any],
        market_outlook: str
    ) -> Dict[str, Any]:
        """
        Use LLM to generate portfolio management recommendation

        Args:
            portfolio: Full portfolio dict
            current_prices: Current prices for all stocks
            price_triggers: Stop-loss/target breaches
            news_analysis: News sentiment for stocks
            market_outlook: General market analysis

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

        # LLM prompt
        prompt = f"""You are an expert portfolio manager analyzing an {portfolio['profile']} portfolio.

PORTFOLIO SUMMARY:
- Profile: {portfolio['profile']}
- Total Capital: Rs. {portfolio['total_capital']:,.0f}
- Holdings: {len(portfolio['stocks'])} stocks
- Stop-loss breaches: {len(price_triggers['stop_loss_breached'])}
- Targets reached: {len(price_triggers['target_reached'])}
- Approaching targets: {len(price_triggers['approaching_target'])}

MARKET OUTLOOK:
{market_outlook}

DETAILED ANALYSIS:
{analysis_text}

Based on this analysis, provide your recommendation:

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
            response = self.llm.generate(
                prompt,
                model_tier=self.model_name,
                response_format="json"
            )

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
            confidence_score=recommendation.get('confidence_level', 50),
            priority=priority
        )

        logger.info(f"Stored manager update (ID: {update_id})")
        return update_id

    def run(self, profile: str = "aggressive") -> Dict[str, Any]:
        """
        Run daily portfolio management analysis

        Args:
            profile: Portfolio profile to analyze

        Returns:
            Analysis results dict
        """
        logger.info("="*80)
        logger.info(f"PORTFOLIO MANAGER - Daily Analysis for {profile.upper()} portfolio")
        logger.info("="*80)

        # Step 1: Load portfolio
        logger.info("\n[1/6] Loading portfolio...")
        portfolio = self.load_portfolio(profile)

        if not portfolio:
            logger.error("Cannot proceed without portfolio")
            return {'success': False, 'error': 'Portfolio not found'}

        stocks = portfolio.get('stocks', [])
        logger.info(f"Portfolio loaded: {len(stocks)} stocks, Rs. {portfolio['total_capital']:,.0f} capital")

        # Step 2: Get current prices
        logger.info("\n[2/6] Fetching current prices...")
        current_prices = self.get_current_prices(stocks)
        logger.info(f"Fetched prices for {len(current_prices)} stocks")

        # Step 3: Check price triggers
        logger.info("\n[3/6] Checking stop-loss and target triggers...")
        price_triggers = self.check_price_triggers(stocks, current_prices)

        logger.info(f"Stop-loss breaches: {len(price_triggers['stop_loss_breached'])}")
        logger.info(f"Targets reached: {len(price_triggers['target_reached'])}")
        logger.info(f"Approaching targets: {len(price_triggers['approaching_target'])}")

        # Step 4: Analyze news
        logger.info("\n[4/6] Analyzing news for portfolio stocks...")
        news_analysis = self.analyze_portfolio_news(stocks)
        logger.info(f"Analyzed news for {len(news_analysis)} stocks")

        # Step 5: Market research
        logger.info("\n[5/6] Researching current market conditions...")
        try:
            market_query = "Current Indian stock market trends, Nifty outlook, and sector performance"
            market_outlook = run_market_research(market_query)
            logger.info("Market research complete")
        except Exception as e:
            logger.error(f"Market research failed: {e}")
            market_outlook = "Market data unavailable"

        # Step 6: Generate recommendation
        logger.info("\n[6/6] Generating portfolio recommendation...")
        recommendation = self.generate_recommendation(
            portfolio,
            current_prices,
            price_triggers,
            news_analysis,
            market_outlook
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

        # Get portfolio ID from database
        db_portfolio = self.db.execute_query(
            "SELECT id FROM portfolios WHERE profile = ? AND is_active = 1 LIMIT 1",
            (profile,)
        )

        if db_portfolio:
            portfolio_id = db_portfolio[0]['id']
            update_id = self.store_manager_update(
                portfolio_id,
                recommendation,
                price_triggers,
                priority
            )
            logger.info(f"Manager update stored (ID: {update_id})")
        else:
            logger.warning("Portfolio not found in database, update not stored")

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


def run_portfolio_manager(profile: str = "aggressive", model_name: str = None) -> Dict[str, Any]:
    """
    Convenience function to run portfolio manager

    Args:
        profile: Portfolio profile ('aggressive' or 'defensive')
        model_name: Optional model name override

    Returns:
        Analysis results dict
    """
    manager = PortfolioManagerAgent(model_name=model_name)
    return manager.run(profile)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Portfolio Manager Agent')
    parser.add_argument(
        '--profile',
        type=str,
        default='aggressive',
        choices=['aggressive', 'defensive'],
        help='Portfolio profile to analyze'
    )
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='LLM model to use (defaults to high-tier model)'
    )

    args = parser.parse_args()

    # Run manager
    result = run_portfolio_manager(args.profile, args.model)

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
