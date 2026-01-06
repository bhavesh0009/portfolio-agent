"""
Execution Decision Engine

Central decision-making logic for automatic portfolio execution.
Evaluates execution decisions based on confidence thresholds, transaction limits,
and risk guardrails.
"""

from typing import Dict, Any, Tuple, List
from configparser import ConfigParser

from utils.logger import get_logger
from utils.db_service import get_db_service
from utils.execution_state import ExecutionStateTracker

logger = get_logger(__name__)


class ExecutionEngine:
    """Central decision-making engine for portfolio execution"""

    def __init__(self, config: ConfigParser = None):
        """
        Initialize execution engine

        Args:
            config: ConfigParser instance. If None, loads from config.ini
        """
        if config is None:
            config = ConfigParser()
            config.read('config.ini')

        self.config = config
        self.execution_mode = config.get('EXECUTION', 'execution_mode', fallback='manual')
        self.state_tracker = ExecutionStateTracker(config)
        self.db = get_db_service()

        # Load confidence thresholds
        self.price_trigger_confidence = config.getfloat('EXECUTION', 'price_trigger_confidence', fallback=100.0)
        self.news_exit_confidence = config.getfloat('EXECUTION', 'news_exit_confidence', fallback=80.0)
        self.rebalancing_confidence = config.getfloat('EXECUTION', 'rebalancing_confidence', fallback=75.0)

        # Load risk guardrails
        self.enforce_sector_limits = config.getboolean('EXECUTION', 'enforce_sector_limits', fallback=True)
        self.max_sector_pct = config.getfloat('EXECUTION', 'max_sector_allocation_pct', fallback=40.0)
        self.min_position_size = config.getfloat('EXECUTION', 'min_position_size_pct', fallback=5.0)
        self.max_position_size = config.getfloat('EXECUTION', 'max_position_size_pct', fallback=25.0)

        logger.info(
            f"ExecutionEngine initialized: mode={self.execution_mode}, "
            f"sector_limits={self.enforce_sector_limits}, "
            f"max_sector={self.max_sector_pct}%, "
            f"position_size={self.min_position_size}-{self.max_position_size}%"
        )

    def should_execute_exit(
        self,
        portfolio_id: int,
        stock: Dict[str, Any],
        trigger_type: str,
        confidence: float,
        reasoning: str
    ) -> Tuple[bool, str]:
        """
        Decide if an exit should be auto-executed

        Args:
            portfolio_id: Portfolio ID
            stock: Stock dict with ticker, allocation, etc.
            trigger_type: 'STOP_LOSS', 'TARGET_HIT', 'NEWS_DRIVEN', 'LLM_RECOMMENDATION'
            confidence: Confidence score (0-100)
            reasoning: Human-readable reasoning

        Returns:
            Tuple of (should_execute: bool, reason: str)
        """
        ticker = stock.get('ticker', 'UNKNOWN')

        logger.info("="*80)
        logger.info(f"EXECUTION DECISION: EXIT {ticker}")
        logger.info(f"  Trigger Type: {trigger_type}")
        logger.info(f"  Confidence: {confidence}%")
        logger.info(f"  Execution Mode: {self.execution_mode}")
        logger.info("="*80)

        # Check execution mode
        if self.execution_mode == 'manual':
            reason = "Manual mode - execution disabled"
            logger.info(f"  Decision: SKIP ({reason})")
            return False, reason

        if self.execution_mode == 'price-only':
            if trigger_type not in ['STOP_LOSS', 'TARGET_HIT']:
                reason = f"Price-only mode - {trigger_type} not executed"
                logger.info(f"  Decision: SKIP ({reason})")
                return False, reason

        # Check confidence threshold
        required_confidence = self.price_trigger_confidence
        if trigger_type in ['NEWS_DRIVEN', 'LLM_RECOMMENDATION']:
            required_confidence = self.news_exit_confidence

        if confidence < required_confidence:
            reason = f"Confidence too low ({confidence}% < {required_confidence}%)"
            logger.warning(f"  Decision: SKIP ({reason})")
            return False, reason

        # Check transaction limits
        can_execute, limit_reason = self.state_tracker.can_execute_transaction(
            portfolio_id,
            'SELL'
        )

        if not can_execute:
            logger.warning(f"  Decision: SKIP ({limit_reason})")
            return False, limit_reason

        # All checks passed
        reason = f"Approved for execution ({limit_reason})"
        logger.info(f"  Decision: EXECUTE ({reason})")
        return True, reason

    def should_execute_entry(
        self,
        portfolio_id: int,
        stock_data: Dict[str, Any],
        confidence: float,
        replacement_for: str = None
    ) -> Tuple[bool, str]:
        """
        Decide if an entry should be auto-executed

        Args:
            portfolio_id: Portfolio ID
            stock_data: Stock data dict with ticker, allocation_pct, sector, etc.
            confidence: Confidence score (0-100)
            replacement_for: Ticker being replaced (optional)

        Returns:
            Tuple of (should_execute: bool, reason: str)
        """
        ticker = stock_data.get('ticker', 'UNKNOWN')

        logger.info("="*80)
        logger.info(f"EXECUTION DECISION: ENTRY {ticker}")
        logger.info(f"  Replacement for: {replacement_for or 'N/A'}")
        logger.info(f"  Confidence: {confidence}%")
        logger.info(f"  Allocation: {stock_data.get('allocation_pct', 0):.2f}%")
        logger.info(f"  Sector: {stock_data.get('sector', 'Unknown')}")
        logger.info("="*80)

        # Check execution mode
        if self.execution_mode == 'manual':
            reason = "Manual mode - execution disabled"
            logger.info(f"  Decision: SKIP ({reason})")
            return False, reason

        if self.execution_mode == 'price-only':
            reason = "Price-only mode - entries not executed"
            logger.info(f"  Decision: SKIP ({reason})")
            return False, reason

        # Check confidence threshold
        if confidence < self.rebalancing_confidence:
            reason = f"Confidence too low ({confidence}% < {self.rebalancing_confidence}%)"
            logger.warning(f"  Decision: SKIP ({reason})")
            return False, reason

        # Check transaction limits
        can_execute, limit_reason = self.state_tracker.can_execute_transaction(
            portfolio_id,
            'BUY'
        )

        if not can_execute:
            logger.warning(f"  Decision: SKIP ({limit_reason})")
            return False, limit_reason

        # Check position sizing
        valid_size, size_reason = self._check_position_size(stock_data.get('allocation_pct', 0))
        if not valid_size:
            logger.warning(f"  Decision: SKIP ({size_reason})")
            return False, size_reason

        # Check sector limits
        valid_sector, sector_reason = self._check_sector_limits(portfolio_id, stock_data)
        if not valid_sector:
            logger.warning(f"  Decision: SKIP ({sector_reason})")
            return False, sector_reason

        # All checks passed
        reason = f"Approved for execution ({limit_reason})"
        logger.info(f"  Decision: EXECUTE ({reason})")
        return True, reason

    def _check_position_size(self, allocation_pct: float) -> Tuple[bool, str]:
        """
        Validate position size within limits

        Args:
            allocation_pct: Position allocation percentage

        Returns:
            Tuple of (valid: bool, reason: str)
        """
        if allocation_pct < self.min_position_size:
            return False, f"Position too small: {allocation_pct:.1f}% (min: {self.min_position_size}%)"

        if allocation_pct > self.max_position_size:
            return False, f"Position too large: {allocation_pct:.1f}% (max: {self.max_position_size}%)"

        return True, "Position size within limits"

    def _check_sector_limits(
        self,
        portfolio_id: int,
        new_stock: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Validate sector concentration limits

        Args:
            portfolio_id: Portfolio ID
            new_stock: New stock data with sector and allocation_pct

        Returns:
            Tuple of (valid: bool, reason: str)
        """
        if not self.enforce_sector_limits:
            return True, "Sector limits not enforced"

        try:
            # Get current holdings
            current_stocks = self.db.get_portfolio_stocks(portfolio_id)

            # Calculate sector allocations
            sector_allocations = {}
            for stock in current_stocks:
                if stock.get('allocation_pct', 0) > 0:  # Active positions only
                    sector = stock.get('sector', 'Unknown')
                    sector_allocations[sector] = sector_allocations.get(sector, 0) + stock['allocation_pct']

            # Add proposed stock
            new_sector = new_stock.get('sector', 'Unknown')
            new_allocation = sector_allocations.get(new_sector, 0) + new_stock.get('allocation_pct', 0)

            if new_allocation > self.max_sector_pct:
                return False, (
                    f"Sector limit exceeded: {new_sector} would be {new_allocation:.1f}% "
                    f"(limit: {self.max_sector_pct}%)"
                )

            return True, f"Sector limits satisfied ({new_sector}: {new_allocation:.1f}%)"

        except Exception as e:
            logger.error(f"Failed to check sector limits: {e}")
            # Fail-safe: reject on error
            return False, f"Sector validation failed: {e}"

    def validate_allocation_constraints(
        self,
        portfolio_id: int,
        proposed_changes: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate multiple allocation changes against constraints

        Args:
            portfolio_id: Portfolio ID
            proposed_changes: List of dicts with {ticker, action, allocation_pct, sector}

        Returns:
            Tuple of (valid: bool, violations: List[str])
        """
        violations = []

        try:
            # Get current holdings
            current_stocks = self.db.get_portfolio_stocks(portfolio_id)

            # Calculate sector allocations after proposed changes
            sector_allocations = {}
            for stock in current_stocks:
                if stock.get('allocation_pct', 0) > 0:
                    sector = stock.get('sector', 'Unknown')
                    sector_allocations[sector] = sector_allocations.get(sector, 0) + stock['allocation_pct']

            # Apply proposed changes
            for change in proposed_changes:
                ticker = change.get('ticker')
                action = change.get('action')  # 'ADD', 'REMOVE', 'ADJUST'
                sector = change.get('sector', 'Unknown')
                allocation = change.get('allocation_pct', 0)

                # Find existing stock
                existing = next((s for s in current_stocks if s['ticker'] == ticker), None)

                if action == 'REMOVE' and existing:
                    # Subtract from sector
                    sector_allocations[sector] = max(0, sector_allocations.get(sector, 0) - existing['allocation_pct'])

                elif action == 'ADD':
                    # Check position size
                    if allocation < self.min_position_size:
                        violations.append(f"{ticker}: Position too small ({allocation:.1f}% < {self.min_position_size}%)")
                    if allocation > self.max_position_size:
                        violations.append(f"{ticker}: Position too large ({allocation:.1f}% > {self.max_position_size}%)")

                    # Add to sector
                    sector_allocations[sector] = sector_allocations.get(sector, 0) + allocation

                elif action == 'ADJUST' and existing:
                    # Adjust sector allocation
                    old_allocation = existing['allocation_pct']
                    sector_allocations[sector] = sector_allocations.get(sector, 0) - old_allocation + allocation

            # Check sector limits
            if self.enforce_sector_limits:
                for sector, allocation in sector_allocations.items():
                    if allocation > self.max_sector_pct:
                        violations.append(
                            f"{sector} sector exceeds limit: {allocation:.1f}% > {self.max_sector_pct}%"
                        )

            if violations:
                logger.warning(f"Allocation constraint violations: {', '.join(violations)}")
                return False, violations

            logger.info("All allocation constraints satisfied")
            return True, []

        except Exception as e:
            logger.error(f"Failed to validate allocation constraints: {e}")
            return False, [f"Validation failed: {e}"]
