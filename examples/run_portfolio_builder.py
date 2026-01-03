#!/usr/bin/env python3
"""
Portfolio Builder Example
Runs the simplified portfolio builder agent to create an initial portfolio
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.portfolio_builder_agent_simple import build_simple_portfolio

def main():
    """Run portfolio builder with default settings"""
    print("=" * 70)
    print("PORTFOLIO BUILDER AGENT")
    print("=" * 70)

    # Configuration
    # Profiles: 'aggressive', 'moderate', or 'defensive'
    profile = "moderate"
    capital = 500000

    print(f"\nBuilding {profile.upper()} portfolio with Rs. {capital:,}...")
    print("This may take several minutes as the agent:")
    print("  1. Researches market trends")
    print("  2. Screens stocks from screener.in")
    print("  3. Analyzes news sentiment")
    print("  4. Allocates capital across selected stocks")
    print("\n" + "=" * 70 + "\n")

    # Build portfolio with specified settings
    portfolio = build_simple_portfolio(
        investor_profile=profile,
        capital=capital,
        verbose=True
    )

    # Display results
    print("\n" + "=" * 70)
    print("PORTFOLIO SUMMARY")
    print("=" * 70)

    if "error" in portfolio:
        print(f"\n❌ Error: {portfolio['error']}")
        if "state_file" in portfolio:
            print(f"State saved to: {portfolio['state_file']}")
    elif "stocks" in portfolio:
        print(f"\n✅ Portfolio built successfully with {len(portfolio['stocks'])} stocks:\n")

        total_allocation = 0
        for stock in portfolio["stocks"]:
            print(f"{'─' * 70}")
            print(f"📊 {stock.get('name', 'N/A')} ({stock.get('ticker', 'N/A')})")
            print(f"   Sector: {stock.get('sector', 'N/A')}")
            print(f"   Allocation: Rs. {stock.get('allocation_amount', 0):,.0f} ({stock.get('allocation_pct', 0):.1f}%)")
            print(f"   Entry: Rs. {stock.get('entry_price', 0):.2f}")
            print(f"   Target: Rs. {stock.get('target_price', 0):.2f} (+{stock.get('target_pct', 0):.1f}%)")
            print(f"   Stop-loss: Rs. {stock.get('stop_loss_price', 0):.2f} ({stock.get('stop_loss_pct', 0):.1f}%)")
            print(f"   Rationale: {stock.get('rationale', 'N/A')[:100]}...")
            total_allocation += stock.get('allocation_amount', 0)

        print(f"{'─' * 70}")
        print(f"\n💰 Total Allocated: Rs. {total_allocation:,.0f}")

        if "diversification" in portfolio:
            print(f"\n🎯 Diversification: {portfolio['diversification']}")

        if "risk_assessment" in portfolio:
            print(f"\n⚠️  Risk Assessment: {portfolio['risk_assessment']}")

        print(f"\n{'=' * 70}")
        print("Portfolio saved to .cache/portfolios/")
        print("View detailed analysis in the log files: logs/")
    else:
        print("\n⚠️  Portfolio incomplete or invalid format")
        print(f"Response: {portfolio}")

    print("=" * 70)

if __name__ == "__main__":
    main()
