"""
Test script for Article Extractor
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.article_extractor import extract_article, extract_article_summary


def test_article_extraction():
    """Test basic article extraction functionality"""

    print("\n" + "="*70)
    print("TESTING ARTICLE EXTRACTOR")
    print("="*70)

    # Test 1: Basic extraction with NLP
    print("\nTest 1: Basic extraction (with NLP)")
    print("-" * 70)

    try:
        url = "https://www.bbc.com/news/business-51706225"
        result = extract_article(url, perform_nlp=True)

        print(f"[SUCCESS] Extracted article")
        print(f"Title: {result['title'][:60]}...")
        print(f"Authors: {len(result['authors'])} author(s)")
        print(f"Text length: {len(result['text'])} characters")
        print(f"Has keywords: {'keywords' in result}")
        print(f"Has summary: {'summary' in result}")

        # Verify essential fields
        assert result['url'] == url
        assert len(result['title']) > 0
        assert len(result['text']) > 100

    except Exception as e:
        print(f"[ERROR] Test 1 failed: {e}")
        return False

    # Test 2: Extraction without NLP (faster)
    print("\n\nTest 2: Extraction without NLP")
    print("-" * 70)

    try:
        url = "https://www.bbc.com/news/technology"
        result = extract_article(url, perform_nlp=False)

        print(f"[SUCCESS] Extracted article")
        print(f"Title: {result['title'][:60]}...")
        print(f"Text length: {len(result['text'])} characters")
        print(f"Has keywords: {'keywords' in result}")
        print(f"Has summary: {'summary' in result}")

        # Verify NLP was skipped
        assert 'keywords' not in result or result['keywords'] == []

    except Exception as e:
        print(f"[ERROR] Test 2 failed: {e}")
        return False

    # Test 3: Quick summary extraction
    print("\n\nTest 3: Quick summary extraction")
    print("-" * 70)

    try:
        url = "https://www.bbc.com/news/business"
        summary = extract_article_summary(url, max_length=200)

        print(f"[SUCCESS] Extracted summary")
        print(f"Summary length: {len(summary)} characters")
        print(f"Summary: {summary[:100]}...")

        assert len(summary) <= 203  # 200 + "..."

    except Exception as e:
        print(f"[ERROR] Test 3 failed: {e}")
        return False

    # Test 4: Error handling (invalid URL)
    print("\n\nTest 4: Error handling (invalid URL)")
    print("-" * 70)

    try:
        result = extract_article("")
        print(f"[ERROR] Test 4 failed: Should have raised ValueError")
        return False

    except ValueError as e:
        print(f"[SUCCESS] Correctly raised ValueError: {str(e)}")

    except Exception as e:
        print(f"[ERROR] Test 4 failed with unexpected error: {e}")
        return False

    # Test 5: Article with images
    print("\n\nTest 5: Article with images")
    print("-" * 70)

    try:
        url = "https://www.bbc.com/news/world"
        result = extract_article(url, perform_nlp=False)

        print(f"[SUCCESS] Extracted article")
        print(f"Images found: {len(result['images'])}")
        print(f"Top image: {result['top_image'][:60] if result['top_image'] else 'None'}...")
        print(f"Has meta description: {bool(result['meta_description'])}")

    except Exception as e:
        print(f"[ERROR] Test 5 failed: {e}")
        return False

    print("\n" + "="*70)
    print("ALL TESTS PASSED SUCCESSFULLY")
    print("="*70)

    return True


if __name__ == "__main__":
    success = test_article_extraction()
    sys.exit(0 if success else 1)
