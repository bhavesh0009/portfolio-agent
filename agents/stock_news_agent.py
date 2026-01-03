"""
Stock News Analysis AI Agent using Google Search Grounding
Uses Gemini's built-in Google Search grounding for news analysis without external tools
"""

import os
import time
from typing import Optional
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai
from google.genai import types
from utils.logger import get_logger
from utils.metrics_collector import get_metrics_collector
from utils.llm_service import GeminiService
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger("agents.stock_news_agent_grounding")


class StockNewsAgentGrounding:
    """AI agent that analyzes news using Google Search grounding (cost-optimized)"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the agent with Gemini API and Google Search grounding

        Args:
            model_name: Gemini model tier ('high', 'mid', 'low') or specific model name
                       Defaults to 'mid' if not specified
        """
        # Resolve model name using llm_service (supports tier resolution and GEMINI_TEST_MODEL override)
        self.model_name = GeminiService.resolve_model_name(model_name or 'mid')

        # Get API key from environment
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")

        # Initialize Google GenAI client
        self.client = genai.Client(api_key=api_key)

        logger.info(f"Initialized StockNewsAgentGrounding with model: {self.model_name}")

    def _create_system_prompt(self) -> str:
        """Create system prompt with grounding instructions"""
        current_date = datetime.now().strftime("%B %d, %Y")

        return f"""You are a stock news and sentiment analysis agent specializing in Indian and global equity markets.

Current Date: {current_date}

Your task is to analyze recent news and provide insights on:
- News sentiment (positive/negative/neutral/mixed)
- Key events and developments
- Impact on stock performance and outlook
- Market reactions and trends
- Credibility assessment of information

You have access to Google Search for finding the latest news. When analyzing:

1. PRIORITIZE REPUTABLE SOURCES:
   - Tier 1 (Highest Trust): Reuters, Bloomberg, ET (Economic Times), Mint, Business Standard, Financial Express
   - Tier 2 (High Trust): Moneycontrol, CNBC, Business Today, Fortune India
   - Tier 3 (Moderate Trust): Times of India Business, Hindustan Times Business, India Today Business
   - Exercise caution with: Opinion blogs, unverified social media, promotional content

2. FOCUS ON TIMEFRAME:
   - Pay close attention to the timeframe specified in the user query (e.g., "last 7 days", "last month")
   - Only analyze news from within that timeframe
   - Clearly indicate the dates of news events in your analysis

3. FACT-BASED ANALYSIS:
   - Prioritize concrete events: earnings reports, management changes, regulatory updates, major deals
   - Distinguish between facts and market speculation
   - Note if news is unverified or from single-source reports

4. SENTIMENT GUIDELINES:
   - Positive: Strong growth indicators, positive earnings, strategic wins, favorable regulatory changes
   - Negative: Revenue/profit decline, legal issues, management exodus, regulatory penalties
   - Neutral: Routine updates, mixed signals, no material impact
   - Mixed: Conflicting signals or offsetting positive/negative developments

5. ALWAYS CITE SOURCES:
   - Reference the source name and approximate date for key points
   - If multiple sources report the same event, note the consensus

Your analysis should be concise, focused, and actionable for investment decision-making."""

    def _format_sources(self, grounding_metadata) -> str:
        """
        Extract and format sources from grounding metadata

        Args:
            grounding_metadata: Grounding metadata from Gemini response

        Returns:
            Formatted string with source citations
        """
        if not grounding_metadata:
            logger.warning("No grounding metadata available")
            return "\n\nSources: No sources available"

        if not hasattr(grounding_metadata, 'grounding_chunks') or not grounding_metadata.grounding_chunks:
            logger.warning("No grounding chunks in metadata")
            return "\n\nSources: No sources available"

        sources = []
        for i, chunk in enumerate(grounding_metadata.grounding_chunks, 1):
            if hasattr(chunk, 'web') and chunk.web:
                title = chunk.web.title or "Unknown Title"
                uri = chunk.web.uri or "#"
                sources.append(f"{i}. [{title}]({uri})")

        if not sources:
            return "\n\nSources: No web sources available"

        logger.info(f"Formatted {len(sources)} source citations")
        return "\n\nSources:\n" + "\n".join(sources)

    def run(self, user_query: str, max_iterations: int = 1, verbose: bool = True) -> str:
        """
        Run news analysis using Google Search grounding (single-shot)

        Args:
            user_query: Natural language query about stock news
                       Example: "Latest news on Reliance Industries in the last 7 days"
            max_iterations: Kept for interface compatibility, always 1 (single LLM call)
            verbose: Print execution details

        Returns:
            Analysis string with source citations
        """
        start_time = time.perf_counter()

        if verbose:
            logger.info(f"Running news analysis query: {user_query}")
            logger.debug(f"Model: {self.model_name}")

        try:
            # Configure Google Search grounding tool
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Create system prompt
            system_prompt = self._create_system_prompt()

            # Combine system prompt with user query
            full_prompt = f"{system_prompt}\n\nUser Query: {user_query}"

            if verbose:
                logger.debug("Calling Gemini with Google Search grounding...")

            # Single LLM call with grounding (cost-optimized)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=full_prompt)]
                    )
                ],
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    temperature=0.7
                )
            )

            # Extract response text
            if not response.text:
                error_msg = "Empty response from Gemini"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            answer = response.text.strip()

            # Parse grounding metadata for sources
            grounding_metadata = None
            if response.candidates and len(response.candidates) > 0:
                grounding_metadata = response.candidates[0].grounding_metadata

            sources = self._format_sources(grounding_metadata)

            # Append sources to answer
            final_answer = f"{answer}{sources}"

            # Extract token usage for metrics
            input_tokens = 0
            output_tokens = 0

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics
            metrics_collector = get_metrics_collector()
            metrics_collector.record_llm_call(
                agent_name="stock_news_agent_grounding",
                model_name=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms
            )

            if verbose:
                logger.info(f"✓ Analysis complete ({duration_ms:.0f}ms)")
                logger.debug(f"  Input tokens: {input_tokens:,}")
                logger.debug(f"  Output tokens: {output_tokens:,}")
                logger.debug(f"  Response length: {len(final_answer)} chars")

            return final_answer

        except Exception as e:
            error_msg = f"Error in news analysis: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e


