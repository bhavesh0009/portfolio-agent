"""
Example usage of the Article Extractor tool
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

from tools.article_extractor import (
    extract_article,
    extract_multiple_articles,
    extract_article_summary
)


def example_1_basic_extraction():
    """Basic article extraction with full details"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Article Extraction")
    print("="*70)

    # Example article URL (BBC News)
    url = "https://www.bbc.com/news/business-51706225"

    result = extract_article(url)

    print(f"\nTitle: {result['title']}")
    print(f"Authors: {', '.join(result['authors']) if result['authors'] else 'N/A'}")
    print(f"Publish Date: {result['publish_date'] or 'N/A'}")
    print(f"Language: {result['meta_lang']}")
    print(f"\nArticle Text (first 300 chars):")
    print(result['text'][:300] + "...")
    print(f"\nTotal article length: {len(result['text'])} characters")
    print(f"Images found: {len(result['images'])}")
    print(f"Top image: {result['top_image'][:60]}..." if result['top_image'] else "No top image")

    if 'keywords' in result:
        print(f"\nKeywords: {', '.join(result['keywords'][:5])}")

    if 'summary' in result and result['summary']:
        print(f"\nAuto-generated summary:")
        print(result['summary'][:200] + "...")


def example_2_without_nlp():
    """Extract article without NLP (faster)"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Fast Extraction (No NLP)")
    print("="*70)

    url = "https://www.reuters.com/technology"

    result = extract_article(url, perform_nlp=False)

    print(f"\nTitle: {result['title']}")
    print(f"Text length: {len(result['text'])} characters")
    print(f"NLP performed: {'keywords' in result}")


def example_3_multiple_articles():
    """Extract multiple articles at once"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Multiple Article Extraction")
    print("="*70)

    urls = [
        "https://www.bbc.com/news/business",
        "https://www.reuters.com/markets",
        "https://www.cnbc.com/world"
    ]

    results = extract_multiple_articles(urls, perform_nlp=False)

    print(f"\nSuccessfully extracted {len(results)} articles:")
    for i, article in enumerate(results, 1):
        print(f"\n{i}. {article['title'][:60]}...")
        print(f"   Length: {len(article['text'])} chars")
        print(f"   URL: {article['url'][:60]}...")


def example_4_save_to_json():
    """Extract and save article to JSON"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Extract and Save to JSON")
    print("="*70)

    url = "https://www.theguardian.com/business"

    result = extract_article(url)

    # Remove HTML to reduce file size
    result_without_html = {k: v for k, v in result.items() if k != 'html'}

    # Save to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"article_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result_without_html, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Article saved to: {filename}")
    print(f"Title: {result['title']}")
    print(f"File size: {len(json.dumps(result_without_html))} bytes")


def example_5_quick_summary():
    """Quick summary extraction"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Quick Summary Extraction")
    print("="*70)

    url = "https://www.bloomberg.com/markets"

    summary = extract_article_summary(url, max_length=300)

    print(f"\nQuick summary (300 chars):")
    print(summary)


def example_6_news_integration():
    """Integration with news_scraper"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Integration with News Scraper")
    print("="*70)

    # First, get news URLs using news_scraper
    from tools.news_scraper import scrape_news

    print("Step 1: Getting news URLs...")
    news_result = scrape_news(
        query="Tesla stock",
        period="1d",
        max_results=3
    )

    print(f"Found {news_result['total_results']} news articles")

    # Extract URLs
    urls = [article['link'] for article in news_result['articles']]

    print("\nStep 2: Extracting full article content...")

    # Extract full articles
    articles = extract_multiple_articles(urls[:2], perform_nlp=False)

    print(f"\nSuccessfully extracted {len(articles)} full articles:")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"   Text length: {len(article['text'])} characters")
        if article['text']:
            print(f"   Preview: {article['text'][:150]}...")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("ARTICLE EXTRACTOR - EXAMPLE USAGE")
    print("="*70)

    try:
        example_1_basic_extraction()
        example_2_without_nlp()
        example_3_multiple_articles()
        example_4_save_to_json()
        example_5_quick_summary()
        example_6_news_integration()

        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*70)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
