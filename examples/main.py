"""
Main script for testing stock screening queries.
Easy to use - just modify the query and run: python main.py
"""

from tools.screen_stocks import screen_stocks
import json
from datetime import datetime


def save_results_to_json(result, filename=None):
    """Save results to a JSON file with timestamp"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Results saved to: {filename}")
    return filename


def save_results_to_csv(result, filename=None):
    """Save results to a CSV file"""
    try:
        import pandas as pd

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results_{timestamp}.csv"

        df = pd.DataFrame(result['stocks'])
        df.to_csv(filename, index=False, encoding='utf-8')

        print(f"[SUCCESS] Results saved to: {filename}")
        return filename
    except ImportError:
        print("Note: pandas not available. CSV export skipped.")
        return None


def print_results(result, max_stocks=10):
    """Pretty print the results"""
    print("\n" + "=" * 80)
    print(f"QUERY RESULTS")
    print("=" * 80)
    print(f"\nTotal stocks found: {result['total_results']}")
    print(f"Query URL: {result['query_url']}")

    if result['total_results'] > 0:
        print(f"\nAvailable columns: {', '.join(result['available_columns'])}")

        num_to_show = min(max_stocks, result['total_results'])
        print(f"\nShowing first {num_to_show} stocks:")
        print("-" * 80)

        for i, stock in enumerate(result['stocks'][:num_to_show], 1):
            print(f"\n{i}. {stock.get('Name', 'N/A')}")
            print(f"   CMP: Rs.{stock.get('CMP Rs.', 'N/A')}")
            print(f"   Market Cap: Rs.{stock.get('Mar Cap Rs.Cr.', 'N/A')} Cr")
            print(f"   P/E: {stock.get('P/E', 'N/A')}")
            print(f"   ROE: {stock.get('ROE %', 'N/A')}%")
            print(f"   Debt/Eq: {stock.get('Debt / Eq', 'N/A')}")

        if result['total_results'] > max_stocks:
            print(f"\n... and {result['total_results'] - max_stocks} more stocks")
    else:
        print("\nNo stocks found matching the criteria.")

    print("\n" + "=" * 80)


def main():
    """
    Main function - Modify the query here to test different screening criteria
    """

    # =============================================================================
    # MODIFY THIS SECTION TO TEST DIFFERENT QUERIES
    # =============================================================================

    # Your screening query (use natural language with ratio names)
    query = """
Market capitalization > 5000 AND
Price to earning < 20 AND
Return on equity > 15%
    """.strip()

    # Optional: Specify which columns you want in the results
    # Leave as None to get all available columns
    #
    # COLUMN NAMES: Two approaches available:
    #
    # Approach 1: Use CONFIGURATION NAMES (auto-configured, easier)
    # - Tool will auto-configure these columns on screener.in
    # - Results will have different table header names
    # - Good for initial setup, less precise filtering
    columns_config_names = [
        "Sales growth 3Years",         # Will auto-configure
        "Profit growth 5Years",        # Will auto-configure
        "Return on capital employed",  # Will auto-configure
        "Debt to equity",              # Will auto-configure
        "Return on equity",        # Will auto-configure
        "Price to Sales"
    ]

    # Approach 2: Use TABLE HEADER NAMES (more precise)
    # - These are the exact column names from screener.in results
    # - More control over filtering, but you need to know exact names
    # - Check result['available_columns'] to see actual names
    columns_table_names = [
        "Name",             # Always present
        "CMP Rs.",          # Always present
        "Mar Cap Rs.Cr.",   # Market Capitalization
        "Sales Var 3Yrs %", # Sales growth (table header)
        "ROCE %",           # Return on capital employed
        "ROE %",            # Return on equity
        "Debt / Eq"         # Debt to equity
    ]

    # Choose which approach to use:
    columns = None   # Use None to get ALL columns
    # columns = columns_config_names  # Use config names (auto-configure, then check result['column_mapping'])
    # columns = columns_table_names   # Use table header names (precise filtering)

    # How many stocks to display in terminal (full results still saved to file)
    max_display = 10

    # Auto-save results? (set to False to skip saving)
    save_json = True
    save_csv = True

    # =============================================================================
    # END OF CONFIGURATION
    # =============================================================================

    print("\n" + "=" * 80)
    print("STOCK SCREENING TOOL")
    print("=" * 80)
    print(f"\nQuery:\n{query}")

    if columns:
        print(f"\nSelected columns: {', '.join(columns)}")
    else:
        print("\nColumns: All available columns")

    print("\n" + "-" * 80)
    print("Executing query...")
    print("-" * 80)

    try:
        # Execute the screening query
        # Note: auto_configure_columns=True (default) means the tool will
        # automatically configure screener.in if any requested columns are missing
        result = screen_stocks(query=query, columns=columns)

        # Display results
        print_results(result, max_stocks=max_display)

        # Save results to files
        if save_json:
            save_results_to_json(result)

        if save_csv:
            save_results_to_csv(result)

        print("\n[DONE] All tasks completed!")

    except ValueError as e:
        print(f"\n[ERROR] {e}")
        print("Please check your query syntax and credentials in .env file")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
