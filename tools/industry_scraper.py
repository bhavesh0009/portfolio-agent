"""
Industry scraper for screener.in market pages.
Scrapes industry overview and individual industry stock listings.
"""

from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from .screener_session import ScreenerSession

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger

# Initialize logger
logger = get_logger("tools.industry_scraper")


def get_industries_overview() -> List[Dict[str, Any]]:
    """
    Scrape the industries overview table from screener.in/market/

    Returns:
        List of dictionaries containing industry data with keys:
        - industry_name: Name of the industry
        - industry_url: URL to the industry page (relative path)
        - company_count: Number of companies in the industry
        - total_market_cap: Total market capitalization (in Cr)
        - median_market_cap: Median market capitalization (in Cr)
        - median_pe: Median Price to Earning ratio
        - avg_sales_growth: Weighted average sales growth (%)
        - avg_opm: Weighted average Operating Profit Margin (%)
        - avg_roce: Weighted average Return on Capital Employed (%)
        - median_1y_return: Median 1-year return (%)

    Example:
        >>> industries = get_industries_overview()
        >>> print(f"Found {len(industries)} industries")
        >>> print(industries[0])
        {
            'industry_name': '2/3 Wheelers',
            'industry_url': '/market/IN02/IN0201/IN020101/IN020101002/',
            'company_count': 10,
            'total_market_cap': 749819,
            ...
        }
    """
    logger.info("Fetching industries overview from screener.in/market/")

    session = ScreenerSession()
    session.start()

    url = "https://www.screener.in/market/"
    html = session.navigate(url)
    soup = BeautifulSoup(html, 'html.parser')

    # Find the data table
    table = soup.find('table', class_='data-table')
    if not table:
        logger.error("Could not find industries table on page")
        return []

    industries = []
    rows = table.find('tbody').find_all('tr')

    # Skip header rows (they have <th> tags)
    data_rows = [row for row in rows if not row.find('th')]

    logger.debug(f"Found {len(data_rows)} industry rows")

    for row in data_rows:
        cells = row.find_all('td')
        if len(cells) < 10:
            continue

        # Extract industry name and URL
        industry_link = cells[1].find('a')
        if not industry_link:
            continue

        industry_name = industry_link.text.strip()
        industry_url = industry_link['href']

        # Helper function to parse numeric values
        def parse_number(text: str) -> Optional[float]:
            """Parse number from text, handling commas and percentage signs"""
            if not text or text == '':
                return None
            text = text.strip().replace(',', '').replace('%', '')
            try:
                return float(text)
            except ValueError:
                return None

        industry_data = {
            'industry_name': industry_name,
            'industry_url': industry_url,
            'company_count': int(cells[2].text.strip()) if cells[2].text.strip() else 0,
            'total_market_cap': parse_number(cells[3].text),
            'median_market_cap': parse_number(cells[4].text),
            'median_pe': parse_number(cells[5].text),
            'avg_sales_growth': parse_number(cells[6].text),
            'avg_opm': parse_number(cells[7].text),
            'avg_roce': parse_number(cells[8].text),
            'median_1y_return': parse_number(cells[9].text),
        }

        industries.append(industry_data)
        logger.trace(f"Parsed industry: {industry_name} ({industry_data['company_count']} companies)")

    logger.info(f"Successfully scraped {len(industries)} industries")
    return industries


