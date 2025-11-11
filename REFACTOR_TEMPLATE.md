# Refactoring Template: Sync → Async + Type Safety + Error Handling

This document shows **exact code transformations** for common patterns in the codebase.
Use as copy-paste reference when refactoring.

---

## Pattern 1: Basic Function with External API Call

### ❌ Before (Current Pattern)
```python
def fetch_stock_data(ticker):
    """Fetch stock data from API"""
    try:
        response = requests.get(f"https://api.example.com/stock/{ticker}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None
```

**Problems**:
- Blocking I/O
- No type hints
- Poor error handling
- No retries
- No metrics

### ✅ After (100x Pattern)
```python
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import aiohttp
from utils.logger import get_logger
from utils.metrics import api_call_duration, api_call_errors

logger = get_logger(__name__)

@api_call_duration.time()
@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True
)
async def fetch_stock_data(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch stock data from API with retry logic.

    Args:
        ticker: Stock ticker symbol (e.g., 'RELIANCE')

    Returns:
        Stock data dictionary, or None if all retries failed

    Raises:
        aiohttp.ClientError: If API is unreachable after retries
    """
    url = f"https://api.example.com/stock/{ticker}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                logger.debug("fetch.success", ticker=ticker)
                return data

    except aiohttp.ClientError as e:
        logger.error("fetch.failed", ticker=ticker, error=str(e))
        api_call_errors.labels(endpoint='stock_data', error_type=type(e).__name__).inc()
        raise

    except asyncio.TimeoutError:
        logger.warning("fetch.timeout", ticker=ticker)
        api_call_errors.labels(endpoint='stock_data', error_type='timeout').inc()
        raise
```

**Improvements**:
- ✅ Non-blocking async I/O
- ✅ Type hints with Optional return
- ✅ Automatic retries (2s, 4s, 8s, 16s)
- ✅ Structured logging with context
- ✅ Metrics tracking
- ✅ Proper exception handling
- ✅ Timeout protection
- ✅ Comprehensive docstring

---

## Pattern 2: Processing Multiple Items Sequentially

### ❌ Before (Sequential = Slow)
```python
def enrich_stocks(stocks):
    """Enrich stocks with additional data"""
    enriched = []
    for stock in stocks:
        # Each takes 2 seconds = 20 seconds for 10 stocks
        data = fetch_yfinance_data(stock['ticker'])
        stock['sector'] = data.get('sector')
        stock['industry'] = data.get('industry')
        enriched.append(stock)
    return enriched
```

**Problem**: Sequential processing, no concurrency

### ✅ After (Parallel = Fast)
```python
from typing import List, Dict, Any
import asyncio

async def enrich_stocks(
    stocks: List[Dict[str, Any]],
    max_concurrent: int = 5
) -> List[Dict[str, Any]]:
    """
    Enrich stocks with additional data in parallel.

    Args:
        stocks: List of stock dictionaries
        max_concurrent: Maximum concurrent API calls (rate limiting)

    Returns:
        Enriched stock list
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def enrich_one(stock: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich single stock with rate limiting"""
        async with semaphore:
            try:
                data = await fetch_yfinance_data(stock['ticker'])
                stock['sector'] = data.get('sector', 'Unknown')
                stock['industry'] = data.get('industry', 'Unknown')
                return stock
            except Exception as e:
                logger.warning(
                    "enrichment.failed",
                    ticker=stock['ticker'],
                    error=str(e)
                )
                # Graceful degradation: return stock without enrichment
                stock['sector'] = 'Unknown'
                stock['industry'] = 'Unknown'
                return stock

    # Process all stocks concurrently
    enriched = await asyncio.gather(
        *[enrich_one(stock) for stock in stocks],
        return_exceptions=False  # Errors already handled in enrich_one
    )

    return list(enriched)
```

