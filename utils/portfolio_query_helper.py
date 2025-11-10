"""
Portfolio Query Helper
Provides convenience functions for portfolio manager to query portfolio data
"""

from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.db_service import get_db_service

logger = get_logger("utils.portfolio_query_helper")


class PortfolioQueryHelper:
    """Helper class for common portfolio queries"""

    def __init__(self):
        """Initialize query helper"""
        self.db_service = get_db_service()

    # ==================== Portfolio Loading ====================

    def load_latest_portfolio(self, profile: str) -> Optional[Dict[str, Any]]:
        """
        Load the latest active portfolio for a profile

        Args:
            profile: 'aggressive' or 'defensive'

        Returns:
            Portfolio with stocks and metadata
        """
        logger.info(f"Loading latest portfolio for {profile}")

        try:
            portfolio = self.db_service.get_active_portfolio(profile)

            if not portfolio:
                logger.warning(f"No active portfolio found for {profile}")
                return None

            portfolio_id = portfolio['id']

            # Get all stocks
            stocks = self.db_service.get_portfolio_stocks(portfolio_id)

            # Get investment views
            for stock in stocks:
                view = self.db_service.get_investment_view(stock['id'])
                if view:
                    stock['investment_view'] = view

                metrics = self.db_service.get_key_metrics(stock['id'])
                if metrics:
                    stock['key_metrics'] = metrics.get('metrics_json', {})

            return {
                'portfolio': portfolio,
                'stocks': stocks,
                'total_stocks': len(stocks)
            }

        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
            return None

    # ==================== Risk Monitoring ====================

    def check_stop_loss_hits(
        self,
        portfolio_id: int,
        current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Check which stocks have hit stop-loss levels

        Args:
            portfolio_id: Portfolio ID
            current_prices: Dictionary of {ticker: current_price}

        Returns:
            List of stocks that hit stop-loss
        """
        logger.info(f"Checking stop-loss levels for portfolio {portfolio_id}")

        stops_hit = []

        try:
            stocks = self.db_service.get_portfolio_stocks(portfolio_id)

            for stock in stocks:
                ticker = stock['ticker']
                current_price = current_prices.get(ticker)

                if current_price is None:
                    logger.warning(f"No price data for {ticker}")
                    continue

                if current_price <= stock['stop_loss_price']:
                    stop_loss_detail = {
                        'ticker': ticker,
                        'name': stock['name'],
                        'entry_price': stock['entry_price'],
                        'current_price': current_price,
                        'stop_loss_price': stock['stop_loss_price'],
                        'loss_pct': ((current_price - stock['entry_price']) / stock['entry_price'] * 100),
                        'allocation_pct': stock['allocation_pct'],
                        'allocation_amount': stock['allocation_amount']
                    }
                    stops_hit.append(stop_loss_detail)

                    logger.warning(f"STOP-LOSS HIT: {ticker} at {current_price} (limit: {stock['stop_loss_price']})")

            return stops_hit

        except Exception as e:
            logger.error(f"Error checking stop-loss: {e}")
            return []

    def check_target_hits(
        self,
        portfolio_id: int,
        current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Check which stocks have hit target levels

        Args:
            portfolio_id: Portfolio ID
            current_prices: Dictionary of {ticker: current_price}

        Returns:
            List of stocks that hit target
        """
        logger.info(f"Checking target levels for portfolio {portfolio_id}")

        targets_hit = []

        try:
            stocks = self.db_service.get_portfolio_stocks(portfolio_id)

            for stock in stocks:
                ticker = stock['ticker']
                current_price = current_prices.get(ticker)

                if current_price is None:
                    continue

                if current_price >= stock['target_price']:
                    target_detail = {
                        'ticker': ticker,
                        'name': stock['name'],
                        'entry_price': stock['entry_price'],
                        'current_price': current_price,
                        'target_price': stock['target_price'],
                        'gain_pct': ((current_price - stock['entry_price']) / stock['entry_price'] * 100),
                        'allocation_pct': stock['allocation_pct'],
                        'allocation_amount': stock['allocation_amount']
                    }
                    targets_hit.append(target_detail)

                    logger.info(f"TARGET HIT: {ticker} at {current_price} (target: {stock['target_price']})")

            return targets_hit

        except Exception as e:
            logger.error(f"Error checking targets: {e}")
            return []

    # ==================== Performance Analysis ====================

    def get_current_performance(
        self,
        portfolio_id: int,
        current_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate current portfolio performance

        Args:
            portfolio_id: Portfolio ID
            current_prices: Current prices for all stocks

        Returns:
            Performance summary
        """
        logger.info(f"Calculating current performance for portfolio {portfolio_id}")

        try:
            portfolio = self.db_service.get_portfolio_by_id(portfolio_id)
            stocks = self.db_service.get_portfolio_stocks(portfolio_id)

            total_invested = sum(s['allocation_amount'] for s in stocks)
            total_current_value = 0
            stock_performances = []

            for stock in stocks:
                ticker = stock['ticker']
                current_price = current_prices.get(ticker, stock['entry_price'])

                # Calculate unrealized P&L
                quantity = stock['allocation_amount'] / stock['entry_price']
                current_value = quantity * current_price
                gain_loss = current_value - stock['allocation_amount']
                gain_loss_pct = (gain_loss / stock['allocation_amount'] * 100) if stock['allocation_amount'] > 0 else 0

                total_current_value += current_value

                stock_performances.append({
                    'ticker': ticker,
                    'name': stock['name'],
                    'sector': stock['sector'],
                    'invested': stock['allocation_amount'],
                    'current_value': current_value,
                    'gain_loss': gain_loss,
                    'gain_loss_pct': gain_loss_pct,
                    'entry_price': stock['entry_price'],
                    'current_price': current_price,
                    'stop_loss_price': stock['stop_loss_price'],
                    'target_price': stock['target_price'],
                    'allocation_pct': stock['allocation_pct']
                })

            overall_gain_loss = total_current_value - total_invested
            overall_gain_loss_pct = (overall_gain_loss / total_invested * 100) if total_invested > 0 else 0

            return {
                'portfolio_id': portfolio_id,
                'profile': portfolio['profile'],
                'total_invested': total_invested,
                'total_current_value': total_current_value,
                'total_gain_loss': overall_gain_loss,
                'total_gain_loss_pct': overall_gain_loss_pct,
                'stock_count': len(stocks),
                'stocks': sorted(stock_performances, key=lambda x: x['gain_loss_pct'], reverse=True),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            return {'error': str(e)}

    # ==================== Trigger Detection ====================

    def check_investment_view_triggers(
        self,
        portfolio_id: int,
        fundamental_changes: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Check if any stocks have violated investment view exit/review triggers

        Args:
            portfolio_id: Portfolio ID
            fundamental_changes: Changes in fundamentals for stocks
                                {ticker: {metric: value}}

        Returns:
            List of stocks with triggered conditions
        """
        logger.info(f"Checking investment view triggers for portfolio {portfolio_id}")

        triggered = []

        try:
            stocks = self.db_service.get_portfolio_stocks(portfolio_id)

            for stock in stocks:
                ticker = stock['ticker']
                view = self.db_service.get_investment_view(stock['id'])

                if not view:
                    continue

                changes = fundamental_changes.get(ticker, {})

                if not changes:
                    continue

                # Check exit triggers
                exit_triggers = view.get('exit_triggers', [])
                review_triggers = view.get('review_triggers', [])

                triggered_exits = []
                triggered_reviews = []

                # This is simplified - in production, you'd need to evaluate these properly
                for trigger in exit_triggers:
                    # Check if any key from trigger appears in changes
                    if any(key.lower() in str(changes).lower() for key in [ticker]):
                        triggered_exits.append(trigger)

                for trigger in review_triggers:
                    if any(key.lower() in str(changes).lower() for key in [ticker]):
                        triggered_reviews.append(trigger)

                if triggered_exits or triggered_reviews:
                    triggered.append({
                        'ticker': ticker,
                        'name': stock['name'],
                        'exit_triggers_hit': triggered_exits,
                        'review_triggers_hit': triggered_reviews,
                        'fundamental_changes': changes
                    })

            return triggered

        except Exception as e:
            logger.error(f"Error checking triggers: {e}")
            return []

    # ==================== Recommendation Generation ====================

    def generate_rebalancing_recommendation(
        self,
        portfolio_id: int,
        current_prices: Dict[str, float],
        allocation_drift_threshold: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        Generate rebalancing recommendation based on allocation drift

        Args:
            portfolio_id: Portfolio ID
            current_prices: Current prices for all stocks
            allocation_drift_threshold: Threshold % for drift to trigger rebalancing

        Returns:
            Rebalancing recommendation or None if no rebalancing needed
        """
        logger.info(f"Generating rebalancing recommendation for portfolio {portfolio_id}")

        try:
            portfolio = self.db_service.get_portfolio_by_id(portfolio_id)
            stocks = self.db_service.get_portfolio_stocks(portfolio_id)

            # Calculate current allocations
            total_value = 0
            stock_values = {}

            for stock in stocks:
                ticker = stock['ticker']
                current_price = current_prices.get(ticker, stock['entry_price'])
                quantity = stock['allocation_amount'] / stock['entry_price']
                value = quantity * current_price
                stock_values[ticker] = {
                    'value': value,
                    'current_pct': 0,  # Will calculate below
                    'target_pct': stock['allocation_pct']
                }
                total_value += value

            # Calculate current percentages
            for ticker in stock_values:
                stock_values[ticker]['current_pct'] = (stock_values[ticker]['value'] / total_value * 100) if total_value > 0 else 0

            # Check for drift
            drifts = []
            for ticker, values in stock_values.items():
                drift = abs(values['current_pct'] - values['target_pct'])
                if drift > allocation_drift_threshold:
                    drifts.append({
                        'ticker': ticker,
                        'target_pct': values['target_pct'],
                        'current_pct': values['current_pct'],
                        'drift_pct': drift,
                        'direction': 'over' if values['current_pct'] > values['target_pct'] else 'under'
                    })

            if drifts:
                recommendation = {
                    'portfolio_id': portfolio_id,
                    'action_needed': 'REBALANCE',
                    'reason': f"Allocation drift exceeds {allocation_drift_threshold}%",
                    'drifts': sorted(drifts, key=lambda x: x['drift_pct'], reverse=True),
                    'total_portfolio_value': total_value,
                    'timestamp': datetime.now().isoformat()
                }

                logger.info(f"Rebalancing recommended: {len(drifts)} stocks with significant drift")
                return recommendation
            else:
                logger.info("Portfolio allocation within drift threshold, no rebalancing needed")
                return None

        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return None

    # ==================== History Queries ====================

    def get_recent_transactions(
        self,
        portfolio_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent transactions"""
        from datetime import date, timedelta

        start_date = date.today() - timedelta(days=days)
        return self.db_service.get_transactions(
            portfolio_id=portfolio_id,
            start_date=start_date
        )

    def get_rebalancing_history(
        self,
        portfolio_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get rebalancing history"""
        return self.db_service.get_rebalancing_history(
            portfolio_id=portfolio_id,
            limit=limit
        )

    def get_recent_market_events(
        self,
        portfolio_id: int,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent market events"""
        from datetime import date, timedelta

        start_date = date.today() - timedelta(days=days)
        return self.db_service.get_market_events(
            portfolio_id=portfolio_id,
            start_date=start_date
        )


# Singleton instance
_query_helper = None


def get_portfolio_helper() -> PortfolioQueryHelper:
    """Get portfolio query helper singleton"""
    global _query_helper
    if _query_helper is None:
        _query_helper = PortfolioQueryHelper()
    return _query_helper
