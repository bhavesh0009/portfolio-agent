"""
Portfolio Builder Agent - Simplified Version
Experimental agent with minimal prompting for more flexible portfolio building
"""

import os
import json
import time
import configparser
import hashlib
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from datetime import datetime
from json_repair import repair_json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_screening_agent import StockScreeningAgent
from agents.stock_news_agent import StockNewsAgent
from agents.market_research_agent import MarketResearchAgent
from utils.logger import get_logger
from utils.llm_service import generate_content
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger("agents.portfolio_builder_agent_simple")


class SimplePortfolioBuilderAgent:
    """Simplified portfolio builder with minimal prompting for maximum flexibility"""

    def __init__(self, config_path: str = "config.ini", model_name: Optional[str] = None):
        """
        Initialize the simplified portfolio builder agent

        Args:
            config_path: Path to configuration file
            model_name: Gemini model tier ('high', 'mid', 'low') or specific model name
                       Defaults to 'high' (gemini-2.5-pro) for complex portfolio reasoning
        """
        # Load configuration
        self.config = configparser.ConfigParser()
        config_file = Path(__file__).parent.parent / config_path
        self.config.read(config_file)

        # Portfolio settings
        self.max_stocks = int(self.config.get('PORTFOLIO', 'max_stocks', fallback='3'))
        self.initial_capital = float(self.config.get('PORTFOLIO', 'initial_capital', fallback='500000'))
        self.default_profile = self.config.get('PORTFOLIO', 'investor_profile', fallback='aggressive')

        # News settings
        self.news_lookback = self.config.get('NEWS', 'news_lookback_period', fallback='7d')
        self.check_news = self.config.getboolean('NEWS', 'check_news_for_shortlisted', fallback=True)

        # Initialize sub-agents
        self.stock_agent = StockScreeningAgent(model_name=model_name)
        self.news_agent = StockNewsAgent(model_name=model_name)
        self.research_agent = MarketResearchAgent(model_name=model_name)

        # Store model name for orchestration
        # Defaults to 'high' (GEMINI_HIGH_MODEL) for complex portfolio reasoning
        # Can be overridden by GEMINI_TEST_MODEL environment variable for testing
        self.model_name = model_name or 'high'

        # Cache directory for agent results
        self.cache_dir = Path(__file__).parent.parent / ".cache"
        self.cache_dir.mkdir(exist_ok=True)

        # Result cache
        self._agent_cache = {}

        # State tracking
        self._state_file = None
        self._iteration_results = []

    def _create_system_prompt(self, investor_profile: str, capital: float) -> str:
        """Create minimal system prompt for maximum flexibility"""
        screening_target = self.max_stocks * 2  # Request double for more selection flexibility
        return f"""You are a portfolio building orchestrator. Build an investment portfolio matching the investor profile using available tools.

INVESTOR PROFILE: {investor_profile.upper()}
CAPITAL: Rs. {capital:,.0f}
TARGET: {self.max_stocks} stocks (screen {screening_target} candidates first, then shortlist to best {self.max_stocks})

AVAILABLE TOOLS:

stock_agent - Screens stocks from screener.in using 335+ financial ratios and metrics
news_agent - Analyzes recent news and market sentiment for stocks
research_agent - Researches Indian market trends, sectors, and economic indicators

OBJECTIVE:
Build a well-researched portfolio that matches the investor profile. Use your judgment to:
- Find fundamentally strong stocks suitable for the profile
- Validate selections with recent news and sentiment
- Allocate capital based on conviction and risk profile
- Ensure reasonable diversification

Think independently about:
- Which stocks to research and why
- When to use each tool and how to query them
- How to interpret and combine fundamental + sentiment analysis
- Optimal allocation strategy for the profile

TOOL USAGE:
To call a tool, respond with:
{{
  "action": "call_agent",
  "agent": "stock_agent" or "news_agent" or "research_agent",
  "query": "your natural language query"
}}

SYMBOL AND EXCHANGE EXTRACTION:
CRITICAL: Screening results now include 'Symbol' and 'Exchange' fields for each stock.
- ALWAYS use the EXACT 'Symbol' value from screening results for the 'ticker' field
- DO NOT abbreviate or guess ticker symbols (e.g., use "WAAREEENER", NOT "WAREE")
- The Symbol field contains the correct NSE/BSE symbol required for price tracking
- If Symbol is missing or "Unknown", flag this stock for manual review

STOP-LOSS AND TARGET CALCULATION:
For each stock, determine:
- entry_price: Current Market Price (CMP) from screening results (e.g., from key_metrics)
- stop_loss_pct: Based on investor profile (aggressive: 15%, defensive: 8%)
- stop_loss_price: entry_price * (1 - stop_loss_pct/100)
- target_pct: Based on investor profile and growth metrics (aggressive: 40-60%, defensive: 15-25%)
- target_price: entry_price * (1 + target_pct/100)

INVESTMENT VIEW GUIDANCE:
For each stock, create a comprehensive view with:
- market_outlook: Your view on Indian market conditions at time of selection
- stock_rationale: Why this stock fits the investor profile and current market opportunity
- holding_period: Recommended duration (e.g., "6-12 months", "Long-term 2+ years")
- exit_triggers: List of 2-3 conditions that would invalidate investment thesis
- review_triggers: List of 2-3 conditions requiring portfolio reassessment

FINAL OUTPUT:
When ready, return your portfolio with this structure:
{{
  "action": "final_portfolio",
  "portfolio": {{
    "stocks": [
      {{
        "name": "Stock Name",
        "ticker": "EXACT_SYMBOL_FROM_SCREENING",
        "exchange": "NSE or BSE from screening results",
        "entry_price": float,
        "allocation_pct": float,
        "allocation_amount": float,
        "stop_loss_pct": float,
        "stop_loss_price": float,
        "target_pct": float,
        "target_price": float,
        "investment_view": {{
          "market_outlook": "string",
          "stock_rationale": "string",
          "holding_period": "string",
          "exit_triggers": ["trigger1", "trigger2"],
          "review_triggers": ["trigger1", "trigger2"]
        }},
        "rationale": "selection reasoning",
        "key_metrics": {{}},
        "news_sentiment": "summary",
        "sector": "sector"
      }}
    ],
    "diversification": "brief summary",
    "risk_assessment": "brief assessment"
  }}
}}

Trust your analysis. Be thorough but efficient."""

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse orchestrator response, extracting JSON from text if needed"""
        original_text = response_text
        response_text = response_text.strip()

        # Step 1: Handle markdown code blocks
        if "```json" in response_text:
            parts = response_text.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0].strip()
                try:
                    data = json.loads(json_part)
                    return data
                except json.JSONDecodeError:
                    # Try json_repair
                    try:
                        repaired = repair_json(json_part)
                        data = json.loads(repaired)
                        logger.debug("Used json_repair to fix JSON in code block")
                        return data
                    except:
                        pass
        elif "```" in response_text:
            parts = response_text.split("```")
            if len(parts) > 1:
                json_part = parts[1].strip()
                try:
                    data = json.loads(json_part)
                    return data
                except json.JSONDecodeError:
                    try:
                        repaired = repair_json(json_part)
                        data = json.loads(repaired)
                        logger.debug("Used json_repair to fix JSON in code block")
                        return data
                    except:
                        pass

        # Step 2: Try direct JSON parse
        try:
            data = json.loads(response_text)
            return data
        except json.JSONDecodeError:
            # Try json_repair on full response
            try:
                repaired = repair_json(response_text)
                data = json.loads(repaired)
                if "action" in data:
                    logger.debug("Used json_repair to fix full response")
                    return data
            except:
                pass

        # Step 3: Extract JSON from text with {"action" pattern
        try:
            search_patterns = ['{"action"', "{'action'"]
            for pattern in search_patterns:
                start = 0
                while True:
                    action_start = response_text.find(pattern, start)
                    if action_start == -1:
                        break

                    # Extract from action_start, balancing braces
                    remaining = response_text[action_start:]
                    brace_count = 0
                    end_idx = -1

                    for i, char in enumerate(remaining):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break

                    if end_idx > 0:
                        json_str = remaining[:end_idx]
                        # Try direct parse
                        try:
                            data = json.loads(json_str)
                            if "action" in data:
                                return data
                        except json.JSONDecodeError:
                            # Try json_repair
                            try:
                                repaired = repair_json(json_str)
                                data = json.loads(repaired)
                                if "action" in data:
                                    logger.debug("Used json_repair to fix extracted JSON")
                                    return data
                            except:
                                pass

                    start = action_start + 1

            # Step 4: Check if response contains portfolio keywords
            if any(keyword in response_text.lower() for keyword in ["rationale for selection", "portfolio", "stocks", "allocation"]):
                logger.info("Response appears to be final portfolio in text format")
                logger.info("Prompting for structured JSON response...")

                return {
                    "action": "needs_json_format",
                    "raw_response": original_text
                }

        except Exception as e:
            logger.debug(f"JSON extraction error: {e}")

        # Step 5: Final fallback
        logger.error("Could not extract valid JSON from response")
        logger.info_preview("Response", response_text, preview_len=300, level="error")
        return {
            "action": "parse_error",
            "portfolio": {"error": "Failed to parse response", "raw": response_text[:500] + "..."}
        }

    def _get_cache_key(self, agent: str, query: str) -> str:
        """Generate cache key for agent query"""
        content = f"{agent}:{query}"
        return hashlib.md5(content.encode()).hexdigest()

    def _call_stock_agent(self, query: str) -> Dict[str, Any]:
        """Call stock screening agent with caching"""
        cache_key = self._get_cache_key("stock_agent", query)

        # Check cache first
        if cache_key in self._agent_cache:
            logger.info("Using cached STOCK_AGENT result")
            return self._agent_cache[cache_key]

        logger.separator()
        logger.info("[SIMPLE PORTFOLIO BUILDER -> STOCK_AGENT] Calling agent")
        logger.info(f"Query sent to Stock Agent: {query}")
        logger.separator()

        result = self.stock_agent.run(query, verbose=True)

        logger.separator()
        logger.info("[SIMPLE PORTFOLIO BUILDER <- STOCK_AGENT] Agent completed")
        logger.info_preview("Result", str(result), preview_len=200)
        logger.separator()

        # Cache result
        result_dict = {"result": result}
        self._agent_cache[cache_key] = result_dict

        return result_dict

    def _call_news_agent(self, query: str) -> Dict[str, Any]:
        """Call news analysis agent with caching"""
        cache_key = self._get_cache_key("news_agent", query)

        # Check cache first
        if cache_key in self._agent_cache:
            logger.info("Using cached NEWS_AGENT result")
            return self._agent_cache[cache_key]

        logger.separator()
        logger.info("[SIMPLE PORTFOLIO BUILDER -> NEWS_AGENT] Calling agent")
        logger.info(f"Query sent to News Agent: {query}")
        logger.separator()

        result = self.news_agent.run(query, verbose=True)

        logger.separator()
        logger.info("[SIMPLE PORTFOLIO BUILDER <- NEWS_AGENT] Agent completed")
        logger.info_preview("Result", str(result), preview_len=200)
        logger.separator()

        # Cache result
        result_dict = {"result": result}
        self._agent_cache[cache_key] = result_dict

        return result_dict

    def _call_research_agent(self, query: str) -> Dict[str, Any]:
        """Call market research agent with caching"""
        cache_key = self._get_cache_key("research_agent", query)

        # Check cache first
        if cache_key in self._agent_cache:
            logger.info("Using cached RESEARCH_AGENT result")
            return self._agent_cache[cache_key]

        logger.separator()
        logger.info("[SIMPLE PORTFOLIO BUILDER -> RESEARCH_AGENT] Calling agent")
        logger.info(f"Query sent to Research Agent: {query}")
        logger.separator()

        result = self.research_agent.run(query, verbose=True)

        logger.separator()
        logger.info("[SIMPLE PORTFOLIO BUILDER <- RESEARCH_AGENT] Agent completed")
        logger.info_preview("Result", str(result), preview_len=200)
        logger.separator()

        # Cache result
        result_dict = {"result": result}
        self._agent_cache[cache_key] = result_dict

        return result_dict

    def _save_state(self, profile: str, capital: float, iteration: int, conversation: list):
        """Save current state to file"""
        if not self._state_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._state_file = self.cache_dir / f"simple_portfolio_state_{profile}_{timestamp}.json"

        state = {
            "profile": profile,
            "capital": capital,
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "agent_cache": self._agent_cache,
            "iteration_results": self._iteration_results
        }

        with open(self._state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _save_final_portfolio(self, portfolio: Dict[str, Any], profile: str) -> str:
        """Save final portfolio to persistent storage for portfolio manager

        Args:
            portfolio: Final portfolio dictionary with stocks and guidance
            profile: Investor profile (aggressive/defensive)

        Returns:
            Path to saved portfolio file
        """
        # Validate symbols before saving
        from tools.symbol_validator import validate_portfolio_symbols, print_validation_report

        stocks = portfolio.get('stocks', [])
        if stocks:
            logger.info("[SYMBOL VALIDATION] Validating portfolio symbols before saving")
            validation_report = validate_portfolio_symbols(stocks)

            # Log validation results
            if validation_report['invalid'] > 0:
                logger.warning(f"Found {validation_report['invalid']} invalid symbols in portfolio")
                logger.warning("These stocks will use fallback pricing (entry price)")
                logger.warning("Consider reviewing symbols manually or re-screening these stocks")

                # Print detailed report
                print_validation_report(validation_report)
            else:
                logger.info(f"All {validation_report['valid']} symbols validated successfully!")

        # Create portfolios directory if it doesn't exist
        portfolios_dir = self.cache_dir / "portfolios"
        portfolios_dir.mkdir(exist_ok=True)

        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        portfolio_file = portfolios_dir / f"portfolio_{profile}_{timestamp}.json"

        # Prepare portfolio data with metadata
        portfolio_data = {
            "metadata": {
                "profile": profile,
                "created_at": datetime.now().isoformat(),
                "total_capital": portfolio.get("total_capital", self.initial_capital),
                "timestamp": timestamp
            },
            "portfolio": portfolio
        }

        # Save timestamped portfolio
        with open(portfolio_file, 'w') as f:
            json.dump(portfolio_data, f, indent=2)

        logger.info(f"Final portfolio saved to: {portfolio_file}")

        # Update latest portfolio pointer
        latest_file = portfolios_dir / f"latest_{profile}.json"
        with open(latest_file, 'w') as f:
            json.dump(portfolio_data, f, indent=2)

        logger.info(f"Latest portfolio pointer updated: {latest_file}")

        # Save to SQLite database via SQL Agent
        try:
            from agents.sql_agent import SQLAgent
            sql_agent = SQLAgent(model_name=self.model_name)

            db_result = sql_agent.generate_insert_from_portfolio(
                portfolio_data=portfolio,
                profile=profile,
                timestamp=timestamp,
                json_path=str(portfolio_file),
                execute=True
            )

            if db_result.get("action") == "insert_success":
                logger.info(f"Portfolio saved to database with ID: {db_result.get('portfolio_id')}")
            else:
                logger.warning(f"Database save partially completed: {db_result.get('status', 'Unknown')}")

        except Exception as e:
            logger.warning(f"Database save failed (JSON saved successfully): {e}")
            logger.debug("Portfolio will still be available from JSON files")

        return str(portfolio_file)

    def build_portfolio(
        self,
        investor_profile: Optional[str] = None,
        capital: Optional[float] = None,
        max_iterations: int = 15,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Build investment portfolio using sub-agents with minimal prompting

        Args:
            investor_profile: 'aggressive' or 'defensive' (default from config)
            capital: Initial capital in INR (default from config)
            max_iterations: Maximum orchestration iterations
            verbose: Print detailed execution steps

        Returns:
            Portfolio dictionary with stock selections and allocations
        """
        # Use defaults if not provided
        profile = (investor_profile or self.default_profile).lower()
        capital = capital or self.initial_capital

        if profile not in ['aggressive', 'defensive']:
            raise ValueError("investor_profile must be 'aggressive' or 'defensive'")

        if verbose:
            logger.separator()
            logger.info("SIMPLE PORTFOLIO BUILDER AGENT")
            logger.separator()
            logger.info(f"Investor Profile: {profile.upper()}")
            logger.info(f"Initial Capital: Rs. {capital:,.0f}")
            logger.info(f"Max Stocks: {self.max_stocks}")
            logger.separator()

        # Initialize conversation with minimal prompt
        conversation = [
            types.Content(role="user", parts=[types.Part.from_text(text=self._create_system_prompt(profile, capital))]),
            types.Content(role="model", parts=[types.Part.from_text(text=f"I understand. I will build a {profile} portfolio using stock_agent and news_agent. I'll respond in JSON format.")]),
            types.Content(role="user", parts=[types.Part.from_text(text=f"Build the portfolio. Start your research.")])
        ]

        iteration = 0
        while iteration < max_iterations:
            time.sleep(3)
            iteration += 1

            if verbose:
                logger.separator()
                logger.info(f"ITERATION {iteration}")
                logger.separator()

            # Get orchestrator response with retry logic
            max_retries = 3
            retry_count = 0
            response_text = None

            while retry_count < max_retries:
                try:
                    if verbose:
                        logger.trace(f"Calling Gemini API (iteration {iteration}, attempt {retry_count + 1}/{max_retries})...")

                    response_text = generate_content(
                        contents=conversation,
                        model=self.model_name,
                        temperature=0.7,
                        verbose=verbose,
                        max_retries=1  # Let orchestrator handle retries
                    )

                    if verbose:
                        logger.trace(f"Received response ({len(response_text)} chars)")
                        logger.info_preview("Planning", response_text, preview_len=300)
                    break  # Success, exit retry loop

                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)

                    if "503" in error_msg or "overloaded" in error_msg.lower():
                        if retry_count < max_retries:
                            wait_time = 5 * retry_count  # Exponential backoff
                            logger.warning(f"API overloaded. Retrying in {wait_time}s... (attempt {retry_count}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            logger.error("Max retries reached. Saving state and exiting...")
                            self._save_state(profile, capital, iteration, conversation)
                            logger.info(f"State saved to: {self._state_file}")
                            return {"error": f"API overloaded after {max_retries} retries. State saved for resume.", "state_file": str(self._state_file)}
                    else:
                        logger.error(f"Orchestrator failed: {e}")
                        self._save_state(profile, capital, iteration, conversation)
                        return {"error": str(e), "state_file": str(self._state_file)}

            if response_text is None:
                return {"error": "Failed to get response after retries"}

            # Parse response
            if verbose:
                logger.trace("Parsing response...")
            parsed = self._parse_response(response_text)
            action = parsed.get("action")
            if verbose:
                logger.debug(f"Parsed action: {action}")

            # Check if response contains another agent call within text
            if action == "final_portfolio" and "call_agent" in response_text:
                # Try to extract JSON from the text
                try:
                    start_idx = response_text.rfind("{")
                    if start_idx != -1:
                        json_part = response_text[start_idx:]
                        parsed = json.loads(json_part)
                        action = parsed.get("action")
                except:
                    pass

            if action == "final_portfolio":
                # Portfolio building complete
                portfolio = parsed.get("portfolio", {})

                if verbose:
                    logger.separator()
                    logger.info("FINAL PORTFOLIO")
                    logger.separator()
                    if "error" in portfolio:
                        logger.error(f"Error: {portfolio.get('error')}")
                        logger.info_preview("Raw response", portfolio.get('raw', ''), preview_len=500, level="error")
                    else:
                        logger.info(json.dumps(portfolio, indent=2))
                    logger.separator()

                # Save final portfolio to persistent storage for portfolio manager
                if "error" not in portfolio and "stocks" in portfolio:
                    try:
                        portfolio_path = self._save_final_portfolio(portfolio, profile)
                        if verbose:
                            logger.info(f"Portfolio saved successfully to: {portfolio_path}")
                    except Exception as e:
                        logger.warning(f"Failed to save portfolio: {e}")

                return portfolio

            elif action == "call_agent":
                # Call sub-agent
                agent_name = parsed.get("agent")
                query = parsed.get("query", "")

                try:
                    if agent_name == "stock_agent":
                        agent_result = self._call_stock_agent(query)
                    elif agent_name == "news_agent":
                        agent_result = self._call_news_agent(query)
                    elif agent_name == "research_agent":
                        agent_result = self._call_research_agent(query)
                    else:
                        agent_result = {"error": f"Unknown agent: {agent_name}"}

                    # Add to conversation
                    conversation.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

                    result_message = f"Agent execution result:\n{json.dumps(agent_result, indent=2)}"
                    conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=result_message)]))

                    if verbose:
                        logger.info("Agent call completed")

                except Exception as e:
                    error_msg = f"Agent call failed: {str(e)}"
                    conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=error_msg)]))

                    if verbose:
                        logger.error(error_msg)

            elif action == "needs_json_format":
                # Response contains portfolio info but not in JSON format
                if verbose:
                    logger.info("Requesting JSON format for portfolio...")

                conversation.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

                prompt = """Please provide your portfolio in the exact JSON format specified:
{
  "action": "final_portfolio",
  "portfolio": {
    "stocks": [...],
    "diversification": "...",
    "risk_assessment": "..."
  }
}

Make sure to use valid JSON syntax."""

                conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

            elif action == "parse_error":
                # Could not parse response at all
                if verbose:
                    logger.error("Failed to parse response. Prompting for clarification...")

                conversation.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

                prompt = """I couldn't parse your response. Please provide your next action in JSON format:

For calling an agent:
{
  "action": "call_agent",
  "agent": "stock_agent" or "news_agent" or "research_agent",
  "query": "your query here"
}

For final portfolio:
{
  "action": "final_portfolio",
  "portfolio": {
    "stocks": [...],
    "diversification": "...",
    "risk_assessment": "..."
  }
}"""

                conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

            else:
                if verbose:
                    logger.warning(f"Unknown action: {action}")
                    logger.warning("Treating as final portfolio...")

                return {"error": "Invalid response format", "raw": response_text}

        return {"error": "Maximum iterations reached", "iterations": max_iterations}


