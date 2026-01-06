"""
Execution State Tracker

Manages daily transaction counts and execution budget to enforce transaction limits
and prevent runaway trading.
"""

from datetime import date
from typing import Dict, Tuple
from configparser import ConfigParser

from utils.logger import get_logger
from utils.db_service import get_db_service

logger = get_logger(__name__)


class ExecutionStateTracker:
    """Track daily transaction counts and enforce execution limits"""

    def __init__(self, config: ConfigParser = None):
        """
        Initialize execution state tracker

        Args:
            config: ConfigParser instance. If None, loads from config.ini
        """
        self.db = get_db_service()

        if config is None:
            config = ConfigParser()
            config.read('config.ini')

        self.config = config
        self.max_daily_exits = config.getint('EXECUTION', 'max_daily_exits', fallback=3)
        self.max_daily_entries = config.getint('EXECUTION', 'max_daily_entries', fallback=3)
        self.max_daily_total = config.getint('EXECUTION', 'max_daily_total_transactions', fallback=5)

        logger.debug(
            f"Initialized ExecutionStateTracker: "
            f"max_exits={self.max_daily_exits}, "
            f"max_entries={self.max_daily_entries}, "
            f"max_total={self.max_daily_total}"
        )

    def get_daily_transaction_count(self, portfolio_id: int, target_date: date = None) -> Dict[str, int]:
        """
        Get transaction counts for a specific date

        Args:
            portfolio_id: Portfolio ID
            target_date: Date to check (defaults to today)

        Returns:
            Dict with 'BUY', 'SELL', and 'TOTAL' counts
        """
        if target_date is None:
            target_date = date.today()

        try:
            # Query transactions table for the given date
            transactions = self.db.get_transactions(
                portfolio_id=portfolio_id,
                start_date=target_date,
                end_date=target_date
            )

            counts = {
                'BUY': 0,
                'SELL': 0,
                'TOTAL': 0
            }

            for txn in transactions:
                txn_type = txn['transaction_type']
                counts[txn_type] = counts.get(txn_type, 0) + 1
                counts['TOTAL'] += 1

            logger.debug(
                f"Transaction counts for portfolio {portfolio_id} on {target_date}: "
                f"BUY={counts['BUY']}, SELL={counts['SELL']}, TOTAL={counts['TOTAL']}"
            )

            return counts

        except Exception as e:
            logger.error(f"Failed to get transaction count: {e}")
            # Return empty counts on error (fail-safe)
            return {'BUY': 0, 'SELL': 0, 'TOTAL': 0}

    def can_execute_transaction(
        self,
        portfolio_id: int,
        transaction_type: str
    ) -> Tuple[bool, str]:
        """
        Check if a transaction can be executed within daily limits

        Args:
            portfolio_id: Portfolio ID
            transaction_type: 'BUY' or 'SELL'

        Returns:
            Tuple of (can_execute: bool, reason: str)
        """
        counts = self.get_daily_transaction_count(portfolio_id)

        # Check total transaction limit
        if counts['TOTAL'] >= self.max_daily_total:
            reason = f"Daily transaction limit reached ({self.max_daily_total})"
            logger.warning(reason)
            return False, reason

        # Check transaction type specific limits
        if transaction_type == 'SELL':
            if counts.get('SELL', 0) >= self.max_daily_exits:
                reason = f"Daily exit limit reached ({self.max_daily_exits})"
                logger.warning(reason)
                return False, reason

        elif transaction_type == 'BUY':
            if counts.get('BUY', 0) >= self.max_daily_entries:
                reason = f"Daily entry limit reached ({self.max_daily_entries})"
                logger.warning(reason)
                return False, reason

        # Calculate remaining budget
        remaining = self.max_daily_total - counts['TOTAL']
        reason = f"Can execute ({remaining} transactions remaining today)"
        logger.debug(reason)

        return True, reason

    def get_execution_budget(self, portfolio_id: int) -> Dict[str, int]:
        """
        Get remaining execution budget for today

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Dict with remaining counts for 'BUY', 'SELL', and 'TOTAL'
        """
        counts = self.get_daily_transaction_count(portfolio_id)

        budget = {
            'BUY': max(0, self.max_daily_entries - counts.get('BUY', 0)),
            'SELL': max(0, self.max_daily_exits - counts.get('SELL', 0)),
            'TOTAL': max(0, self.max_daily_total - counts['TOTAL'])
        }

        logger.debug(
            f"Execution budget for portfolio {portfolio_id}: "
            f"BUY={budget['BUY']}, SELL={budget['SELL']}, TOTAL={budget['TOTAL']}"
        )

        return budget

    def reset_daily_counters(self) -> None:
        """
        Reset daily counters (typically called at midnight or first run of new day)

        Note: This is informational only. Actual counts are always queried from database.
        """
        logger.info("Daily counter reset triggered (counts are always queried from database)")
