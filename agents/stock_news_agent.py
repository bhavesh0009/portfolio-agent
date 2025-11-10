"""
Stock News Analysis AI Agent using Gemini
Focuses on analyzing news and sentiment for specific stocks/companies
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
logger = get_logger("agents.stock_news_agent")


class StockNewsAgent:
    """AI agent that analyzes news and sentiment for specific stocks/companies"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the agent with Gemini API

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
        """Create system prompt with tool information"""
        return f"""You are a stock news analysis AI agent specializing in analyzing news for specific stocks and companies.

You have access to TWO tools:

TOOL 1: scrape_news
DESCRIPTION: Search Google News with flexible date options (period or date range)
PARAMETERS:
  - query (required): Search query for news articles
    Example: "Tesla stock", "Indian economy", "NVIDIA earnings"

  DATE OPTIONS (choose ONE):
  Option A - Use period:
  - period (optional): Time period like "1h", "1d", "7d", "1m", "1y"
    Example: {{"period": "7d"}}

  Option B - Use date range:
  - from_date (optional): Start date in MM/DD/YYYY format
  - to_date (optional): End date in MM/DD/YYYY format
    Example: {{"from_date": "01/01/2025", "to_date": "01/31/2025"}}

  NOTE: Cannot use both period and date range together. If neither provided, defaults to last 7 days.

  OTHER PARAMETERS:
  - region (optional): Region code like "US", "IN", "GB" (default: "US")
  - language (optional): Language code like "en", "hi", "es" (default: "en")
  - max_results (optional): Maximum number of articles to return (recommended: 10-20)

TOOL 2: extract_article
DESCRIPTION: Extract full article content, summary, and metadata from a news URL
PARAMETERS:
  - url (required): URL of the news article to extract
    Example: "https://www.reuters.com/article/..."
  - language (optional): Language code (default: "en")
  - perform_nlp (optional): Whether to perform NLP analysis for keywords/summary (default: true)

WORKFLOW:
1. When user asks about news, determine the appropriate time frame
2. Use 'period' for recent news (last 24h, last week, etc.)
3. Use 'from_date'/'to_date' for specific date ranges
4. Execute news search with appropriate parameters using scrape_news
5. Analyze the news article highlights (titles, sources, dates, descriptions)
6. If any news article is particularly significant or requires deeper analysis, use extract_article with the URL to get full text and summary
7. Provide insights, trends, or summaries based on the news data
8. Answer the user's question with data-driven analysis

SOURCE RELIABILITY GUIDANCE:
Based on extraction success rate testing, when analyzing news articles prioritize these reliable sources:

HIGHLY RELIABLE (100% extraction success):
- Markets Mojo: Excellent content extraction
- scanx.trade: Consistent, clean article content
- ET Now: Financial news focused, reliable extraction
- Zee Business: Good extraction success rate

MODERATELY RELIABLE (50%+ extraction success):
- Business Standard: Mixed results, but good content when successful
- Business Today: Balanced coverage
- Outlook Money: Investment focused
- BusinessLine (Hindu BusinessLine): Quality content

PROBLEMATIC (avoid if possible):
- mint (LiveMint): Appears frequently but has extraction issues (~0% success)
- The Financial Express: Frequent but extraction failures (~0% success)
- The Economic Times: Frequent but extraction failures (~0% success)

STRATEGY:
- When multiple articles exist on the same stock/topic, prefer highly reliable sources
- If using problematic sources, extract multiple articles to ensure content quality
- Skip extraction for YouTube and Cloudflare-protected sources (Groww, Goodreturns)
- Focus on financial/stock-specific sources rather than general news

OUTPUT FORMAT FOR TOOL CALLS:
When you want to call the tool, respond with JSON in this exact format:
{{
  "action": "call_tool",
  "tool": "scrape_news",
  "parameters": {{
    "query": "your query here",
    "period": "7d",
    "max_results": 20
  }}
}}

OUTPUT FORMAT FOR FINAL ANSWER:
When you have the final answer, respond in this format:
{{
  "action": "final_answer",
  "answer": "your detailed analysis here with insights"
}}

Current date: {self._get_current_date()}

Be analytical, identify trends, and provide actionable insights from news data."""

    def _get_current_date(self) -> str:
        """Get current date for context"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse agent response to extract action and parameters"""
        return parse_agent_response(
            response_text,
            fallback_action="final_answer",
            agent_name="stock_news_agent"
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

    def run(self, user_query: str, max_iterations: int = 10, verbose: bool = True) -> str:
        """
        Run the agent to answer user query

        Args:
            user_query: User's question about news/market
            max_iterations: Maximum planning/execution iterations
            verbose: Print detailed execution steps

        Returns:
            Final answer from the agent
        """
        if verbose:
            logger.separator('=', 60)
            logger.info(f"USER QUERY: {user_query}")
            logger.separator('=', 60)

        # Initialize conversation with system prompt
        conversation = [
            types.Content(role="user", parts=[types.Part.from_text(text=self._create_system_prompt())]),
            types.Content(role="model", parts=[types.Part.from_text(text="I understand. I'm ready to help analyze news using the news scraping tools. I'll respond in JSON format for tool calls or final answers.")]),
            types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
        ]

        iteration = 0
        while iteration < max_iterations:
            time.sleep(3)
            iteration += 1

            if verbose:
                logger.trace(f"--- Iteration {iteration} ---")

            # Get response from Gemini
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
                    logger.info("FINAL ANSWER:")
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
                    # Only send first 10 articles with truncated descriptions
                    limited_result = tool_result.copy()
                    if 'articles' in limited_result and len(limited_result['articles']) > 10:
                        limited_result['articles'] = limited_result['articles'][:10]
                        limited_result['note'] = f"Showing 10 of {tool_result['total_results']} articles"

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
                    logger.info("FINAL ANSWER (no action specified):")
                    logger.separator('=', 60)
                    logger.info(response_text)
                    logger.separator('=', 60)

                return response_text

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached without final answer")
        if 'response_text' in locals():
            logger.info_preview("Last response", response_text, preview_len=500)
            return f"Maximum iterations reached. Unable to complete the task. Last response: {response_text[:500]}"
        return "Maximum iterations reached. Unable to complete the task."


def run_stock_news(query: str, model: Optional[str] = None, verbose: bool = True) -> str:
    """
    Convenience function to run stock news analysis agent with a single query

    Args:
        query: User question about stock/company news
        model: Optional Gemini model name
        verbose: Print execution details

    Returns:
        Agent's final answer
    """
    agent = StockNewsAgent(model_name=model)
    return agent.run(query, verbose=verbose)


# Backward compatibility alias
def run_news_agent(query: str, model: Optional[str] = None, verbose: bool = True) -> str:
    """Deprecated: Use run_stock_news() instead"""
    return run_stock_news(query, model, verbose)


if __name__ == "__main__":
    # Example usage
    example_query = (
        "Any significant news on Force Motors in the last month? why it is so much down recently "
        "Summarize the key trends and sentiment for this share."
    )

    answer = run_stock_news(example_query)
    print("\nStock news agent execution completed!")
