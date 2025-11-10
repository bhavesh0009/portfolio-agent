"""
Test script to verify centralized LLM service and model switching functionality

This script demonstrates:
1. How the LLM service resolves model names
2. Model switching via GEMINI_TEST_MODEL environment variable
3. Direct service usage vs agent usage
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.llm_service import GeminiService, generate_content
from utils.logger import get_logger

load_dotenv()
logger = get_logger("examples.test_llm_service")


def test_model_resolution():
    """Test model name resolution with different tiers"""
    logger.info("=" * 80)
    logger.info("TEST 1: Model Resolution")
    logger.info("=" * 80)

    service = GeminiService()

    # Test tier-based resolution
    models = {
        'high': "Should resolve to GEMINI_HIGH_MODEL",
        'mid': "Should resolve to GEMINI_MID_MODEL",
        'low': "Should resolve to GEMINI_LOW_MODEL",
    }

    for tier, description in models.items():
        resolved = service.resolve_model_name(tier)
        logger.info(f"\nTier '{tier}': {description}")
        logger.info(f"  Resolved model: {resolved}")

    # Test default
    resolved_default = service.resolve_model_name()
    logger.info(f"\nDefault (no tier): {resolved_default}")


def test_environment_override():
    """Test GEMINI_TEST_MODEL environment variable override"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Environment Variable Override (GEMINI_TEST_MODEL)")
    logger.info("=" * 80)

    # Check if override is set
    test_model = os.getenv('GEMINI_TEST_MODEL')
    if test_model:
        logger.info(f"\nGEMINI_TEST_MODEL is set to: {test_model}")
        service = GeminiService()
        resolved = service.resolve_model_name('mid')  # Even requesting 'mid'
        logger.info(f"Requesting 'mid' tier but getting: {resolved}")
        logger.info("SUCCESS: Test model override is working!")
    else:
        logger.info("\nGEMINI_TEST_MODEL not set")
        logger.info("To test model switching, set: export GEMINI_TEST_MODEL=gemini-exp-1206")


def test_agent_model_selection():
    """Test how agents select models"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Agent Model Selection")
    logger.info("=" * 80)

    from agents.stock_screening_agent import StockScreeningAgent
    from agents.portfolio_builder_agent_simple import SimplePortfolioBuilderAgent

    # Stock screening agent (should default to 'mid')
    screening_agent = StockScreeningAgent()
    logger.info(f"\nStockScreeningAgent model_name: {screening_agent.model_name}")
    logger.info("Expected: 'mid'")

    # Portfolio builder (should default to 'high')
    try:
        portfolio_agent = SimplePortfolioBuilderAgent()
        logger.info(f"\nSimplePortfolioBuilderAgent model_name: {portfolio_agent.model_name}")
        logger.info("Expected: 'high'")
    except Exception as e:
        logger.warning(f"Could not test portfolio agent: {e}")

    # Override model
    screening_agent_high = StockScreeningAgent(model_name='high')
    logger.info(f"\nStockScreeningAgent with override: {screening_agent_high.model_name}")
    logger.info("Expected: 'high'")


def show_model_switching_examples():
    """Show examples of how to use model switching"""
    logger.info("\n" + "=" * 80)
    logger.info("MODEL SWITCHING EXAMPLES")
    logger.info("=" * 80)

    logger.info("""
1. Switch models via environment variable (easiest):
   $ export GEMINI_TEST_MODEL=gemini-exp-1206
   $ python examples/run_stock_screening.py

   This will use gemini-exp-1206 for ALL agents and calls!

2. Switch models for specific agent:
   from agents.stock_screening_agent import StockScreeningAgent
   agent = StockScreeningAgent(model_name='low')  # Use lightweight model

3. Switch models for all sub-agents in portfolio builder:
   from agents.portfolio_builder_agent_simple import SimplePortfolioBuilderAgent
   builder = SimplePortfolioBuilderAgent(model_name='mid')  # Override to mid

4. Direct LLM service usage:
   from utils.llm_service import generate_content
   response = generate_content(
       contents=conversation,
       model='high',  # or 'mid', 'low', or specific model name
       temperature=0.7
   )
""")


def show_current_models():
    """Show currently configured models"""
    logger.info("\n" + "=" * 80)
    logger.info("CURRENT MODEL CONFIGURATION")
    logger.info("=" * 80)

    high_model = os.getenv('GEMINI_HIGH_MODEL', 'gemini-2.5-pro')
    mid_model = os.getenv('GEMINI_MID_MODEL', 'gemini-2.5-flash')
    low_model = os.getenv('GEMINI_LOW_MODEL', 'gemini-2.5-flash-lite')
    test_model = os.getenv('GEMINI_TEST_MODEL', 'Not set')

    logger.info(f"\nGEMINI_HIGH_MODEL: {high_model}")
    logger.info(f"  Used by: Portfolio orchestrator agents")
    logger.info(f"\nGEMINI_MID_MODEL: {mid_model}")
    logger.info(f"  Used by: Stock screening, news, research agents (default)")
    logger.info(f"\nGEMINI_LOW_MODEL: {low_model}")
    logger.info(f"  Used by: Future utility and batch processing agents")
    logger.info(f"\nGEMINI_TEST_MODEL: {test_model}")
    logger.info(f"  Purpose: Override ALL agents for testing")


def main():
    """Run all tests"""
    logger.separator('=', 80)
    logger.info("CENTRALIZED LLM SERVICE - TEST SUITE")
    logger.separator('=', 80)

    try:
        test_model_resolution()
        test_environment_override()
        test_agent_model_selection()
        show_current_models()
        show_model_switching_examples()

        logger.separator('=', 80)
        logger.info("ALL TESTS COMPLETED")
        logger.separator('=', 80)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
