"""
Tests for Database Service
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_service import DatabaseService


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_portfolio.db"
        db = DatabaseService(str(db_path))
        yield db


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data"""
    return {
        'total_capital': 500000,
        'diversification': 'Well diversified across sectors',
        'risk_assessment': 'Moderate risk',
        'stocks': [
            {
                'name': 'Stock A',
                'ticker': 'STKA',
                'sector': 'Technology',
                'entry_price': 100.0,
                'allocation_pct': 30.0,
                'allocation_amount': 150000.0,
                'stop_loss_pct': 15.0,
                'stop_loss_price': 85.0,
                'target_pct': 50.0,
                'target_price': 150.0,
                'rationale': 'Good fundamentals',
                'news_sentiment': 'Positive',
                'investment_view': {
                    'market_outlook': 'Bullish',
                    'stock_rationale': 'Strong growth potential',
                    'holding_period': '12-18 months',
                    'exit_triggers': ['Loss of major contract', 'Regulatory issues'],
                    'review_triggers': ['Quarterly miss', 'Management change']
                },
                'key_metrics': {
                    'Market Capitalization (Rs. Cr.)': 50000,
                    'Price to Earning': 25.5,
                    'Return on Equity (%)': 25.0
                }
            },
            {
                'name': 'Stock B',
                'ticker': 'STKB',
                'sector': 'Finance',
                'entry_price': 200.0,
                'allocation_pct': 40.0,
                'allocation_amount': 200000.0,
                'stop_loss_pct': 15.0,
                'stop_loss_price': 170.0,
                'target_pct': 60.0,
                'target_price': 320.0,
                'rationale': 'Stable performer',
                'news_sentiment': 'Mixed',
                'investment_view': {
                    'market_outlook': 'Neutral',
                    'stock_rationale': 'Defensive play',
                    'holding_period': '6-12 months',
                    'exit_triggers': ['Dividend cut', 'Downgrades'],
                    'review_triggers': ['Earnings beat', 'Policy changes']
                },
                'key_metrics': {
                    'Market Capitalization (Rs. Cr.)': 75000,
                    'Price to Earning': 15.0,
                    'Return on Equity (%)': 18.0
                }
            }
        ]
    }


class TestPortfolioOperations:
    """Test portfolio save and retrieve operations"""

    def test_save_portfolio(self, temp_db, sample_portfolio_data):
        """Test saving portfolio"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000',
            json_path='/path/to/portfolio.json'
        )

        assert portfolio_id == 1
        assert isinstance(portfolio_id, int)

    def test_get_portfolio_by_id(self, temp_db, sample_portfolio_data):
        """Test retrieving portfolio by ID"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        portfolio = temp_db.get_portfolio_by_id(portfolio_id)

        assert portfolio is not None
        assert portfolio['profile'] == 'aggressive'
        assert portfolio['total_capital'] == 500000
        assert portfolio['is_active'] == 1

    def test_get_active_portfolio(self, temp_db, sample_portfolio_data):
        """Test getting active portfolio"""
        # Save first portfolio
        pid1 = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        # Save second portfolio (should become active)
        pid2 = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250102_100000'
        )

        active = temp_db.get_active_portfolio('aggressive')

        assert active is not None
        assert active['id'] == pid2
        assert active['is_active'] == 1


class TestStockOperations:
    """Test stock save and retrieve operations"""

    def test_save_stocks(self, temp_db, sample_portfolio_data):
        """Test saving stocks"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        stock_ids = temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])

        assert len(stock_ids) == 2
        assert all(isinstance(sid, int) for sid in stock_ids)

    def test_get_portfolio_stocks(self, temp_db, sample_portfolio_data):
        """Test retrieving portfolio stocks"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        stock_ids = temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])
        stocks = temp_db.get_portfolio_stocks(portfolio_id)

        assert len(stocks) == 2
        assert stocks[0]['ticker'] in ['STKA', 'STKB']
        assert stocks[0]['name'] in ['Stock A', 'Stock B']

    def test_get_stock_by_ticker(self, temp_db, sample_portfolio_data):
        """Test retrieving stock by ticker"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])
        stock = temp_db.get_stock_by_ticker('STKA', portfolio_id)

        assert stock is not None
        assert stock['ticker'] == 'STKA'
        assert stock['name'] == 'Stock A'


class TestInvestmentViewOperations:
    """Test investment view operations"""

    def test_get_investment_view(self, temp_db, sample_portfolio_data):
        """Test retrieving investment view"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        stock_ids = temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])
        view = temp_db.get_investment_view(stock_ids[0])

        assert view is not None
        assert view['market_outlook'] == 'Bullish'
        assert view['stock_rationale'] == 'Strong growth potential'
        assert view['holding_period'] == '12-18 months'
        assert isinstance(view['exit_triggers'], list)
        assert len(view['exit_triggers']) == 2