**Improvements**:
- ✅ Parallel processing (10 stocks in ~4 seconds instead of 20)
- ✅ Rate limiting (don't overwhelm API)
- ✅ Graceful degradation (continue on errors)
- ✅ Type hints
- ✅ Proper error handling per item

---

## Pattern 3: Agent Tool Call with Caching

### ❌ Before (No Caching)
```python
def screen_stocks(query, columns):
    """Screen stocks based on query"""
    session = ScreenerSession()
    url = build_query_url(query)
    results = session.fetch_all_pages(url)

    if columns:
        results = filter_columns(results, columns)

    return {
        'total_results': len(results),
        'stocks': results
    }
```

**Problems**:
- No caching (repeated queries are expensive)
- No validation
- Synchronous I/O

### ✅ After (Cached + Validated)
```python
from typing import Optional, List, Dict, Any
from functools import lru_cache
import hashlib
from pydantic import BaseModel, Field, validator

# Pydantic model for validation
class ScreeningQuery(BaseModel):
    """Validated screening query"""
    query: str = Field(min_length=10, max_length=500)
    columns: Optional[List[str]] = None
    max_results: int = Field(default=30, gt=0, le=1000)

    @validator('query')
    def sanitize_query(cls, v: str) -> str:
        """Prevent injection attacks"""
        dangerous = ['<script>', 'DROP', '--', ';', 'javascript:']
        v_upper = v.upper()
        if any(d in v_upper for d in dangerous):
            raise ValueError(f"Potentially dangerous query: {v}")
        return v

    @validator('columns')
    def validate_columns(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate column names"""
        if v:
            # Check against whitelist
            valid_columns = get_valid_column_names()
            invalid = [c for c in v if c not in valid_columns]
            if invalid:
                raise ValueError(f"Invalid columns: {invalid}")
        return v

# In-memory cache with TTL
_screening_cache: Dict[str, Dict[str, Any]] = {}

async def screen_stocks(
    query: str,
    columns: Optional[List[str]] = None,
    max_results: int = 30,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Screen stocks with validation, caching, and async I/O.

    Args:
        query: Screening query (validated)
        columns: Optional list of columns to return
        max_results: Maximum results to return
        use_cache: Whether to use cached results

    Returns:
        Screening results dictionary

    Raises:
        ValueError: If query or columns are invalid
    """
    # Validate inputs
    validated = ScreeningQuery(
        query=query,
        columns=columns,
        max_results=max_results
    )

    # Check cache
    cache_key = _generate_cache_key(validated.query, validated.columns)

    if use_cache and cache_key in _screening_cache:
        logger.debug("cache.hit", query=query[:50])
        return _screening_cache[cache_key]

    logger.debug("cache.miss", query=query[:50])

    # Fetch data asynchronously
    session = await ScreenerSession.create()
    url = build_query_url(validated.query)
    results = await session.fetch_all_pages(url)

    if validated.columns:
        results = filter_columns(results, validated.columns)

    # Limit results
    if len(results) > validated.max_results:
        results = results[:validated.max_results]

    response = {
        'total_results': len(results),
        'stocks': results,
        'query_url': url,
        'is_cached': False
    }

    # Cache for future requests
    _screening_cache[cache_key] = response

    return response

def _generate_cache_key(query: str, columns: Optional[List[str]]) -> str:
    """Generate cache key from query and columns"""
    key_data = f"{query}:{','.join(columns or [])}"
    return hashlib.md5(key_data.encode()).hexdigest()
```

**Improvements**:
- ✅ Input validation with Pydantic
- ✅ Injection attack prevention
- ✅ Caching for repeated queries
- ✅ Async I/O
- ✅ Result limiting
- ✅ Type safety

---

## Pattern 4: Agent Class Refactoring

### ❌ Before (Basic Agent)
```python
class StockScreeningAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    def screen(self, query):
        """Screen stocks"""
        prompt = f"Screen stocks with query: {query}"
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
```

**Problems**:
- No error handling
- No metrics
- No retry logic
- Hardcoded model

### ✅ After (Production-Grade Agent)
```python
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
from circuitbreaker import circuit

from utils.logger import get_logger
from utils.llm_service import GeminiService
from utils.metrics import agent_execution_time, agent_errors, llm_tokens_used

logger = get_logger(__name__)

@dataclass
class AgentResult:
    """Structured agent result"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str] = None
    tokens_used: int = 0
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

class StockScreeningAgent:
    """
    Agent for screening stocks using LLM and screener.in.

    Attributes:
        model_name: Gemini model tier or specific model name
        max_retries: Maximum retry attempts for LLM calls
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        model_name: str = 'mid',
        max_retries: int = 3,
        timeout: int = 60
    ):
        self.gemini = GeminiService()
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout = timeout

        logger.info(
            "agent.initialized",
            agent_type="StockScreening",
            model=self.model_name
        )

    @agent_execution_time.time()
    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def screen(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        Screen stocks using LLM-powered analysis.

        Args:
            query: Natural language screening query
            context: Optional context from other agents

        Returns:
            AgentResult with screening results

        Raises:
            TimeoutError: If request exceeds timeout
            ValueError: If query is invalid
        """
        start_time = time.time()

        try:
            # Build prompt with context
            prompt = self._build_prompt(query, context)

            # Call LLM with timeout
            response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self.timeout
            )

            # Parse and validate response
            data = self._parse_response(response)

            # Track metrics
            execution_time = time.time() - start_time
            llm_tokens_used.labels(
                agent='StockScreening',
                model=self.model_name
            ).inc(response.usage_metadata.total_token_count)

            logger.info(
                "agent.screen.success",
                query=query[:100],
                execution_time=execution_time,
                tokens=response.usage_metadata.total_token_count
            )

            return AgentResult(
                success=True,
                data=data,
                tokens_used=response.usage_metadata.total_token_count,
                execution_time=execution_time
            )

        except asyncio.TimeoutError:
            logger.error("agent.screen.timeout", query=query[:100])
            agent_errors.labels(agent='StockScreening', error_type='timeout').inc()
            return AgentResult(
                success=False,
                data=None,
                error=f"Request timed out after {self.timeout}s"
            )

        except ValueError as e:
            logger.error("agent.screen.validation_error", error=str(e))
            agent_errors.labels(agent='StockScreening', error_type='validation').inc()
            return AgentResult(
                success=False,
                data=None,
                error=str(e)
            )

        except Exception as e:
            logger.error("agent.screen.error", error=str(e), query=query[:100])
            agent_errors.labels(agent='StockScreening', error_type='unknown').inc()
            return AgentResult(
                success=False,
                data=None,
                error=str(e)
            )

    async def _call_llm(self, prompt: str) -> Any:
        """Call LLM with current configuration"""
        response = await self.gemini.generate_content_async(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048
            )
        )
        return response

    def _build_prompt(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt with optional context"""
        base_prompt = f"Screen stocks with query: {query}"

        if context:
            context_str = "\n\n".join(
                f"{k}: {v}" for k, v in context.items()
            )
            base_prompt += f"\n\nContext:\n{context_str}"

        return base_prompt

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate LLM response"""
        # Add parsing logic here
        return {"raw": response.text}
```

**Improvements**:
- ✅ Structured results with dataclass
- ✅ Comprehensive error handling
- ✅ Circuit breaker for cascading failures
- ✅ Retry logic with exponential backoff
- ✅ Timeout protection
- ✅ Metrics tracking (execution time, tokens, errors)
- ✅ Structured logging
- ✅ Type hints everywhere
- ✅ Docstrings
- ✅ Context injection support

---

## Pattern 5: Configuration with Validation

### ❌ Before (No Validation)
```python
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

max_stocks = int(config.get('PORTFOLIO', 'max_stocks'))
capital = float(config.get('PORTFOLIO', 'initial_capital'))
```

**Problems**:
- No validation
- Can crash at runtime
- No type safety

### ✅ After (Validated Config)
```python
from typing import Literal
from pydantic import BaseModel, Field, validator, ValidationError
from decimal import Decimal
import configparser

class PortfolioConfig(BaseModel):
    """Validated portfolio configuration"""

    max_stocks: int = Field(ge=1, le=50, description="Maximum stocks in portfolio")
    initial_capital: Decimal = Field(
        ge=100000,
        le=100000000,
        description="Initial capital in INR"
    )
    investor_profile: Literal['aggressive', 'defensive'] = Field(
        description="Investor risk profile"
    )
    news_lookback_period: str = Field(
        regex=r'^\d+[dmy]$',
        description="News lookback period (e.g., '7d', '1m')"
    )

    @validator('max_stocks')
    def validate_max_stocks(cls, v: int) -> int:
        """Ensure reasonable portfolio size"""
        if v < 3:
            raise ValueError("Portfolio needs at least 3 stocks for diversification")
        if v > 50:
            raise ValueError("Portfolio too large (max 50 stocks)")
        return v

    @validator('initial_capital')
    def validate_capital(cls, v: Decimal) -> Decimal:
        """Ensure sufficient capital"""
        if v < 100000:
            raise ValueError("Minimum capital is ₹1,00,000")
        return v

    class Config:
        frozen = True  # Immutable config

def load_config(config_path: str = 'config.ini') -> PortfolioConfig:
    """
    Load and validate configuration from INI file.

    Args:
        config_path: Path to config.ini

    Returns:
        Validated PortfolioConfig

    Raises:
        ValidationError: If config is invalid
        FileNotFoundError: If config file doesn't exist
    """
    parser = configparser.ConfigParser()
    parser.read(config_path)

    try:
        config = PortfolioConfig(
            max_stocks=parser.getint('PORTFOLIO', 'max_stocks'),
            initial_capital=Decimal(parser.get('PORTFOLIO', 'initial_capital')),
            investor_profile=parser.get('PORTFOLIO', 'investor_profile'),
            news_lookback_period=parser.get('NEWS', 'news_lookback_period')
        )

        logger.info("config.loaded", config=config.dict())
        return config

    except ValidationError as e:
        logger.error("config.validation_failed", errors=e.errors())
        raise
```

**Improvements**:
- ✅ Runtime validation with Pydantic
- ✅ Type safety
- ✅ Clear error messages
- ✅ Business rule enforcement
- ✅ Immutable config
- ✅ Regex validation for complex patterns

---

## Quick Reference: Common Transformations

### Add async
```python
# Before
def func():
    return requests.get(url).json()

# After
async def func():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()
```

### Add type hints
```python
# Before
def process(items):
    return [x * 2 for x in items]

# After
from typing import List
def process(items: List[int]) -> List[int]:
    return [x * 2 for x in items]
```

### Add retry logic
```python
# Before
def fetch():
    return api.get()

# After
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def fetch():
    return api.get()
```

### Add metrics
```python
# Before
def build_portfolio():
    # ... logic
    return portfolio

# After
from utils.metrics import portfolio_build_duration

@portfolio_build_duration.time()
def build_portfolio():
    # ... logic
    return portfolio
```

### Add logging
```python
# Before
print(f"Processing {ticker}")

# After
from utils.logger import get_logger
logger = get_logger(__name__)

logger.info("processing.start", ticker=ticker)
```

---

## Checklist: Refactoring Any Function

When refactoring any function, apply these in order:

1. [ ] **Add type hints**
   - Parameters
   - Return value
   - Class attributes

2. [ ] **Convert to async** (if does I/O)
   - Change `def` to `async def`
   - Add `await` to I/O operations
   - Use `asyncio.gather()` for parallel ops

3. [ ] **Add validation**
   - Input validation (Pydantic)
   - Output validation
   - Business rule checks

4. [ ] **Add error handling**
   - Try/except with specific exceptions
   - Graceful degradation
   - Structured logging

5. [ ] **Add retry logic**
   - `@retry` decorator for network calls
   - Exponential backoff
   - Circuit breaker for cascading failures

6. [ ] **Add metrics**
   - Execution time
   - Success/failure counts
   - Resource usage

7. [ ] **Add structured logging**
   - Context fields
   - Consistent log levels
   - Sensitive data redaction

8. [ ] **Add docstring**
   - Purpose
   - Args with types
   - Returns
   - Raises
   - Example usage

9. [ ] **Add test**
   - Unit test for happy path
   - Unit test for error cases
   - Integration test if needed

---

## Copy-Paste Imports

Add to top of file:

```python
# Standard library
import asyncio
import time
import hashlib
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from functools import lru_cache

# Third-party
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from circuitbreaker import circuit
from pydantic import BaseModel, Field, validator

# Project
from utils.logger import get_logger
from utils.llm_service import GeminiService
from utils.metrics import (
    agent_execution_time,
    agent_errors,
    llm_tokens_used,
    api_call_duration
)

logger = get_logger(__name__)
```

---

## Next Steps

1. Pick one file to refactor (start with `tools/screener_session.py`)
2. Apply patterns above
3. Run tests to verify behavior unchanged
4. Measure performance improvement
5. Repeat for next file

**Goal**: Refactor 1 file per day = entire codebase transformed in 2-3 weeks

Good luck! 🚀
