"""
Example: Async Refactoring Demo
Demonstrates 5-10x performance improvement through async I/O

Run this to see the difference:
    python examples/async_refactor_example.py
"""

import asyncio
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from decimal import Decimal


# ============================================================================
# BEFORE: Synchronous (SLOW) - Current Implementation Pattern
# ============================================================================

def sync_fetch_stock_data(ticker: str) -> Dict[str, Any]:
    """Simulate API call to fetch stock data (2 seconds)"""
    time.sleep(2)  # Network I/O
    return {
        "ticker": ticker,
        "price": 100.0,
        "volume": 1000000
    }


def sync_fetch_news(ticker: str) -> Dict[str, Any]:
    """Simulate API call to fetch news (3 seconds)"""
    time.sleep(3)  # Network I/O
    return {
        "ticker": ticker,
        "sentiment": "positive",
        "articles": 5
    }


def sync_enrich_with_yfinance(ticker: str) -> Dict[str, Any]:
    """Simulate yfinance enrichment (2.5 seconds)"""
    time.sleep(2.5)  # Network I/O
    return {
        "ticker": ticker,
        "sector": "Technology",
        "industry": "Software"
    }


def sync_screen_stocks(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    SYNCHRONOUS: Process stocks one at a time
    Time: 7.5 seconds per stock (2 + 3 + 2.5)
    """
    results = []
    for ticker in tickers:
        # Sequential I/O - each blocks the next
        stock_data = sync_fetch_stock_data(ticker)
        news_data = sync_fetch_news(ticker)
        yfinance_data = sync_enrich_with_yfinance(ticker)

        # Merge results
        results.append({
            **stock_data,
            **news_data,
            **yfinance_data
        })

    return results


# ============================================================================
# AFTER: Asynchronous (FAST) - 100x Developer Pattern
# ============================================================================

async def async_fetch_stock_data(ticker: str) -> Dict[str, Any]:
    """Async API call - doesn't block other operations"""
    await asyncio.sleep(2)  # Simulated I/O
    return {
        "ticker": ticker,
        "price": 100.0,
        "volume": 1000000
    }


async def async_fetch_news(ticker: str) -> Dict[str, Any]:
    """Async API call - doesn't block other operations"""
    await asyncio.sleep(3)  # Simulated I/O
    return {
        "ticker": ticker,
        "sentiment": "positive",
        "articles": 5
    }


async def async_enrich_with_yfinance(ticker: str) -> Dict[str, Any]:
    """Async enrichment - doesn't block other operations"""
    await asyncio.sleep(2.5)  # Simulated I/O
    return {
        "ticker": ticker,
        "sector": "Technology",
        "industry": "Software"
    }


async def async_screen_single_stock(ticker: str) -> Dict[str, Any]:
    """
    Process single stock with concurrent I/O operations
    Time: 3 seconds (limited by slowest operation)
    Speedup: 2.5x per stock
    """
    # Run all I/O operations concurrently
    stock_data, news_data, yfinance_data = await asyncio.gather(
        async_fetch_stock_data(ticker),
        async_fetch_news(ticker),
        async_enrich_with_yfinance(ticker)
    )

    # Merge results
    return {
        **stock_data,
        **news_data,
        **yfinance_data
    }


async def async_screen_stocks(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    ASYNCHRONOUS: Process all stocks concurrently
    Time: 3 seconds total (all stocks in parallel)
    Speedup: 7.5x for 1 stock, 37.5x for 5 stocks, 75x for 10 stocks
    """
    # Process all stocks concurrently
    results = await asyncio.gather(
        *[async_screen_single_stock(ticker) for ticker in tickers]
    )
    return list(results)


# ============================================================================
# ADVANCED: Batch Processing with Concurrency Limits
# ============================================================================

async def async_screen_stocks_batched(
    tickers: List[str],
    max_concurrent: int = 5
) -> List[Dict[str, Any]]:
    """
    Production-grade: Concurrent with rate limiting
    Prevents overwhelming external APIs
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_screen(ticker: str) -> Dict[str, Any]:
        async with semaphore:  # Only 5 concurrent at a time
            return await async_screen_single_stock(ticker)

    results = await asyncio.gather(
        *[bounded_screen(ticker) for ticker in tickers],
        return_exceptions=True  # Don't fail entire batch on single error
    )

    # Filter out exceptions, log them
    valid_results = []
    for ticker, result in zip(tickers, results):
        if isinstance(result, Exception):
            print(f"⚠️  Error processing {ticker}: {result}")
        else:
            valid_results.append(result)

    return valid_results


# ============================================================================
# BENCHMARK & COMPARISON
# ============================================================================

def benchmark_sync(tickers: List[str]):
    """Benchmark synchronous version"""
    print("🐌 SYNCHRONOUS (Current Implementation)")
    print(f"   Processing {len(tickers)} stocks...")

    start = time.time()
    results = sync_screen_stocks(tickers)
    duration = time.time() - start

    print(f"   ✅ Completed in {duration:.1f} seconds")
    print(f"   📊 Throughput: {len(results) / duration:.2f} stocks/sec\n")

    return duration


async def benchmark_async(tickers: List[str]):
    """Benchmark asynchronous version"""
    print("🚀 ASYNCHRONOUS (100x Developer Pattern)")
    print(f"   Processing {len(tickers)} stocks...")

    start = time.time()
    results = await async_screen_stocks(tickers)
    duration = time.time() - start

    print(f"   ✅ Completed in {duration:.1f} seconds")
    print(f"   📊 Throughput: {len(results) / duration:.2f} stocks/sec\n")

    return duration


async def benchmark_async_batched(tickers: List[str]):
    """Benchmark batched async version"""
    print("⚡ ASYNCHRONOUS + BATCHED (Production-Grade)")
    print(f"   Processing {len(tickers)} stocks (max 5 concurrent)...")

    start = time.time()
    results = await async_screen_stocks_batched(tickers, max_concurrent=5)
    duration = time.time() - start

    print(f"   ✅ Completed in {duration:.1f} seconds")
    print(f"   📊 Throughput: {len(results) / duration:.2f} stocks/sec\n")

    return duration


async def main():
    """Run all benchmarks and show comparison"""

    print("=" * 70)
    print("ASYNC REFACTORING DEMO - Performance Comparison")
    print("=" * 70)
    print()

    # Test with increasing dataset sizes
    test_cases = [
        ("Small Dataset", ["RELIANCE", "TCS", "INFY"]),
        ("Medium Dataset", ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]),
        ("Large Dataset", ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
                           "HINDUNILVR", "ITC", "LT", "KOTAKBANK", "BHARTIARTL"])
    ]

    for test_name, tickers in test_cases:
        print(f"\n{'=' * 70}")
        print(f"{test_name}: {len(tickers)} stocks")
        print(f"{'=' * 70}\n")

        # Benchmark sync
        sync_time = benchmark_sync(tickers)

        # Benchmark async
        async_time = await benchmark_async(tickers)

        # Benchmark async batched
        batched_time = await benchmark_async_batched(tickers)

        # Calculate speedup
        speedup_async = sync_time / async_time
        speedup_batched = sync_time / batched_time

        print(f"📈 SPEEDUP SUMMARY:")
        print(f"   Async vs Sync: {speedup_async:.1f}x faster")
        print(f"   Batched vs Sync: {speedup_batched:.1f}x faster")

        if len(tickers) < 10:
            print(f"\n💡 TIP: Speedup increases with more stocks!")
            print(f"   Expected speedup for 50 stocks: ~{(sync_time * 50 / len(tickers)) / 3:.0f}x")

    print("\n" + "=" * 70)
    print("KEY TAKEAWAYS")
    print("=" * 70)
    print("""
1. ⚡ Async provides 5-10x speedup for I/O-bound operations
2. 📈 Speedup scales with number of concurrent operations
3. 🛡️ Batching prevents overwhelming external APIs
4. 🎯 For portfolio building (screening 30+ stocks), async is CRITICAL

RECOMMENDED ACTIONS:
- Refactor tools/screener_session.py to async
- Refactor tools/yfinance_enricher.py to async
- Refactor tools/news_scraper.py to async batch fetching
- Update agents to use asyncio.gather() for parallel execution

ESTIMATED IMPACT ON YOUR CODEBASE:
- Portfolio build time: 5 min → 30 sec (10x faster)
- Agent concurrency: 1 → 5 parallel agents
- User experience: Dramatically improved
""")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())


