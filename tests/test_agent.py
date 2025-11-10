"""
Simple test for the AI agent
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.agent import run_agent


def test_simple_query():
    """Test agent with a simple query"""

    query = (
        "Find me 2-3 stocks with low P/E ratio (below 15) and "
        "good return on equity (above 15%). Show me their key metrics."
    )

    print("\n" + "="*70)
    print("TESTING AI AGENT")
    print("="*70)
    print(f"\nQuery: {query}\n")

    try:
        answer = run_agent(query, verbose=True)

        print("\n" + "="*70)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*70)

        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple_query()
    sys.exit(0 if success else 1)
