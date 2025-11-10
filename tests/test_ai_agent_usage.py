"""
Test script demonstrating AI-agent friendly column mapping.
Shows how AI agents can use natural column names and get transparency.
"""

from tools.screen_stocks import screen_stocks
import json


def test_ai_agent_workflow():
    """Demonstrate AI agent workflow with column mapping"""

    print("=" * 70)
    print("AI AGENT USAGE DEMONSTRATION")
    print("=" * 70)

    # AI agent uses natural configuration names
    print("\n1. AI Agent requests columns using configuration names:")
    print("   - 'Price to Sales'")
    print("   - 'Sales growth 3Years'")
    print("   - 'Return on capital employed'")

    result = screen_stocks(
        query="Market capitalization > 50000 AND Price to earning < 15",
        columns=["Price to Sales", "Sales growth 3Years", "Return on capital employed"]
    )

    print(f"\n2. Tool auto-configures and returns mapping transparency:")
    if 'column_mapping' in result:
        print("\n   Column Mapping:")
        for config, table in result['column_mapping'].items():
            print(f"     '{config}' maps to '{table}'")

    print(f"\n3. Actual table headers available:")
    print(f"   {result['available_columns']}")

    print(f"\n4. AI agent now knows:")
    print("   - 'Price to Sales' appears as 'CMP / Sales' in table")
    print("   - 'Sales growth 3Years' appears as 'Sales Var 3Yrs' (with % suffix)")
    print("   - 'Return on capital employed' appears as 'ROCE' (with % suffix)")

    print(f"\n5. Results returned: {result['total_results']} stocks")

    # Save for inspection
    with open('ai_agent_test_result.json', 'w') as f:
        json.dump(result, f, indent=2)

    print("\n[SUCCESS] Results saved to: ai_agent_test_result.json")
    print("\nAI agents can now:")
    print("  - Use natural column names")
    print("  - Get automatic mapping transparency")
    print("  - Adapt to actual table header names")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_ai_agent_workflow()
