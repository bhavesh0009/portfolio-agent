"""
Supabase enrichment utility for stock data

Enriches stock screening results with industry, sector, and symbol data
from Supabase PostgreSQL database (v_company_industry view).

Performance characteristics:
- Single bulk query for all stocks (vs. N API calls with yfinance)
- Typical latency: ~200-500ms for 300 stocks (vs. ~60s with yfinance)
- No rate limiting or external API dependencies
"""

import os
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger

logger = get_logger("tools.supabase_enricher")

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    logger.warning("supabase-py not installed. Install with: pip install supabase-py")
    SUPABASE_AVAILABLE = False


class SupabaseEnricher:
    """
    Enriches stock data with industry, sector, and symbol information
    from Supabase PostgreSQL database.

    Features:
    - Bulk enrichment: Single query for all stocks (not per-stock)
    - Maps data_row_company_id to industry/sector/symbol data
    - Graceful error handling (sets 'Unknown' on failures)
    - Minimal memory footprint (no session cache needed)
    """

    def __init__(self):
        """Initialize Supabase client"""
        if not SUPABASE_AVAILABLE:
            logger.error("supabase-py is not available. Enrichment will not work.")
            self.client = None
            return

        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_API_KEY')

        if not supabase_url or not supabase_key:
            logger.error(
                "SUPABASE_URL and SUPABASE_API_KEY must be set in .env file. "
                "Add these credentials to enable industry/sector enrichment."
            )
            self.client = None
            return

        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            logger.debug("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None

        # Track enrichment statistics
        self._enrichment_successes = 0
        self._enrichment_failures = 0

    def enrich_stocks_bulk(self, stocks: List[Dict]) -> List[Dict]:
        """
        Enrich multiple stocks with industry/sector/symbol data in a single query.

        Args:
            stocks: List of stock dicts from screener results
                    Each stock must have '_company_id' field

        Returns:
            Same list of stocks with added fields:
            - Industry: Industry name (from industry_name)
            - Sector: Sector name (from category_name)
            - Symbol: Stock ticker symbol (from company_identifier)
            - Exchange: Stock exchange (inferred from symbol format)

        Example:
            >>> stocks = [
            ...     {'Name': 'TCS', '_company_id': '14'},
            ...     {'Name': 'Infosys', '_company_id': '16'}
            ... ]
            >>> enricher.enrich_stocks_bulk(stocks)
            >>> stocks[0]
            {
                'Name': 'TCS',
                '_company_id': '14',
                'Industry': 'IT Services & Consulting',
                'Sector': 'Technology',
                'Symbol': 'TCS',
                'Exchange': 'NSE'
            }
        """
        if not self.client:
            logger.error("Supabase client not initialized. Skipping enrichment.")
            self._set_unknown_fields(stocks)
            return stocks

        if not stocks:
            return stocks

        # Extract company IDs from stocks
        company_ids = []
        for stock in stocks:
            company_id = stock.get('_company_id')
            if company_id:
                company_ids.append(str(company_id))  # Ensure string type

        if not company_ids:
            logger.warning("No company IDs found in stocks. Skipping enrichment.")
            self._set_unknown_fields(stocks)
            return stocks

        logger.info(f"Enriching {len(company_ids)} stocks via Supabase bulk query...")

        try:
            # Single bulk query to v_company_industry view
            # Filter by data_row_company_id IN (list of IDs)
            response = (
                self.client.table('v_company_industry')
                .select('data_row_company_id, industry_name, category_name, company_identifier')
                .in_('data_row_company_id', company_ids)
                .execute()
            )

            # Build lookup dictionary: company_id -> enrichment data
            enrichment_map = {}
            for row in response.data:
                company_id = row.get('data_row_company_id')
                enrichment_map[company_id] = {
                    'industry': row.get('industry_name', 'Unknown'),
                    'sector': row.get('category_name', 'Unknown'),
                    'symbol': row.get('company_identifier', 'Unknown'),
                    'exchange': self._infer_exchange(row.get('company_identifier'))
                }

            logger.debug(f"Retrieved enrichment data for {len(enrichment_map)} companies")

            # Map enrichment data back to stocks
            for stock in stocks:
                company_id = stock.get('_company_id')

                if not company_id:
                    # No company ID - set unknown
                    stock['Industry'] = 'Unknown'
                    stock['Sector'] = 'Unknown'
                    stock['Symbol'] = 'Unknown'
                    stock['Exchange'] = 'Unknown'
                    self._enrichment_failures += 1
                    continue

                enrichment = enrichment_map.get(str(company_id))

                if enrichment:
                    # Found in database
                    stock['Industry'] = enrichment['industry']
                    stock['Sector'] = enrichment['sector']
                    stock['Symbol'] = enrichment['symbol']
                    stock['Exchange'] = enrichment['exchange']
                    self._enrichment_successes += 1
                else:
                    # Not found in database
                    stock['Industry'] = 'Unknown'
                    stock['Sector'] = 'Unknown'
                    stock['Symbol'] = 'Unknown'
                    stock['Exchange'] = 'Unknown'
                    self._enrichment_failures += 1
                    logger.debug(f"No enrichment data found for company_id={company_id}")

            logger.info(f"Enrichment complete: {self._enrichment_successes} successful, {self._enrichment_failures} failed")
            return stocks

        except Exception as e:
            logger.error(f"Supabase enrichment failed: {e}")
            self._set_unknown_fields(stocks)
            return stocks

    def _infer_exchange(self, symbol: Optional[str]) -> str:
        """
        Infer stock exchange from symbol format.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Exchange name ('NSE', 'BSE', or 'Unknown')

        Logic:
        - If symbol is purely numeric: BSE
        - If symbol is alphabetic (may contain &, -, etc.): NSE
        - Otherwise: Unknown
        """
        if not symbol or symbol == 'Unknown':
            return 'Unknown'

        if symbol.isdigit():
            return 'BSE'
        elif symbol.isalpha() or any(c in symbol for c in ['&', '-']):
            return 'NSE'
        else:
            return 'Unknown'

    def _set_unknown_fields(self, stocks: List[Dict]):
        """Set all enrichment fields to 'Unknown' for all stocks"""
        for stock in stocks:
            stock['Industry'] = 'Unknown'
            stock['Sector'] = 'Unknown'
            stock['Symbol'] = 'Unknown'
            stock['Exchange'] = 'Unknown'
            self._enrichment_failures += 1

    def get_enrichment_stats(self) -> Dict[str, int]:
        """
        Get enrichment statistics.

        Returns:
            Dict with enrichment_successes and enrichment_failures
        """
        return {
            'enrichment_successes': self._enrichment_successes,
            'enrichment_failures': self._enrichment_failures
        }

    def log_enrichment_stats(self):
        """Log enrichment statistics"""
        stats = self.get_enrichment_stats()
        total = stats['enrichment_successes'] + stats['enrichment_failures']
        failure_rate = (stats['enrichment_failures'] / total * 100) if total > 0 else 0

        logger.info(
            f"Supabase enrichment stats: {stats['enrichment_successes']} successful, "
            f"{stats['enrichment_failures']} failed ({failure_rate:.1f}% failure rate)"
        )


# Singleton instance for session-wide consistency
_enricher_instance = None


def get_enricher() -> SupabaseEnricher:
    """
    Get singleton enricher instance.

    This ensures consistent enrichment statistics across multiple calls.
    """
    global _enricher_instance
    if _enricher_instance is None:
        _enricher_instance = SupabaseEnricher()
    return _enricher_instance


if __name__ == "__main__":
    # Test the enricher
    from dotenv import load_dotenv
    load_dotenv()

    print("Testing Supabase Enricher\n")

    enricher = SupabaseEnricher()

    if enricher.client:
        # Test with sample data
        test_stocks = [
            {'Name': 'Test Company 1', '_company_id': '369'},
            {'Name': 'Test Company 2', '_company_id': '681'},
            {'Name': 'Test Company 3', '_company_id': '999999'},  # Should fail
        ]

        print("Before enrichment:")
        for stock in test_stocks:
            print(f"  {stock}")

        enricher.enrich_stocks_bulk(test_stocks)

        print("\nAfter enrichment:")
        for stock in test_stocks:
            print(f"  {stock['Name']}:")
            print(f"    Industry: {stock.get('Industry')}")
            print(f"    Sector: {stock.get('Sector')}")
            print(f"    Symbol: {stock.get('Symbol')}")
            print(f"    Exchange: {stock.get('Exchange')}")

        print("\n")
        enricher.log_enrichment_stats()
    else:
        print("Supabase client not available. Check your .env configuration.")
