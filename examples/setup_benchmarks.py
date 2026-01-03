"""
Setup benchmark preferences and generate comparisons for a portfolio
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from utils.db_service import DatabaseService
from tools.performance_calculator import PerformanceCalculator
from datetime import date

def setup_portfolio_benchmarks(portfolio_id: int):
    """
    Setup default benchmark preferences and generate comparisons

    Args:
        portfolio_id: Portfolio ID to setup benchmarks for
    """
    db = DatabaseService()
    calc = PerformanceCalculator()

    print(f"Setting up benchmarks for portfolio {portfolio_id}...")

    # Define default Indian market benchmarks
    benchmarks = [
        # Primary benchmarks (shown on dashboard)
        ('^NSEI', 'Nifty 50', True, 1),
        ('NIFTY_MIDCAP_100.NS', 'Nifty Midcap 100', True, 2),
        ('NIFTYSMLCAP250.NS', 'Nifty Smallcap 250', True, 3),

        # Secondary benchmarks
        ('^BSESN', 'Sensex', False, 4),
        ('NIFTYIT.NS', 'Nifty IT', False, 5),
        ('NIFTYPHARMA.NS', 'Nifty Pharma', False, 6),
        ('NIFTYAUTO.NS', 'Nifty Auto', False, 7),
        ('NIFTYENERGY.NS', 'Nifty Energy', False, 8),
    ]

    # Insert benchmark preferences
    print("\n1. Inserting benchmark preferences...")
    for index_symbol, index_name, is_primary, display_order in benchmarks:
        try:
            db.client.table('user_benchmark_preferences').insert({
                'portfolio_id': portfolio_id,
                'index_symbol': index_symbol,
                'index_name': index_name,
                'is_primary': is_primary,
                'display_order': display_order,
                'enabled': True
            }).execute()

            primary_tag = "PRIMARY" if is_primary else "secondary"
            print(f"   ✓ Added {index_name} ({primary_tag})")
        except Exception as e:
            if 'duplicate' in str(e).lower():
                print(f"   ⊙ {index_name} already exists")
            else:
                print(f"   ✗ Error adding {index_name}: {e}")

    # Generate benchmark comparisons
    print("\n2. Generating benchmark comparisons...")
    print("   This may take a minute as it fetches historical index data...")

    try:
        comparisons = calc.update_benchmark_comparisons(portfolio_id, date.today())

        if comparisons:
            print(f"\n✓ Generated {len(comparisons)} benchmark comparisons")
            print("\nSample comparisons:")
            for comp in comparisons[:3]:
                print(f"   • {comp['index_name']} ({comp['period']}): "
                      f"Portfolio {comp['portfolio_return']:.2f}% vs "
                      f"Index {comp['index_return']:.2f}% "
                      f"(Alpha: {comp['alpha']:.2f}%)")
        else:
            print("\n⚠ No comparisons generated. Check if:")
            print("   - Portfolio has snapshots in database")
            print("   - Portfolio has been active for at least 1 day")
    except Exception as e:
        print(f"\n✗ Error generating comparisons: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("Setup complete! Refresh your dashboard to see benchmark data.")
    print("="*60)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        portfolio_id = int(sys.argv[1])
    else:
        # Default to portfolio 42 (current active)
        portfolio_id = 42

    setup_portfolio_benchmarks(portfolio_id)
