"""
Shared JSON parsing utilities for AI agent responses
Handles various response formats: markdown code blocks, embedded JSON, malformed JSON
"""

import json
import re
from typing import Dict, Any, Optional
from json_repair import repair_json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger

logger = get_logger("utils.json_parser")


def parse_agent_response(
    response_text: str,
    fallback_action: str = "final_answer",
    agent_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse agent response to extract action and parameters with robust handling.

    This function handles multiple formats:
    1. JSON in markdown code blocks (```json ... ```)
    2. JSON embedded in prose text
    3. Malformed JSON using json_repair
    4. Plain text (fallback to specified action)

    Args:
        response_text: Raw response text from agent
        fallback_action: Action to use if no JSON found (default: "final_answer")
        agent_name: Optional agent name for logging context

    Returns:
        Dictionary with at minimum {"action": "..."} structure

    Examples:
        >>> parse_agent_response('{"action": "call_tool", "tool": "screen_stocks"}')
        {'action': 'call_tool', 'tool': 'screen_stocks'}

        >>> parse_agent_response('Here is the plan:\\n```json\\n{"action": "final_answer"}\\n```')
        {'action': 'final_answer'}

        >>> parse_agent_response('Just some text without JSON')
        {'action': 'final_answer', 'answer': 'Just some text without JSON'}
    """
    log_prefix = f"[{agent_name}] " if agent_name else ""
    original_text = response_text

    try:
        response_text = response_text.strip()

        # Strategy 1: Extract JSON from markdown code blocks ANYWHERE in text
        # Handles: "Some text\\n```json\\n{...}\\n```\\nMore text"
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1).strip()
            logger.trace(f"{log_prefix}Extracted JSON from markdown code block")

        # Strategy 2: Extract any JSON object from text (find outermost braces)
        # Handles: "I will do this: {...} because..."
        elif '{' in response_text and '}' in response_text:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                extracted = response_text[start_idx:end_idx]
                # Validate it looks like JSON (has quotes and colons)
                if '"' in extracted and ':' in extracted:
                    response_text = extracted
                    logger.trace(f"{log_prefix}Extracted JSON object from text")

        # Strategy 3: Try standard JSON parse
        try:
            data = json.loads(response_text)
            logger.trace(f"{log_prefix}Successfully parsed JSON (standard)")
            return data
        except json.JSONDecodeError as e:
            # Strategy 4: Try json_repair for malformed JSON
            logger.debug(f"{log_prefix}Standard JSON parse failed: {e}, trying json_repair...")
            try:
                repaired = repair_json(response_text)
                data = json.loads(repaired)
                logger.debug(f"{log_prefix}Successfully repaired and parsed JSON")
                return data
            except Exception as repair_error:
                logger.debug(f"{log_prefix}json_repair also failed: {repair_error}")
                raise  # Re-raise to trigger fallback

    except Exception as e:
        # Strategy 5: Fallback - treat entire response as final answer
        logger.debug(f"{log_prefix}All JSON parsing strategies failed: {e}")
        logger.trace(f"{log_prefix}Falling back to action='{fallback_action}'")

        return {
            "action": fallback_action,
            "answer": original_text
        }

    # Should not reach here, but just in case
    logger.warning(f"{log_prefix}Unexpected path in parse_agent_response")
    return {
        "action": fallback_action,
        "answer": original_text
    }


def validate_agent_result(
    result: Any,
    agent_name: str,
    query: str
) -> bool:
    """
    Validate that an agent result is complete and not an intermediate planning step.

    Args:
        result: Result returned by agent
        agent_name: Name of the agent for logging
        query: Original query sent to agent

    Returns:
        True if result looks complete, False if it appears incomplete

    Common incomplete patterns:
    - "I will..." - agent describing what it will do
    - "Let me..." - agent planning next steps
    - Contains "call_tool" - agent returning internal JSON instead of result
    - Contains "action" - agent returning raw action dict
    """
    if not isinstance(result, str):
        # If it's not a string, assume it's structured data (probably complete)
        return True

    result_lower = result.lower()

    # Check for incomplete response patterns
    incomplete_indicators = [
        "i will",
        "let me",
        "i'll",
        "i should",
        "call_tool",
        "call_agent",
        '"action":',
        "i need to",
        "first, i",
        "next, i"
    ]

    for indicator in incomplete_indicators:
        if indicator in result_lower:
            logger.warning(
                f"[{agent_name}] Result appears incomplete - contains '{indicator}'"
            )
            logger.debug(f"[{agent_name}] Query was: {query[:100]}...")
            logger.debug(f"[{agent_name}] Result preview: {result[:200]}...")
            return False

    return True
