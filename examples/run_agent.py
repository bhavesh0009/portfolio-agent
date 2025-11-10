"""
Example script to run the AI agent for stock screening
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_screening_agent import run_stock_screening as run_agent


def main():
    """Run example queries using the AI agent"""

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
    answer = run_agent(example_query_1, verbose=True)

    # Example 2: Value stocks
    print("\n\n" + "="*70)
    print("\n\nEXAMPLE 2: Undervalued stocks with strong fundamentals")
    print("-" * 70)

    example_query_2 = (
        "Find me 3 undervalued stocks with strong fundamentals. "
        "I'm looking for companies with low P/E ratios (below 15), "
        "good profit growth, and healthy return on equity."
    )

    answer = run_agent(example_query_2, verbose=True)

    # Example 3: Growth stocks
    print("\n\n" + "="*70)
    print("\n\nEXAMPLE 3: High-growth stocks")
    print("-" * 70)

    example_query_3 = (
        "Show me companies with exceptional sales growth in the last 3 years "
        "and strong operating profit margins. I want to invest in growth stocks."
    )

    answer = run_agent(example_query_3, verbose=True)

    print("\n\n" + "="*70)
    print("ALL EXAMPLES COMPLETED")
    print("="*70)


if __name__ == "__main__":
    main()
