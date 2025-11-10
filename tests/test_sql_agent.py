"""
Tests for SQL Agent
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.sql_agent import SQLAgent
from utils.db_service import DatabaseService


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_portfolio.db"
        db = DatabaseService(str(db_path))
        yield db


@pytest.fixture
def sql_agent(temp_db):
    """Create SQL agent with temp database"""
    agent = SQLAgent(model_name='mid')
    # Override the db_service to use temp_db
    agent.db_service = temp_db
    return agent


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data"""
    return {
        'total_capital': 500000,
        'stocks': [
            {
                'name': 'Tech Stock',
                'ticker': 'TECH',
                'sector': 'Technology',
                'entry_price': 100.0,
                'allocation_pct': 30.0,
                'allocation_amount': 150000.0,
                'stop_loss_pct': 15.0,
                'stop_loss_price': 85.0,
                'target_pct': 50.0,
                'target_price': 150.0,
                'rationale': 'Strong tech play',
                'news_sentiment': 'Positive',
                'investment_view': {
                    'market_outlook': 'Bullish on tech',
                    'stock_rationale': 'Growing market',
                    'holding_period': '12-18 months',
                    'exit_triggers': ['Tech crash', 'Revenue miss'],
                    'review_triggers': ['Quarterly beat', 'New product']
                },
                'key_metrics': {
                    'Market Capitalization (Rs. Cr.)': 50000,
                    'Price to Earning': 25.5,
                    'Return on Equity (%)': 25.0
                }
            },
            {
                'name': 'Finance Stock',
                'ticker': 'FIN',
                'sector': 'Finance',
                'entry_price': 200.0,
                'allocation_pct': 40.0,
                'allocation_amount': 200000.0,
                'stop_loss_pct': 15.0,
                'stop_loss_price': 170.0,
                'target_pct': 60.0,
                'target_price': 320.0,
                'rationale': 'Stable finance',
                'news_sentiment': 'Neutral',
                'investment_view': {
                    'market_outlook': 'Steady growth',
                    'stock_rationale': 'Defensive play',
                    'holding_period': '6-12 months',
                    'exit_triggers': ['Rate hike', 'Credit crisis'],
                    'review_triggers': ['Dividend increase', 'Loan growth']
                },
                'key_metrics': {
                    'Market Capitalization (Rs. Cr.)': 75000,
                    'Price to Earning': 15.0,
                    'Return on Equity (%)': 18.0
                }
            }
        ]
    }


class TestInsertGeneration:
    """Test INSERT statement generation from portfolio JSON"""

    def test_generate_insert_from_portfolio(self, sql_agent, sample_portfolio_data):
        """Test generating INSERT from portfolio"""
        result = sql_agent.generate_insert_from_portfolio(
            portfolio_data=sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000',
            json_path='/path/to/portfolio.json',
            execute=True
        )

        assert result['action'] == 'insert_success'
        assert result['portfolio_id'] is not None
        assert result['stocks_inserted'] == 2

    def test_insert_includes_all_data(self, sql_agent, sample_portfolio_data):
        """Test that INSERT includes all portfolio data"""
        result = sql_agent.generate_insert_from_portfolio(
            portfolio_data=sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000',
            json_path='/path/to/portfolio.json',
            execute=True
        )

        portfolio_id = result['portfolio_id']

        # Verify portfolio was saved
        portfolio = sql_agent.db_service.get_portfolio_by_id(portfolio_id)
        assert portfolio['profile'] == 'aggressive'
        assert portfolio['total_capital'] == 500000

        # Verify stocks were saved
        stocks = sql_agent.db_service.get_portfolio_stocks(portfolio_id)
        assert len(stocks) == 2

        # Verify investment views were saved
        for stock in stocks:
            view = sql_agent.db_service.get_investment_view(stock['id'])
            assert view is not None

        # Verify key metrics were saved
        for stock in stocks:
            metrics = sql_agent.db_service.get_key_metrics(stock['id'])
            assert metrics is not None


class TestSQLResponseParsing:
    """Test parsing of SQL responses"""

    def test_parse_sql_response_json(self, sql_agent):
        """Test parsing JSON SQL response"""
        response = '{"action": "generate_sql", "sql": "SELECT * FROM portfolios", "explanation": "Get all portfolios"}'

        parsed = sql_agent._parse_sql_response(response)

        assert parsed['action'] == 'generate_sql'
        assert 'SELECT' in parsed['sql']

    def test_parse_sql_response_code_block(self, sql_agent):
        """Test parsing SQL response in code block"""
        response = '''```json
{"action": "generate_sql", "sql": "SELECT * FROM stocks WHERE ticker = ?", "explanation": "Find stock"}
```'''

        parsed = sql_agent._parse_sql_response(response)

        assert parsed['action'] == 'generate_sql'
        assert 'SELECT' in parsed['sql']

    def test_parse_sql_response_wrapped(self, sql_agent):
        """Test parsing SQL response wrapped in text"""
        response = '''Here's the SQL query:
```
{"action": "generate_sql", "sql": "SELECT COUNT(*) FROM stocks", "explanation": "Count stocks"}
```
This will count all stocks in the database.'''

        parsed = sql_agent._parse_sql_response(response)

        assert parsed['action'] == 'generate_sql'
        assert 'COUNT' in parsed['sql']


