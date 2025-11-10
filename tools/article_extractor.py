"""
Article content extraction tool using newspaper4k with trafilatura fallback
"""

from typing import Dict, Any, Optional, List
import newspaper
import trafilatura
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def clean_google_news_url(url: str) -> str:
    """
    Clean Google News tracking parameters from URLs.

    Google News appends tracking parameters that break article extraction:
    - &ved=... (navigation tracking)
    - &usg=... (URL signature/verification)
    - &hl=... (language)
    - &gl=... (region)

    Args:
        url: Original URL (possibly with Google News parameters)

    Returns:
        Cleaned URL with tracking parameters removed

    Example:
        >>> url = "https://www.mint.com/article?id=123&ved=2ah...&usg=AOv..."
        >>> clean_google_news_url(url)
        'https://www.mint.com/article?id=123'
    """
    if not url:
        return url

    # Parameters to remove (Google News tracking)
    params_to_remove = {'ved', 'usg', 'hl', 'gl'}

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Remove Google tracking parameters
        cleaned_params = {k: v for k, v in params.items() if k not in params_to_remove}

        # Reconstruct query string
        if cleaned_params:
            # parse_qs returns lists for values, need to flatten for single values
            new_query = urlencode({k: v[0] if isinstance(v, list) and len(v) == 1 else v
                                   for k, v in cleaned_params.items()}, doseq=True)
        else:
            new_query = ''

        # Reconstruct URL
        cleaned_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

        return cleaned_url

    except Exception as e:
        # If URL parsing fails, return original URL
        print(f"Warning: Could not parse URL: {str(e)}")
        return url


def _extract_with_newspaper4k(
    url: str,
    language: str = 'en',
    perform_nlp: bool = True
) -> Dict[str, Any]:
    """
    Extract article using newspaper4k library.

    Args:
        url: Cleaned article URL
        language: Language code
        perform_nlp: Whether to perform NLP analysis

    Returns:
        Extracted article data dictionary

    Raises:
        Exception: If extraction fails
    """
    # Create article object
    article = newspaper.article(url, language=language)

    # Download article
    article.download()

    # Parse article
    article.parse()

    # Perform NLP if requested
    if perform_nlp:
        try:
            article.nlp()
        except Exception as e:
            print(f"Warning: NLP analysis failed: {e}")
            # Continue without NLP results

    # Extract publication date and convert to ISO format
    publish_date = None
    if article.publish_date:
        if isinstance(article.publish_date, datetime):
            publish_date = article.publish_date.isoformat()
        else:
            publish_date = str(article.publish_date)

    # Build result
    result = {
        'title': article.title or '',
        'authors': article.authors or [],
        'publish_date': publish_date,
        'text': article.text or '',
        'top_image': article.top_image or '',
        'images': list(article.images) if article.images else [],
        'videos': list(article.movies) if hasattr(article, 'movies') and article.movies else [],
        'meta_description': article.meta_description or '',
        'meta_keywords': article.meta_keywords or '',
        'meta_lang': article.meta_lang or language,
        'canonical_link': article.canonical_link or '',
        'html': article.html or '',
    }

    # Add NLP results if performed
    if perform_nlp:
        result['keywords'] = article.keywords or []
        result['summary'] = article.summary or ''

    return result


