"""
Regenerate benchmark comparisons with Yahoo Finance data
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from tools.performance_calculator import PerformanceCalculator
from datetime import date

def regenerate_benchmarks(portfolio_id: int):
    """Regenerate benchmark comparisons with Yahoo Finance data"""

    calc = PerformanceCalculator()

    print(f'Regenerating benchmark comparisons for portfolio {portfolio_id}...')
    print('This will fetch historical index data from Yahoo Finance')
    print()

    comparisons = calc.update_benchmark_comparisons(portfolio_id, date.today())

    if comparisons:
        print(f'\n✓ Generated {len(comparisons)} benchmark comparisons')
        print('\nSample comparisons (ALL period):')

        all_period = [c for c in comparisons if c['period'] == 'ALL'][:3]
        for comp in all_period:
            print(f'  {comp["index_name"]}: Portfolio {comp["portfolio_return"]:.2f}% vs Index {comp["index_return"]:.2f}% (Alpha: {comp["alpha"]:.2f}%)')

        print('\n' + '='*60)
        print('Benchmarks regenerated! Refresh dashboard to see updated data.')
        print('='*60)
    else:
        print('⚠ No comparisons generated')


if __name__ == '__main__':
    portfolio_id = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    regenerate_benchmarks(portfolio_id)