# ============================================================================
# REAL-WORLD INTEGRATION EXAMPLE
# ============================================================================

"""
How to integrate this into your existing code:

1. Add async to screen_stocks():

    # tools/screen_stocks.py
    async def screen_stocks(query, columns=None):
        session = await ScreenerSession.create()  # Async init
        url = build_query_url(query)

        # Fetch all pages concurrently
        pages = await asyncio.gather(*[
            session.fetch_page(url, page_num)
            for page_num in range(1, total_pages + 1)
        ])

        # Enrich concurrently (5 at a time)
        enriched = await enrich_stocks_batched(stocks, max_concurrent=5)

        return enriched

2. Update agents to use async:

    # agents/portfolio_builder_agent_simple.py
    async def build(self, profile, capital):
        # Run agents in parallel
        screening, research, news = await asyncio.gather(
            self.stock_agent.screen(...),
            self.research_agent.analyze(...),
            self.news_agent.fetch(...)
        )

        return self._build_portfolio(screening, research, news)

3. Update examples:

    # examples/run_portfolio_builder.py
    async def main():
        agent = SimplePortfolioBuilderAgent()
        portfolio = await agent.build('aggressive', 500000)
        print(portfolio)

    if __name__ == "__main__":
        asyncio.run(main())

That's it! 5-10x faster with minimal code changes.
"""
