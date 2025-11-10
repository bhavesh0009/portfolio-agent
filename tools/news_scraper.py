"""
Google News scraper tool (unified version)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from GoogleNews import GoogleNews

from utils.logger import get_logger

logger = get_logger("tools.news_scraper")


def scrape_news(
    query: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    period: Optional[str] = None,
    language: str = 'en',
    region: str = 'US',
    max_results: Optional[int] = None
) -> Dict[str, Any]:
    """
    Scrape Google News based on search query with flexible date options.

    Args:
        query: Search query for news articles.
               Example: "Reliance Industries stock", "Indian stock market", "NVIDIA earnings"

        from_date: Start date in format 'MM/DD/YYYY' (optional).
                   Example: "01/01/2024"
                   Cannot be used with 'period'.

        to_date: End date in format 'MM/DD/YYYY' (optional).
                 Example: "01/31/2024"
                 Cannot be used with 'period'.

        period: Time period for news (optional).
                Options: '1h', '1d', '7d', '1m', '1y'
                h = hours, d = days, m = months, y = years
                Cannot be used with 'from_date' or 'to_date'.

        language: Language code for news (default: 'en').
                  Options: 'en', 'es', 'fr', 'de', 'it', 'pt', etc.

        region: Region code for news (default: 'US').
                Options: 'US', 'IN', 'GB', 'CA', etc.

        max_results: Maximum number of results to return (optional).
                     If None, returns all available results.

    Returns:
        Dictionary containing:
        - total_results: Number of articles found
        - query: The search query used
        - search_mode: "period" or "date_range"
        - period OR from_date/to_date: Search parameters used
        - articles: List of dictionaries, each containing article data
          - title: Article headline
          - media: Source/Publisher name
          - date: Publication date (human readable)
          - datetime: Publication datetime (ISO format string)
          - desc: Article description/snippet
          - link: URL to article
          - img: Image URL (if available)

    Example:
        >>> # Using period
        >>> result = scrape_news(query="Tesla stock", period="7d")

        >>> # Using date range
        >>> result = scrape_news(
        ...     query="Tesla stock",
        ...     from_date="01/01/2024",
        ...     to_date="01/31/2024"
        ... )

        >>> # Default (7 days)
        >>> result = scrape_news(query="Tesla stock")

    Raises:
        ValueError: If query is empty, date format is invalid, or conflicting parameters
        RuntimeError: If news scraping fails
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    # Check for conflicting parameters
    has_date_range = from_date is not None or to_date is not None
    has_period = period is not None

    if has_date_range and has_period:
        raise ValueError(
            "Cannot use both 'period' and date range ('from_date'/'to_date'). "
            "Please use only one search mode."
        )

    # Determine search mode
    search_mode = None
    googlenews_params = {
        'lang': language,
        'region': region
    }

    if has_period:
        # Period-based search
        search_mode = "period"
        googlenews_params['period'] = period

        print(f"Searching Google News for: '{query}'")
        print(f"Period: {period}")

    else:
        # Date range search (default or explicit)
        search_mode = "date_range"

        # Set default date range if not provided
        if not from_date:
            from_date_obj = datetime.now() - timedelta(days=7)
            from_date = from_date_obj.strftime('%m/%d/%Y')

        if not to_date:
            to_date_obj = datetime.now()
            to_date = to_date_obj.strftime('%m/%d/%Y')

        # Validate date format
        try:
            datetime.strptime(from_date, '%m/%d/%Y')
            datetime.strptime(to_date, '%m/%d/%Y')
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use MM/DD/YYYY format. Error: {e}")

        googlenews_params['start'] = from_date
        googlenews_params['end'] = to_date

        print(f"Searching Google News for: '{query}'")
        print(f"Date range: {from_date} to {to_date}")

    # Initialize GoogleNews and execute search
    try:
        googlenews = GoogleNews(**googlenews_params)
        googlenews.search(query)

        # Get results
        articles = googlenews.results()

        # Convert datetime objects to strings for JSON serialization
        for article in articles:
            if 'datetime' in article and article['datetime'] is not None:
                if isinstance(article['datetime'], datetime):
                    article['datetime'] = article['datetime'].isoformat()

        # Apply max_results limit if specified
        if max_results and len(articles) > max_results:
            articles = articles[:max_results]

        # Clean up the googlenews object
        googlenews.clear()

        print(f"Found {len(articles)} articles")

        # Build response
        result = {
            'total_results': len(articles),
            'query': query,
            'search_mode': search_mode,
            'language': language,
            'region': region,
            'articles': articles
        }

        # Add search parameters based on mode
        if search_mode == "period":
            result['period'] = period
        else:
            result['from_date'] = from_date
            result['to_date'] = to_date
        # log the result as debug mode
        logger.debug(f"[SCRAPE_NEWS] Search result: {result}")
        return result

    except Exception as e:
        raise RuntimeError(f"Failed to scrape news: {str(e)}")


def get_article_titles(articles: List[Dict[str, Any]]) -> List[str]:
    """
    Extract just the titles from articles list.

    Args:
        articles: List of article dictionaries

    Returns:
        List of article titles
    """
    return [article.get('title', '') for article in articles]


def get_article_links(articles: List[Dict[str, Any]]) -> List[str]:
    """
    Extract just the links from articles list.

    Args:
        articles: List of article dictionaries

    Returns:
        List of article URLs
    """
    return [article.get('link', '') for article in articles]


def filter_articles_by_source(
    articles: List[Dict[str, Any]],
    sources: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter articles by source/media name.

    Args:
        articles: List of article dictionaries
        sources: List of source names to filter by (case-insensitive)

    Returns:
        Filtered list of articles
    """
    sources_lower = [s.lower() for s in sources]
    return [
        article for article in articles
        if article.get('media', '').lower() in sources_lower
    ]


# Tool metadata for AI agent integration
TOOL_METADATA = {
    "name": "scrape_news",
    "description": (
        "Scrape Google News articles based on search query. "
        "Supports both time period (e.g., '7d') and specific date ranges. "
        "Returns news headlines, descriptions, sources, and links. "
        "Supports multiple languages and regions."
    ),
    "parameters": {
        "query": {
            "type": "string",
            "description": (
                "Search query for news articles. "
                "Example: 'Tesla stock', 'Indian economy', 'NVIDIA earnings'"
            ),
            "required": True
        },
        "from_date": {
            "type": "string",
            "description": (
                "Start date in MM/DD/YYYY format. "
                "Example: '01/01/2024'. "
                "Cannot be used with 'period'."
            ),
            "required": False
        },
        "to_date": {
            "type": "string",
            "description": (
                "End date in MM/DD/YYYY format. "
                "Example: '01/31/2024'. "
                "Cannot be used with 'period'."
            ),
            "required": False
        },
        "period": {
            "type": "string",
            "description": (
                "Time period for news. "
                "Options: '1h', '1d', '7d', '1m', '1y'. "
                "Cannot be used with date range."
            ),
            "required": False
        },
        "language": {
            "type": "string",
            "description": "Language code (default: 'en')",
            "required": False
        },
        "region": {
            "type": "string",
            "description": "Region code (default: 'US')",
            "required": False
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return",
            "required": False
        }
    },
    "returns": {
        "type": "object",
        "properties": {
            "total_results": {"type": "integer"},
            "query": {"type": "string"},
            "search_mode": {"type": "string"},
            "articles": {"type": "array"}
        }
    }
}