def build_simple_portfolio(
    investor_profile: Optional[str] = None,
    capital: Optional[float] = None,
    config_path: str = "config.ini",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to build portfolio with simple agent

    Args:
        investor_profile: 'aggressive' or 'defensive'
        capital: Initial capital in INR
        config_path: Path to config file
        verbose: Print execution details

    Returns:
        Portfolio dictionary
    """
    agent = SimplePortfolioBuilderAgent(config_path=config_path)
    return agent.build_portfolio(investor_profile=investor_profile, capital=capital, verbose=verbose)


if __name__ == "__main__":
    # Example usage
    print("Building AGGRESSIVE portfolio with Rs. 5,00,000 (Simple Agent)...")
    portfolio = build_simple_portfolio(investor_profile="aggressive", capital=500000)

    print("\n" + "="*70)
    print("PORTFOLIO SUMMARY")
    print("="*70)

    if "stocks" in portfolio:
        for stock in portfolio["stocks"]:
            print(f"\n{stock.get('name', 'N/A')} ({stock.get('ticker', 'N/A')})")
            print(f"  Allocation: Rs. {stock.get('allocation_amount', 0):,.0f} ({stock.get('allocation_pct', 0):.1f}%)")
            print(f"  Sector: {stock.get('sector', 'N/A')}")
            print(f"  Sentiment: {stock.get('news_sentiment', 'N/A')}")
    else:
        print("Portfolio building failed or incomplete")
