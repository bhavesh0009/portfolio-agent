"""
Simple test for industry_scraper integration with stock_screening_agent
Tests the tools directly without full agent initialization
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.industry_scraper import get_industries_overview, get_industry_stocks, search_industries


def test_all_functions():
    """Test all industry scraper functions"""

    print("\n" + "="*80)
    print("TEST 1: Search Industries")
    print("="*80)

    pharma_industries = search_industries('pharma')
    print(f"\nFound {len(pharma_industries)} pharma-related industries:")
    for ind in pharma_industries:
        print(f"  - {ind['industry_name']}: {ind['company_count']} companies, "
              f"Median P/E: {ind['median_pe']}, Avg ROCE: {ind['avg_roce']}%")

    print("\n" + "="*80)
    print("TEST 2: Get Industries Overview (Top 10 by ROCE)")
    print("="*80)

    all_industries = get_industries_overview()
    # Sort by ROCE and filter out None values
    top_roce = sorted(
        [i for i in all_industries if i['avg_roce'] is not None],
        key=lambda x: x['avg_roce'],
        reverse=True
    )[:10]

    print(f"\nTop 10 industries by weighted average ROCE:")
    for i, ind in enumerate(top_roce, 1):
        print(f"{i:2d}. {ind['industry_name']:<40} ROCE: {ind['avg_roce']:>5.1f}% | "
              f"Companies: {ind['company_count']:>3} | P/E: {ind['median_pe'] or 'N/A'}")

    print("\n" + "="*80)
    print("TEST 3: Get Industry Stocks (2/3 Wheelers)")
    print("="*80)

    # Find 2/3 Wheelers industry
    wheelers = [i for i in all_industries if '2/3 Wheelers' in i['industry_name']][0]
    print(f"\nFetching stocks from: {wheelers['industry_name']}")

    stocks_data = get_industry_stocks(wheelers['industry_url'])

    print(f"\nIndustry: {stocks_data['industry_name']}")
    print(f"Total stocks: {stocks_data['total_results']}")
    print(f"\nTop stocks by Market Cap:")

    # Sort by market cap
    top_stocks = sorted(
        [s for s in stocks_data['stocks'] if s.get('market_cap')],
        key=lambda x: x['market_cap'],
        reverse=True
    )[:5]

    for i, stock in enumerate(top_stocks, 1):
        pe_val = f"{stock.get('pe'):>6.2f}" if stock.get('pe') else "   N/A"
        roce_val = f"{stock.get('roce'):>6.2f}" if stock.get('roce') else "   N/A"
        print(f"{i}. {stock['name']:<20} CMP: Rs. {stock.get('cmp', 0):>8.2f} | "
              f"Market Cap: {stock.get('market_cap', 0):>10,.0f} Cr | "
              f"P/E: {pe_val} | "
              f"ROCE: {roce_val}%")

    print("\n" + "="*80)
    print("TEST 4: Combined Workflow - Find best IT stocks")
    print("="*80)

    # Step 1: Find IT industries
    print("\nStep 1: Searching for IT industries...")
    it_industries = search_industries('information technology')

    if it_industries:
        print(f"Found {len(it_industries)} IT industries:")
        for ind in it_industries:
            print(f"  - {ind['industry_name']}: {ind['company_count']} companies")

        # Step 2: Get stocks from first IT industry
        it_industry = it_industries[0]
        print(f"\nStep 2: Getting stocks from '{it_industry['industry_name']}'...")

        it_stocks = get_industry_stocks(it_industry['industry_url'])

        # Step 3: Filter high ROCE stocks with market cap > 1000 Cr
        print(f"\nStep 3: Filtering for high-quality stocks (ROCE > 20%, Market Cap > 1000 Cr)...")

        quality_stocks = [
            s for s in it_stocks['stocks']
            if s.get('roce') and s.get('roce') > 20
            and s.get('market_cap') and s.get('market_cap') > 1000
        ]

        quality_stocks_sorted = sorted(quality_stocks, key=lambda x: x.get('roce', 0), reverse=True)

        print(f"\nFound {len(quality_stocks)} high-quality stocks:")
        for i, stock in enumerate(quality_stocks_sorted[:5], 1):
            cmp_val = f"{stock.get('cmp'):>8.2f}" if stock.get('cmp') else "     N/A"
            roce_val = f"{stock.get('roce'):>6.1f}" if stock.get('roce') else "   N/A"
            print(f"{i}. {stock['name']:<30} "
                  f"CMP: Rs. {cmp_val} | "
                  f"Market Cap: {stock.get('market_cap', 0):>10,.0f} Cr | "
                  f"ROCE: {roce_val}%")
    else:
        print("No IT industries found!")

    print("\n" + "="*80)
    print("Integration test completed successfully!")
    print("="*80)
    print("\nNOTE: stock_screening_agent.py has been updated with these tools:")
    print("  1. get_industries_overview() - Get all industries with metrics")
    print("  2. search_industries(keyword) - Search industries by keyword")
    print("  3. get_industry_stocks(url) - Get all stocks from an industry")
    print("  4. screen_stocks(query) - Original stock screening tool")
    print("\nThe agent can now autonomously use all 4 tools to answer queries!")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_all_functions()