def get_industry_stocks(industry_url: str) -> Dict[str, Any]:
    """
    Scrape stock listings from a specific industry page.

    Args:
        industry_url: URL path to the industry page (e.g., '/market/IN02/IN0201/IN020101/IN020101002/')
                     Can be a full URL or relative path

    Returns:
        Dictionary containing:
        - industry_name: Name of the industry
        - breadcrumb: Hierarchical breadcrumb path
        - total_results: Total number of stocks found
        - stocks: List of stock dictionaries with available metrics

    Example:
        >>> result = get_industry_stocks('/market/IN02/IN0201/IN020101/IN020101002/')
        >>> print(f"{result['industry_name']}: {result['total_results']} stocks")
        >>> print(result['stocks'][0])
        {
            'name': 'Bajaj Auto',
            'url': '/company/BAJAJ-AUTO/consolidated/',
            'cmp': 8721.50,
            'pe': 29.24,
            'market_cap': 243554.52,
            ...
        }
    """
    logger.info(f"Fetching stocks for industry: {industry_url}")

    session = ScreenerSession()
    session.start()

    # Normalize URL
    if not industry_url.startswith('http'):
        industry_url = f"https://www.screener.in{industry_url}"

    html = session.navigate(industry_url)
    soup = BeautifulSoup(html, 'html.parser')

    # Extract breadcrumb hierarchy
    breadcrumb_list = []
    breadcrumb = soup.find('ul', class_='breadcrumb') or soup.find('div', class_='breadcrumb')
    if breadcrumb:
        items = breadcrumb.find_all('li')
        for item in items:
            link = item.find('a')
            if link:
                breadcrumb_list.append({
                    'name': link.text.strip(),
                    'url': link.get('href', '')
                })
            else:
                # Last item (current page) - no link
                text = item.get_text(strip=True)
                # Remove icon text if present
                text = text.replace('/', '').strip()
                if text and text not in ['Industries']:
                    breadcrumb_list.append({
                        'name': text,
                        'url': ''
                    })

    industry_name = breadcrumb_list[-1]['name'] if breadcrumb_list else "Unknown Industry"
    logger.debug(f"Industry breadcrumb: {' > '.join([b['name'] for b in breadcrumb_list])}")

    # Extract result count
    result_info = soup.find('div', class_='responsive-holder')
    total_results = 0
    if result_info:
        result_text = result_info.find_previous_sibling('div')
        if result_text:
            # Parse "12 results found: Showing page 1 of 1"
            text = result_text.text.strip()
            if 'results found' in text:
                try:
                    total_results = int(text.split()[0])
                except (ValueError, IndexError):
                    pass

    # Find the stock table
    table = soup.find('table', class_='data-table')
    if not table:
        logger.error("Could not find stock table on page")
        return {
            'industry_name': industry_name,
            'breadcrumb': breadcrumb_list,
            'total_results': 0,
            'stocks': []
        }

    # Extract table headers to map column positions
    headers = []
    header_row = table.find('thead') or table.find('tbody').find('tr')
    if header_row:
        header_cells = header_row.find_all('th')
        for cell in header_cells:
            header_text = cell.get_text(strip=True)
            headers.append(header_text)

    logger.debug(f"Table headers: {headers}")

    # Helper function to parse numeric values
    def parse_number(text: str) -> Optional[float]:
        """Parse number from text, handling commas, percentage signs, and empty cells"""
        if not text or text == '':
            return None
        text = text.strip().replace(',', '')
        try:
            return float(text)
        except ValueError:
            return None

    # Parse stock data rows
    stocks = []
    rows = table.find('tbody').find_all('tr')

    # Skip header row if it's in tbody
    data_rows = [row for row in rows if not row.find('th') or len(row.find_all('th')) < len(headers)]

    logger.debug(f"Found {len(data_rows)} stock rows")

    for row in data_rows:
        cells = row.find_all('td')
        if len(cells) < 3:  # Need at least S.No, Name, and one metric
            continue

        # Extract stock name and URL (typically in second column)
        stock_link = cells[1].find('a')
        if not stock_link:
            continue

        stock_name = stock_link.text.strip()
        stock_url = stock_link['href']

        # Build stock data dictionary dynamically based on available columns
        stock_data = {
            'name': stock_name,
            'url': stock_url,
        }

        # Map remaining cells to metrics based on headers
        for i in range(2, len(cells)):  # Skip S.No (0) and Name (1)
            if i >= len(headers):
                break

            cell = cells[i]
            header = headers[i]
            value_text = cell.get_text(strip=True)
            value = parse_number(value_text)

            # Map header names to field names
            # Note: Headers may have spaces removed (e.g., 'CMPRs.' instead of 'CMP Rs.')
            field_mapping = {
                'CMP Rs.': 'cmp',
                'CMPRs.': 'cmp',
                'P/E': 'pe',
                'Mar Cap Rs.Cr.': 'market_cap',
                'Mar CapRs.Cr.': 'market_cap',
                'Div Yld %': 'dividend_yield',
                'Div Yld%': 'dividend_yield',
                'NP Qtr Rs.Cr.': 'net_profit_qtr',
                'NP QtrRs.Cr.': 'net_profit_qtr',
                'Qtr Profit Var %': 'qtr_profit_growth',
                'Qtr Profit Var%': 'qtr_profit_growth',
                'Sales Qtr Rs.Cr.': 'sales_qtr',
                'Sales QtrRs.Cr.': 'sales_qtr',
                'Qtr Sales Var %': 'qtr_sales_growth',
                'Qtr Sales Var%': 'qtr_sales_growth',
                'ROCE %': 'roce',
                'ROCE%': 'roce',
            }

            field_name = field_mapping.get(header)
            if field_name:
                stock_data[field_name] = value

        stocks.append(stock_data)
        logger.trace(f"Parsed stock: {stock_name} (CMP: {stock_data.get('cmp')})")

    logger.info(f"Successfully scraped {len(stocks)} stocks from {industry_name}")

    return {
        'industry_name': industry_name,
        'breadcrumb': breadcrumb_list,
        'total_results': total_results or len(stocks),
        'stocks': stocks
    }


def search_industries(keyword: str, overview_data: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
    """
    Search for industries by keyword in their names.

    Args:
        keyword: Search term to match against industry names (case-insensitive)
        overview_data: Optional pre-fetched industry overview data.
                      If not provided, will fetch fresh data.

    Returns:
        List of matching industry dictionaries

    Example:
        >>> matches = search_industries("auto")
        >>> for industry in matches:
        ...     print(f"{industry['industry_name']} - {industry['company_count']} companies")
    """
    logger.info(f"Searching industries for keyword: '{keyword}'")

    if overview_data is None:
        overview_data = get_industries_overview()

    keyword_lower = keyword.lower()
    matches = [
        industry for industry in overview_data
        if keyword_lower in industry['industry_name'].lower()
    ]

    logger.info(f"Found {len(matches)} industries matching '{keyword}'")
    return matches
