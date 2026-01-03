"""
SQL Agent for Portfolio Database Management
Handles natural language to SQL conversion and automated data insertion
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.llm_service import generate_content
from utils.db_service import get_db_service

logger = get_logger("agents.sql_agent")


class SQLAgent:
    """AI-powered agent for SQL generation and database operations"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize SQL agent

        Args:
            model_name: Gemini model tier ('high', 'mid', 'low')
                       Defaults to 'mid' (gemini-2.5-flash)
        """
        self.model_name = model_name or 'mid'
        self.db_service = get_db_service()

        # Schema information for prompts
        self.schema_info = self._get_schema_info()

    def _get_schema_info(self) -> str:
        """Get database schema information for prompts"""
        return """
Database Schema:

portfolios:
  - id (INTEGER PRIMARY KEY)
  - profile (TEXT: 'aggressive' or 'defensive')
  - total_capital (REAL)
  - created_at (TIMESTAMP)
  - timestamp (TEXT: YYYYMMDD_HHMMSS)
  - json_path (TEXT)
  - is_active (BOOLEAN)

stocks:
  - id (INTEGER PRIMARY KEY)
  - portfolio_id (INTEGER FK)
  - name (TEXT)
  - ticker (TEXT)
  - sector (TEXT)
  - entry_price (REAL)
  - allocation_pct (REAL)
  - allocation_amount (REAL)
  - stop_loss_pct (REAL)
  - stop_loss_price (REAL)
  - target_pct (REAL)
  - target_price (REAL)
  - rationale (TEXT)
  - news_sentiment (TEXT)

investment_views:
  - id (INTEGER PRIMARY KEY)
  - stock_id (INTEGER FK)
  - market_outlook (TEXT)
  - stock_rationale (TEXT)
  - holding_period (TEXT)
  - exit_triggers (JSON array)
  - review_triggers (JSON array)

key_metrics:
  - id (INTEGER PRIMARY KEY)
  - stock_id (INTEGER FK)
  - metrics_json (JSON object)

transactions:
  - id (INTEGER PRIMARY KEY)
  - portfolio_id (INTEGER FK)
  - stock_id (INTEGER FK)
  - transaction_type (TEXT: 'BUY' or 'SELL')
  - quantity (INTEGER)
  - price (REAL)
  - total_amount (REAL)
  - transaction_date (TIMESTAMP)

performance_metrics:
  - id (INTEGER PRIMARY KEY)
  - portfolio_id (INTEGER FK)
  - stock_id (INTEGER FK, can be NULL)
  - metric_date (DATE)
  - portfolio_value (REAL)
  - stock_value (REAL)
  - daily_return_pct (REAL)
  - cumulative_return_pct (REAL)
  - status (TEXT: 'HOLDING', 'TARGET_HIT', 'STOP_LOSS_HIT', 'SOLD')

rebalancing_history:
  - id (INTEGER PRIMARY KEY)
  - portfolio_id (INTEGER FK)
  - rebalancing_date (TIMESTAMP)
  - reason (TEXT)
  - action_type (TEXT: 'ADJUSTMENT', 'ROTATION', 'EXIT')
  - affected_stocks (JSON array of tickers)
  - allocation_changes (JSON object)
  - status (TEXT: 'PENDING', 'EXECUTED', 'CANCELLED')

market_events:
  - id (INTEGER PRIMARY KEY)
  - portfolio_id (INTEGER FK, can be NULL)
  - stock_id (INTEGER FK, can be NULL)
  - event_type (TEXT: 'TRIGGER_HIT', 'NEWS', 'EARNINGS', etc)
  - title (TEXT)
  - description (TEXT)
  - impact (TEXT: 'POSITIVE', 'NEGATIVE', 'NEUTRAL')
  - action_taken (TEXT)
  - event_date (TIMESTAMP)
