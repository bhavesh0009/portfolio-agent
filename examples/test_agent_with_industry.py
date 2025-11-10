"""
Test script for stock_screening_agent with integrated industry_scraper tools
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_screening_agent import StockScreeningAgent


def test_industry_overview():
    """Test agent using get_industries_overview"""
    print("\n" + "="*80)
    print("TEST 1: Industry Overview - Find top performing industries")
    print("="*80)

    agent = StockScreeningAgent()
    query = "Show me the top 5 industries by weighted average ROCE with at least 10 companies"

    result = agent.run(query, max_iterations=15, verbose=True)

    print("\n" + "-"*80)
    print("AGENT RESULT:")
    print("-"*80)
    print(result)


def test_industry_search():
    """Test agent using search_industries"""
    print("\n" + "="*80)
    print("TEST 2: Industry Search - Find auto-related industries")
    print("="*80)

    agent = StockScreeningAgent()
    query = "Find all industries related to 'pharma' and show their market metrics"

    result = agent.run(query, max_iterations=15, verbose=True)

    print("\n" + "-"*80)
    print("AGENT RESULT:")
    print("-"*80)
    print(result)


def test_industry_stocks():
    """Test agent using get_industry_stocks"""
    print("\n" + "="*80)
    print("TEST 3: Industry Stocks - Get stocks from specific industry")
    print("="*80)

    agent = StockScreeningAgent()
    query = "Show me all stocks in the '2/3 Wheelers' industry with their current prices and ROCE"

    result = agent.run(query, max_iterations=15, verbose=True)

    print("\n" + "-"*80)
    print("AGENT RESULT:")
    print("-"*80)
    print(result)


def test_combined_workflow():
    """Test agent combining industry and stock screening tools"""
    print("\n" + "="*80)
    print("TEST 4: Combined Workflow - Find best IT stocks")
    print("="*80)

    agent = StockScreeningAgent()
    query = """
    Find the IT industry, get all stocks from it, and then identify
    the top 3 stocks with highest ROCE and market cap above 1000 Cr
    """

    result = agent.run(query, max_iterations=20, verbose=True)

    print("\n" + "-"*80)
    print("AGENT RESULT:")
    print("-"*80)
    print(result)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test stock screening agent with industry tools')
    parser.add_argument('--test', type=int, choices=[1, 2, 3, 4],
                       help='Run specific test (1-4)')

    args = parser.parse_args()

    if args.test == 1:
        test_industry_overview()
    elif args.test == 2:
        test_industry_search()
    elif args.test == 3:
        test_industry_stocks()
    elif args.test == 4:
        test_combined_workflow()
    else:
        # Run all tests
        print("\nRunning all tests...")
        test_industry_overview()
        test_industry_search()
        test_industry_stocks()
        test_combined_workflow()

        print("\n" + "="*80)
        print("All tests completed!")
        print("="*80 + "\n")
