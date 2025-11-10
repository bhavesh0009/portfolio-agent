"""
Test script for industry_scraper tool
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.industry_scraper import get_industries_overview, get_industry_stocks, search_industries


def test_industries_overview():
    """Test fetching the industries overview table"""
    print("\n" + "="*80)
    print("TEST: Get Industries Overview")
    print("="*80)

    industries = get_industries_overview()

    print(f"\nTotal industries found: {len(industries)}")
    print("\nFirst 5 industries:")
    print("-" * 80)

    for i, industry in enumerate(industries[:5], 1):
        print(f"\n{i}. {industry['industry_name']}")
        print(f"   Companies: {industry['company_count']}")
        print(f"   Total Market Cap: {industry['total_market_cap']:,.0f} Cr" if industry['total_market_cap'] else "   Total Market Cap: N/A")
        print(f"   Median P/E: {industry['median_pe']}" if industry['median_pe'] else "   Median P/E: N/A")
        print(f"   Avg Sales Growth: {industry['avg_sales_growth']}%" if industry['avg_sales_growth'] else "   Avg Sales Growth: N/A")
        print(f"   URL: {industry['industry_url']}")

    return industries


def test_industry_stocks(industry_url: str = '/market/IN02/IN0201/IN020101/IN020101002/'):
    """Test fetching stocks from a specific industry"""
    print("\n" + "="*80)
    print("TEST: Get Industry Stocks")
    print("="*80)

    result = get_industry_stocks(industry_url)

    print(f"\nIndustry: {result['industry_name']}")
    print(f"Breadcrumb: {' > '.join([b['name'] for b in result['breadcrumb']])}")
    print(f"Total Results: {result['total_results']}")

    print(f"\nStocks ({len(result['stocks'])} found):")
    print("-" * 80)

    for i, stock in enumerate(result['stocks'][:10], 1):  # Show first 10
        print(f"\n{i}. {stock['name']}")
        print(f"   CMP: Rs. {stock.get('cmp', 'N/A')}")
        print(f"   P/E: {stock.get('pe', 'N/A')}")
        print(f"   Market Cap: {stock.get('market_cap', 'N/A'):,.2f} Cr" if stock.get('market_cap') else "   Market Cap: N/A")
        print(f"   ROCE: {stock.get('roce', 'N/A')}%" if stock.get('roce') else "   ROCE: N/A")
        print(f"   URL: {stock['url']}")

    return result


def test_search_industries(keyword: str = 'auto'):
    """Test searching industries by keyword"""
    print("\n" + "="*80)
    print(f"TEST: Search Industries (keyword: '{keyword}')")
    print("="*80)

    matches = search_industries(keyword)

    print(f"\nFound {len(matches)} matching industries:")
    print("-" * 80)

    for i, industry in enumerate(matches, 1):
        print(f"\n{i}. {industry['industry_name']}")
        print(f"   Companies: {industry['company_count']}")
        print(f"   Median Market Cap: {industry['median_market_cap']:,.0f} Cr" if industry['median_market_cap'] else "   Median Market Cap: N/A")
        print(f"   URL: {industry['industry_url']}")

    return matches


if __name__ == "__main__":
    # Test 1: Get industries overview
    industries = test_industries_overview()

    # Test 2: Get stocks from a specific industry (2/3 Wheelers)
    test_industry_stocks()

    # Test 3: Search for industries
    test_search_industries('auto')

    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80 + "\n")
