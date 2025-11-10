"""
Test script for automatic column configuration feature.

This demonstrates how the screen_stocks tool can automatically configure
columns on screener.in without manual intervention.
"""

from tools.screen_stocks import screen_stocks
from tools.screener_session_simple import ScreenerSession


def test_auto_column_configuration():
    """Test automatic column configuration"""

    print("=" * 80)
    print("TESTING AUTOMATIC COLUMN CONFIGURATION")
    print("=" * 80)

    # Step 1: Configure columns using their configuration names
    print("\n1. Auto-configuring columns using configuration names...")
    print("   Requesting: Sales growth 3Years, Profit growth 5Years, etc.")

    result = screen_stocks(
        query="Market capitalization > 50000 AND Price to earning < 25",
        columns=[
            "Sales growth 3Years",
            "Profit growth 5Years",
            "Return on capital employed",
            "Return on equity",
            "Debt to equity"
        ],
        auto_configure_columns=True
    )

    print(f"\n   Success! Configured columns and got {result['total_results']} results")
    print(f"   Available columns in table: {len(result['available_columns'])} columns")

    # Step 2: Show the mapping between config names and table headers
    print("\n2. Note: Configuration names != Table header names")
    print("   Examples:")
    print("   - 'Sales growth 3Years' appears as 'Sales Var 3Yrs %'")
    print("   - 'Return on capital employed' appears as 'ROCE %'")
    print("   - 'Debt to equity' appears as 'Debt / Eq'")

    # Step 3: Use table header names to filter results
    print("\n3. Filtering results using actual table header names...")

    result2 = screen_stocks(
        query="Market capitalization > 50000 AND Price to earning < 25",
        columns=["Name", "CMP Rs.", "P/E", "Sales Var 3Yrs %", "ROCE %", "ROE %", "Debt / Eq"],
        auto_configure_columns=False  # Already configured
    )

    print(f"\n   Top 10 stocks:")
    print("   " + "-" * 76)
    for i, stock in enumerate(result2['stocks'][:10]):
        name = stock.get('Name', 'N/A')[:18]
        cmp = stock.get('CMP Rs.', 'N/A')
        pe = stock.get('P/E', 'N/A')
        sales = stock.get('Sales Var 3Yrs %', 'N/A')
        roce = stock.get('ROCE %', 'N/A')
        roe = stock.get('ROE %', 'N/A')
        debt = stock.get('Debt / Eq', 'N/A')

        print(f"   {i+1:2}. {name:20} P/E:{pe:7} ROCE:{roce:7} ROE:{roe:7} Debt:{debt:6}")

    print("\n" + "=" * 80)


def get_column_mapping():
    """Show how to get available columns and their names"""

    print("\n" + "=" * 80)
    print("AVAILABLE COLUMNS REFERENCE")
    print("=" * 80)

    with ScreenerSession() as session:
        available = session.get_available_columns()

        # Show some important categories
        categories = {
            "Growth Metrics": [k for k in available.keys() if "growth" in k.lower()],
            "Profitability": [k for k in available.keys() if any(x in k.lower() for x in ["roe", "roce", "roa", "opm", "npm"])],
            "Valuation": [k for k in available.keys() if any(x in k.lower() for x in ["p/e", "price to", "peg"])],
        }

        for category, cols in categories.items():
            print(f"\n{category} ({len(cols)} columns):")
            for col in sorted(cols)[:10]:  # Show first 10
                print(f"  - {col}")
            if len(cols) > 10:
                print(f"  ... and {len(cols) - 10} more")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run tests
    test_auto_column_configuration()

    # Show available columns
    get_column_mapping()

    print("\nTest completed successfully!")