class TestKeyMetricsOperations:
    """Test key metrics operations"""

    def test_get_key_metrics(self, temp_db, sample_portfolio_data):
        """Test retrieving key metrics"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        stock_ids = temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])
        metrics = temp_db.get_key_metrics(stock_ids[0])

        assert metrics is not None
        assert 'metrics_json' in metrics
        assert metrics['metrics_json']['Price to Earning'] == 25.5


class TestTransactionOperations:
    """Test transaction recording and querying"""

    def test_record_transaction(self, temp_db, sample_portfolio_data):
        """Test recording transaction"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        stock_ids = temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])

        tx_id = temp_db.record_transaction(
            portfolio_id=portfolio_id,
            stock_id=stock_ids[0],
            transaction_type='BUY',
            quantity=100,
            price=100.0,
            transaction_date=datetime.now(),
            notes='Initial purchase'
        )

        assert isinstance(tx_id, int)

    def test_get_transactions(self, temp_db, sample_portfolio_data):
        """Test retrieving transactions"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        stock_ids = temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])

        temp_db.record_transaction(
            portfolio_id=portfolio_id,
            stock_id=stock_ids[0],
            transaction_type='BUY',
            quantity=100,
            price=100.0,
            transaction_date=datetime.now()
        )

        transactions = temp_db.get_transactions(portfolio_id=portfolio_id)

        assert len(transactions) == 1
        assert transactions[0]['ticker'] is None  # ticker not in transactions table
        assert transactions[0]['total_amount'] == 10000.0


class TestPerformanceOperations:
    """Test performance metrics operations"""

    def test_record_performance(self, temp_db, sample_portfolio_data):
        """Test recording performance"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        metric_id = temp_db.record_performance(
            portfolio_id=portfolio_id,
            metric_date=date.today(),
            portfolio_value=510000.0,
            daily_return_pct=2.0,
            cumulative_return_pct=2.0
        )

        assert isinstance(metric_id, int)

    def test_get_performance_history(self, temp_db, sample_portfolio_data):
        """Test retrieving performance history"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        today = date.today()
        temp_db.record_performance(
            portfolio_id=portfolio_id,
            metric_date=today,
            portfolio_value=510000.0,
            daily_return_pct=2.0
        )

        temp_db.record_performance(
            portfolio_id=portfolio_id,
            metric_date=today - timedelta(days=1),
            portfolio_value=500000.0,
            daily_return_pct=0.0
        )

        history = temp_db.get_performance_history(portfolio_id)

        assert len(history) == 2


class TestRebalancingOperations:
    """Test rebalancing history operations"""

    def test_record_rebalancing(self, temp_db, sample_portfolio_data):
        """Test recording rebalancing"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        rebalancing_id = temp_db.record_rebalancing(
            portfolio_id=portfolio_id,
            rebalancing_date=datetime.now(),
            reason='Allocation drift exceeded 5%',
            action_type='ADJUSTMENT',
            affected_stocks=['STKA', 'STKB'],
            allocation_changes={'STKA': (30.0, 25.0), 'STKB': (40.0, 45.0)},
            expected_result='Realign allocations to targets'
        )

        assert isinstance(rebalancing_id, int)

    def test_get_rebalancing_history(self, temp_db, sample_portfolio_data):
        """Test retrieving rebalancing history"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        temp_db.record_rebalancing(
            portfolio_id=portfolio_id,
            rebalancing_date=datetime.now(),
            reason='Test rebalancing',
            action_type='ADJUSTMENT',
            affected_stocks=['STKA'],
            allocation_changes={'STKA': (30.0, 35.0)}
        )

        history = temp_db.get_rebalancing_history(portfolio_id)

        assert len(history) == 1
        assert history[0]['action_type'] == 'ADJUSTMENT'
        assert 'STKA' in history[0]['affected_stocks']


class TestMarketEventOperations:
    """Test market events operations"""

    def test_record_market_event(self, temp_db, sample_portfolio_data):
        """Test recording market event"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        event_id = temp_db.record_market_event(
            event_type='NEWS',
            title='Positive earnings',
            description='Company reported strong Q1 earnings',
            event_date=datetime.now(),
            portfolio_id=portfolio_id,
            impact='POSITIVE',
            source='News'
        )

        assert isinstance(event_id, int)

    def test_get_market_events(self, temp_db, sample_portfolio_data):
        """Test retrieving market events"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        temp_db.record_market_event(
            event_type='NEWS',
            title='Test event',
            description='Test description',
            event_date=datetime.now(),
            portfolio_id=portfolio_id,
            impact='POSITIVE'
        )

        events = temp_db.get_market_events(portfolio_id=portfolio_id)

        assert len(events) == 1
        assert events[0]['event_type'] == 'NEWS'


class TestPortfolioSummary:
    """Test portfolio summary operations"""

    def test_portfolio_summary(self, temp_db, sample_portfolio_data):
        """Test getting portfolio summary"""
        portfolio_id = temp_db.save_portfolio(
            sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000'
        )

        stock_ids = temp_db.save_stocks(portfolio_id, sample_portfolio_data['stocks'])

        summary = temp_db.portfolio_summary(portfolio_id)

        assert 'portfolio' in summary
        assert 'stocks' in summary
        assert summary['stock_count'] == 2
        assert summary['total_allocation'] == 70.0  # 30% + 40%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
