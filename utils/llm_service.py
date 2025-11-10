"""
Centralized Gemini LLM Service

Provides unified interface for all agents to call Gemini models with:
- Consistent error handling and retry logic
- Easy model switching for testing (via GEMINI_TEST_MODEL env var)
- Support for three model tiers: HIGH (pro), MID (flash), LOW (flash-lite)
- Centralized logging and request tracking
- Token usage tracking
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from google import genai
from google.genai import types
import time

from utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger("utils.llm_service")


class GeminiService:
    """
    Centralized service for Gemini LLM calls.

    Provides:
    - Singleton client instance (reused across agents)
    - Smart model selection (test override → agent tier → global default)
    - Unified generate_content() wrapper with error handling
    - Token usage tracking and logging
    """

    # Class variable for singleton client
    _client = None
    _instance = None

    def __new__(cls):
        """Singleton pattern - only one instance of GeminiService"""
        if cls._instance is None:
            cls._instance = super(GeminiService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the service (only runs once due to singleton pattern)"""
        if not hasattr(self, '_initialized'):
            self._initialize_client()
            self._initialized = True

    def _initialize_client(self):
        """Initialize Gemini client"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        GeminiService._client = genai.Client(api_key=api_key)
        logger.debug("Gemini client initialized (singleton)")

    @staticmethod
    def get_client() -> genai.Client:
        """Get the singleton Gemini client"""
        if GeminiService._client is None:
            service = GeminiService()
        return GeminiService._client

    @staticmethod
    def resolve_model_name(tier: Optional[str] = None) -> str:
        """
        Resolve model name with intelligent fallback:
        1. GEMINI_TEST_MODEL env var (for testing different models)
        2. Specified tier (high/mid/low)
        3. Default: GEMINI_MID_MODEL

        Args:
            tier: Model tier ('high', 'mid', 'low') or specific model name

        Returns:
            Full model name (e.g., 'gemini-2.5-pro')
        """
        # Priority 1: Test override (for easy model switching)
        test_model = os.getenv('GEMINI_TEST_MODEL')
        if test_model:
            logger.debug(f"Using test model override: {test_model}")
            return test_model

        # Priority 2: Tier-based selection
        if tier:
            tier_lower = tier.lower()
            if tier_lower == 'high':
                model = os.getenv('GEMINI_HIGH_MODEL', 'gemini-2.5-pro')
            elif tier_lower == 'mid':
                model = os.getenv('GEMINI_MID_MODEL', 'gemini-2.5-flash')
            elif tier_lower == 'low':
                model = os.getenv('GEMINI_LOW_MODEL', 'gemini-2.5-flash-lite')
            else:
                # Assume it's a specific model name
                model = tier
            logger.debug(f"Resolved tier '{tier}' to model: {model}")
            return model

        # Priority 3: Default (MID)
        model = os.getenv('GEMINI_MID_MODEL', 'gemini-2.5-flash')
        logger.debug(f"Using default model: {model}")
        return model

    @staticmethod
    def generate_content(
        contents: Any,
        model: Optional[str] = None,
        temperature: float = 0.7,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        verbose: bool = False
    ) -> str:
        """
        Generate content using Gemini with unified error handling and retries.

        Args:
            contents: Conversation/prompt contents (list of messages or string)
            model: Model tier ('high', 'mid', 'low') or specific model name
                  Defaults to 'mid' if not specified
            temperature: Sampling temperature (0.0-2.0), default 0.7
            top_p: Nucleus sampling parameter, optional
            max_tokens: Maximum tokens in response, optional
            max_retries: Number of retry attempts on failure, default 3
            retry_delay: Delay between retries in seconds, default 1.0
            verbose: Enable detailed logging, default False

        Returns:
            Response text from the model

        Raises:
            RuntimeError: If all retry attempts fail
        """
        client = GeminiService.get_client()
        model_name = GeminiService.resolve_model_name(model)

        if verbose:
            logger.info(f"Generating content with model: {model_name}")

        # Build generation config
        generation_config = {
            "temperature": temperature,
        }
        if top_p is not None:
            generation_config["top_p"] = top_p
        if max_tokens is not None:
            generation_config["max_output_tokens"] = max_tokens

        # Retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                if verbose:
                    logger.debug(f"Attempt {attempt + 1}/{max_retries} to generate content")

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=generation_config["temperature"],
                        top_p=generation_config.get("top_p"),
                        max_output_tokens=generation_config.get("max_output_tokens"),
                    )
                )

                response_text = response.text

                if verbose:
                    token_info = ""
                    if hasattr(response, 'usage_metadata') and response.usage_metadata:
                        usage = response.usage_metadata
                        # Handle different Gemini API versions
                        input_tokens = getattr(usage, 'input_tokens', getattr(usage, 'prompt_token_count', 'N/A'))
                        output_tokens = getattr(usage, 'output_tokens', getattr(usage, 'candidates_token_count', 'N/A'))
                        token_info = (
                            f" (Tokens: input={input_tokens}, "
                            f"output={output_tokens})"
                        )
                    logger.debug(f"Successfully generated content{token_info}")

                return response_text

            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Log the error
                if verbose or attempt == max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {error_msg}"
                    )

                # Don't retry on last attempt
                if attempt < max_retries - 1:
                    logger.debug(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

        # All retries exhausted
        error_msg = f"Failed to generate content after {max_retries} attempts. Last error: {str(last_error)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def get_llm_service() -> GeminiService:
    """
    Get the singleton GeminiService instance.

    Returns:
        GeminiService instance
    """
    return GeminiService()


def generate_content(
    contents: Any,
    model: Optional[str] = None,
    **kwargs
) -> str:
    """
    Convenience function for generating content.

    Usage:
        from utils.llm_service import generate_content

        response = generate_content(
            contents=conversation,
            model='high',  # or 'mid', 'low', or specific model name
            temperature=0.7,
            max_retries=3
        )

    Args:
        contents: Conversation/prompt contents
        model: Model tier or specific model name
        **kwargs: Additional parameters (temperature, top_p, max_tokens, etc.)

    Returns:
        Response text from the model
    """
    return GeminiService.generate_content(contents=contents, model=model, **kwargs)


# Module metadata for easy access
__all__ = [
    'GeminiService',
    'get_llm_service',
    'generate_content',
]