def _extract_with_trafilatura(
    url: str,
    language: str = 'en',
    perform_nlp: bool = True
) -> Dict[str, Any]:
    """
    Extract article using trafilatura library (higher accuracy).

    Args:
        url: Cleaned article URL
        language: Language code
        perform_nlp: Whether to perform NLP analysis (limited support in trafilatura)

    Returns:
        Extracted article data dictionary

    Raises:
        Exception: If extraction fails
    """
    # Download the page
    downloaded = trafilatura.fetch_url(url)

    if not downloaded:
        raise RuntimeError("Failed to download URL with trafilatura")

    # Extract main content with metadata
    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False
    )

    if not text:
        raise RuntimeError("No text extracted with trafilatura")

    # Extract metadata
    metadata = trafilatura.extract_metadata(downloaded)

    # Parse HTML for additional metadata
    from lxml import html as lhtml
    tree = lhtml.fromstring(downloaded)

    # Try to find images
    images = []
    try:
        img_elements = tree.xpath('.//img[@src]')
        images = [img.get('src') for img in img_elements if img.get('src')]
    except:
        pass

    # Build result
    result = {
        'title': metadata.title if metadata and metadata.title else '',
        'authors': [metadata.author] if metadata and metadata.author else [],
        'publish_date': metadata.date.isoformat() if metadata and metadata.date else None,
        'text': text,
        'top_image': metadata.image if metadata and metadata.image else '',
        'images': images,
        'videos': [],  # Trafilatura doesn't extract videos
        'meta_description': metadata.description if metadata and metadata.description else '',
        'meta_keywords': '',  # Trafilatura doesn't extract keywords from meta
        'meta_lang': language,
        'canonical_link': metadata.url if metadata and metadata.url else '',
        'html': '',  # Don't include raw HTML from trafilatura
    }

    # trafilatura doesn't provide NLP-style keywords/summary
    if perform_nlp:
        result['keywords'] = []
        result['summary'] = ''

    return result


def extract_article(
    url: str,
    language: str = 'en',
    perform_nlp: bool = True
) -> Dict[str, Any]:
    """
    Extract full article content and metadata from a news URL.

    Args:
        url: URL of the news article to extract.
             Example: "https://www.reuters.com/article/..."

        language: Language code for the article (default: 'en').
                  Options: 'en', 'es', 'fr', 'de', 'it', 'pt', 'hi', etc.
                  Supports 80+ languages.

        perform_nlp: Whether to perform NLP analysis (keywords, summary).
                     Default: True. Set to False for faster extraction.

    Returns:
        Dictionary containing:
        - url: Article URL
        - title: Article headline/title
        - authors: List of article authors
        - publish_date: Publication date (ISO format string or None)
        - text: Full article text content
        - top_image: URL of the main article image
        - images: List of all image URLs in article
        - videos: List of video URLs in article
        - keywords: List of extracted keywords (if perform_nlp=True)
        - summary: Auto-generated summary (if perform_nlp=True)
        - meta_description: Meta description from page
        - meta_keywords: Meta keywords from page
        - meta_lang: Detected language
        - canonical_link: Canonical URL
        - html: Raw HTML content
        - extraction_time: Timestamp of extraction

    Example:
        >>> result = extract_article("https://www.bbc.com/news/article-123")
        >>> print(result['title'])
        'Breaking News: Market Hits Record High'
        >>> print(result['text'][:200])
        'The stock market reached unprecedented levels today...'
        >>> print(result['keywords'])
        ['stock market', 'record high', 'trading', 'investors']

    Raises:
        ValueError: If URL is empty or invalid
        RuntimeError: If article download or parsing fails
    """
    if not url or not url.strip():
        raise ValueError("URL cannot be empty")

    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must start with http:// or https://")

    # Clean URL from Google News tracking parameters
    original_url = url
    cleaned_url = clean_google_news_url(url)

    # Log URL cleaning if parameters were removed
    if original_url != cleaned_url:
        print(f"Cleaning URL: Removed Google News tracking parameters")
        print(f"  Original: {original_url[:100]}...")
        print(f"  Cleaned:  {cleaned_url[:100]}...")

    print(f"Extracting article from: {cleaned_url}")

    # Try newspaper4k first (Method 1)
    result = None
    extraction_method = None

    try:
        print("  [Method 1/2] Trying newspaper4k extraction...")
        result_data = _extract_with_newspaper4k(cleaned_url, language, perform_nlp)

        # Validate extraction quality
        text_length = len(result_data.get('text', ''))
        if text_length > 200 and result_data.get('title'):
            print(f"  Success: newspaper4k extracted {text_length} characters")
            extraction_method = 'newspaper4k'
            result = result_data
        else:
            print(f"  newspaper4k extraction insufficient ({text_length} chars), trying trafilatura...")
            result = None

    except Exception as e:
        print(f"  newspaper4k failed: {str(e)[:100]}")
        result = None

    # Fallback to trafilatura (Method 2)
    if not result:
        try:
            print("  [Method 2/2] Trying trafilatura extraction...")
            result_data = _extract_with_trafilatura(cleaned_url, language, perform_nlp)

            # Validate extraction quality
            text_length = len(result_data.get('text', ''))
            if text_length > 0:
                print(f"  Success: trafilatura extracted {text_length} characters")
                extraction_method = 'trafilatura'
                result = result_data
            else:
                print(f"  trafilatura extraction failed (no text)")
                result = None

        except Exception as e:
            print(f"  trafilatura failed: {str(e)[:100]}")
            result = None

    # Check if any method succeeded
    if not result:
        error_msg = f"All extraction methods failed for: {cleaned_url}"
        if original_url != cleaned_url:
            error_msg += f"\n  Original URL: {original_url}"
            error_msg += f"\n  Cleaned URL: {cleaned_url}"
        raise RuntimeError(error_msg)

    # Build final result with metadata
    result['url'] = url
    result['cleaned_url'] = cleaned_url if cleaned_url != original_url else None
    result['extraction_time'] = datetime.now().isoformat()
    result['extraction_method'] = extraction_method

    print(f"Successfully extracted article: {result['title'][:60]}...")
    print(f"Article length: {len(result['text'])} characters (via {extraction_method})")

    return result


