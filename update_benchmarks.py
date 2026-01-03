#!/usr/bin/env python
"""Quick script to update benchmark comparisons"""

from tools.performance_calculator import PerformanceCalculator

def main():
    print("Creating performance calculator...")
    calc = PerformanceCalculator()

    portfolio_id = 42
    print(f"\nUpdating benchmark comparisons for portfolio {portfolio_id}...")
    results = calc.update_benchmark_comparisons(portfolio_id)

    if results:
        print(f"\n✓ Updated {len(results)} benchmark comparisons")
        print(f"✓ Portfolio return: {results[0]['portfolio_return']:.4f}%")
        print("\nBenchmark details:")
        for result in results:
            print(f"  - {result['index_name']}: {result['index_return']:.4f}% (Alpha: {result['alpha']:.4f}%)")
    else:
        print("✗ No benchmarks configured for this portfolio")

if __name__ == "__main__":
    main()
