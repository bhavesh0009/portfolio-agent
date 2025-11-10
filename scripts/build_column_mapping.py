"""
One-time script to build column name mapping from screener.in
Extracts config names and table header names for all 365 columns.

Usage: python build_column_mapping.py
"""

import json
from bs4 import BeautifulSoup
from tools.screener_session_simple import ScreenerSession


def extract_column_mapping():
    """Extract column mapping from Edit Columns page"""

    print("Building column name mapping...")
    print("=" * 60)

    with ScreenerSession() as session:
        # Step 1: Get Edit Columns page HTML
        print("\n1. Fetching Edit Columns page...")
        html = session.navigate('https://www.screener.in/user/columns/')
        soup = BeautifulSoup(html, 'html.parser')

        # Step 2: Extract all label.ratio elements
        print("2. Extracting column metadata...")
        labels = soup.find_all('label', class_='ratio')
        print(f"   Found {len(labels)} columns")

        mapping = {}

        for label in labels:
            config_name = label.get('data-name')
            short_name = label.get('data-short-name')
            description = label.get('data-description', '')
            group = label.get('data-group-name', '')

            if config_name and short_name:
                mapping[config_name] = {
                    "short_name": short_name,
                    "description": description,
                    "group": group
                }

        # Step 3: Add special always-present columns
        print("3. Adding always-present columns...")
        always_present = {
            "Name": {
                "short_name": "Name",
                "description": "Company name",
                "group": "always_present"
            },
            "CMP Rs.": {
                "short_name": "CMP Rs.",
                "description": "Current market price",
                "group": "always_present"
            },
            "S.No.": {
                "short_name": "S.No.",
                "description": "Serial number",
                "group": "always_present"
            }
        }

        mapping.update(always_present)

        print(f"4. Total columns in mapping: {len(mapping)}")

        return mapping


def save_mapping(mapping, filename='data/column_name_mapping.json'):
    """Save mapping to JSON file"""

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Mapping saved to: {filename}")
    print(f"Total columns mapped: {len(mapping)}")


def print_sample_mappings(mapping, count=10):
    """Print sample mappings for verification"""

    print(f"\nSample mappings (first {count}):")
    print("-" * 60)

    for i, (config_name, data) in enumerate(list(mapping.items())[:count]):
        print(f"\n{i+1}. Config: \"{config_name}\"")
        print(f"   Short:  \"{data['short_name']}\"")
        if data.get('description'):
            desc = data['description'][:50] + "..." if len(data['description']) > 50 else data['description']
            print(f"   Desc:   {desc}")


def main():
    """Main execution"""

    # Extract mapping
    mapping = extract_column_mapping()

    # Save to file
    save_mapping(mapping)

    # Print samples
    print_sample_mappings(mapping, count=15)

    # Print specific examples user asked about
    print("\n" + "=" * 60)
    print("Specific Examples:")
    print("=" * 60)

    examples = [
        "Sales growth 3Years",
        "Price to Sales",
        "Return on capital employed",
        "Debt to equity"
    ]

    for ex in examples:
        if ex in mapping:
            print(f"\n\"{ex}\"")
            print(f"  Table: \"{mapping[ex]['short_name']}\"")
            print(f"  Desc: {mapping[ex]['description'][:60]}...")

    print("\n" + "=" * 60)
    print("[DONE] Column mapping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
