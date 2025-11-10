"""
Market Research AI Agent using Gemini
Focuses on Indian market trends, sectors, economic indicators, and macro-economic analysis
"""

import os
import json
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.news_scraper import scrape_news
from tools.article_extractor import extract_article
from utils.logger import get_logger
from utils.json_parser import parse_agent_response, validate_agent_result
from utils.llm_service import generate_content
from google.genai import types

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger("agents.market_research_agent")


class MarketResearchAgent:
    """AI agent that researches market trends, sectors, and economic factors (focused on Indian markets)"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the research agent with Gemini API

        Args:
            model_name: Gemini model tier ('high', 'mid', 'low') or specific model name
                       Defaults to 'mid' if not specified
        """
        # Store model name (defaults to 'mid' if not specified)
        # Can be overridden by GEMINI_TEST_MODEL environment variable for testing
        self.model_name = model_name or 'mid'

        # Conversation history
        self.chat_history = []

    def _create_system_prompt(self) -> str:
        """Create system prompt with tool information for market research"""
        return f"""You are an Indian market research AI agent specializing in macro-economic analysis, sector trends, and market insights.

You have access to TWO tools:

TOOL 1: scrape_news
DESCRIPTION: Search Google News with flexible date options (period or date range)
PARAMETERS:
  - query (required): Search query for news articles
    Example: "Indian GDP growth", "RBI interest rate policy", "Indian IT sector trends"

  DATE OPTIONS (choose ONE):
  Option A - Use period:
  - period (optional): Time period like "1h", "1d", "7d", "1m", "1y"
    Example: {{"period": "30d"}}

  Option B - Use date range:
  - from_date (optional): Start date in MM/DD/YYYY format
  - to_date (optional): End date in MM/DD/YYYY format
    Example: {{"from_date": "01/01/2025", "to_date": "01/31/2025"}}

  NOTE: Cannot use both period and date range together. If neither provided, defaults to last 7 days.

  OTHER PARAMETERS:
  - region (optional): Region code - use "IN" for India-focused news (default: "US")
  - language (optional): Language code like "en", "hi" (default: "en")
  - max_results (optional): Maximum number of articles to return (recommended: 15-30)

TOOL 2: extract_article
DESCRIPTION: Extract full article content, summary, and metadata from a news URL
PARAMETERS:
  - url (required): URL of the news article to extract
    Example: "https://economictimes.indiatimes.com/..."
  - language (optional): Language code (default: "en")
  - perform_nlp (optional): Whether to perform NLP analysis for keywords/summary (default: true)

YOUR RESEARCH FOCUS:
As an Indian market research agent, you specialize in:
1. Overall Indian market trends and movements (Nifty, Sensex, BSE)
2. Sector-specific analysis (IT, Banking, Pharma, Auto, Manufacturing, etc.)
3. Economic indicators (GDP, inflation, exports, manufacturing PMI, etc.)
4. Monetary policy (RBI interest rates, repo rate, liquidity measures)
5. Government policies and initiatives (Make in India, PLI schemes, budget impacts)
6. Global factors affecting Indian markets (crude oil, dollar-rupee, FII/DII flows)
7. Regulatory changes (SEBI regulations, tax policies)
8. Infrastructure and development trends

RESEARCH METHODOLOGY:
1. When asked about market/sector/economic topics, determine appropriate search queries
2. Use region="IN" for India-focused news when relevant
3. Search for recent news on the topic using scrape_news
4. For deeper analysis, extract full articles using extract_article
5. Synthesize information from multiple sources
6. Provide comprehensive analysis with:
   - Key trends and patterns
   - Supporting data and facts from news
   - Market implications
   - Expert opinions cited in articles
   - Future outlook based on current developments

SOURCE RELIABILITY FOR MARKET RESEARCH:
Based on extraction success rate testing, prioritize these sources for Indian market analysis:

BEST FOR MARKET RESEARCH (100% extraction success):
- ET Now: Financial and market news focused
- Zee Business: Comprehensive market coverage
- Markets Mojo: Market data and analysis
- Outlook Money: Investment and market insights
- BusinessLine (Hindu BusinessLine): Quality financial journalism

GOOD COVERAGE (50%+ extraction success):
- Business Standard: Economic and market analysis
- Business Today: Market news and analysis
- Moneycontrol: Stock and market data (when accessible)

FREQUENT BUT UNRELIABLE EXTRACTION:
- mint (LiveMint): High frequency but extraction failures (0% success)
  Use only if critical - content is good but extraction is problematic
- The Financial Express: Market coverage but extraction issues (0% success)
- The Economic Times: Economic news but extraction failures (0% success)

STRATEGY FOR MARKET RESEARCH:
- Lead research with highly reliable sources (ET Now, Zee Business, Markets Mojo)
- Use moderately reliable sources for additional perspectives
- For problematic sources, cite facts from metadata/snippets without full extraction
- Prefer aggregated/analyzed sources over raw data sources
- Combine multiple sources for comprehensive market outlook

OUTPUT FORMAT FOR TOOL CALLS:
When you want to call the tool, respond with JSON in this exact format:
{{
  "action": "call_tool",
  "tool": "scrape_news",
  "parameters": {{
    "query": "your query here",
    "region": "IN",
    "period": "30d",
    "max_results": 20
  }}
}}

OUTPUT FORMAT FOR FINAL ANSWER:
When you have the final answer, respond in this format:
{{
  "action": "final_answer",
  "answer": "your comprehensive research analysis here with insights"
}}

Current date: {self._get_current_date()}

Be thorough, data-driven, and provide actionable market intelligence from your research."""

    def _get_current_date(self) -> str:
        """Get current date for context"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse agent response to extract action and parameters"""
        return parse_agent_response(
            response_text,
            fallback_action="final_answer",
            agent_name="market_research_agent"
        )

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the requested tool"""
        logger.info(f"Executing tool: {tool_name}")

        if tool_name == "scrape_news":
            logger.debug(f"Query: {parameters.get('query', 'N/A')}")

            # Show search mode
            if 'period' in parameters:
                logger.debug(f"Period: {parameters.get('period')}")
            elif 'from_date' in parameters or 'to_date' in parameters:
                logger.debug(f"Date range: {parameters.get('from_date', 'default')} to {parameters.get('to_date', 'default')}")
            else:
                logger.debug("Using default (last 7 days)")

            # Show region
            region = parameters.get('region', 'US')
            logger.debug(f"Region: {region}")

            result = scrape_news(**parameters)
            logger.info(f"Found {result['total_results']} articles (search mode: {result.get('search_mode')})")
            return result

        elif tool_name == "extract_article":
            url = parameters.get('url', 'N/A')
            logger.info_preview("URL", url, preview_len=80)

            result = extract_article(**parameters)
            logger.info_preview("Extracted article", result['title'], preview_len=60)
            logger.debug(f"Content length: {len(result['text'])} characters")
            return result

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def run(self, research_query: str, max_iterations: int = 10, verbose: bool = True) -> str:
        """
        Run the research agent to analyze market/sector/economic topics

        Args:
            research_query: Research question about Indian market/economy/sectors
            max_iterations: Maximum planning/execution iterations
            verbose: Print detailed execution steps

        Returns:
            Final research analysis from the agent
        """
        if verbose:
            logger.separator('=', 60)
            logger.info(f"RESEARCH QUERY: {research_query}")
            logger.separator('=', 60)

        # Initialize conversation with system prompt
        conversation = [
            types.Content(role="user", parts=[types.Part.from_text(text=self._create_system_prompt())]),
            types.Content(role="model", parts=[types.Part.from_text(text="I understand. I'm ready to research Indian market trends, sectors, and economic factors using news analysis tools. I'll respond in JSON format for tool calls or final answers.")]),
            types.Content(role="user", parts=[types.Part.from_text(text=research_query)])
        ]

        iteration = 0
        while iteration < max_iterations:
            time.sleep(3)
            iteration += 1

            if verbose:
                logger.trace(f"--- Iteration {iteration} ---")

            # Get response from Gemini using centralized service
            try:
                response_text = generate_content(
                    contents=conversation,
                    model=self.model_name,
                    temperature=0.7,
                    verbose=verbose
                )

                if verbose:
                    logger.info_preview("Response", response_text, preview_len=200)

            except Exception as e:
                logger.error(f"Failed to get response from Gemini: {e}")
                return f"Error: {str(e)}"

            # Parse response
            parsed = self._parse_response(response_text)
            action = parsed.get("action")

            if action == "final_answer":
                # Agent has completed its work
                final_answer = parsed.get("answer", response_text)

                if verbose:
                    logger.separator('=', 60)
                    logger.info("FINAL RESEARCH ANALYSIS:")
                    logger.separator('=', 60)
                    logger.info(final_answer)
                    logger.separator('=', 60)

                return final_answer

            elif action == "call_tool":
                # Execute tool
                tool_name = parsed.get("tool")
                parameters = parsed.get("parameters", {})

                try:
                    tool_result = self._execute_tool(tool_name, parameters)

                    # Add tool execution to conversation
                    conversation.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

                    # Limit article content in response to avoid token limits
                    # Only send first 15 articles with truncated descriptions
                    limited_result = tool_result.copy()
                    if 'articles' in limited_result and len(limited_result['articles']) > 15:
                        limited_result['articles'] = limited_result['articles'][:15]
                        limited_result['note'] = f"Showing 15 of {tool_result['total_results']} articles"

                    # Truncate descriptions
                    for article in limited_result.get('articles', []):
                        if 'desc' in article and article['desc']:
                            article['desc'] = article['desc'][:200]

                    # Provide results back to agent
                    result_message = f"Tool execution result:\n{json.dumps(limited_result, indent=2)}"
                    conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=result_message)]))

                    if verbose:
                        logger.info("Tool executed successfully")

                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=error_msg)]))

                    if verbose:
                        logger.error(error_msg)
            else:
                # Unknown action, treat as final answer
                if verbose:
                    logger.separator('=', 60)
                    logger.info("FINAL RESEARCH ANALYSIS (no action specified):")
                    logger.separator('=', 60)
                    logger.info(response_text)
                    logger.separator('=', 60)

                return response_text

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached without final answer")
        if 'response_text' in locals():
            logger.info_preview("Last response", response_text, preview_len=500)
            return f"Maximum iterations reached. Unable to complete the research. Last response: {response_text[:500]}"
        return "Maximum iterations reached. Unable to complete the research."


def run_market_research(query: str, model: Optional[str] = None, verbose: bool = True) -> str:
    """
    Convenience function to run Indian market research with a single query

    Args:
        query: Research question about Indian market/economy/sectors
        model: Optional Gemini model name
        verbose: Print execution details

    Returns:
        Agent's final research analysis
    """
    agent = MarketResearchAgent(model_name=model)
    return agent.run(query, verbose=verbose)


if __name__ == "__main__":
    # Example usage
    example_query = (
        "What are the key trends in the Indian automobile sector over the last 3 months? "
        "Include market sentiment, government policies, and growth outlook."
    )

    answer = run_market_research(example_query)
    logger.info("Market research agent execution completed!")
