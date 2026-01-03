"""
Portfolio Builder Super Agent - DEPRECATED
Orchestrates stock_agent and news_agent to build investment portfolios

DEPRECATION NOTICE:
This module is no longer actively maintained. Use portfolio_builder_agent_simple.py instead.
The simple version provides the same functionality with better flexibility and cleaner implementation.

To migrate:
  from agents.portfolio_builder_agent_simple import build_simple_portfolio
  portfolio = build_simple_portfolio(investor_profile="aggressive", capital=500000)
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
from utils.llm_service import generate_content

# Load environment variables
load_dotenv()


class PortfolioBuilderAgent:
    """Super agent that builds portfolios using stock screening and news analysis"""

    def __init__(self, config_path: str = "config.ini", model_name: Optional[str] = None):
        """
        Initialize the portfolio builder agent

        Args:
            config_path: Path to configuration file
            model_name: Gemini model to use (defaults to GEMINI_MID_MODEL from .env)
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

        # Store model name for orchestration (defaults to 'mid' if not specified)
        # Can be overridden by GEMINI_TEST_MODEL environment variable for testing
        self.model_name = model_name or 'mid'

        # Cache directory for agent results
        self.cache_dir = Path(__file__).parent.parent / ".cache"
        self.cache_dir.mkdir(exist_ok=True)

        # Result cache
        self._agent_cache = {}

        # State tracking
        self._state_file = None
        self._iteration_results = []

    def _create_system_prompt(self, investor_profile: str, capital: float) -> str:
        """Create system prompt for portfolio building orchestration"""
        return f"""You are a portfolio building orchestrator agent. Your job is to coordinate two specialized agents to build an investment portfolio.

INVESTOR PROFILE: {investor_profile.upper()}
INITIAL CAPITAL: Rs. {capital:,.0f}
MAX STOCKS IN PORTFOLIO: {self.max_stocks}

YOU HAVE ACCESS TO THREE AGENTS:

1. STOCK_AGENT: Screens stocks from screener.in using 335+ financial ratios
   - Can find stocks based on fundamental criteria
   - Returns stock data with financials, ratios, valuations

2. NEWS_AGENT: Analyzes recent news and sentiment for specific stocks
   - Can search Google News for specific stocks
   - Provides news summary, trends, and sentiment analysis

3. RESEARCH_AGENT: Analyzes Indian market, sectors, and economic trends
   - Can research overall market conditions, sector performance
   - Provides macro-economic insights, policy impacts, sector trends
   - Use for understanding market context before stock selection

YOUR WORKFLOW:
1. Understand the investor profile ({investor_profile}) and what it means:
   - AGGRESSIVE: Higher risk tolerance, seeking growth and higher returns
   - DEFENSIVE: Lower risk tolerance, seeking stability and capital preservation

2. (Optional) Use RESEARCH_AGENT to understand current market context:
   - Ask about overall Indian market trends, sector performance, economic indicators
   - Example: "What are the key trends in Indian market this month?"
   - Use insights to identify promising sectors or understand market conditions
   - This step is optional but recommended for better portfolio alignment

3. Use STOCK_AGENT to find candidate stocks:
   - Ask the stock_agent natural language questions about finding stocks suitable for the profile
   - The stock_agent will autonomously decide screening criteria, ratios, and thresholds
   - Example: "Find 5-7 stocks suitable for an aggressive growth investor"
   - Let the stock_agent handle column selection and query optimization
   - If results are not satisfactory, ask the stock_agent to refine or try different approaches
   - Consider using research_agent insights to guide stock selection (e.g., focus on sectors identified as promising)

HANDLING STOCK_AGENT RESULTS:
   - Stock agent uses automatic result management for large datasets
   - Check response fields:
     * "is_sampled": If true, results were large and sampled
     * "stored_count": Total stocks found
     * "sample_stocks": Stocks provided for analysis
     * "analysis_summary": Statistical insights from coding agent
     * "analysis_suggestions": Data-driven refinement ideas

   - If is_sampled=true:
     * You're working with a sample (e.g., 30 out of 169 stocks)
     * Full data is stored, but focus on the sample provided
     * Review analysis_summary for patterns and insights
     * Use analysis_suggestions if you need to guide stock_agent to refine

   - Your options:
     * Proceed with sample if it looks good for portfolio selection
     * Ask stock_agent to refine query (provide specific criteria based on analysis)
     * Request different approach if sample doesn't fit profile

4. Use NEWS_AGENT to validate shortlisted stocks:
   - For each promising stock from stock_agent results, ask news_agent for recent news
   - Example: "Check recent news and sentiment for [Stock Name] in the last week"
   - Let news_agent decide which news sources and analysis methods to use
   - Look for red flags or positive catalysts

5. Select final {self.max_stocks} stocks based on:
   - Fundamental strength (from stock_agent analysis)
   - News sentiment and market developments (from news_agent)
   - Sector diversification
   - Market context (from research_agent if used)
   - Your own reasoning about fit with investor profile

6. Allocate capital:
   - Use your judgment to allocate based on conviction and profile
   - AGGRESSIVE profiles may favor concentrated positions in top picks
   - DEFENSIVE profiles may favor more balanced allocation

7. Return final portfolio with complete rationale

OUTPUT FORMAT FOR CALLING AGENTS:
{{
  "action": "call_agent",
  "agent": "stock_agent" or "news_agent" or "research_agent",
  "query": "detailed query for the agent"
}}

OUTPUT FORMAT FOR FINAL PORTFOLIO:
{{
  "action": "final_portfolio",
  "portfolio": {{
    "profile": "{investor_profile}",
    "total_capital": {capital},
    "stocks": [
      {{
        "name": "Stock Name",
        "ticker": "SYMBOL",
        "allocation_pct": 33.33,
        "allocation_amount": 166666.67,
        "rationale": "Why this stock was selected",
        "key_metrics": {{"PE": 15.5, "ROE": 18.5}},
        "news_sentiment": "Positive/Neutral/Negative",
        "sector": "Technology"
      }}
    ],
    "diversification": "Sector diversification summary",
    "risk_assessment": "Overall portfolio risk assessment"
  }}
}}

Be systematic, thorough, and data-driven. Always validate with news before finalizing."""

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
                        print("[ORCHESTRATOR] Used json_repair to fix JSON in code block")
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
                        print("[ORCHESTRATOR] Used json_repair to fix JSON in code block")
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
                    print("[ORCHESTRATOR] Used json_repair to fix full response")
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
                                    print("[ORCHESTRATOR] Used json_repair to fix extracted JSON")
                                    return data
                            except:
                                pass

                    start = action_start + 1

            # Step 4: Check if response contains portfolio keywords
            if any(keyword in response_text.lower() for keyword in ["rationale for selection", "portfolio", "stocks", "allocation"]):
                print("[ORCHESTRATOR] Response appears to be final portfolio in text format")
                print("[ORCHESTRATOR] Prompting for structured JSON response...")

                return {
                    "action": "needs_json_format",
                    "raw_response": original_text
                }

        except Exception as e:
            print(f"[DEBUG] JSON extraction error: {e}")

        # Step 5: Final fallback
        print(f"[ERROR] Could not extract valid JSON from response")
        print(f"[ERROR] Response preview: {response_text[:300]}")
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
            print(f"\n[PORTFOLIO BUILDER] Using cached STOCK_AGENT result")
            return self._agent_cache[cache_key]

        print(f"\n{'='*70}")
        print(f"[PORTFOLIO BUILDER -> STOCK_AGENT] Calling agent")
        print(f"Query sent to Stock Agent:")
        print(f"  {query}")
        print(f"{'='*70}")

        result = self.stock_agent.run(query, verbose=False)

        print(f"\n{'='*70}")
        print(f"[PORTFOLIO BUILDER <- STOCK_AGENT] Agent completed")
        print(f"Result preview: {str(result)[:200]}...")
        print(f"{'='*70}\n")

        # Cache result
        result_dict = {"result": result}
        self._agent_cache[cache_key] = result_dict

        return result_dict

    def _call_news_agent(self, query: str) -> Dict[str, Any]:
        """Call news analysis agent with caching"""
        cache_key = self._get_cache_key("news_agent", query)

        # Check cache first
        if cache_key in self._agent_cache:
            print(f"\n[PORTFOLIO BUILDER] Using cached NEWS_AGENT result")
            return self._agent_cache[cache_key]

        print(f"\n{'='*70}")
        print(f"[PORTFOLIO BUILDER -> NEWS_AGENT] Calling agent")
        print(f"Query sent to News Agent:")
        print(f"  {query}")
        print(f"{'='*70}")

        result = self.news_agent.run(query, verbose=False)

        print(f"\n{'='*70}")
        print(f"[PORTFOLIO BUILDER <- NEWS_AGENT] Agent completed")
        print(f"Result preview: {str(result)[:200]}...")
        print(f"{'='*70}\n")

        # Cache result
        result_dict = {"result": result}
        self._agent_cache[cache_key] = result_dict

        return result_dict

    def _call_research_agent(self, query: str) -> Dict[str, Any]:
        """Call market research agent with caching"""
        cache_key = self._get_cache_key("research_agent", query)

        # Check cache first
        if cache_key in self._agent_cache:
            print(f"\n[PORTFOLIO BUILDER] Using cached RESEARCH_AGENT result")
            return self._agent_cache[cache_key]

        print(f"\n{'='*70}")
        print(f"[PORTFOLIO BUILDER -> RESEARCH_AGENT] Calling agent")
        print(f"Query sent to Research Agent:")
        print(f"  {query}")
        print(f"{'='*70}")

        result = self.research_agent.run(query, verbose=False)

        print(f"\n{'='*70}")
        print(f"[PORTFOLIO BUILDER <- RESEARCH_AGENT] Agent completed")
        print(f"Result preview: {str(result)[:200]}...")
        print(f"{'='*70}\n")

        # Cache result
        result_dict = {"result": result}
        self._agent_cache[cache_key] = result_dict

        return result_dict

    def _save_state(self, profile: str, capital: float, iteration: int, conversation: list):
        """Save current state to file"""
        if not self._state_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._state_file = self.cache_dir / f"portfolio_state_{profile}_{timestamp}.json"

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

    def build_portfolio(
        self,
        investor_profile: Optional[str] = None,
        capital: Optional[float] = None,
        max_iterations: int = 15,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Build investment portfolio using sub-agents

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

        if profile not in ['aggressive', 'moderate', 'defensive']:
            raise ValueError("investor_profile must be 'aggressive', 'moderate', or 'defensive'")

        if verbose:
            print(f"\n{'='*70}")
            print(f"PORTFOLIO BUILDER AGENT")
            print(f"{'='*70}")
            print(f"Investor Profile: {profile.upper()}")
            print(f"Initial Capital: Rs. {capital:,.0f}")
            print(f"Max Stocks: {self.max_stocks}")
            print(f"{'='*70}\n")

        # Initialize conversation
        conversation = [
            types.Content(role="user", parts=[types.Part.from_text(text=self._create_system_prompt(profile, capital))]),
            types.Content(role="model", parts=[types.Part.from_text(text=f"I understand. I will build a {profile} portfolio with Rs. {capital:,.0f} by coordinating stock_agent and news_agent. I'll respond in JSON format.")]),
            types.Content(role="user", parts=[types.Part.from_text(text=f"Build a {profile} portfolio with {self.max_stocks} stocks for Rs. {capital:,.0f}. Start by screening stocks.")])
        ]

        iteration = 0
        while iteration < max_iterations:
            time.sleep(3)
            iteration += 1

            if verbose:
                print(f"\n{'='*70}")
                print(f"ITERATION {iteration}")
                print(f"{'='*70}")

            # Get orchestrator response with retry logic
            max_retries = 3
            retry_count = 0
            response_text = None

            while retry_count < max_retries:
                try:
                    if verbose:
                        print(f"\n[ORCHESTRATOR] Calling Gemini API (iteration {iteration}, attempt {retry_count + 1}/{max_retries})...")

                    response_text = generate_content(
                        contents=conversation,
                        model=self.model_name,
                        temperature=0.7,
                        verbose=verbose,
                        max_retries=1  # Let orchestrator handle retries
                    )

                    if verbose:
                        print(f"[ORCHESTRATOR] Received response ({len(response_text)} chars)")
                        print(f"[ORCHESTRATOR] Planning: {response_text[:300]}...")
                    break  # Success, exit retry loop

                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)

                    if "503" in error_msg or "overloaded" in error_msg.lower():
                        if retry_count < max_retries:
                            wait_time = 5 * retry_count  # Exponential backoff: 5s, 10s, 15s
                            print(f"[WARNING] API overloaded. Retrying in {wait_time}s... (attempt {retry_count}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            print(f"[ERROR] Max retries reached. Saving state and exiting...")
                            self._save_state(profile, capital, iteration, conversation)
                            print(f"[INFO] State saved to: {self._state_file}")
                            return {"error": f"API overloaded after {max_retries} retries. State saved for resume.", "state_file": str(self._state_file)}
                    else:
                        print(f"[ERROR] Orchestrator failed: {e}")
                        self._save_state(profile, capital, iteration, conversation)
                        return {"error": str(e), "state_file": str(self._state_file)}

            if response_text is None:
                return {"error": "Failed to get response after retries"}

            # Parse response
            if verbose:
                print(f"[ORCHESTRATOR] Parsing response...")
            parsed = self._parse_response(response_text)
            action = parsed.get("action")
            if verbose:
                print(f"[ORCHESTRATOR] Parsed action: {action}")

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
                    print(f"\n{'='*70}")
                    print("FINAL PORTFOLIO")
                    print(f"{'='*70}")
                    if "error" in portfolio:
                        print(f"Error: {portfolio.get('error')}")
                        print(f"Raw response preview: {portfolio.get('raw', '')[:500]}")
                    else:
                        print(json.dumps(portfolio, indent=2))
                    print(f"{'='*70}\n")

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
                        print(f"[ORCHESTRATOR] Agent call completed")

                except Exception as e:
                    error_msg = f"Agent call failed: {str(e)}"
                    conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=error_msg)]))

                    if verbose:
                        print(f"[ERROR] {error_msg}")

            elif action == "needs_json_format":
                # Response contains portfolio info but not in JSON format
                # Ask the model to reformat it
                if verbose:
                    print(f"[ORCHESTRATOR] Requesting JSON format for portfolio...")

                conversation.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

                prompt = """Please provide your portfolio response in the exact JSON format specified:
{
  "action": "final_portfolio",
  "portfolio": {
    "profile": "...",
    "total_capital": ...,
    "stocks": [...],
    "diversification": "...",
    "risk_assessment": "..."
  }
}

Make sure to include all required fields and use valid JSON syntax."""

                conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

            elif action == "parse_error":
                # Could not parse response at all
                if verbose:
                    print(f"[ERROR] Failed to parse response. Prompting for clarification...")

                conversation.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

                prompt = """I couldn't parse your response. Please provide your next action in one of these JSON formats:

For calling an agent:
{
  "action": "call_agent",
  "agent": "stock_agent" or "news_agent",
  "query": "your query here"
}

For final portfolio:
{
  "action": "final_portfolio",
  "portfolio": {
    "profile": "...",
    "total_capital": ...,
    "stocks": [...],
    "diversification": "...",
    "risk_assessment": "..."
  }
}"""

                conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

            else:
                if verbose:
                    print(f"[WARNING] Unknown action: {action}")
                    print("Treating as final portfolio...")

                return {"error": "Invalid response format", "raw": response_text}

        return {"error": "Maximum iterations reached", "iterations": max_iterations}


def build_portfolio(
    investor_profile: Optional[str] = None,
    capital: Optional[float] = None,
    config_path: str = "config.ini",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to build portfolio

    Args:
        investor_profile: 'aggressive' or 'defensive'
        capital: Initial capital in INR
        config_path: Path to config file
        verbose: Print execution details

    Returns:
        Portfolio dictionary
    """
    agent = PortfolioBuilderAgent(config_path=config_path)
    return agent.build_portfolio(investor_profile=investor_profile, capital=capital, verbose=verbose)


if __name__ == "__main__":
    # Example usage
    print("Building AGGRESSIVE portfolio with Rs. 5,00,000...")
    portfolio = build_portfolio(investor_profile="aggressive", capital=500000)

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
