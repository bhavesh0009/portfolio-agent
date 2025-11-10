"""
Sector and Industry query parser for stock screening

Parses queries to extract and remove Sector and Industry filter conditions.
This is needed because screener.in doesn't support Sector or Industry as queryable columns,
but we can post-filter results after enriching with yfinance data.
"""

import re
from typing import Tuple, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger

logger = get_logger("tools.industry_query_parser")


def extract_sector_industry_values(query: str) -> Tuple[List[str], List[str]]:
    """
    Extract both sector and industry values from query string.

    Supports formats for both Sector and Industry:
    - Sector = "Infrastructure"
    - Industry = "Hotels"
    - (Sector = "Infrastructure" OR Sector = "Capital Goods")
    - (Industry = "Hotels" OR Industry = "Restaurants")
    - Sector IN ("Infrastructure", "Capital Goods")
    - Industry IN ("Hotels", "Restaurants")

    Args:
        query: SQL-like query string

    Returns:
        Tuple of (list_of_sectors, list_of_industries) (case-preserved)

    Examples:
        >>> extract_sector_industry_values('Sector = "Infrastructure"')
        (['Infrastructure'], [])

        >>> extract_sector_industry_values('Industry = "Hotels"')
        ([], ['Hotels'])

        >>> extract_sector_industry_values('Sector = "Infrastructure" AND Industry = "Hotels"')
        (['Infrastructure'], ['Hotels'])
    """
    sectors = []
    industries = []

    # Pattern 1: Sector = "value" or Sector = 'value'
    pattern_sector = r'Sector\s*=\s*["\']([^"\']+)["\']'
    matches = re.findall(pattern_sector, query, re.IGNORECASE)
    sectors.extend(matches)

    # Pattern 2: Sector IN ("val1", "val2", ...)
    pattern_sector_in = r'Sector\s+IN\s*\(([^)]+)\)'
    matches = re.findall(pattern_sector_in, query, re.IGNORECASE)
    for match in matches:
        values = re.findall(r'["\']([^"\']+)["\']', match)
        sectors.extend(values)

    # Pattern 3: Industry = "value" or Industry = 'value'
    pattern_industry = r'Industry\s*=\s*["\']([^"\']+)["\']'
    matches = re.findall(pattern_industry, query, re.IGNORECASE)
    industries.extend(matches)

    # Pattern 4: Industry IN ("val1", "val2", ...)
    pattern_industry_in = r'Industry\s+IN\s*\(([^)]+)\)'
    matches = re.findall(pattern_industry_in, query, re.IGNORECASE)
    for match in matches:
        values = re.findall(r'["\']([^"\']+)["\']', match)
        industries.extend(values)

    # Remove duplicates while preserving order
    def deduplicate(items):
        seen = set()
        unique = []
        for item in items:
            item_lower = item.lower()
            if item_lower not in seen:
                seen.add(item_lower)
                unique.append(item)
        return unique

    return (deduplicate(sectors), deduplicate(industries))


def extract_industry_values(query: str) -> List[str]:
    """
    Extract all industry values from query string.

    DEPRECATED: Use extract_sector_industry_values() instead for both Sector and Industry.

    Supports formats:
    - Industry = "Hotels"
    - Industry = 'Hotels'
    - (Industry = "Hotels" OR Industry = "Restaurants")
    - Industry IN ("Hotels", "Restaurants")

    Args:
        query: SQL-like query string

    Returns:
        List of industry values (case-preserved)

    Examples:
        >>> extract_industry_values('Industry = "Hotels"')
        ['Hotels']

        >>> extract_industry_values('(Industry = "Hotels" OR Industry = "Restaurants")')
        ['Hotels', 'Restaurants']
    """
    _, industries = extract_sector_industry_values(query)
    return industries


