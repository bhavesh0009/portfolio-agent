"""
Example script to run the Stock News Analysis AI Agent
"""

import sys
from pathlib import Path
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_news_agent import run_stock_news


def main():
    """Run example queries using the News Analysis AI Agent"""

    print("="*70)
    print("NEWS ANALYSIS AI AGENT - EXAMPLE USAGE")
    print("="*70)

    # Example 1: Market sentiment
    example_query_1 = (
        "What are the major news stories about Indian stock market in the last 24 hours? "
        "Summarize the key trends and overall market sentiment."
    )

    print("\n\nEXAMPLE 1: Indian market sentiment (last 24 hours)")
    print("-" * 70)
    answer = run_stock_news(example_query_1, verbose=True)

    # Example 2: Company-specific news
    print("\n\n" + "="*70)
    print("\n\nEXAMPLE 2: Tesla news analysis")
    print("-" * 70)

    example_query_2 = (
        "What's the latest news about Tesla in the last week? "
        "Are there any major announcements or developments that could impact the stock price?"
    )

    answer = run_stock_news(example_query_2, verbose=True)

    # Example 3: Sector news
    print("\n\n" + "="*70)
    print("\n\nEXAMPLE 3: Tech sector news")
    print("-" * 70)

    example_query_3 = (
        "What are the major news stories about AI and technology stocks in the last 3 days? "
        "Focus on companies like NVIDIA, Microsoft, and Google."
    )

    answer = run_stock_news(example_query_3, verbose=True)

    # Example 4: Economic news
    print("\n\n" + "="*70)
    print("\n\nEXAMPLE 4: Economic indicators")
    print("-" * 70)

    example_query_4 = (
        "What are the recent news stories about inflation and interest rates? "
        "How might this impact the stock market?"
    )

    answer = run_stock_news(example_query_4, verbose=True)

    print("\n\n" + "="*70)
    print("ALL EXAMPLES COMPLETED")
    print("="*70)


if __name__ == "__main__":
    main()