def run_stock_news_grounding(query: str, model: Optional[str] = None, verbose: bool = True) -> str:
    """
    Run stock news analysis using Google Search grounding

    Interface-compatible wrapper function for StockNewsAgentGrounding
    (matches signature of run_stock_news from stock_news_agent.py)

    Args:
        query: Natural language query about stock news/sentiment
               Examples:
               - "Latest news on Reliance Industries in the last 7 days"
               - "News and sentiment analysis for TCS. Focus on news from the last 5d only."
               - "Any significant news on Infosys in the last month?"

        model: Gemini model tier ('high', 'mid', 'low') or specific model name
               Defaults to 'mid' (gemini-2.5-flash) if not specified

        verbose: Print execution details and progress
                 Default: True

    Returns:
        Analysis string with news summary, sentiment, and source citations

    Example:
        >>> result = run_stock_news_grounding("Latest news on HDFC Bank stock price movements")
        >>> print(result)
        Based on recent news analysis, HDFC Bank has shown...

        Sources:
        1. [HDFC Bank Q3 Results 2024](https://www.moneycontrol.com/...)
        2. [HDFC Bank Share Price Analysis](https://economictimes.indiatimes.com/...)

    Raises:
        RuntimeError: If API call fails or response is invalid
        ValueError: If API key is not configured
    """
    agent = StockNewsAgentGrounding(model_name=model)
    return agent.run(user_query=query, verbose=verbose)


# Backward compatibility alias
run_news_agent_grounding = run_stock_news_grounding

# ============================================================================
# BACKWARD COMPATIBILITY EXPORTS
# ============================================================================
# These exports allow this new grounding-based agent to be a drop-in
# replacement for the old tool-based stock_news_agent.py
#
# Old code that imports:
#   from agents.stock_news_agent import StockNewsAgent, run_stock_news
#
# Will now get the new grounding-based implementations automatically.
# ============================================================================

# Export class under old name
StockNewsAgent = StockNewsAgentGrounding

# Export function under old name
run_stock_news = run_stock_news_grounding

# Export deprecated alias
run_news_agent = run_stock_news_grounding


if __name__ == "__main__":
    # Quick test
    print("Testing Google Search Grounding News Agent...")
    print("-" * 60)

    test_query = "Latest news on Infosys in the last 7 days"
    print(f"Query: {test_query}\n")

    result = run_stock_news_grounding(test_query, verbose=True)
    print("\nResult:")
    print("=" * 60)
    print(result)
    print("=" * 60)
