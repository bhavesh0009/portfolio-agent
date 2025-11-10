"""
yfinance enrichment utility for stock data

Enriches stock screening results with industry and sector data from yfinance.
Extracts NSE/BSE symbols from screener.in company links and fetches additional data.
"""

import re
from typing import Dict, Optional, Tuple
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger

logger = get_logger("tools.yfinance_enricher")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    logger.warning("yfinance not installed. Install with: pip install yfinance")
    YFINANCE_AVAILABLE = False


class YFinanceEnricher:
    """
    Enriches stock data with industry and sector information from yfinance.

    Features:
    - Extracts NSE/BSE symbols from screener.in company hrefs
    - Fetches industry and sector data using yfinance API
    - In-memory session caching to avoid repeated API calls
    - Graceful error handling (sets 'Unknown' on failures)
    """

    def __init__(self):
        """Initialize enricher with empty cache"""
        self._cache: Dict[str, Dict[str, str]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._enrichment_failures = 0  # Track how many enrichments failed
        self._enrichment_successes = 0  # Track how many enrichments succeeded

        if not YFINANCE_AVAILABLE:
            logger.error("yfinance is not available. Enrichment will not work.")

    def extract_symbol_from_href(self, href: str) -> Optional[Tuple[str, str]]:
        """
        Extract stock symbol and exchange from screener.in company href.

        Args:
            href: Company link href (e.g., "/company/WAAREEENER/consolidated/" or "/company/539337/")

        Returns:
            Tuple of (symbol, exchange) e.g., ('WAAREEENER', 'NSE') or ('539337', 'BSE')
            Returns None if extraction fails

        Examples:
            >>> extract_symbol_from_href("/company/WAAREEENER/consolidated/")
            ('WAAREEENER', 'NSE')

            >>> extract_symbol_from_href("/company/539337/")
            ('539337', 'BSE')
        """
        if not href:
            return None

        # Pattern: /company/{SYMBOL}/ or /company/{SYMBOL}/consolidated/
        pattern = r'/company/([^/]+)/?'
        match = re.search(pattern, href)

        if not match:
            logger.debug(f"Could not extract symbol from href: {href}")
            return None

        symbol = match.group(1)

        # Determine exchange based on symbol format
        # NSE symbols are alphabetic (may contain &, -, etc.)
        # BSE symbols are purely numeric
        if symbol.isdigit():
            exchange = 'BSE'
        else:
            exchange = 'NSE'

        return (symbol, exchange)

    def get_yfinance_ticker(self, symbol: str, exchange: str) -> str:
        """
        Convert symbol and exchange to yfinance ticker format.

        Args:
            symbol: Stock symbol
            exchange: Exchange ('NSE' or 'BSE')

        Returns:
            yfinance ticker string (e.g., 'WAAREEENER.NS' or '539337.BO')
        """
        suffix = '.NS' if exchange == 'NSE' else '.BO'
        return f"{symbol}{suffix}"

    def get_industry_sector(self, symbol: str, exchange: str) -> Dict[str, str]:
        """
        Fetch industry and sector from yfinance for given symbol.

        Uses in-memory cache to avoid repeated API calls.
        Returns 'Unknown' for industry/sector if fetch fails.

        Args:
            symbol: Stock symbol
            exchange: Exchange ('NSE' or 'BSE')

        Returns:
            Dict with 'industry' and 'sector' keys
        """
        if not YFINANCE_AVAILABLE:
            return {'industry': 'Unknown', 'sector': 'Unknown'}

        cache_key = f"{symbol}:{exchange}"

        # Check cache first
        if cache_key in self._cache:
            self._cache_hits += 1
            logger.trace(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        self._cache_misses += 1
        logger.trace(f"Cache miss for {cache_key}, fetching from yfinance...")

        # Fetch from yfinance
        ticker_str = self.get_yfinance_ticker(symbol, exchange)

        try:
            ticker = yf.Ticker(ticker_str)
            info = ticker.info

            industry = info.get('industry', 'Unknown')
            sector = info.get('sector', 'Unknown')

            # Handle None values
            if industry is None:
                industry = 'Unknown'
            if sector is None:
                sector = 'Unknown'

            result = {
                'industry': industry,
                'sector': sector
            }

            # Cache the result
            self._cache[cache_key] = result

            logger.debug(f"Fetched {ticker_str}: Industry={industry}, Sector={sector}")

            return result

        except Exception as e:
            logger.warning(f"Failed to fetch data for {ticker_str}: {e}")

            # Return Unknown on failure
            result = {
                'industry': 'Unknown',
                'sector': 'Unknown'
            }

            # Cache the failure to avoid retrying
            self._cache[cache_key] = result

            return result

    def enrich_symbol_only(self, stock_data: Dict) -> Dict:
        """
        Lightweight enrichment: Only extract Symbol/Exchange from _company_href.
        Does NOT make yfinance API calls for Industry/Sector.

        Adds 'Symbol', 'Exchange' fields only.

        Args:
            stock_data: Stock dict from screener results (must have '_company_href')

        Returns:
            Enriched stock dict (modifies in place and returns)
        """
        # Check if href is available
        href = stock_data.get('_company_href')

        if not href:
            logger.debug(f"No _company_href found for stock: {stock_data.get('Name', 'Unknown')}")
            stock_data['Symbol'] = 'Unknown'
            stock_data['Exchange'] = 'Unknown'
            return stock_data

        # Extract symbol and exchange
        extracted = self.extract_symbol_from_href(href)

        if not extracted:
            logger.debug(f"Could not extract symbol from href: {href}")
            stock_data['Symbol'] = 'Unknown'
            stock_data['Exchange'] = 'Unknown'
            return stock_data

        symbol, exchange = extracted
        stock_data['Symbol'] = symbol
        stock_data['Exchange'] = exchange

        return stock_data

    def enrich_stock(self, stock_data: Dict) -> Dict:
        """
        Enrich stock data dict with industry and sector from yfinance.

        Looks for '_company_href' field in stock_data to extract symbol.
        Adds 'Industry', 'Sector', 'Symbol', 'Exchange' fields.

        Args:
            stock_data: Stock dict from screener results (must have '_company_href')

        Returns:
            Enriched stock dict (modifies in place and returns)
        """
        # Check if href is available
        href = stock_data.get('_company_href')

        if not href:
            logger.debug(f"No _company_href found for stock: {stock_data.get('Name', 'Unknown')}")
            stock_data['Industry'] = 'Unknown'
            stock_data['Sector'] = 'Unknown'
            stock_data['Symbol'] = 'Unknown'
            stock_data['Exchange'] = 'Unknown'
            self._enrichment_failures += 1
            return stock_data

        # Extract symbol and exchange
        extracted = self.extract_symbol_from_href(href)

        if not extracted:
            logger.debug(f"Could not extract symbol from href: {href}")
            stock_data['Industry'] = 'Unknown'
            stock_data['Sector'] = 'Unknown'
            stock_data['Symbol'] = 'Unknown'
            stock_data['Exchange'] = 'Unknown'
            self._enrichment_failures += 1
            return stock_data

        symbol, exchange = extracted

        # Get industry and sector
        data = self.get_industry_sector(symbol, exchange)

        # Add to stock data
        stock_data['Symbol'] = symbol
        stock_data['Exchange'] = exchange
        stock_data['Industry'] = data['industry']
        stock_data['Sector'] = data['sector']

        # Track success or failure
        if data['industry'] == 'Unknown' or data['sector'] == 'Unknown':
            self._enrichment_failures += 1
        else:
            self._enrichment_successes += 1

        return stock_data

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache and enrichment statistics.

        Returns:
            Dict with cache_hits, cache_misses, cache_size, enrichment_successes, enrichment_failures
        """
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_size': len(self._cache),
            'enrichment_successes': self._enrichment_successes,
            'enrichment_failures': self._enrichment_failures
        }

    def log_cache_stats(self):
        """Log cache and enrichment statistics"""
        stats = self.get_cache_stats()
        total_requests = stats['cache_hits'] + stats['cache_misses']
        hit_rate = (stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0

        total_enrichments = stats['enrichment_successes'] + stats['enrichment_failures']
        failure_rate = (stats['enrichment_failures'] / total_enrichments * 100) if total_enrichments > 0 else 0

        logger.info(f"yfinance cache stats: {stats['cache_hits']} hits, {stats['cache_misses']} misses "
                   f"({hit_rate:.1f}% hit rate), {stats['cache_size']} entries")

        if total_enrichments > 0:
            logger.info(f"yfinance enrichment stats: {stats['enrichment_successes']} successful, "
                       f"{stats['enrichment_failures']} failed ({failure_rate:.1f}% failure rate)")


# Singleton instance for session-wide caching
_enricher_instance = None


def get_enricher() -> YFinanceEnricher:
    """
    Get singleton enricher instance.

    This ensures we have session-wide caching across multiple screen_stocks calls.
    """
    global _enricher_instance
    if _enricher_instance is None:
        _enricher_instance = YFinanceEnricher()
    return _enricher_instance


if __name__ == "__main__":
    # Test the enricher
    enricher = YFinanceEnricher()

    # Test symbol extraction
    test_cases = [
        "/company/WAAREEENER/consolidated/",
        "/company/539337/",
        "/company/TCS/",
        "/company/500325/"
    ]

    print("Testing symbol extraction:")
    for href in test_cases:
        result = enricher.extract_symbol_from_href(href)
        print(f"  {href} -> {result}")

    print("\nTesting enrichment:")
    if YFINANCE_AVAILABLE:
        # Test NSE stock
        test_stock_nse = {
            'Name': 'Waaree Energies',
            '_company_href': '/company/WAAREEENER/consolidated/'
        }
        enriched_nse = enricher.enrich_stock(test_stock_nse)
        print(f"\nNSE Stock: {enriched_nse['Name']}")
        print(f"  Symbol: {enriched_nse.get('Symbol')}")
        print(f"  Exchange: {enriched_nse.get('Exchange')}")
        print(f"  Industry: {enriched_nse.get('Industry')}")
        print(f"  Sector: {enriched_nse.get('Sector')}")

        # Test BSE stock
        test_stock_bse = {
            'Name': 'Waaree Tech',
            '_company_href': '/company/539337/'
        }
        enriched_bse = enricher.enrich_stock(test_stock_bse)
        print(f"\nBSE Stock: {enriched_bse['Name']}")
        print(f"  Symbol: {enriched_bse.get('Symbol')}")
        print(f"  Exchange: {enriched_bse.get('Exchange')}")
        print(f"  Industry: {enriched_bse.get('Industry')}")
        print(f"  Sector: {enriched_bse.get('Sector')}")

        # Show cache stats
        print("\n")
        enricher.log_cache_stats()
    else:
        print("yfinance not available, skipping API tests")