def extract_multiple_articles(
    urls: List[str],
    language: str = 'en',
    perform_nlp: bool = False
) -> List[Dict[str, Any]]:
    """
    Extract multiple articles from a list of URLs.

    Args:
        urls: List of article URLs
        language: Language code (default: 'en')
        perform_nlp: Perform NLP analysis (default: False for speed)

    Returns:
        List of article dictionaries (same format as extract_article)
        Failed extractions are skipped with error logged

    Example:
        >>> urls = [
        ...     "https://www.bbc.com/news/article-1",
        ...     "https://www.reuters.com/article/article-2"
        ... ]
        >>> results = extract_multiple_articles(urls)
        >>> print(f"Extracted {len(results)} articles")
    """
    if not urls:
        raise ValueError("URLs list cannot be empty")

    results = []
    total = len(urls)

    print(f"\nExtracting {total} articles...")

    for i, url in enumerate(urls, 1):
        try:
            print(f"\n[{i}/{total}] Processing: {url[:60]}...")
            article = extract_article(url, language=language, perform_nlp=perform_nlp)
            results.append(article)
            print(f"[{i}/{total}] Success")

        except Exception as e:
            print(f"[{i}/{total}] Failed: {str(e)[:100]}")
            # Continue with next article

    print(f"\nCompleted: {len(results)}/{total} articles extracted successfully")

    return results


def extract_article_summary(url: str, max_length: int = 500) -> str:
    """
    Quick extraction of article summary only (faster, no NLP).

    Args:
        url: Article URL
        max_length: Maximum summary length in characters

    Returns:
        Article summary text (truncated to max_length)

    Example:
        >>> summary = extract_article_summary("https://example.com/news")
        >>> print(summary)
    """
    article = extract_article(url, perform_nlp=False)

    # Use first N characters of text as summary
    text = article['text']
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


# Tool metadata for AI agent integration
TOOL_METADATA = {
    "name": "extract_article",
    "description": (
        "Extract full article content and metadata from news URLs. "
        "Retrieves title, authors, publish date, full text, images, "
        "and performs NLP analysis (keywords, summary). "
        "Supports 80+ languages and works with most news websites."
    ),
    "parameters": {
        "url": {
            "type": "string",
            "description": (
                "URL of the news article to extract. "
                "Example: 'https://www.reuters.com/article/...'"
            ),
            "required": True
        },
        "language": {
            "type": "string",
            "description": (
                "Language code for the article (default: 'en'). "
                "Options: 'en', 'es', 'fr', 'de', 'it', 'pt', 'hi', etc."
            ),
            "required": False
        },
        "perform_nlp": {
            "type": "boolean",
            "description": (
                "Perform NLP analysis for keywords and summary (default: True). "
                "Set to False for faster extraction without NLP."
            ),
            "required": False
        }
    },
    "returns": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "title": {"type": "string"},
            "authors": {"type": "array"},
            "publish_date": {"type": "string"},
            "text": {"type": "string"},
            "top_image": {"type": "string"},
            "keywords": {"type": "array"},
            "summary": {"type": "string"}
        }
    }
}
