"""
Stock screening tool using screener.in
"""

import urllib.parse
from typing import List, Optional, Dict, Any
from .screener_session import ScreenerSession
from .column_manager import map_to_short_names
from .industry_query_parser import parse_sector_industry_filter, matches_sector_industry_filter
from .yfinance_enricher import get_enricher

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger

# Initialize logger
logger = get_logger("tools.screen_stocks")


def build_query_url(query: str) -> str:
    """
    Build screener.in query URL from natural language query.

    Args:
        query: Natural language screening query
               Example: "Market capitalization > 500 AND Price to earning < 15"

    Returns:
        Complete URL for the screening query
    """
    # URL encode the query
    encoded_query = urllib.parse.quote_plus(query)

    # Build the complete URL
    base_url = "https://www.screener.in/screen/raw/"
    url = f"{base_url}?sort=&order=&source_id=&query={encoded_query}"

    return url


def screen_stocks(
    query: str,
    columns: Optional[List[str]] = None,
    auto_configure_columns: bool = True,
    fetch_all_pages: bool = True,
    max_pages: int = 0,
    page_delay: float = 1.5,
    max_results_to_return: int = 30,
    enable_storage: bool = True,
    enable_analysis: bool = True
) -> Dict[str, Any]:
    """
    Screen stocks on screener.in based on custom query.

    Args:
        query: Screening query in natural language format.
               Example: "Market capitalization > 500 AND Price to earning < 15 AND Return on capital employed > 22%"

        columns: Optional list of specific column names to return.
                 If None, returns all available columns.
                 If specified and auto_configure_columns=True, will automatically configure
                 screener.in to include these columns.
                 Example: ["Name", "CMP Rs.", "P/E", "ROE %"]

        auto_configure_columns: If True (default), automatically configures screener.in
                                to include the requested columns if they're missing.
                                Set to False to disable automatic column configuration.

        fetch_all_pages: If True (default), fetches all pages of results.
                         If False, fetches only the first page (max 50 stocks).

        max_pages: Maximum number of pages to fetch (0 = unlimited, default).
                   Only used if fetch_all_pages=True.

        page_delay: Delay in seconds between page requests (default 1.5).
                    Used for rate limiting to avoid overwhelming the server.

        max_results_to_return: Maximum number of stocks to return in response (default 30).
                               If results exceed this, full data is stored and analyzed.

        enable_storage: If True (default), stores full results when count exceeds threshold.

        enable_analysis: If True (default), analyzes results with coding agent when stored.

    Returns:
        Dictionary containing:
        - total_results: Number of stocks found
        - query_url: The URL that was used
        - stocks: List of dictionaries (all stocks if <= threshold, sample if > threshold)
        - pages_fetched: Number of pages fetched (if fetch_all_pages=True)
        - is_sampled: Boolean indicating if results were sampled
        - stored_file: Path to stored file (if sampled)
        - stored_count: Total count in stored file (if sampled)
        - sample_stocks: Same as stocks field (for clarity)
        - analysis_summary: Analysis results from coding agent (if enabled and sampled)
        - sample_note: Explanation of sampling (if sampled)

    Example:
        >>> result = screen_stocks(
        ...     query="Market capitalization > 500 AND Price to earning < 15",
        ...     columns=["Name", "CMP Rs.", "P/E"],
        ...     fetch_all_pages=True
        ... )
        >>> print(result['total_results'])
        169
        >>> print(result['pages_fetched'])
        4
        >>> print(result['stocks'][0])
        {'Name': 'Indosolar', 'CMP Rs.': '558.50', 'P/E': '13.16'}

    Raises:
        ValueError: If query is empty or credentials are missing
        RuntimeError: If login fails or data extraction fails
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    logger.separator()
    logger.info("[SCREEN_STOCKS] Input validation")
    logger.info("Received parameters:")
    logger.info(f"  Query: {query}")
    logger.info(f"  Columns: {columns}")
    logger.info(f"  Auto-configure: {auto_configure_columns}")
    logger.separator()

    # Parse query to extract and remove Sector and Industry filter conditions
    # screener.in doesn't support Sector or Industry as queryable columns,
    # but we can post-filter results after enriching with yfinance
    cleaned_query, sector_filter, industry_filter = parse_sector_industry_filter(query)
    has_sector_filter = len(sector_filter) > 0
    has_industry_filter = len(industry_filter) > 0
    has_filter = has_sector_filter or has_industry_filter

    if has_filter:
        if has_sector_filter:
            logger.info(f"Sector filter detected: {sector_filter}")
        if has_industry_filter:
            logger.info(f"Industry filter detected: {industry_filter}")
        logger.info("Will use cleaned query for screener.in and post-filter results")
        logger.info(f"Cleaned query: {cleaned_query}")
        query_to_use = cleaned_query if cleaned_query.strip() else "Market Capitalization > 0"  # Fallback if query is now empty
    else:
        query_to_use = query

    # Determine if enrichment is needed
    # We need enrichment if: (1) Sector or Industry filters present, or (2) Sector or Industry requested in columns
    needs_enrichment = has_filter or (columns and ('Industry' in columns or 'Sector' in columns))

    # Build the query URL
    url = build_query_url(query_to_use)

    with ScreenerSession() as session:
        # If specific columns are requested and auto-configure is enabled,
        # check if we need to configure columns
        if columns and auto_configure_columns:
            logger.debug("Checking column configuration...")
            current_columns = session.get_configured_columns()

            # Note: "Name" and "CMP Rs." are always present in tables and not in the configurable list
            # Also note: Some column names in config differ from table headers
            # e.g., "Current price" in config appears as "CMP Rs." in table
            always_present = ["Name", "CMP Rs.", "S.No."]

            # Filter out always-present columns from our configuration check
            columns_to_configure = [col for col in columns if col not in always_present]

            missing_columns = [col for col in columns_to_configure if col not in current_columns]

            if missing_columns:
                logger.info(f"Configuring {len(missing_columns)} missing columns: {', '.join(missing_columns)}")

                # Get available columns to validate
                available_columns = session.get_available_columns()

                # Check which requested columns are actually available
                invalid_columns = [col for col in missing_columns if col not in available_columns]
                if invalid_columns:
                    logger.warning(f"The following columns are not in the configurable list: {', '.join(invalid_columns)}")
                    logger.info("Note: Some columns like 'Name' and 'CMP Rs.' are always present and don't need configuration")

                # Configure all required columns (existing + new)
                valid_required = [col for col in missing_columns if col in available_columns]
                all_columns_to_configure = list(set(current_columns + valid_required))

                session.configure_columns(all_columns_to_configure)
            else:
                logger.info("All requested columns are already configured")

        # Navigate to query results and fetch data
        logger.info(f"Executing query: {query}")

        # Fetch data - either single page or all pages
        if fetch_all_pages:
            # Fetch all pages
            pagination_data = session.navigate_all_pages(url, max_pages=max_pages, page_delay=page_delay, verbose=True)
            stocks = pagination_data['all_stocks']
            table_headers = pagination_data['headers']
            pages_fetched = pagination_data['pages_fetched']
            total_results = pagination_data['total_results']
        else:
            # Fetch only first page
            html = session.navigate(url)
            table_data = session.extract_table_data(html)

            if not table_data or 'rows'  not in table_data:
                return {
                    'total_results': 0,
                    'query_url': url,
                    'query': query,
                    'stocks': [],
                    'pages_fetched': 0
                }

            stocks = table_data['rows']
            table_headers = table_data['headers']
            pages_fetched = 1
            total_results = len(stocks)

        # Early return if no stocks found
        if not stocks:
            return {
                'total_results': 0,
                'query_url': url,
                'query': query,
                'stocks': [],
                'pages_fetched': pages_fetched,
                'available_columns': table_headers
            }

        # Always enrich with Symbol/Exchange (lightweight, no API calls)
        if len(stocks) > 0:
            enricher = get_enricher()

            # If Industry/Sector requested, do full enrichment
            if needs_enrichment:
                logger.separator()
                logger.info(f"[YFINANCE ENRICHMENT] Enriching {len(stocks)} stocks with symbol, industry and sector data")
                logger.separator()

                # Full enrichment (includes symbols + industry/sector via yfinance API)
                enriched_count = 0
                for stock in stocks:
                    try:
                        enricher.enrich_stock(stock)
                        enriched_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to enrich stock {stock.get('Name', 'Unknown')}: {e}")
                        # Set defaults on failure
                        stock['Industry'] = 'Unknown'
                        stock['Sector'] = 'Unknown'
                        stock['Symbol'] = 'Unknown'
                        stock['Exchange'] = 'Unknown'

                logger.info(f"Enriched {enriched_count}/{len(stocks)} stocks successfully")
                enricher.log_cache_stats()
                logger.separator()
            else:
                # Lightweight symbol-only enrichment (no API calls)
                logger.separator()
                logger.info(f"[SYMBOL EXTRACTION] Extracting symbols for {len(stocks)} stocks")
                logger.separator()

                for stock in stocks:
                    try:
                        enricher.enrich_symbol_only(stock)
                    except Exception as e:
                        logger.warning(f"Failed to extract symbol for {stock.get('Name', 'Unknown')}: {e}")
                        stock['Symbol'] = 'Unknown'
                        stock['Exchange'] = 'Unknown'

                logger.info(f"Symbol extraction complete")
                logger.separator()

        # Post-filter by sector and/or industry if filters were present in query
        if has_filter:
            original_count = len(stocks)

            if has_sector_filter:
                logger.info(f"[POST-FILTERING] Filtering by sector: {sector_filter}")
            if has_industry_filter:
                logger.info(f"[POST-FILTERING] Filtering by industry: {industry_filter}")

            filtered_stocks = [stock for stock in stocks if matches_sector_industry_filter(stock, sector_filter, industry_filter)]

            logger.info(f"Post-filtered: {original_count} -> {len(filtered_stocks)} stocks")
            stocks = filtered_stocks

            # Update total_results to reflect filtered count
            total_results = len(stocks)

        # Filter columns if specified
        if columns:
            # Map config names to short names first
            short_names = map_to_short_names(columns)

            # Note: Table headers may have suffixes like "ROE %" or "Mar Cap Rs.Cr."
            # We need to find the actual column names in the table that match our short names
            filtered_stocks = []
            for stock in stocks:
                filtered_stock = {}

                # Try to match each requested column with actual table columns
                for i, config_name in enumerate(columns):
                    short_name = short_names[i]

                    # First try exact match with config name
                    if config_name in stock:
                        filtered_stock[config_name] = stock[config_name]
                    # Then try exact match with short name
                    elif short_name in stock:
                        filtered_stock[config_name] = stock[short_name]
                    # Then try fuzzy match (short name might have suffix like "%" or "Rs.Cr.")
                    else:
                        # Look for columns that start with the short name
                        found = False
                        for table_col in stock.keys():
                            if table_col.startswith(short_name):
                                filtered_stock[config_name] = stock[table_col]
                                found = True
                                break

                # Always include Name and CMP Rs. if they exist
                if 'Name' in stock and 'Name' not in filtered_stock:
                    filtered_stock['Name'] = stock['Name']
                if 'CMP Rs.' in stock and 'CMP Rs.' not in filtered_stock:
                    filtered_stock['CMP Rs.'] = stock['CMP Rs.']

                filtered_stocks.append(filtered_stock)
            stocks = filtered_stocks

        # Build column mapping info for transparency
        column_mapping_info = None
        if columns:
            logger.separator()
            logger.info("[SCREEN_STOCKS] Column name mapping")
            logger.info("Mapping requested columns to short names:")

            # Map config names to short names for reference
            short_names = map_to_short_names(columns)
            column_mapping_info = {columns[i]: short_names[i] for i in range(len(columns))}

            for config_name, short_name in column_mapping_info.items():
                status = "MAPPED" if config_name != short_name else "NO MAPPING"
                logger.debug(f"  '{config_name}' -> '{short_name}' [{status}]")

            # Show sample of filtered data
            if stocks and len(stocks) > 0:
                logger.info("First stock filtered data (sample):")
                for key in list(stocks[0].keys())[:5]:
                    logger.debug(f"  '{key}': {stocks[0][key]}")
                if len(stocks[0]) > 5:
                    logger.debug(f"  ... and {len(stocks[0]) - 5} more columns")

            logger.separator()

        # Handle large result sets: Store + Analyze + Sample
        if len(stocks) > max_results_to_return and enable_storage:
            logger.separator()
            logger.info(f"[RESULT_MANAGEMENT] Large result set detected ({len(stocks)} stocks > {max_results_to_return} threshold)")
            logger.separator()

            # Import result manager
            from .result_manager import ResultManager

            # Create base result for storage
            full_result = {
                'total_results': total_results,
                'query_url': url,
                'query': query,
                'available_columns': table_headers,
                'stocks': stocks,
                'pages_fetched': pages_fetched
            }
            if column_mapping_info:
                full_result['column_mapping'] = column_mapping_info

            # Store full results and analyze if enabled
            manager = ResultManager()
            stored_file = manager.save(full_result, query, metadata={'stock_count': len(stocks)})

            # Analyze results with coding agent
            analysis = None
            if enable_analysis:
                logger.info("[RESULT_MANAGEMENT] Analyzing results with coding agent...")
                try:
                    analysis = manager.analyze(stocks, query)
                    logger.info("[RESULT_MANAGEMENT] Analysis complete")
                    logger.info(f"\n{analysis.get('markdown', '')}")
                except Exception as e:
                    logger.error(f"[RESULT_MANAGEMENT] Analysis failed: {e}")
                    analysis = {"error": str(e), "summary": f"Analysis failed: {e}"}

            # Create sample (first N stocks)
            sample_stocks = stocks[:max_results_to_return]

            # Build response with sampled data
            result = {
                'total_results': total_results,
                'query_url': url,
                'query': query,
                'available_columns': table_headers,
                'stocks': sample_stocks,  # Return only sample
                'pages_fetched': pages_fetched,
                'is_sampled': True,
                'stored_file': stored_file,
                'stored_count': len(stocks),
                'sample_stocks': sample_stocks,
                'sample_note': (
                    f"Results ({len(stocks)}) exceeded threshold ({max_results_to_return}). "
                    f"Full data stored in {stored_file}. "
                    f"Returning first {len(sample_stocks)} stocks as sample. "
                    f"{'Analysis included below.' if analysis else ''}"
                )
            }

            if column_mapping_info:
                result['column_mapping'] = column_mapping_info

            if analysis:
                result['analysis_summary'] = analysis.get('summary', '')
                result['analysis_markdown'] = analysis.get('markdown', '')
                result['analysis_statistics'] = analysis.get('statistics', {})
                result['analysis_suggestions'] = analysis.get('suggestions', [])

            print(f"\n[RESULT_MANAGEMENT] Returning {len(sample_stocks)} sample stocks (full {len(stocks)} stored)")
            return result

        else:
            # Normal response (not sampled)
            result = {
                'total_results': total_results,
                'query_url': url,
                'query': query,
                'available_columns': table_headers,
                'stocks': stocks,
                'pages_fetched': pages_fetched,
                'is_sampled': False
            }

            if column_mapping_info:
                result['column_mapping'] = column_mapping_info

            return result


def get_available_ratios() -> List[str]:
    """
    Get list of all available ratios that can be used in queries.

    Returns:
        List of ratio names
    """
    import csv
    from pathlib import Path

    ratios_file = Path(__file__).parent.parent / 'data' / 'screener_ratios.csv'

    if not ratios_file.exists():
        raise FileNotFoundError(f"Ratios file not found at {ratios_file}")

    with open(ratios_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        ratios = [row[0].split('→')[1] if '→' in row[0] else row[0] for row in reader]

    return ratios


# Tool metadata for AI agent integration
TOOL_METADATA = {
    "name": "screen_stocks",
    "description": (
        "Screen stocks on screener.in based on custom filtering criteria. "
        "Supports 335+ financial ratios including market cap, P/E, ROE, ROCE, etc. "
        "Returns structured data with stock names and selected metrics."
    ),
    "parameters": {
        "query": {
            "type": "string",
            "description": (
                "Screening query using natural language with ratio names and conditions. "
                "Example: 'Market capitalization > 500 AND Price to earning < 15 AND "
                "Return on capital employed > 22%'"
            ),
            "required": True
        },
        "columns": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Optional list of specific columns to return. "
                "If not specified, returns all available columns."
            ),
            "required": False
        }
    },
    "returns": {
        "type": "object",
        "properties": {
            "total_results": {"type": "integer"},
            "query_url": {"type": "string"},
            "stocks": {"type": "array"}
        }
    }
}
