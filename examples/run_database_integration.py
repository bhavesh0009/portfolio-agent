"""
Example: Database Integration with Portfolio Builder and SQL Agent
Demonstrates:
1. Building a portfolio with database storage
2. Querying portfolio data via SQL agent
3. Monitoring portfolio with performance metrics
4. Recording market events and decisions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.portfolio_builder_agent_simple import build_simple_portfolio
from agents.sql_agent import SQLAgent
from utils.portfolio_query_helper import PortfolioQueryHelper
from utils.logger import get_logger

logger = get_logger("examples.run_database_integration")


def example_1_build_and_store_portfolio():
    """Example 1: Build portfolio and store in database"""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Build Portfolio and Store in Database")
    logger.info("=" * 70)

    # Build portfolio (automatically saves to JSON and database)
    portfolio = build_simple_portfolio(
        investor_profile="aggressive",
        capital=500000,
        verbose=True
    )

    if "stocks" in portfolio:
        logger.info(f"Portfolio built successfully with {len(portfolio['stocks'])} stocks")
        logger.info("Portfolio has been saved to:")
        logger.info("  - JSON: .cache/portfolios/portfolio_aggressive_*.json")
        logger.info("  - Database: .cache/portfolio.db")
    else:
        logger.error("Portfolio building failed")

    return portfolio


def example_2_query_portfolio_with_sql_agent():
    """Example 2: Query portfolio using SQL agent"""
    logger.info("=" * 70)
    logger.info("EXAMPLE 2: Query Portfolio with SQL Agent")
    logger.info("=" * 70)

    agent = SQLAgent(model_name='mid')

    # Example 1: Get portfolio summary
    logger.info("\nQuery 1: Get latest aggressive portfolio summary")
    summary_result = agent.natural_language_to_sql(
        query="Show me all stocks in the aggressive portfolio with their allocations and sectors",
        portfolio_id=1,
        context="Focus on allocation percentage and sector diversification"
    )

    if summary_result['action'] == 'query_success':
        logger.info(f"Found {summary_result['row_count']} stocks")
        for stock in summary_result['results'][:3]:  # Show first 3
            logger.info(f"  - {stock.get('ticker', 'N/A')}: {stock.get('allocation_pct', 0):.1f}%")
    else:
        logger.warning(f"Query failed: {summary_result.get('error')}")

    # Example 2: Get high allocation stocks
    logger.info("\nQuery 2: Stocks with allocation > 20%")
    allocation_result = agent.natural_language_to_sql(
        query="Which stocks have allocation greater than 20%?",
        portfolio_id=1
    )

    if allocation_result['action'] == 'query_success':
        logger.info(f"Found {allocation_result['row_count']} stocks with allocation > 20%")

    # Example 3: Get stop-loss and target prices
    logger.info("\nQuery 3: Risk parameters (stop-loss and targets)")
    risk_result = agent.natural_language_to_sql(
        query="Show me the stop-loss prices and target prices for each stock",
        portfolio_id=1
    )

    if risk_result['action'] == 'query_success':
        logger.info(f"Retrieved risk parameters for {risk_result['row_count']} stocks")


def example_3_monitor_portfolio():
    """Example 3: Monitor portfolio with helper"""
    logger.info("=" * 70)
    logger.info("EXAMPLE 3: Monitor Portfolio Performance")
    logger.info("=" * 70)

    helper = PortfolioQueryHelper()

    # Load latest portfolio
    logger.info("\nLoading latest aggressive portfolio...")
    portfolio_data = helper.load_latest_portfolio('aggressive')

    if portfolio_data:
        logger.info(f"Loaded portfolio with {portfolio_data['total_stocks']} stocks")

        # Simulate current prices
        current_prices = {
            'TECH': 105.0,      # Up 5% from 100
            'FIN': 185.0,       # Down 7.5% from 200
            'PHARMA': 95.0,     # Down 5% (example)
        }

        # Check for stop-loss hits
        logger.info("\nChecking stop-loss levels...")
        stops_hit = helper.check_stop_loss_hits(
            portfolio_data['portfolio']['id'],
            current_prices
        )

        if stops_hit:
            logger.warning(f"Found {len(stops_hit)} stocks at stop-loss:")
            for stock in stops_hit:
                logger.warning(f"  - {stock['ticker']}: {stock['current_price']} (limit: {stock['stop_loss_price']})")
        else:
            logger.info("No stop-loss hits detected")

        # Check for target hits
        logger.info("\nChecking target levels...")
        targets_hit = helper.check_target_hits(
            portfolio_data['portfolio']['id'],
            current_prices
        )

        if targets_hit:
            logger.info(f"Found {len(targets_hit)} stocks at target:")
            for stock in targets_hit:
                logger.info(f"  - {stock['ticker']}: {stock['current_price']} (target: {stock['target_price']})")
        else:
            logger.info("No target hits detected")

        # Calculate performance
        logger.info("\nCalculating current performance...")
        performance = helper.get_current_performance(
            portfolio_data['portfolio']['id'],
            current_prices
        )

        logger.info(f"Total Portfolio Value: Rs. {performance['total_current_value']:,.0f}")
        logger.info(f"Total Gain/Loss: Rs. {performance['total_gain_loss']:,.0f} ({performance['total_gain_loss_pct']:.2f}%)")

    else:
        logger.warning("No active portfolio found. Build one first using example_1.")


def example_4_record_decisions():
    """Example 4: Record portfolio decisions and events"""
    logger.info("=" * 70)
    logger.info("EXAMPLE 4: Record Market Events and Decisions")
    logger.info("=" * 70)

    agent = SQLAgent()

    logger.info("\nRecording market events for portfolio 1...")

    # Record a positive news event
    event1 = agent.record_market_event_from_manager(
        portfolio_id=1,
        event_type='NEWS',
        title='Earnings Beat',
        description='TECH company exceeded earnings expectations by 15%',
        impact='POSITIVE',
        stock_ticker='TECH',
        action_taken='Increased position'
    )

    logger.info(f"Recorded event: {event1.get('event_id')}")

    # Record a trigger hit
    event2 = agent.record_market_event_from_manager(
        portfolio_id=1,
        event_type='TRIGGER_HIT',
        title='Target Price Hit',
        description='FIN stock reached 50% gain target',
        impact='POSITIVE',
        stock_ticker='FIN',
        action_taken='Consider profit booking'
    )

    logger.info(f"Recorded event: {event2.get('event_id')}")

    # Record a regulatory event
    event3 = agent.record_market_event_from_manager(
        portfolio_id=1,
        event_type='REGULATORY',
        title='Policy Change',
        description='Government announced new tech regulations',
        impact='NEGATIVE',
        action_taken='Monitor impact on portfolio'
    )

    logger.info(f"Recorded event: {event3.get('event_id')}")

    logger.info("\nMarket events recorded successfully")


def example_5_natural_language_queries():
    """Example 5: Natural language queries for portfolio analysis"""
    logger.info("=" * 70)
    logger.info("EXAMPLE 5: Natural Language Queries")
    logger.info("=" * 70)

    agent = SQLAgent()

    queries = [
        "What are the top 3 stocks by allocation percentage?",
        "Which stocks are in the Technology sector?",
        "Show me all stocks with P/E ratio less than 20?",
        "List stocks with positive news sentiment",
        "Get recent market events in the last 7 days"
    ]

    for query in queries:
        logger.info(f"\nQuery: {query}")
        logger.info("Note: This requires active Gemini API connection")
        logger.info("In production, the SQL agent would convert this to SQL and execute")


def main():
    """Run all examples"""
    logger.info("\n")
    logger.info("PORTFOLIO DATABASE INTEGRATION EXAMPLES")
    logger.info("=" * 70)
    logger.info("These examples demonstrate database storage and SQL agent usage")
    logger.info("=" * 70)

    try:
        # Example 1: Build and store portfolio
        # Uncomment to run (requires valid Gemini API and screener credentials)
        # portfolio = example_1_build_and_store_portfolio()

        # Example 2: Query with SQL agent
        # example_2_query_portfolio_with_sql_agent()

        # Example 3: Monitor portfolio
        # example_3_monitor_portfolio()

        # Example 4: Record decisions
        # example_4_record_decisions()

        # Example 5: Natural language queries
        example_5_natural_language_queries()

        logger.info("\n" + "=" * 70)
        logger.info("EXAMPLES COMPLETE")
        logger.info("=" * 70)
        logger.info("\nKey Features Demonstrated:")
        logger.info("1. Automatic database storage during portfolio building")
        logger.info("2. SQL agent for natural language queries")
        logger.info("3. Portfolio monitoring with stop-loss/target detection")
        logger.info("4. Market event recording for audit trail")
        logger.info("5. Natural language SQL conversion for flexible queries")
        logger.info("\nDatabase Location: .cache/portfolio.db")
        logger.info("JSON Files: .cache/portfolios/")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        logger.error("Make sure you have:")
        logger.error("  1. Valid .env with Gemini API key")
        logger.error("  2. Valid screener.in credentials")
        logger.error("  3. All dependencies installed (playwright, google-genai, etc.)")


if __name__ == "__main__":
    main()
