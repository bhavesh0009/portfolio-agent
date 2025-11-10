"""
Stock Screening AI Agent using Gemini
"""

import os
import json
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.screen_stocks import screen_stocks, get_available_ratios
from tools.industry_scraper import get_industries_overview, get_industry_stocks, search_industries
from utils.logger import get_logger
from utils.json_parser import parse_agent_response, validate_agent_result
from utils.llm_service import generate_content
from google.genai import types

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger("agents.stock_screening_agent")


class StockScreeningAgent:
    """AI agent that uses Gemini to plan and execute stock screening queries"""

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

        # Available ratios for context
        try:
            self.available_ratios = get_available_ratios()
        except Exception as e:
            logger.warning(f"Could not load available ratios: {e}")
            self.available_ratios = []

        # Conversation history
        self.chat_history = []

    def _create_system_prompt(self) -> str:
        """Create system prompt with tool information"""
        return f"""You are a stock screening AI agent with access to screener.in data.

You have access to FOUR tools for stock screening and industry analysis:

TOOL 1: screen_stocks
DESCRIPTION: Screen stocks based on custom filtering criteria using 335+ financial ratios
PARAMETERS:
  - query (required): Screening query using ratio names and conditions
    Example: "Market capitalization > 500 AND Price to earning < 15 AND Return on capital employed > 22%"
  - columns (optional): List of column names to return in results
    Example: ["Name", "CMP Rs.", "P/E", "ROE %", "Sales growth 3Years"]

TOOL 2: get_industries_overview
DESCRIPTION: Get overview of all industries with aggregate metrics (187 industries)
PARAMETERS: None
RETURNS: List of industries with metrics:
  - industry_name, industry_url, company_count
  - total_market_cap, median_market_cap, median_pe
  - avg_sales_growth, avg_opm, avg_roce, median_1y_return
USE WHEN: User wants to explore industries, compare sectors, or find industry-specific opportunities

TOOL 3: search_industries
DESCRIPTION: Search for industries by keyword
PARAMETERS:
  - keyword (required): Search term to match industry names (case-insensitive)
    Example: "auto", "pharma", "it", "bank"
RETURNS: List of matching industries with their metrics
USE WHEN: User asks about specific industry/sector without knowing exact name

TOOL 4: get_industry_stocks
DESCRIPTION: Get all stocks from a specific industry with available metrics
PARAMETERS:
  - industry_url (required): Industry URL path from get_industries_overview or search_industries
    Example: "/market/IN02/IN0201/IN020101/IN020101002/"
RETURNS: Dictionary with:
  - industry_name: Name of the industry
  - breadcrumb: Hierarchical category path
  - total_results: Number of stocks in industry
  - stocks: List of stocks with metrics (CMP, P/E, Market Cap, ROCE, etc.)
USE WHEN: User wants to see all stocks in a specific industry/sector

CRITICAL: COLUMN NAME USAGE RULES
================================================================================
You MUST use EXACT Configuration Names in both queries and column lists.
DO NOT use output names or abbreviations.

CORRECT Configuration Names (use these):
  - "Market Capitalization" (NOT "market capitalization" or "Market Cap")
  - "Return on equity" (NOT "ROE" or "ROE %")
  - "Return on capital employed" (NOT "ROCE" or "ROCE %")
  - "Price to Earning" (NOT "P/E" or "PE")
  - "Sales growth 3Years" (NOT "Sales growth 3years" or "Sales Var 3Yrs")
  - "Profit growth 3Years" (NOT "Profit growth 3years" or "Profit Var 3Yrs")
  - "Debt to equity" (NOT "Debt / Eq")
  - "Promoter holding" (NOT "Prom. Hold.")
  - "YOY Quarterly sales growth" (NOT "Qtr Sales Var")
  - "YOY Quarterly profit growth" (NOT "Qtr Profit Var")

Common Mappings (Config Name -> Table Header):
  - "Sales growth 3Years" -> appears as "Sales Var 3Yrs %" in table
  - "Profit growth 3Years" -> appears as "Profit Var 3Yrs %" in table
  - "Return on equity" -> appears as "ROE %" in table
  - "Return on capital employed" -> appears as "ROCE %" in table
  - "Price to Earning" -> appears as "P/E" in table
  - "Market Capitalization" -> appears as "Mar Cap Rs.Cr." in table
  - "Debt to equity" -> appears as "Debt / Eq" in table

NAMING REQUIREMENTS:
1. Case-sensitive: "Market Capitalization" NOT "market capitalization"
2. Use full names: "Return on equity" NOT "ROE"
3. Check spacing: "Sales growth 3Years" NOT "Sales growth 3years"
4. Use config names in queries: "Market Capitalization > 5000" is correct
5. Use config names in columns: ["Return on equity", "Sales growth 3Years"] is correct

EXAMPLE CORRECT USAGE:
{{{{
  "action": "call_tool",
  "tool": "screen_stocks",
  "parameters": {{{{
    "query": "Market Capitalization > 5000 AND Return on equity > 15 AND Sales growth 3Years > 15",
    "columns": ["Name", "Market Capitalization", "Return on equity", "Sales growth 3Years", "Profit growth 3Years"]
  }}}}
}}}}

EXAMPLE INCORRECT USAGE (DO NOT DO THIS):
{{{{
  "action": "call_tool",
  "tool": "screen_stocks",
  "parameters": {{{{
    "query": "market capitalization > 5000 AND ROE > 15 AND Sales growth 3years > 15",
    "columns": ["Name", "Market Cap", "ROE %", "Sales Var 3Yrs"]
  }}}}
}}}}

WORKFLOW:
1. When user asks a question, create a plan for how to answer it
2. Generate appropriate screen_stocks query with relevant filters
3. Use EXACT configuration names in both query and columns
4. Execute the query using JSON function calling format
5. Analyze results and refine if needed
6. Provide final answer with reasoning

HANDLING LARGE RESULT SETS:
================================================================================
The screening tool automatically manages large result sets to avoid token overflow.

When screen_stocks returns results, check for these fields:
- "is_sampled": Boolean (true if results were large and sampled)
- "stored_count": Total number of stocks found
- "sample_stocks" or "stocks": Sample stocks for analysis (max 30 by default)
- "stored_file": Path to full results file (if sampled)
- "sample_note": Explanation of sampling
- "analysis_summary": Coding agent's statistical analysis (if available)
- "analysis_statistics": Detailed statistics on numeric columns
- "analysis_suggestions": Data-driven refinement suggestions

IF is_sampled = true:
  - You received a SAMPLE of results (e.g., 30 out of 169 stocks)
  - Full data is stored in the file specified in "stored_file"
  - A coding agent has analyzed the full dataset
  - Review "analysis_summary" for insights and patterns
  - Check "analysis_suggestions" for data-driven refinement ideas

YOUR OPTIONS (use your judgment):
1. Analyze the sample if it looks sufficient for the task
2. Refine the query with additional filters to reduce results
   - Use insights from "analysis_statistics" to choose good thresholds
   - Example: If analysis shows "ROE ranges 20-154, mean 42", consider adding "ROE > 35"
3. Adjust thresholds based on statistical analysis
   - Use Q1, Q3, mean, median from "analysis_statistics"
4. Request different sorting or grouping criteria if needed

IMPORTANT PRINCIPLES:
- NO hardcoded rules - use your judgment based on the situation
- Consider investor profile (aggressive vs defensive)
- Use statistical insights to make informed refinements
- Balance between too broad (too many results) and too narrow (too few results)
- Optimal result size: 10-30 stocks for effective analysis

EXAMPLE SCENARIO:
Query returns 169 results (is_sampled=true, sample_stocks=30):
- Check analysis_summary: "ROE ranges 20-154 (mean 42), Market Cap 500-12304 (median 1890)"
- Consider refinement: Add "ROE > 35 AND Market Capitalization > 1500"
- This focuses on above-average quality stocks in mid-to-large cap range
- Re-run query, likely get 20-40 results (more manageable)

OUTPUT FORMAT FOR TOOL CALLS:
When you want to call the tool, respond with JSON in this exact format:
{{
  "action": "call_tool",
  "tool": "screen_stocks",
  "parameters": {{
    "query": "your query here",
    "columns": ["column1", "column2"]
  }}
}}

OUTPUT FORMAT FOR FINAL ANSWER:
When you have the final answer, respond in this format:
{{
  "action": "final_answer",
  "answer": "your detailed answer here with reasoning"
}}

Current date: {self._get_current_date()}

Be concise, analytical, and data-driven in your responses."""

    def _get_current_date(self) -> str:
        """Get current date for context"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse agent response to extract action and parameters"""
        return parse_agent_response(
            response_text,
            fallback_action="final_answer",
            agent_name="stock_screening_agent"
        )

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute stock screening or industry analysis tools"""
        logger.separator()
        logger.info(f"[STOCK_AGENT -> TOOL] Executing {tool_name}")
        logger.debug(f"  Parameters: {json.dumps(parameters, indent=2)}")
        logger.separator()

        # Execute appropriate tool
        if tool_name == "screen_stocks":
            logger.info("Parameters sent to screener:")
            logger.info(f"  Query: {parameters.get('query', 'N/A')}")
            logger.info(f"  Columns: {parameters.get('columns', 'All')}")

            result = screen_stocks(**parameters)

            logger.separator()
            logger.info("[STOCK_AGENT <- SCREENER_TOOL] Tool execution completed")
            logger.info(f"  Total stocks found: {result['total_results']}")
            logger.debug(f"  Available columns: {result.get('available_columns', [])}")
            if 'column_mapping' in result:
                logger.debug(f"  Column mapping: {json.dumps(result['column_mapping'], indent=4)}")

        elif tool_name == "get_industries_overview":
            result = get_industries_overview()

            logger.separator()
            logger.info("[STOCK_AGENT <- INDUSTRY_TOOL] Tool execution completed")
            logger.info(f"  Total industries found: {len(result)}")

        elif tool_name == "search_industries":
            keyword = parameters.get('keyword', '')
            logger.info(f"  Search keyword: {keyword}")

            result = search_industries(keyword)

            logger.separator()
            logger.info("[STOCK_AGENT <- INDUSTRY_TOOL] Tool execution completed")
            logger.info(f"  Matching industries: {len(result)}")

        elif tool_name == "get_industry_stocks":
            industry_url = parameters.get('industry_url', '')
            logger.info(f"  Industry URL: {industry_url}")

            result = get_industry_stocks(industry_url)

            logger.separator()
            logger.info("[STOCK_AGENT <- INDUSTRY_TOOL] Tool execution completed")
            logger.info(f"  Industry: {result.get('industry_name', 'Unknown')}")
            logger.info(f"  Total stocks: {result.get('total_results', 0)}")

        else:
            raise ValueError(f"Unknown tool: {tool_name}. Available tools: screen_stocks, get_industries_overview, search_industries, get_industry_stocks")

        logger.separator()
        return result

    def run(self, user_query: str, max_iterations: int = 10, verbose: bool = True) -> str:
        """
        Run the agent to answer user query

        Args:
            user_query: User's question about stocks
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
            types.Content(role="model", parts=[types.Part.from_text(text="I understand. I'm ready to help screen stocks using the screen_stocks tool. I'll respond in JSON format for tool calls or final answers.")]),
            types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
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

                    # Provide results back to agent
                    result_message = f"Tool execution result:\n{json.dumps(tool_result, indent=2)}"
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
        logger.info_preview("Last response", response_text, preview_len=500)
        return f"Maximum iterations reached. Unable to complete the task. Last response: {response_text[:500]}"


def run_stock_screening(query: str, model: Optional[str] = None, verbose: bool = True) -> str:
    """
    Convenience function to run stock screening agent with a single query

    Args:
        query: User question about stocks
        model: Optional Gemini model name
        verbose: Print execution details

    Returns:
        Agent's final answer
    """
    agent = StockScreeningAgent(model_name=model)
    return agent.run(query, verbose=verbose)


# Backward compatibility alias
def run_stock_agent(query: str, model: Optional[str] = None, verbose: bool = True) -> str:
    """Deprecated: Use run_stock_screening() instead"""
    return run_stock_screening(query, model, verbose)


if __name__ == "__main__":
    # Example usage
    example_query = (
        "I want you to find five potential stocks which can give me 5% return over next 1 month"
    )

    answer = run_stock_screening(example_query)
    logger.info("Stock screening agent execution completed!")
