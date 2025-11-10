"""
Example script to run the Stock Screening AI Agent
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_screening_agent import run_stock_screening


def main():
    """Run example queries using the Stock Screening AI Agent"""

    print("="*70)
    print("STOCK SCREENING AI AGENT - EXAMPLE USAGE")
    print("="*70)

    # Example 1: Find high-potential stock
    example_query_1 = (
        "Suggest a stock that has the potential to deliver at least 50% returns "
        "in the next 12 months. Explain the reasoning behind your choice, including "
        "key financial metrics and market trends that support this projection."
    )

    print("\n\nEXAMPLE 1: High-potential stock recommendation")
    print("-" * 70)
    answer = run_stock_screening(example_query_1, verbose=True)

    # Example 2: Value investing
    print("\n\n" + "="*70)
    print("\n\nEXAMPLE 2: Peter Lynch style investing")
    print("-" * 70)

    example_query_2 = (
        "If you were a Peter Lynch style investor, which stock would you invest "
        "in right now? Pick any 5 stocks and explain your reasoning."
    )

    answer = run_stock_screening(example_query_2, verbose=True)

    # Example 3: Sector analysis
    print("\n\n" + "="*70)
    print("\n\nEXAMPLE 3: IT sector analysis")
    print("-" * 70)

    example_query_3 = (
        "Find the best 3 stocks in the IT sector with market cap > 10000 crores. "
        "Compare them and recommend which one to invest in."
    )

    answer = run_stock_screening(example_query_3, verbose=True)

    print("\n\n" + "="*70)
    print("ALL EXAMPLES COMPLETED")
    print("="*70)


if __name__ == "__main__":
    main()