def remove_sector_industry_conditions(query: str) -> str:
    """
    Remove all Sector and Industry filter conditions from query.

    Handles:
    - Simple: Sector = "Infrastructure", Industry = "Hotels"
    - OR groups: (Sector = "Infrastructure" OR Sector = "Capital Goods")
    - IN clauses: Sector IN ("Infrastructure", "Capital Goods"), Industry IN ("Hotels", "Restaurants")
    - Mixed: Market Cap > 5000 AND (Sector = "Infrastructure" OR Industry = "Hotels") AND ROE > 15

    Cleans up leftover AND/OR operators and parentheses.

    Args:
        query: SQL-like query string

    Returns:
        Query string with Sector and Industry conditions removed

    Examples:
        >>> remove_sector_industry_conditions('Market Cap > 5000 AND Sector = "Infrastructure"')
        'Market Cap > 5000'

        >>> remove_sector_industry_conditions('(Sector = "Infrastructure" OR Sector = "Capital Goods") AND Market Cap > 5000')
        'Market Cap > 5000'
    """
    original_query = query

    # Pattern 1: Remove parenthesized OR groups containing only Sector/Industry conditions
    # Example: (Sector = "Infrastructure" OR Sector = "Capital Goods")
    # Example: (Industry = "Hotels" OR Industry = "Restaurants")
    pattern1 = r'\(\s*(?:Sector|Industry)\s*=\s*["\'][^"\']+["\']\s*(?:OR\s+(?:Sector|Industry)\s*=\s*["\'][^"\']+["\']\s*)*\)'
    query = re.sub(pattern1, '', query, flags=re.IGNORECASE)

    # Pattern 2: Remove Sector IN clauses
    pattern2 = r'Sector\s+IN\s*\([^)]+\)'
    query = re.sub(pattern2, '', query, flags=re.IGNORECASE)

    # Pattern 3: Remove Industry IN clauses
    pattern3 = r'Industry\s+IN\s*\([^)]+\)'
    query = re.sub(pattern3, '', query, flags=re.IGNORECASE)

    # Pattern 4: Remove simple Sector conditions
    pattern4 = r'Sector\s*=\s*["\'][^"\']+["\']'
    query = re.sub(pattern4, '', query, flags=re.IGNORECASE)

    # Pattern 5: Remove simple Industry conditions
    pattern5 = r'Industry\s*=\s*["\'][^"\']+["\']'
    query = re.sub(pattern5, '', query, flags=re.IGNORECASE)

    # Clean up leftover logical operators and parentheses
    # Remove leading/trailing AND/OR
    query = re.sub(r'^\s*(?:AND|OR)\s+', '', query, flags=re.IGNORECASE)
    query = re.sub(r'\s+(?:AND|OR)\s*$', '', query, flags=re.IGNORECASE)

    # Remove duplicate AND/OR operators
    query = re.sub(r'\s+AND\s+AND\s+', ' AND ', query, flags=re.IGNORECASE)
    query = re.sub(r'\s+OR\s+OR\s+', ' OR ', query, flags=re.IGNORECASE)

    # Remove AND/OR before/after parentheses if they're now empty or invalid
    query = re.sub(r'\s+(?:AND|OR)\s+\(\s*\)', '', query, flags=re.IGNORECASE)
    query = re.sub(r'\(\s*\)\s+(?:AND|OR)\s+', '', query, flags=re.IGNORECASE)

    # Remove standalone AND/OR between conditions
    query = re.sub(r'(AND|OR)\s+\1\s+', r'\1 ', query, flags=re.IGNORECASE)

    # Remove empty parentheses
    query = re.sub(r'\(\s*\)', '', query)

    # Clean up multiple spaces
    query = re.sub(r'\s+', ' ', query)

    # Final cleanup of leading/trailing AND/OR (in case they reappeared)
    query = re.sub(r'^\s*(?:AND|OR)\s+', '', query, flags=re.IGNORECASE)
    query = re.sub(r'\s+(?:AND|OR)\s*$', '', query, flags=re.IGNORECASE)

    query = query.strip()

    if query != original_query:
        logger.debug(f"Query transformation:")
        logger.debug(f"  Before: {original_query}")
        logger.debug(f"  After:  {query}")

    return query


def remove_industry_conditions(query: str) -> str:
    """
    Remove all Industry filter conditions from query.

    DEPRECATED: Use remove_sector_industry_conditions() instead for both Sector and Industry.

    Handles:
    - Simple: Industry = "Hotels"
    - OR groups: (Industry = "Hotels" OR Industry = "Restaurants")
    - IN clauses: Industry IN ("Hotels", "Restaurants")
    - Mixed: Market Cap > 5000 AND (Industry = "Hotels" OR Industry = "Restaurants") AND ROE > 15

    Cleans up leftover AND/OR operators and parentheses.

    Args:
        query: SQL-like query string

    Returns:
        Query string with Industry conditions removed

    Examples:
        >>> remove_industry_conditions('Market Cap > 5000 AND Industry = "Hotels"')
        'Market Cap > 5000'

        >>> remove_industry_conditions('Industry = "Hotels" AND Market Cap > 5000')
        'Market Cap > 5000'
    """
    return remove_sector_industry_conditions(query)