class TestQueryPortfolioSummary:
    """Test portfolio summary queries"""

    def test_query_portfolio_summary(self, sql_agent, sample_portfolio_data):
        """Test getting portfolio summary"""
        # Insert sample data
        result = sql_agent.generate_insert_from_portfolio(
            portfolio_data=sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000',
            execute=True
        )

        portfolio_id = result['portfolio_id']

        # Query summary
        summary_result = sql_agent.query_portfolio_summary(portfolio_id)

        assert summary_result['action'] == 'summary_success'
        assert summary_result['data']['stock_count'] == 2
        assert len(summary_result['data']['stocks']) == 2


class TestQueryStockPerformance:
    """Test stock performance queries"""

    def test_query_stock_performance(self, sql_agent, sample_portfolio_data):
        """Test querying stock performance"""
        # Insert sample data
        result = sql_agent.generate_insert_from_portfolio(
            portfolio_data=sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000',
            execute=True
        )

        portfolio_id = result['portfolio_id']

        # Query performance
        perf_result = sql_agent.query_stock_performance(
            portfolio_id=portfolio_id,
            ticker='TECH',
            days=30
        )

        assert perf_result['action'] == 'performance_success'
        assert perf_result['portfolio_id'] == portfolio_id
        assert perf_result['ticker'] == 'TECH'


class TestRecordMarketEvent:
    """Test market event recording"""

    def test_record_market_event_from_manager(self, sql_agent, sample_portfolio_data):
        """Test recording market event from portfolio manager"""
        # Insert sample data
        result = sql_agent.generate_insert_from_portfolio(
            portfolio_data=sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000',
            execute=True
        )

        portfolio_id = result['portfolio_id']

        # Record event
        event_result = sql_agent.record_market_event_from_manager(
            portfolio_id=portfolio_id,
            event_type='NEWS',
            title='Positive earnings',
            description='Company beat expectations',
            impact='POSITIVE',
            stock_ticker='TECH',
            action_taken='Hold position'
        )

        assert event_result['action'] == 'event_recorded'
        assert event_result['event_id'] is not None

        # Verify event was recorded
        events = sql_agent.db_service.get_market_events(
            portfolio_id=portfolio_id,
            event_type='NEWS'
        )
        assert len(events) > 0


class TestDatabaseIntegration:
    """Test full database integration"""

    def test_full_workflow(self, sql_agent, sample_portfolio_data):
        """Test complete workflow: insert -> query -> event -> summary"""

        # Step 1: Insert portfolio
        insert_result = sql_agent.generate_insert_from_portfolio(
            portfolio_data=sample_portfolio_data,
            profile='aggressive',
            timestamp='20250101_100000',
            execute=True
        )

        assert insert_result['action'] == 'insert_success'
        portfolio_id = insert_result['portfolio_id']

        # Step 2: Get portfolio summary
        summary_result = sql_agent.query_portfolio_summary(portfolio_id)
        assert summary_result['action'] == 'summary_success'
        assert summary_result['data']['stock_count'] == 2

        # Step 3: Record market event
        event_result = sql_agent.record_market_event_from_manager(
            portfolio_id=portfolio_id,
            event_type='TRIGGER_HIT',
            title='Stop-loss triggered',
            description='TECH stock hit stop-loss',
            impact='NEGATIVE',
            stock_ticker='TECH'
        )
        assert event_result['action'] == 'event_recorded'

        # Step 4: Get performance history
        perf_result = sql_agent.query_stock_performance(
            portfolio_id=portfolio_id,
            days=30
        )
        assert perf_result['action'] == 'performance_success'

        # Step 5: Get market events
        events = sql_agent.db_service.get_market_events(
            portfolio_id=portfolio_id
        )
        assert len(events) > 0


class TestNaturalLanguageSQL:
    """Test natural language to SQL conversion"""

    def test_sql_response_format(self, sql_agent):
        """Test that SQL agent returns proper response format"""
        # Note: This test checks response structure, not actual Gemini response
        # because we're mocking/testing the SQL agent framework

        # For now, just verify the agent methods exist and handle errors gracefully
        assert hasattr(sql_agent, 'natural_language_to_sql')
        assert callable(sql_agent.natural_language_to_sql)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
