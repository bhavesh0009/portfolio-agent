"""
Example usage of the screen_stocks tool
"""

from tools.screen_stocks import screen_stocks, get_available_ratios
import json


def main():
    print("=" * 80)
    print("Stock Screening Tool - Example Usage")
    print("=" * 80)

    # Example 1: Basic screening
    print("\n1. Basic Screening Query")
    print("-" * 80)

    query1 = """Market capitalization > 500 AND
Price to earning < 15 AND
Return on capital employed > 22% AND
Return over 3months > 10"""

    print(f"Query: {query1}")
    print("\nExecuting query...")

    try:
        result = screen_stocks(query=query1)

        print(f"\nResults:")
        print(f"  Total stocks found: {result['total_results']}")
        print(f"  Query URL: {result['query_url']}")
        print(f"\nAvailable columns: {', '.join(result['available_columns'])}")

        if result['stocks']:
            print(f"\nFirst 3 stocks:")
            for i, stock in enumerate(result['stocks'][:3], 1):
                print(f"\n  {i}. {stock.get('Name', 'N/A')}")
                print(f"     CMP: {stock.get('CMP Rs.', 'N/A')}")
                print(f"     Market Cap: {stock.get('Mar Cap Rs.Cr.', 'N/A')}")
                print(f"     P/E: {stock.get('P/E', 'N/A')}")
                print(f"     ROE: {stock.get('ROE %', 'N/A')}")

    except Exception as e:
        print(f"Error: {e}")
        return

    # Example 2: Screening with specific columns
    print("\n\n2. Screening with Specific Columns")
    print("-" * 80)

    query2 = "Market capitalization > 1000 AND Price to earning < 20"
    columns = ["Name", "CMP Rs.", "P/E", "ROE %", "Debt / Eq"]

    print(f"Query: {query2}")
    print(f"Columns: {columns}")
    print("\nExecuting query...")

    try:
        result = screen_stocks(query=query2, columns=columns)

        print(f"\nResults:")
        print(f"  Total stocks found: {result['total_results']}")

        if result['stocks']:
            print(f"\nFirst 5 stocks with selected columns:")
            for i, stock in enumerate(result['stocks'][:5], 1):
                print(f"\n  {i}. {stock}")

    except Exception as e:
        print(f"Error: {e}")

    # Example 3: Show available ratios
    print("\n\n3. Available Ratios (first 20)")
    print("-" * 80)

    try:
        ratios = get_available_ratios()
        print(f"Total ratios available: {len(ratios)}")
        print("\nFirst 20 ratios:")
        for i, ratio in enumerate(ratios[:20], 1):
            print(f"  {i}. {ratio}")
    except Exception as e:
        print(f"Error loading ratios: {e}")

    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