def parse_sector_industry_filter(query: str) -> Tuple[str, List[str], List[str]]:
    """
    Parse query to extract and remove both Sector and Industry filter conditions.

    Args:
        query: SQL-like query string

    Returns:
        Tuple of (cleaned_query, list_of_sectors, list_of_industries)
        - cleaned_query: Query with Sector and Industry conditions removed
        - list_of_sectors: List of sector values to filter by (empty if no Sector filter)
        - list_of_industries: List of industry values to filter by (empty if no Industry filter)

    Examples:
        >>> parse_sector_industry_filter('Market Cap > 5000 AND Sector = "Infrastructure"')
        ('Market Cap > 5000', ['Infrastructure'], [])

        >>> parse_sector_industry_filter('Industry = "Hotels" AND Market Cap > 5000')
        ('Market Cap > 5000', [], ['Hotels'])

        >>> parse_sector_industry_filter('(Sector = "Infrastructure" OR Sector = "Capital Goods") AND Industry = "Hotels"')
        ('', ['Infrastructure', 'Capital Goods'], ['Hotels'])

        >>> parse_sector_industry_filter('Market Cap > 5000 AND ROE > 15')
        ('Market Cap > 5000 AND ROE > 15', [], [])
    """
    # Extract sector and industry values
    sectors, industries = extract_sector_industry_values(query)

    # Remove sector and industry conditions
    cleaned_query = remove_sector_industry_conditions(query)

    if sectors:
        logger.info(f"Detected Sector filter in query: {sectors}")
        logger.info(f"Will post-filter results by these sectors after enrichment")

    if industries:
        logger.info(f"Detected Industry filter in query: {industries}")
        logger.info(f"Will post-filter results by these industries after enrichment")

    return (cleaned_query, sectors, industries)


def parse_industry_filter(query: str) -> Tuple[str, List[str]]:
    """
    Parse query to extract and remove Industry filter conditions.

    DEPRECATED: Use parse_sector_industry_filter() instead for both Sector and Industry.

    Args:
        query: SQL-like query string

    Returns:
        Tuple of (cleaned_query, list_of_industries)
        - cleaned_query: Query with Industry conditions removed
        - list_of_industries: List of industry values to filter by (empty if no Industry filter)

    Examples:
        >>> parse_industry_filter('Market Cap > 5000 AND Industry = "Hotels"')
        ('Market Cap > 5000', ['Hotels'])

        >>> parse_industry_filter('Industry = "Hotels" OR Industry = "Restaurants"')
        ('', ['Hotels', 'Restaurants'])

        >>> parse_industry_filter('Market Cap > 5000 AND ROE > 15')
        ('Market Cap > 5000 AND ROE > 15', [])
    """
    cleaned_query, _, industries = parse_sector_industry_filter(query)
    return (cleaned_query, industries)


def matches_industry_filter(stock: dict, allowed_industries: List[str]) -> bool:
    """
    Check if stock matches any of the allowed industries.

    Case-insensitive matching. If industry is 'Unknown' (yfinance enrichment failed),
    the stock is INCLUDED to avoid losing valid candidates.

    Args:
        stock: Stock dict with 'Industry' field
        allowed_industries: List of allowed industry values

    Returns:
        True if stock's industry matches any allowed industry (or is Unknown)

    Examples:
        >>> stock = {'Industry': 'Hotels'}
        >>> matches_industry_filter(stock, ['Hotels', 'Restaurants'])
        True

        >>> stock = {'Industry': 'Technology'}
        >>> matches_industry_filter(stock, ['Hotels', 'Restaurants'])
        False

        >>> stock = {'Industry': 'Unknown'}  # yfinance failed, but matched all other criteria
        >>> matches_industry_filter(stock, ['Hotels', 'Restaurants'])
        True  # INCLUDED - don't lose valid stocks due to enrichment failure
    """
    if not allowed_industries:
        return True  # No filter means all industries allowed

    stock_industry = stock.get('Industry', '').strip()

    # If industry is unknown (enrichment failed), include it anyway
    # to avoid losing stocks that matched all other criteria
    if not stock_industry or stock_industry == 'Unknown':
        logger.debug(f"Stock {stock.get('Name', 'Unknown')}: Industry enrichment failed (Unknown), including in results")
        return True

    # Case-insensitive comparison
    stock_industry_lower = stock_industry.lower()
    allowed_industries_lower = [ind.lower() for ind in allowed_industries]

    return stock_industry_lower in allowed_industries_lower


