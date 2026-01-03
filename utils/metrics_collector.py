"""
MetricsCollector - Singleton class for tracking LLM usage metrics and tool execution times.

This module provides centralized metrics collection for:
- LLM token usage (input/output tokens)
- LLM execution time
- Tool execution time
- Cost calculation based on Gemini pricing
- Summary report generation
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """
    Singleton class for collecting and aggregating metrics across agents and tools.

    Tracks:
    - LLM calls: token counts, duration, cost
    - Tool calls: execution time
    - Per-agent/tool aggregation
    - Summary report generation
    """

    _instance: Optional['MetricsCollector'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize metrics collector (only once)."""
        if not MetricsCollector._initialized:
            self.reset()
            self._load_pricing()
            MetricsCollector._initialized = True
            logger.debug("MetricsCollector initialized")

    def reset(self):
        """Reset all metrics (useful for starting new run)."""
        self.agent_metrics: Dict[str, Dict] = {}
        self.tool_metrics: Dict[str, Dict] = {}
        self.run_start_time = time.perf_counter()
        self.total_llm_calls = 0
        self.total_tool_calls = 0
        logger.debug("Metrics reset for new run")

    def _load_pricing(self):
        """Load Gemini pricing configuration from JSON file."""
        config_path = Path(__file__).parent.parent / "config" / "llm_pricing.json"

        try:
            with open(config_path, 'r') as f:
                self.pricing = json.load(f)
            logger.debug(f"Loaded pricing config for {len(self.pricing)} models")
        except FileNotFoundError:
            logger.warning(f"Pricing config not found at {config_path}. Using default pricing.")
            # Default fallback pricing
            self.pricing = {
                "gemini-2.5-pro": {
                    "input_cost_per_million": 4.00,
                    "output_cost_per_million": 20.00,
                    "tier": "high"
                },
                "gemini-2.5-flash": {
                    "input_cost_per_million": 0.075,
                    "output_cost_per_million": 0.30,
                    "tier": "mid"
                },
                "gemini-2.5-flash-lite": {
                    "input_cost_per_million": 0.10,
                    "output_cost_per_million": 0.40,
                    "tier": "low"
                }
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pricing config: {e}")
            self.pricing = {}

    def _calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD based on token usage and model pricing.

        Args:
            model_name: Gemini model name (e.g., "gemini-2.5-pro")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if model_name not in self.pricing:
            logger.warning(f"Pricing not found for model '{model_name}'. Cost calculation skipped.")
            return 0.0

        pricing = self.pricing[model_name]
        input_cost = (input_tokens / 1_000_000) * pricing["input_cost_per_million"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_cost_per_million"]
        total_cost = input_cost + output_cost

        return total_cost

    def record_llm_call(
        self,
        agent_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float
    ):
        """
        Record metrics for a single LLM call.

        Args:
            agent_name: Name of the agent making the call
            model_name: Gemini model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            duration_ms: Execution time in milliseconds
        """
        # Initialize agent metrics if not exists
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "duration_ms": 0,
                "cost_usd": 0.0,
                "model_name": model_name
            }

        # Calculate cost for this call
        cost = self._calculate_cost(model_name, input_tokens, output_tokens)

        # Accumulate metrics
        metrics = self.agent_metrics[agent_name]
        metrics["calls"] += 1
        metrics["input_tokens"] += input_tokens
        metrics["output_tokens"] += output_tokens
        metrics["total_tokens"] += (input_tokens + output_tokens)
        metrics["duration_ms"] += duration_ms
        metrics["cost_usd"] += cost

        self.total_llm_calls += 1

        logger.trace(
            f"LLM call recorded: {agent_name} | {model_name} | "
            f"tokens: {input_tokens}→{output_tokens} | "
            f"time: {duration_ms:.0f}ms | cost: ${cost:.6f}"
        )

    def record_tool_call(self, tool_name: str, duration_ms: float):
        """
        Record execution time for a tool call.

        Args:
            tool_name: Name of the tool
            duration_ms: Execution time in milliseconds
        """
        # Initialize tool metrics if not exists
        if tool_name not in self.tool_metrics:
            self.tool_metrics[tool_name] = {
                "calls": 0,
                "duration_ms": 0
            }

        # Accumulate metrics
        metrics = self.tool_metrics[tool_name]
        metrics["calls"] += 1
        metrics["duration_ms"] += duration_ms

        self.total_tool_calls += 1

        logger.trace(f"Tool call recorded: {tool_name} | time: {duration_ms:.0f}ms")

    def get_summary(self) -> Dict:
        """
        Get complete metrics summary.

        Returns:
            Dictionary with agent metrics, tool metrics, and totals
        """
        total_run_time = (time.perf_counter() - self.run_start_time) * 1000  # ms

        # Calculate totals
        total_input_tokens = sum(m["input_tokens"] for m in self.agent_metrics.values())
        total_output_tokens = sum(m["output_tokens"] for m in self.agent_metrics.values())
        total_tokens = sum(m["total_tokens"] for m in self.agent_metrics.values())
        total_llm_duration = sum(m["duration_ms"] for m in self.agent_metrics.values())
        total_cost = sum(m["cost_usd"] for m in self.agent_metrics.values())

        total_tool_duration = sum(m["duration_ms"] for m in self.tool_metrics.values())

        return {
            "agent_metrics": self.agent_metrics,
            "tool_metrics": self.tool_metrics,
            "totals": {
                "llm_calls": self.total_llm_calls,
                "tool_calls": self.total_tool_calls,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "llm_duration_ms": total_llm_duration,
                "tool_duration_ms": total_tool_duration,
                "total_run_time_ms": total_run_time,
                "total_cost_usd": total_cost
            }
        }

    def print_summary(self):
        """Print formatted summary report to console and log."""
        summary = self.get_summary()
        totals = summary["totals"]

        # Convert times to seconds for display
        total_run_time_s = totals["total_run_time_ms"] / 1000

        # Build report
        report_lines = []
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("LLM USAGE & COST REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Total Execution Time: {self._format_duration(total_run_time_s)}")
        report_lines.append("")

        # Agent Metrics Table
        if self.agent_metrics:
            report_lines.append("Agent Metrics:")
            report_lines.append("┌─────────────────────────────┬───────┬────────────┬─────────────┬──────────┬──────────┐")
            report_lines.append("│ Agent                       │ Calls │ Input Tok  │ Output Tok  │ Time (s) │ Cost ($) │")
            report_lines.append("├─────────────────────────────┼───────┼────────────┼─────────────┼──────────┼──────────┤")

            for agent_name, metrics in sorted(self.agent_metrics.items()):
                duration_s = metrics["duration_ms"] / 1000
                report_lines.append(
                    f"│ {agent_name:<27} │ {metrics['calls']:>5} │ "
                    f"{metrics['input_tokens']:>10,} │ {metrics['output_tokens']:>11,} │ "
                    f"{duration_s:>8.1f} │ {metrics['cost_usd']:>8.4f} │"
                )

            # Totals row
            total_llm_s = totals["llm_duration_ms"] / 1000
            report_lines.append("├─────────────────────────────┼───────┼────────────┼─────────────┼──────────┼──────────┤")
            report_lines.append(
                f"│ {'TOTAL':<27} │ {totals['llm_calls']:>5} │ "
                f"{totals['input_tokens']:>10,} │ {totals['output_tokens']:>11,} │ "
                f"{total_llm_s:>8.1f} │ {totals['total_cost_usd']:>8.4f} │"
            )
            report_lines.append("└─────────────────────────────┴───────┴────────────┴─────────────┴──────────┴──────────┘")
            report_lines.append("")

        # Tool Metrics Table
        if self.tool_metrics:
            report_lines.append("Tool Metrics:")
            report_lines.append("┌─────────────────────────────┬───────┬──────────┐")
            report_lines.append("│ Tool                        │ Calls │ Time (s) │")
            report_lines.append("├─────────────────────────────┼───────┼──────────┤")

            for tool_name, metrics in sorted(self.tool_metrics.items()):
                duration_s = metrics["duration_ms"] / 1000
                report_lines.append(
                    f"│ {tool_name:<27} │ {metrics['calls']:>5} │ {duration_s:>8.1f} │"
                )

            # Totals row
            total_tool_s = totals["tool_duration_ms"] / 1000
            report_lines.append("├─────────────────────────────┼───────┼──────────┤")
            report_lines.append(
                f"│ {'TOTAL':<27} │ {totals['tool_calls']:>5} │ {total_tool_s:>8.1f} │"
            )
            report_lines.append("└─────────────────────────────┴───────┴──────────┘")
            report_lines.append("")

        # Top Cost Contributors
        if self.agent_metrics:
            sorted_agents = sorted(
                self.agent_metrics.items(),
                key=lambda x: x[1]["cost_usd"],
                reverse=True
            )

            report_lines.append("Top Cost Contributors:")
            for i, (agent_name, metrics) in enumerate(sorted_agents[:5], 1):
                cost_pct = (metrics["cost_usd"] / totals["total_cost_usd"] * 100) if totals["total_cost_usd"] > 0 else 0
                report_lines.append(
                    f"{i}. {agent_name}: ${metrics['cost_usd']:.4f} ({cost_pct:.1f}% of total)"
                )
            report_lines.append("")

        report_lines.append("=" * 80)

        # Print to console and log
        report = "\n".join(report_lines)
        print(report)
        logger.info("Metrics summary:\n" + report)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}h {minutes}m {secs:.1f}s"


# Global singleton instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global MetricsCollector singleton instance.

    Returns:
        MetricsCollector instance
    """
    return _metrics_collector