"""

    def generate_insert_from_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        profile: str,
        timestamp: str,
        json_path: Optional[str] = None,
        execute: bool = False
    ) -> Dict[str, Any]:
        """
        Generate INSERT statements from portfolio builder JSON output

        Args:
            portfolio_data: Portfolio dictionary with stocks and metadata
            profile: Investor profile ('aggressive' or 'defensive')
            timestamp: Timestamp string (YYYYMMDD_HHMMSS)
            json_path: Path to JSON file
            execute: Whether to execute the inserts or just generate SQL

        Returns:
            Dictionary with generated SQL and execution results
        """
        logger.separator()
        logger.info("SQL AGENT: Generating INSERT statements from portfolio")
        logger.separator()

        try:
            # Step 1: Save portfolio metadata
            cash_balance = portfolio_data.get('cash_balance', 0.0)
            portfolio_id = self.db_service.save_portfolio(
                portfolio_data,
                profile,
                timestamp,
                json_path,
                cash_balance=cash_balance
            )

            logger.info(f"Saved portfolio metadata (ID: {portfolio_id})")

            # Step 2: Save stocks with related data
            stocks = portfolio_data.get('stocks', [])
            stock_ids = self.db_service.save_stocks(portfolio_id, stocks)

            logger.info(f"Saved {len(stock_ids)} stocks to database")

            result = {
                "action": "insert_success",
                "portfolio_id": portfolio_id,
                "stocks_inserted": len(stock_ids),
                "stock_ids": stock_ids,
                "timestamp": datetime.now().isoformat(),
                "status": "Portfolio data successfully inserted into database"
            }

            logger.separator()
            logger.info("INSERT Generation Successful")
            logger.info(f"Portfolio ID: {portfolio_id}")
            logger.info(f"Stocks Inserted: {len(stock_ids)}")
            logger.separator()

            return result

        except Exception as e:
            logger.error(f"Failed to generate/execute INSERT: {e}")
            return {
                "action": "insert_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def natural_language_to_sql(
        self,
        query: str,
        portfolio_id: Optional[int] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert natural language query to SQL and execute

        Args:
            query: Natural language query
            portfolio_id: Optional portfolio context
            context: Optional additional context for the query

        Returns:
            Dictionary with SQL query and results
        """
        logger.separator()
        logger.info("SQL AGENT: Converting natural language to SQL")
        logger.info(f"Query: {query}")
        if portfolio_id:
            logger.info(f"Portfolio Context: {portfolio_id}")
        logger.separator()

        # Build system prompt
        system_prompt = f"""You are a SQL query expert for a portfolio database.

Your task:
1. Understand the user's natural language query
2. Convert it to a valid SQLite query
3. Return ONLY the SQL query in a JSON response

{self.schema_info}

RESPONSE FORMAT:
{{
  "action": "generate_sql",
  "sql": "SELECT ... FROM ... WHERE ...",
  "explanation": "What this query does"
}}

IMPORTANT:
- Return ONLY valid SQLite syntax
- Use JSON objects/arrays for complex conditions
- For historical queries, use performance_metrics table
- For transaction queries, use transactions table
- For trigger/event queries, use market_events table
- Always order results by date DESC for time-series data
- Use proper table aliases when joining
"""

        if portfolio_id:
            system_prompt += f"\n\nDefault portfolio_id for context: {portfolio_id}"

        if context:
            system_prompt += f"\n\nAdditional context: {context}"

        try:
            # Call Gemini to generate SQL
            response = generate_content(
                contents=system_prompt + f"\n\nUser query: {query}",
                model=self.model_name,
                temperature=0.2,  # Low temperature for deterministic SQL
                verbose=True
            )

            logger.trace("Parsing SQL generation response...")

            # Parse response
            parsed = self._parse_sql_response(response)

            if parsed.get("action") == "generate_sql":
                sql = parsed.get("sql", "")
                explanation = parsed.get("explanation", "")

                logger.info(f"Generated SQL: {sql}")
                logger.info(f"Explanation: {explanation}")

                # Execute query
                try:
                    results = self.db_service.execute_query(sql)

                    logger.info(f"Query executed successfully, {len(results)} rows returned")

                    return {
                        "action": "query_success",
                        "sql": sql,
                        "explanation": explanation,
                        "results": results,
                        "row_count": len(results),
                        "timestamp": datetime.now().isoformat()
                    }

                except Exception as e:
                    logger.error(f"SQL execution error: {e}")
                    logger.warning(f"SQL that failed: {sql}")

                    return {
                        "action": "query_error",
                        "sql": sql,
                        "explanation": explanation,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }

            else:
                logger.error(f"Unexpected response action: {parsed.get('action')}")
                return {
                    "action": "parse_error",
                    "error": "Could not parse SQL generation response",
                    "raw_response": response,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return {
                "action": "generation_error",
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }

    def _parse_sql_response(self, response: str) -> Dict[str, Any]:
        """Parse SQL generation response from Gemini"""
        response = response.strip()

        # Try to extract JSON from code blocks
        if "```json" in response:
            json_part = response.split("```json")[1].split("```")[0].strip()
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass

        elif "```" in response:
            json_part = response.split("```")[1].split("```")[0].strip()
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass

        # Try direct JSON parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Fallback: Look for JSON pattern
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        logger.error("Could not parse response as JSON")
        return {"action": "parse_error", "raw": response}

    def query_portfolio_summary(self, portfolio_id: int) -> Dict[str, Any]:
        """Get summary of a portfolio"""
        logger.info(f"Fetching portfolio summary for portfolio {portfolio_id}")

        try:
            summary = self.db_service.portfolio_summary(portfolio_id)

            return {
                "action": "summary_success",
                "portfolio_id": portfolio_id,
                "data": summary,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {e}")
            return {
                "action": "summary_error",
                "error": str(e),
                "portfolio_id": portfolio_id
            }

    def query_stock_performance(
        self,
        portfolio_id: int,
        ticker: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Query stock performance over time"""
        logger.info(f"Fetching performance history for portfolio {portfolio_id}")

        try:
            # Get stock if ticker provided
            stock_id = None
            if ticker:
                stock = self.db_service.get_stock_by_ticker(ticker, portfolio_id)
                if stock:
                    stock_id = stock['id']
                else:
                    logger.warning(f"Stock not found: {ticker}")

            # Get performance metrics
            from datetime import date, timedelta
            start_date = date.today() - timedelta(days=days)
            performance = self.db_service.get_performance_history(
                portfolio_id,
                stock_id=stock_id,
                start_date=start_date
            )

            return {
                "action": "performance_success",
                "portfolio_id": portfolio_id,
                "stock_id": stock_id,
                "ticker": ticker,
                "period_days": days,
                "records": performance,
                "record_count": len(performance),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get performance history: {e}")
            return {
                "action": "performance_error",
                "error": str(e),
                "portfolio_id": portfolio_id
            }

    def query_trigger_hits(
        self,
        portfolio_id: int,
        trigger_type: str = "TRIGGER_HIT",  # stop-loss or target hit
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query stocks that have hit stop-loss or target"""
        logger.info(f"Fetching trigger hits for portfolio {portfolio_id}")

        try:
            events = self.db_service.get_market_events(
                portfolio_id=portfolio_id,
                event_type=trigger_type
            )

            # Enrich with stock information
            enriched_events = []
            for event in events:
                if event.get('stock_id'):
                    stock = self.db_service.db_path  # Get stock details
                enriched_events.append(event)

            return {
                "action": "triggers_success",
                "portfolio_id": portfolio_id,
                "trigger_type": trigger_type,
                "triggers": enriched_events,
                "trigger_count": len(enriched_events),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get trigger hits: {e}")
            return {
                "action": "triggers_error",
                "error": str(e),
                "portfolio_id": portfolio_id
            }

    def record_market_event_from_manager(
        self,
        portfolio_id: int,
        event_type: str,
        title: str,
        description: str,
        impact: str,
        stock_ticker: Optional[str] = None,
        action_taken: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a market event from portfolio manager"""
        logger.info(f"Recording market event for portfolio {portfolio_id}")

        try:
            stock_id = None
            if stock_ticker:
                stock = self.db_service.get_stock_by_ticker(stock_ticker, portfolio_id)
                if stock:
                    stock_id = stock['id']

            event_id = self.db_service.record_market_event(
                event_type=event_type,
                title=title,
                description=description,
                event_date=datetime.now(),
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                impact=impact,
                action_taken=action_taken,
                source="portfolio_manager"
            )

            logger.info(f"Recorded market event {event_id}")

            return {
                "action": "event_recorded",
                "event_id": event_id,
                "portfolio_id": portfolio_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to record market event: {e}")
            return {
                "action": "event_error",
                "error": str(e),
                "portfolio_id": portfolio_id
            }


def run_sql_agent(
    query: str,
    portfolio_id: Optional[int] = None,
    mode: str = "query"  # 'query' or 'insert'
) -> Dict[str, Any]:
    """Convenience function to run SQL agent"""
    agent = SQLAgent()

    if mode == "query":
        return agent.natural_language_to_sql(query, portfolio_id)
    elif mode == "insert":
        # This expects portfolio_data to be passed as query
        # For direct use, prefer using agent.generate_insert_from_portfolio()
        logger.warning("Use agent.generate_insert_from_portfolio() for INSERT mode")
        return {"error": "Invalid mode usage"}
    else:
        return {"error": f"Unknown mode: {mode}"}


if __name__ == "__main__":
    # Example usage
    agent = SQLAgent()

    # Example: Query portfolio summary
    print("SQL Agent Initialized")
    print("=" * 70)

    # Natural language query example
    result = agent.natural_language_to_sql(
        "Show me all stocks in my portfolio with allocation greater than 10%",
        portfolio_id=1
    )

    print(json.dumps(result, indent=2))
