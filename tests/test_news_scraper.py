"""
Test script for Google News scraper
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.news_scraper import scrape_news


def test_basic_scraping():
    """Test basic news scraping functionality"""

    print("\n" + "="*70)
    print("TESTING GOOGLE NEWS SCRAPER (UNIFIED)")
    print("="*70)

    # Test 1: Period-based search
    print("\nTest 1: Search news from last 7 days (using period parameter)")
    print("-" * 70)

    try:
        result = scrape_news(
            query="stock market",
            period="7d",
            max_results=5
        )

        print(f"[SUCCESS] Found {result['total_results']} articles")
        print(f"Query: {result['query']}")
        print(f"Period: {result['period']}")

        if result['articles']:
            print("\nSample article:")
            article = result['articles'][0]
            print(f"  Title: {article['title']}")
            print(f"  Source: {article['media']}")
            print(f"  Date: {article['date']}")
            print(f"  Link: {article['link']}")

    except Exception as e:
        print(f"[ERROR] Test 1 failed: {e}")
        return False

    # Test 2: Date range search
    print("\n\nTest 2: Search with date range")
    print("-" * 70)

    try:
        result = scrape_news(
            query="Tesla",
            from_date="01/01/2025",
            to_date="01/15/2025",
            max_results=5
        )

        print(f"[SUCCESS] Found {result['total_results']} articles")
        print(f"Query: {result['query']}")
        print(f"Date range: {result['from_date']} to {result['to_date']}")

        if result['articles']:
            print("\nFirst 3 headlines:")
            for i, article in enumerate(result['articles'][:3], 1):
                print(f"  {i}. {article['title']}")

    except Exception as e:
        print(f"[ERROR] Test 2 failed: {e}")
        return False

    # Test 3: Default date range (last 7 days)
    print("\n\nTest 3: Default date range")
    print("-" * 70)

    try:
        result = scrape_news(
            query="NVIDIA",
            max_results=3
        )

        print(f"[SUCCESS] Found {result['total_results']} articles")
        print(f"Auto date range: {result['from_date']} to {result['to_date']}")

    except Exception as e:
        print(f"[ERROR] Test 3 failed: {e}")
        return False

    # Test 4: Different region
    print("\n\nTest 4: Region-specific search (using period parameter)")
    print("-" * 70)

    try:
        result = scrape_news(
            query="cricket",
            period="1d",
            region="IN",
            max_results=3
        )

        print(f"[SUCCESS] Found {result['total_results']} articles")
        print(f"Region: {result['region']}")

    except Exception as e:
        print(f"[ERROR] Test 4 failed: {e}")
        return False

    print("\n" + "="*70)
    print("ALL TESTS PASSED SUCCESSFULLY")
    print("="*70)

    return True


if __name__ == "__main__":
    success = test_basic_scraping()
    sys.exit(0 if success else 1)
