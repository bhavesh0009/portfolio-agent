"""
Example: Run Portfolio Manager Agent

Monitors existing portfolio and generates daily analysis with recommendations.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.portfolio_manager_agent import run_portfolio_manager
from utils.logger import get_logger

logger = get_logger("examples.run_portfolio_manager")


def main():
    """Run portfolio manager for LATEST portfolio"""

    print("\n" + "=" * 80)
    print("PORTFOLIO MANAGER AGENT - Daily Portfolio Analysis")
    print("=" * 80)
    print("\nThis agent will:")
    print("1. Load your LATEST portfolio (always works with newest portfolio)")
    print("2. Fetch current stock & index prices (auto-refresh)")
    print("3. Check current prices vs stop-loss/targets")
    print("4. Analyze recent news for your holdings")
    print("5. Research current market conditions")
    print("6. Generate AI-powered recommendations")
    print("7. Store updates in database for dashboard display")
    print("\n" + "=" * 80)

    # Run portfolio manager (handles all data refresh internally)
    result = run_portfolio_manager()

    if not result['success']:
        print(f"\nERROR: {result.get('error', 'Unknown error')}")
        return

    # Display summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    portfolio = result['portfolio']
    print(f"\nPortfolio: {portfolio['profile'].upper()}")
    print(f"Total Capital: Rs. {portfolio['total_capital']:,.0f}")
    print(f"Holdings: {len(portfolio['stocks'])} stocks")

    # Price triggers
    triggers = result['price_triggers']
    print(f"\n--- Price Triggers ---")
    print(f"Stop-loss breached: {len(triggers['stop_loss_breached'])}")
    print(f"Targets reached: {len(triggers['target_reached'])}")
    print(f"Approaching targets: {len(triggers['approaching_target'])}")

    # Show critical stocks
    if triggers['stop_loss_breached']:
        print(f"\nCRITICAL - Stop-Loss Breached:")
        for item in triggers['stop_loss_breached']:
            stock = item['stock']
            print(f"  - {stock['name']} ({stock['ticker']})")
            print(f"    Current: Rs. {item['current_price']:.2f} | "
                  f"Stop-Loss: Rs. {item['stop_loss_price']:.2f} | "
                  f"P&L: {item['current_pnl_pct']:.2f}%")

    if triggers['target_reached']:
        print(f"\nSUCCESS - Targets Reached:")
        for item in triggers['target_reached']:
            stock = item['stock']
            print(f"  - {stock['name']} ({stock['ticker']})")
            print(f"    Current: Rs. {item['current_price']:.2f} | "
                  f"Target: Rs. {item['target_price']:.2f} | "
                  f"P&L: {item['current_pnl_pct']:.2f}%")

    # Recommendation
    recommendation = result['recommendation']
    print(f"\n--- AI Recommendation ---")
    print(f"Action: {recommendation.get('recommendation', 'UNKNOWN')}")
    print(f"Priority: {result['priority']}")
    print(f"Confidence: {recommendation.get('confidence_level', 0)}%")

    print(f"\nAssessment:")
    print(f"{recommendation.get('assessment', 'N/A')}")

    if recommendation.get('immediate_actions'):
        print(f"\nImmediate Actions:")
        for action in recommendation['immediate_actions']:
            print(f"  - {action}")

    if recommendation.get('stocks_to_review'):
        print(f"\nStocks to Review:")
        for stock in recommendation['stocks_to_review']:
            print(f"  - {stock}")

    print(f"\nReasoning:")
    print(f"{recommendation.get('reasoning', 'N/A')}")

    print("\n" + "=" * 80)
    print("Update stored in database - view on dashboard!")
    print("=" * 80)


if __name__ == '__main__':
    main()
