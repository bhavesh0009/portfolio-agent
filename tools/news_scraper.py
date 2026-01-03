"""
Google News scraper tool (unified version)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from GoogleNews import GoogleNews
import re

from utils.logger import get_logger

logger = get_logger("tools.news_scraper")


def parse_period_to_timedelta(period: str) -> timedelta:
    """
    Convert period string to timedelta object.

    Args:
        period: Period string like '1h', '5d', '7d', '1m', '1y'

    Returns:
        timedelta object

    Raises:
        ValueError: If period format is invalid
    """
    match = re.match(r'^(\d+)([hdmy])$', period.lower())
    if not match:
        raise ValueError(
            f"Invalid period format: '{period}'. "
            "Expected format: number + unit (h/d/m/y), e.g., '5d', '1m', '1y'"
        )

    value = int(match.group(1))
    unit = match.group(2)

    if unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'm':
        return timedelta(days=value * 30)  # Approximate month as 30 days
    elif unit == 'y':
        return timedelta(days=value * 365)  # Approximate year as 365 days
    else:
        raise ValueError(f"Unknown period unit: {unit}")


def parse_article_date(article: Dict[str, Any]) -> Optional[datetime]:
    """
    Parse article datetime from various formats.

    Args:
        article: Article dictionary with 'datetime' or 'date' field

    Returns:
        datetime object or None if parsing fails
    """
    # Try datetime field first (ISO format)
    if 'datetime' in article and article['datetime']:
        try:
            if isinstance(article['datetime'], datetime):
                return article['datetime']
            return datetime.fromisoformat(article['datetime'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass

    # Try parsing human-readable date field
    if 'date' in article and article['date']:
        date_str = article['date'].lower()
        now = datetime.now()

        # Handle relative dates like "1 hour ago", "2 days ago", etc.
        if 'ago' in date_str:
            # Check for seconds
            if 'second' in date_str:
                match = re.search(r'(\d+)\s*second', date_str)
                if match:
                    return now - timedelta(seconds=int(match.group(1)))
            # Check for minutes
            elif 'minute' in date_str:
                match = re.search(r'(\d+)\s*minute', date_str)
                if match:
                    return now - timedelta(minutes=int(match.group(1)))
            # Check for hours
            elif 'hour' in date_str:
                match = re.search(r'(\d+)\s*hour', date_str)
                if match:
                    return now - timedelta(hours=int(match.group(1)))
            # Check for days
            elif 'day' in date_str:
                match = re.search(r'(\d+)\s*day', date_str)
                if match:
                    return now - timedelta(days=int(match.group(1)))
            # Check for weeks
            elif 'week' in date_str:
                match = re.search(r'(\d+)\s*week', date_str)
                if match:
                    return now - timedelta(weeks=int(match.group(1)))
            # Check for months
            elif 'month' in date_str:
                match = re.search(r'(\d+)\s*month', date_str)
                if match:
                    return now - timedelta(days=int(match.group(1)) * 30)

    return None


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
    import time
    from utils.metrics_collector import get_metrics_collector

    # Start timing
    tool_start_time = time.perf_counter()

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

    # Store original period for response
    original_period = period

    if has_period:
        # Convert period to date range for more reliable results
        try:
            period_delta = parse_period_to_timedelta(period)
            to_date_obj = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            from_date_obj = (to_date_obj - period_delta).replace(hour=0, minute=0, second=0, microsecond=0)

            from_date = from_date_obj.strftime('%m/%d/%Y')
            to_date = to_date_obj.strftime('%m/%d/%Y')

            search_mode = "period"
            logger.info(f"Converted period '{period}' to date range: {from_date} to {to_date}")
            print(f"Searching Google News for: '{query}'")
            print(f"Period: {period} (converted to date range: {from_date} to {to_date})")

        except ValueError as e:
            raise ValueError(f"Invalid period format: {e}")

        googlenews_params['start'] = from_date
        googlenews_params['end'] = to_date

    else:
        # Date range search (default or explicit)
        search_mode = "date_range"

        # Set default date range if not provided
        if not from_date:
            from_date_obj = (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            from_date = from_date_obj.strftime('%m/%d/%Y')
        else:
            from_date_obj = datetime.strptime(from_date, '%m/%d/%Y').replace(hour=0, minute=0, second=0, microsecond=0)

        if not to_date:
            to_date_obj = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            to_date = to_date_obj.strftime('%m/%d/%Y')
        else:
            to_date_obj = datetime.strptime(to_date, '%m/%d/%Y').replace(hour=23, minute=59, second=59, microsecond=999999)

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

        # Filter articles by date range (post-validation)
        # This ensures we only return articles actually within the requested range
        filtered_articles = []
        total_articles_before_filter = len(articles)

        for article in articles:
            article_date = parse_article_date(article)
            if article_date:
                # Check if article falls within date range
                if from_date_obj <= article_date <= to_date_obj:
                    filtered_articles.append(article)
                else:
                    logger.debug(
                        f"Filtered out article '{article.get('title', 'Unknown')}' "
                        f"(date: {article.get('date', 'Unknown')}, "
                        f"parsed: {article_date.strftime('%Y-%m-%d %H:%M:%S')})"
                    )
            else:
                # If we can't parse the date, include it to be safe
                # (but log a warning)
                logger.warning(
                    f"Could not parse date for article '{article.get('title', 'Unknown')}' "
                    f"(date field: {article.get('date', 'None')}). Including in results."
                )
                filtered_articles.append(article)

        articles = filtered_articles

        # Log filtering results
        if total_articles_before_filter > len(articles):
            logger.info(
                f"Filtered articles: {total_articles_before_filter} -> {len(articles)} "
                f"(removed {total_articles_before_filter - len(articles)} outside date range)"
            )

        # Apply max_results limit if specified
        if max_results and len(articles) > max_results:
            articles = articles[:max_results]

        # Clean up the googlenews object
        googlenews.clear()

        print(f"Found {len(articles)} articles within date range")

        # Build response
        result = {
            'total_results': len(articles),
            'query': query,
            'search_mode': search_mode,
            'language': language,
            'region': region,
            'articles': articles,
            'date_range_applied': True,
            'from_date': from_date,
            'to_date': to_date
        }

        # Add original period if it was used
        if original_period:
            result['period'] = original_period

        # Add warning if no articles found
        if len(articles) == 0:
            warning_msg = (
                f"No news articles found for query '{query}' "
                f"within date range {from_date} to {to_date}"
            )
            result['warning'] = warning_msg
            logger.warning(warning_msg)
            print(f"⚠️  {warning_msg}")

        # log the result as debug mode
        logger.debug(f"[SCRAPE_NEWS] Search result: {result}")

        # Record metrics before return
        duration_ms = (time.perf_counter() - tool_start_time) * 1000
        metrics_collector = get_metrics_collector()
        metrics_collector.record_tool_call("news_scraper", duration_ms)

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
