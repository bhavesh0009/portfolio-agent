"""
Price Fetcher - Yahoo Finance Integration
Fetches current and historical prices for stocks and indices
"""

import yfinance as yf
import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.db_service import get_db_service

logger = get_logger("tools.price_fetcher")

# Indian market indices with Yahoo Finance symbols
INDIAN_INDICES = {
    '^NSEI': 'Nifty 50',
    '^BSESN': 'Sensex',
    '^NSEMDCP50': 'Nifty Midcap 50',
    'NIFTY_MIDCAP_100.NS': 'Nifty Midcap 100',
    'NIFTYSMLCAP250.NS': 'Nifty Smallcap 250',
    'NIFTYMIDCAP150.NS': 'Nifty Midcap 150',
    'NIFTYIT.NS': 'Nifty IT',
    'NIFTYPHARMA.NS': 'Nifty Pharma',
    'NIFTYAUTO.NS': 'Nifty Auto',
    'NIFTYENERGY.NS': 'Nifty Energy',
    'NIFTYBANK.NS': 'Nifty Bank',
    'NIFTYFMCG.NS': 'Nifty FMCG'
}


class PriceFetcher:
    """Fetch and cache stock/index prices from Yahoo Finance"""

    def __init__(self):
        self.db = get_db_service()
        self._price_cache = {}  # In-memory cache: {symbol: (price, timestamp)}
        self._cache_duration = 300  # 5 minutes in seconds
        self._symbol_mappings = {}  # Cache discovered symbol mappings: {original: (corrected, exchange)}

    def _get_yf_symbol(self, ticker: str, exchange: str = 'NSE') -> str:
        """
        Convert stock ticker to Yahoo Finance symbol format

        Args:
            ticker: Stock symbol (e.g., 'RELIANCE', 'TCS')
            exchange: 'NSE' or 'BSE'

        Returns:
            Yahoo Finance symbol (e.g., 'RELIANCE.NS', '500325.BO')
        """
        suffix = '.NS' if exchange == 'NSE' else '.BO'
        return f"{ticker}{suffix}"

    def _search_yahoo_symbol(self, query: str) -> Optional[str]:
        """
        Search Yahoo Finance for symbol using their search API

        Args:
            query: Company name or partial ticker to search

        Returns:
            Best matching .NS or .BO symbol, or None

        Examples:
            _search_yahoo_symbol("Rajesh Power") → "RAJESH.BO"
            _search_yahoo_symbol("544291") → "RAJESH.BO"
        """
        import requests

        try:
            # Yahoo Finance search endpoint
            url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {
                'q': query,
                'quotesCount': 10,
                'newsCount': 0,
                'enableFuzzyQuery': False
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()

            data = response.json()
            quotes = data.get('quotes', [])

            # Filter for Indian stocks (.NS or .BO) and validate
            for quote in quotes:
                symbol = quote.get('symbol', '')
                if symbol.endswith('.NS') or symbol.endswith('.BO'):
                    # Validate symbol has actual data
                    if self._validate_symbol(symbol):
                        logger.info(f"Yahoo search found: {query} → {symbol}")
                        return symbol

            logger.debug(f"No valid Indian stock found for: {query}")
            return None

        except Exception as e:
            logger.debug(f"Yahoo search failed for {query}: {e}")
            return None

    def _validate_symbol(self, yf_symbol: str) -> bool:
        """
        Validate that a Yahoo Finance symbol has actual tradeable data

        Args:
            yf_symbol: Full Yahoo symbol (e.g., "RELIANCE.NS")

        Returns:
            True if symbol returns valid 1-day history data
        """
        try:
            ticker_obj = yf.Ticker(yf_symbol)
            history = ticker_obj.history(period="1d")

            # Valid if:
            # 1. History is not empty
            # 2. Has at least one price column with data
            if not history.empty and 'Close' in history.columns:
                return True

            return False

        except Exception as e:
            logger.debug(f"Validation failed for {yf_symbol}: {e}")
            return False

    def _store_symbol_mapping(self, original_ticker: str, corrected_ticker: str, exchange: str):
        """Store discovered symbol mapping for future reference"""
        self._symbol_mappings[original_ticker] = (corrected_ticker, exchange)
        logger.info(f"Cached symbol mapping: {original_ticker} → {corrected_ticker} ({exchange})")

    def _generate_ticker_variations(self, ticker: str) -> List[str]:
        """
        Generate common ticker variations for truncated/partial tickers

        Args:
            ticker: Original ticker (potentially truncated)

        Returns:
            List of possible ticker variations to try

        Examples:
            PREMIEREN -> [PREMIERENE, PREMIERENEL, ...]
            ORIANAPOW -> [ORIANA-SM, ORIANAPOWE, ...] (tries SME format first)
            SHILCHAR -> [SHILCHAR-SM, SHILCHARE, ...]
        """
        variations = []

        # PRIORITY 1: Try SME (Small and Medium Enterprises) format
        # SME stocks use format: BASENAME-SM (e.g., ORIANA-SM, SHILCHAR-SM)
        # Extract potential base name by removing common truncated suffixes
        base_candidates = [
            ticker,  # Original as-is
        ]

        # If ticker ends with common partial suffixes, try base without them
        sme_trim_suffixes = ['POW', 'TECH', 'EN', 'IE', 'AR', 'ER']
        for trim in sme_trim_suffixes:
            if ticker.endswith(trim):
                base_candidates.append(ticker[:-len(trim)])

        # Add SME format for all base candidates
        for base in base_candidates:
            variations.append(f"{base}-SM")

        # PRIORITY 2: Try common suffixes for regular stocks
        common_suffixes = [
            'E',        # PREMIEREN -> PREMIERENE
            'EL',       # SHILCHAR -> SHILCHAREL
            'ER',       # OSWALP -> OSWALPER
            'NE',       # Extra N+E
            'RGY',      # ENERGIE -> ENERGY
            'IES',      # TECHNOLOG -> TECHNOLOGIES
        ]

        for suffix in common_suffixes:
            variations.append(f"{ticker}{suffix}")

        # PRIORITY 3: Try replacing truncated suffix patterns
        # SHILCHAR -> SHILCTECH (HAR truncated from TECH)
        replacement_patterns = [
            ('HAR$', 'TECH'),   # SHILCHAR -> SHILCTECH
            ('AR$', 'TECH'),    # Generic AR -> TECH
            ('EN$', 'ENE'),     # Similar pattern
            ('ER$', 'ERGY'),    # POWER truncated
        ]

        for pattern, replacement in replacement_patterns:
            if re.search(pattern, ticker):
                new_ticker = re.sub(pattern, replacement, ticker)
                variations.append(new_ticker)

        return variations

    def get_current_price(
        self,
        ticker: str,
        exchange: str = 'NSE',
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Get current price for a stock

        Args:
            ticker: Stock symbol
            exchange: 'NSE' or 'BSE'
            use_cache: Whether to use cached price if available

        Returns:
            Current price or None if failed
        """
        cache_key = f"{ticker}:{exchange}"

        # Check cache
        if use_cache and cache_key in self._price_cache:
            cached_price, timestamp = self._price_cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self._cache_duration:
                logger.debug(f"Using cached price for {ticker}: {cached_price} (age: {age:.0f}s)")
                return cached_price

        # Check if we have a known symbol mapping from previous discoveries
        if ticker in self._symbol_mappings:
            corrected_ticker, corrected_exchange = self._symbol_mappings[ticker]
            logger.debug(f"Using cached symbol mapping: {ticker} → {corrected_ticker}")
            price = self._fetch_price_single(corrected_ticker, corrected_exchange)
            if price:
                self._price_cache[cache_key] = (price, datetime.now())
                return price

        # Try primary ticker first
        price = self._fetch_price_single(ticker, exchange)

        # If failed, try common ticker variations for NSE stocks
        if price is None and exchange == 'NSE':
            alternate_tickers = self._generate_ticker_variations(ticker)

            for alt_ticker in alternate_tickers:
                logger.debug(f"Trying alternate ticker: {alt_ticker}")
                price = self._fetch_price_single(alt_ticker, exchange)
                if price:
                    logger.info(f"Found price using alternate ticker {alt_ticker} for {ticker}")
                    # Cache with original ticker for future use
                    self._price_cache[cache_key] = (price, datetime.now())
                    return price

        # If still failed and was NSE, try BSE as fallback (some stocks only trade on BSE)
        if price is None and exchange == 'NSE':
            logger.debug(f"NSE lookup failed for {ticker}, trying BSE as fallback")

            # Try original ticker on BSE
            price = self._fetch_price_single(ticker, 'BSE')
            if price:
                logger.info(f"Found price on BSE for {ticker} (was looking for NSE)")
                self._price_cache[cache_key] = (price, datetime.now())
                return price

            # Try variations on BSE
            for alt_ticker in self._generate_ticker_variations(ticker):
                logger.debug(f"Trying alternate ticker on BSE: {alt_ticker}")
                price = self._fetch_price_single(alt_ticker, 'BSE')
                if price:
                    logger.info(f"Found price using BSE ticker {alt_ticker} for {ticker}")
                    self._price_cache[cache_key] = (price, datetime.now())
                    return price

        # NEW: If all previous attempts failed, try Yahoo search as last resort
        if price is None:
            logger.debug(f"All direct lookups failed for {ticker}, trying Yahoo search API")

            # Try searching by ticker first
            yf_symbol = self._search_yahoo_symbol(ticker)

            if yf_symbol:
                # Extract ticker and exchange from found symbol
                found_ticker = yf_symbol.replace('.NS', '').replace('.BO', '')
                found_exchange = 'NSE' if '.NS' in yf_symbol else 'BSE'

                price = self._fetch_price_single(found_ticker, found_exchange)

                if price:
                    logger.info(f"Yahoo search successfully found price: {ticker} → {yf_symbol} = {price}")
                    # Cache with ORIGINAL ticker for future lookups
                    self._price_cache[cache_key] = (price, datetime.now())

                    # Store symbol mapping for future use
                    self._store_symbol_mapping(ticker, found_ticker, found_exchange)

                    return price

        if price:
            self._price_cache[cache_key] = (price, datetime.now())

        return price

    def _fetch_price_single(
        self,
        ticker: str,
        exchange: str = 'NSE'
    ) -> Optional[float]:
        """
        Fetch price for a single ticker without caching or fallback logic

        Args:
            ticker: Stock symbol
            exchange: 'NSE' or 'BSE'

        Returns:
            Current price or None if failed
        """
        try:
            yf_symbol = self._get_yf_symbol(ticker, exchange)
            ticker_obj = yf.Ticker(yf_symbol)

            # Try fast_info first (faster)
            try:
                price = ticker_obj.fast_info.get('lastPrice')
            except:
                # Fallback to full info (slower but more reliable)
                info = ticker_obj.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')

            if price:
                logger.debug(f"Fetched current price for {ticker}: {price}")
                return float(price)
            else:
                logger.debug(f"No price data available for {ticker}")
                return None

        except Exception as e:
            logger.debug(f"Failed to fetch price for {ticker}: {e}")
            return None

    def get_historical_prices(
        self,
        ticker: str,
        exchange: str = 'NSE',
        start: Optional[date] = None,
        end: Optional[date] = None,
        period: str = '1mo'
    ) -> Optional[Dict[str, Any]]:
        """
        Get historical OHLCV data for a stock

        Args:
            ticker: Stock symbol
            exchange: 'NSE' or 'BSE'
            start: Start date (if None, uses period)
            end: End date (defaults to today)
            period: Period string like '1d', '5d', '1mo', '3mo', '6mo', '1y', 'max'

        Returns:
            Dict with keys: dates, open, high, low, close, volume
        """
        try:
            yf_symbol = self._get_yf_symbol(ticker, exchange)
            ticker_obj = yf.Ticker(yf_symbol)

            if start and end:
                hist = ticker_obj.history(start=start, end=end)
            else:
                hist = ticker_obj.history(period=period)

            if hist.empty:
                logger.warning(f"No historical data for {ticker}")
                return None

            # Convert DataFrame to dict
            return {
                'dates': hist.index.tolist(),
                'open': hist['Open'].tolist(),
                'high': hist['High'].tolist(),
                'low': hist['Low'].tolist(),
                'close': hist['Close'].tolist(),
                'volume': hist['Volume'].tolist()
            }

        except Exception as e:
            logger.error(f"Failed to fetch historical data for {ticker}: {e}")
            return None

    def get_index_price(
        self,
        index_symbol: str,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Get current price for an index

        Args:
            index_symbol: Index symbol (e.g., '^NSEI', '^BSESN')
            use_cache: Whether to use cached price

        Returns:
            Current index value or None
        """
        cache_key = f"index:{index_symbol}"

        # Check cache
        if use_cache and cache_key in self._price_cache:
            cached_price, timestamp = self._price_cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self._cache_duration:
                logger.debug(f"Using cached index price for {index_symbol}: {cached_price}")
                return cached_price

        # Fetch from Yahoo Finance
        try:
            index_obj = yf.Ticker(index_symbol)

            # Try fast_info
            try:
                price = index_obj.fast_info.get('lastPrice')
            except:
                # Fallback to history
                hist = index_obj.history(period='1d')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                else:
                    price = None

            if price:
                self._price_cache[cache_key] = (price, datetime.now())
                logger.debug(f"Fetched index price for {index_symbol}: {price}")
                return float(price)
            else:
                logger.warning(f"No price data for index {index_symbol}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch index price for {index_symbol}: {e}")
            return None

    def get_index_history(
        self,
        index_symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        period: str = '1mo'
    ) -> Optional[Dict[str, Any]]:
        """Get historical data for an index"""
        try:
            index_obj = yf.Ticker(index_symbol)

            if start and end:
                hist = index_obj.history(start=start, end=end)
            else:
                hist = index_obj.history(period=period)

            if hist.empty:
                logger.warning(f"No historical data for index {index_symbol}")
                return None

            return {
                'dates': hist.index.tolist(),
                'open': hist['Open'].tolist(),
                'high': hist['High'].tolist(),
                'low': hist['Low'].tolist(),
                'close': hist['Close'].tolist(),
                'volume': hist['Volume'].tolist()
            }

        except Exception as e:
            logger.error(f"Failed to fetch index history for {index_symbol}: {e}")
            return None

    def batch_fetch_prices(
        self,
        stocks: List[Dict[str, str]],
        delay: float = 0.1
    ) -> Dict[str, float]:
        """
        Fetch prices for multiple stocks

        Args:
            stocks: List of dicts with 'ticker' and 'exchange' keys
            delay: Delay between requests to avoid rate limiting

        Returns:
            Dict mapping ticker to price
        """
        results = {}

        for stock in stocks:
            ticker = stock.get('ticker')
            exchange = stock.get('exchange', 'NSE')

            price = self.get_current_price(ticker, exchange)
            if price:
                results[ticker] = price

            # Rate limiting
            time.sleep(delay)

        logger.info(f"Batch fetched prices for {len(results)}/{len(stocks)} stocks")
        return results

    def batch_fetch_indices(
        self,
        index_symbols: Optional[List[str]] = None,
        delay: float = 0.1
    ) -> Dict[str, float]:
        """
        Fetch current values for multiple indices

        Args:
            index_symbols: List of index symbols (uses default if None)
            delay: Delay between requests

        Returns:
            Dict mapping index_symbol to value
        """
        if index_symbols is None:
            index_symbols = list(INDIAN_INDICES.keys())

        results = {}

        for symbol in index_symbols:
            price = self.get_index_price(symbol)
            if price:
                results[symbol] = price

            time.sleep(delay)

        logger.info(f"Batch fetched {len(results)}/{len(index_symbols)} indices")
        return results

    def update_portfolio_prices(self, portfolio_id: int, price_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Fetch and store prices for all stocks in a portfolio

        Args:
            portfolio_id: Portfolio ID
            price_date: Date to record prices (defaults to today)

        Returns:
            Summary dict with success/failure counts
        """
        if price_date is None:
            price_date = date.today()

        logger.info(f"Updating prices for portfolio {portfolio_id} on {price_date}")

        # Get all stocks in portfolio
        stocks = self.db.get_portfolio_stocks(portfolio_id)

        if not stocks:
            logger.warning(f"No stocks found in portfolio {portfolio_id}")
            return {'success': 0, 'failed': 0, 'total': 0}

        success_count = 0
        failed_stocks = []

        for stock in stocks:
            ticker = stock['ticker']
            stock_id = stock['id']
            exchange = stock.get('exchange', 'NSE')

            # Fetch historical data for the date (to get OHLC, not just close)
            try:
                yf_symbol = self._get_yf_symbol(ticker, exchange)
                ticker_obj = yf.Ticker(yf_symbol)

                # Get data for the specific date (or today)
                hist = ticker_obj.history(start=price_date, end=price_date + timedelta(days=1))

                if not hist.empty:
                    row = hist.iloc[0]

                    # Store in database
                    self.db.store_daily_price(
                        stock_id=stock_id,
                        price_date=price_date,
                        open_price=float(row['Open']),
                        high_price=float(row['High']),
                        low_price=float(row['Low']),
                        close_price=float(row['Close']),
                        volume=int(row['Volume']) if row['Volume'] else None
                    )

                    success_count += 1
                    logger.debug(f"Stored price for {ticker}: {row['Close']:.2f}")
                else:
                    failed_stocks.append(ticker)
                    logger.warning(f"No data for {ticker} on {price_date}")

            except Exception as e:
                failed_stocks.append(ticker)
                logger.error(f"Failed to update price for {ticker}: {e}")

            # Rate limiting
            time.sleep(0.1)

        logger.info(f"Price update complete: {success_count}/{len(stocks)} successful")

        if failed_stocks:
            logger.warning(f"Failed stocks: {', '.join(failed_stocks)}")

        return {
            'success': success_count,
            'failed': len(failed_stocks),
            'total': len(stocks),
            'failed_stocks': failed_stocks
        }

    def update_index_prices(
        self,
        index_symbols: Optional[List[str]] = None,
        price_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Fetch and store prices for market indices

        Args:
            index_symbols: List of index symbols (uses default if None)
            price_date: Date to record prices (defaults to today)

        Returns:
            Summary dict
        """
        if price_date is None:
            price_date = date.today()

        if index_symbols is None:
            index_symbols = list(INDIAN_INDICES.keys())

        logger.info(f"Updating {len(index_symbols)} index prices for {price_date}")

        success_count = 0
        failed_indices = []

        for symbol in index_symbols:
            try:
                index_obj = yf.Ticker(symbol)
                hist = index_obj.history(start=price_date, end=price_date + timedelta(days=1))

                if not hist.empty:
                    row = hist.iloc[0]

                    self.db.store_index_price(
                        index_symbol=symbol,
                        index_name=INDIAN_INDICES.get(symbol, symbol),
                        price_date=price_date,
                        open_price=float(row['Open']),
                        high_price=float(row['High']),
                        low_price=float(row['Low']),
                        close_price=float(row['Close']),
                        volume=int(row['Volume']) if row['Volume'] else None
                    )

                    success_count += 1
                    logger.debug(f"Stored index price for {symbol}: {row['Close']:.2f}")
                else:
                    failed_indices.append(symbol)
                    logger.warning(f"No data for index {symbol} on {price_date}")

            except Exception as e:
                failed_indices.append(symbol)
                logger.error(f"Failed to update index {symbol}: {e}")

            time.sleep(0.1)

        logger.info(f"Index update complete: {success_count}/{len(index_symbols)} successful")

        return {
            'success': success_count,
            'failed': len(failed_indices),
            'total': len(index_symbols),
            'failed_indices': failed_indices
        }

    def clear_cache(self):
        """Clear in-memory price cache"""
        self._price_cache.clear()
        logger.info("Price cache cleared")


# Singleton instance
_price_fetcher = None


def get_price_fetcher() -> PriceFetcher:
    """Get or create price fetcher singleton"""
    global _price_fetcher
    if _price_fetcher is None:
        _price_fetcher = PriceFetcher()
    return _price_fetcher


if __name__ == '__main__':
    # Test script
    fetcher = PriceFetcher()

    print("Testing price fetcher...")
    print("\n1. Fetching current price for RELIANCE:")
    price = fetcher.get_current_price('RELIANCE')
    print(f"   Price: Rs. {price:.2f}" if price else "   Failed")

    print("\n2. Fetching Nifty 50:")
    nifty = fetcher.get_index_price('^NSEI')
    print(f"   Nifty: {nifty:.2f}" if nifty else "   Failed")

    print("\n3. Batch fetching indices:")
    indices = fetcher.batch_fetch_indices(['^NSEI', '^BSESN', 'NIFTYIT.NS'])
    for symbol, value in indices.items():
        print(f"   {INDIAN_INDICES.get(symbol, symbol)}: {value:.2f}")

    print("\nDone!")
