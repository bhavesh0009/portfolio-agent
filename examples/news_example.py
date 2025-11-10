"""
Example usage of the Google News scraper tool
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.news_scraper import (
    scrape_news,
    scrape_news_by_period,
    get_article_titles,
    filter_articles_by_source
)


def example_1_basic_search():
    """Basic news search with date range"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic News Search with Date Range")
    print("="*70)

    result = scrape_news(
        query="Tesla stock",
        from_date="01/01/2025",
        to_date="01/31/2025"
    )

    print(f"\nTotal results: {result['total_results']}")
    print(f"Date range: {result['from_date']} to {result['to_date']}")

    print("\nFirst 3 articles:")
    for i, article in enumerate(result['articles'][:3], 1):
        print(f"\n{i}. {article['title']}")
        print(f"   Source: {article['media']}")
        print(f"   Date: {article['date']}")
        print(f"   Link: {article['link'][:80]}...")


def example_2_period_search():
    """Search news from last 24 hours"""
    print("\n" + "="*70)
    print("EXAMPLE 2: News from Last 24 Hours")
    print("="*70)

    result = scrape_news(
        query="Indian stock market",
        period="1d"
    )

    print(f"\nTotal results: {result['total_results']}")
    print(f"Period: {result['period']}")

    titles = get_article_titles(result['articles'])
    print("\nHeadlines:")
    for i, title in enumerate(titles[:5], 1):
        print(f"{i}. {title}")


def example_3_company_news():
    """Search for specific company news"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Company-Specific News")
    print("="*70)

    companies = ["Reliance Industries", "TCS", "Infosys"]

    for company in companies:
        result = scrape_news(
            query=f"{company} stock",
            period="7d",
            max_results=3
        )

        print(f"\n{company}:")
        print(f"  Found {result['total_results']} articles (showing 3)")

        for article in result['articles']:
            print(f"  - {article['title']}")


def example_4_filter_by_source():
    """Filter articles by specific sources"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Filter by News Sources")
    print("="*70)

    result = scrape_news(
        query="NVIDIA earnings",
        period="1d"
    )

    print(f"\nTotal articles found: {result['total_results']}")

    # Filter for specific sources
    trusted_sources = ["Reuters", "Bloomberg", "CNBC"]
    filtered = filter_articles_by_source(result['articles'], trusted_sources)

    print(f"Articles from {trusted_sources}: {len(filtered)}")

    for article in filtered[:5]:
        print(f"\n- {article['title']}")
        print(f"  Source: {article['media']}")


def example_5_save_to_json():
    """Search and save results to JSON"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Save Results to JSON")
    print("="*70)

    result = scrape_news(
        query="Nifty 50",
        from_date="01/01/2025",
        to_date="01/15/2025",
        max_results=10
    )

    # Save to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"news_results_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Results saved to: {filename}")
    print(f"Total articles: {result['total_results']}")


def example_6_multi_region():
    """Search news from different regions"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Multi-Region News Search")
    print("="*70)

    regions = [
        ("US", "United States"),
        ("IN", "India"),
        ("GB", "United Kingdom")
    ]

    query = "stock market"

    for region_code, region_name in regions:
        result = scrape_news(
            query=query,
            period="1d",
            region=region_code,
            max_results=3
        )

        print(f"\n{region_name} ({region_code}):")
        print(f"  Found {result['total_results']} articles")

        for article in result['articles'][:2]:
            print(f"  - {article['title'][:60]}...")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("GOOGLE NEWS SCRAPER - EXAMPLE USAGE")
    print("="*70)

    try:
        example_1_basic_search()
        example_2_period_search()
        example_3_company_news()
        example_4_filter_by_source()
        example_5_save_to_json()
        example_6_multi_region()

        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*70)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