def matches_sector_filter(stock: dict, allowed_sectors: List[str]) -> bool:
    """
    Check if stock matches any of the allowed sectors.

    Case-insensitive matching. If sector is 'Unknown' (yfinance enrichment failed),
    the stock is INCLUDED to avoid losing valid candidates.

    Args:
        stock: Stock dict with 'Sector' field
        allowed_sectors: List of allowed sector values

    Returns:
        True if stock's sector matches any allowed sector (or is Unknown)

    Examples:
        >>> stock = {'Sector': 'Infrastructure'}
        >>> matches_sector_filter(stock, ['Infrastructure', 'Capital Goods'])
        True

        >>> stock = {'Sector': 'Technology'}
        >>> matches_sector_filter(stock, ['Infrastructure', 'Capital Goods'])
        False

        >>> stock = {'Sector': 'Unknown'}  # yfinance failed, but matched all other criteria
        >>> matches_sector_filter(stock, ['Infrastructure', 'Capital Goods'])
        True  # INCLUDED - don't lose valid stocks due to enrichment failure
    """
    if not allowed_sectors:
        return True  # No filter means all sectors allowed

    stock_sector = stock.get('Sector', '').strip()

    # If sector is unknown (enrichment failed), include it anyway
    # to avoid losing stocks that matched all other criteria
    if not stock_sector or stock_sector == 'Unknown':
        logger.debug(f"Stock {stock.get('Name', 'Unknown')}: Sector enrichment failed (Unknown), including in results")
        return True

    # Case-insensitive comparison
    stock_sector_lower = stock_sector.lower()
    allowed_sectors_lower = [sec.lower() for sec in allowed_sectors]

    return stock_sector_lower in allowed_sectors_lower


def matches_sector_industry_filter(stock: dict, allowed_sectors: List[str], allowed_industries: List[str]) -> bool:
    """
    Check if stock matches any of the allowed sectors AND industries.

    Case-insensitive matching. If both filters are provided, stock must match at least one sector AND at least one industry.
    If only one filter is provided, use that filter. If neither is provided, all stocks match.

    Args:
        stock: Stock dict with 'Sector' and 'Industry' fields
        allowed_sectors: List of allowed sector values (empty = no sector filter)
        allowed_industries: List of allowed industry values (empty = no industry filter)

    Returns:
        True if stock matches the filters

    Examples:
        >>> stock = {'Sector': 'Infrastructure', 'Industry': 'Hotels'}
        >>> matches_sector_industry_filter(stock, ['Infrastructure'], ['Hotels'])
        True

        >>> stock = {'Sector': 'Technology', 'Industry': 'Software'}
        >>> matches_sector_industry_filter(stock, ['Infrastructure'], ['Hotels'])
        False
    """
    sector_match = matches_sector_filter(stock, allowed_sectors)
    industry_match = matches_industry_filter(stock, allowed_industries)

    # If no filters provided, match all stocks
    if not allowed_sectors and not allowed_industries:
        return True

    # If both filters provided, both must match
    if allowed_sectors and allowed_industries:
        return sector_match and industry_match

    # If only one filter provided, that one must match
    if allowed_sectors:
        return sector_match

    if allowed_industries:
        return industry_match

    return True


if __name__ == "__main__":
    # Test cases
    print("Testing Industry Query Parser\n")

    test_queries = [
        'Market Capitalization > 5000 AND Industry = "Hotels"',
        'Industry = "Hotels" AND Market Cap > 5000',
        '(Industry = "Hotels" OR Industry = "Restaurants") AND Market Cap > 5000',
        'Market Cap > 5000 AND (Industry = "Hotels" OR Industry = "Restaurants")',
        'Industry IN ("Hotels", "Restaurants", "Retail")',
        'Market Cap > 5000 AND Industry IN ("Hotels", "Restaurants") AND ROE > 15',
        'Industry = "Hotels"',
        'Market Cap > 5000 AND ROE > 15',  # No Industry filter
    ]

    print("="*80)
    print("Test 1: Parsing queries")
    print("="*80)
    for query in test_queries:
        print(f"\nOriginal: {query}")
        cleaned, industries = parse_industry_filter(query)
        print(f"Cleaned:  {cleaned}")
        print(f"Industries: {industries}")

    print("\n" + "="*80)
    print("Test 2: Matching stocks")
    print("="*80)

    test_stocks = [
        {'Name': 'Hotel Co', 'Industry': 'Hotels'},
        {'Name': 'Restaurant Co', 'Industry': 'Restaurants'},
        {'Name': 'Tech Co', 'Industry': 'Technology'},
        {'Name': 'Unknown Co', 'Industry': 'Unknown'},
    ]

    allowed = ['Hotels', 'Restaurants']
    print(f"\nAllowed industries: {allowed}")

    for stock in test_stocks:
        match = matches_industry_filter(stock, allowed)
        print(f"  {stock['Name']} ({stock['Industry']}): {'MATCH' if match else 'NO MATCH'}")
