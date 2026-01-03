# Stock News Agent Architecture Documentation

## Executive Summary

The Stock News Agent is an autonomous AI agent that analyzes news and sentiment for specific stocks and companies in the Indian equity market. It leverages Google News for article discovery and employs advanced NLP for content extraction and analysis.

**Key Characteristics:**
- **Model:** gemini-2.5-flash (MID tier) - $0.075/$0.30 per million tokens
- **Max Iterations:** 10 per query (default)
- **Tool Arsenal:** 2 tools (news_scraper, article_extractor)
- **Workflow:** Iterative agentic pattern with tool-calling capability
- **Performance:** Avg 22,947 input tokens per call, 38 calls in typical portfolio manager run

**Primary Use Cases:**
1. Analyzing news for portfolio stocks (called by Portfolio Manager)
2. Validating stock picks with sentiment analysis (called by Portfolio Builder)
3. Researching company-specific developments

---

## Table of Contents

1. [Agent Architecture](#agent-architecture)
2. [Detailed Workflow](#detailed-workflow)
3. [LLM Call Pattern Analysis](#llm-call-pattern-analysis)
4. [Tool Integration](#tool-integration)
5. [System Prompts & Instructions](#system-prompts--instructions)
6. [Token Consumption Deep Dive](#token-consumption-deep-dive)
7. [Real-World Performance Metrics](#real-world-performance-metrics)
8. [Code Reference Guide](#code-reference-guide)

---

## Agent Architecture

### File Location

**Primary Implementation:** `agents/stock_news_agent.py`

**Dependencies:**
- `tools/news_scraper.py` - Google News search integration
- `tools/article_extractor.py` - Full article content extraction
- `utils/llm_service.py` - Unified Gemini API interface
- `utils/json_parser.py` - Robust JSON response parsing
- `utils/logger.py` - Logging infrastructure
- `utils/metrics_collector.py` - Token usage tracking

### Class Structure

**File:** `agents/stock_news_agent.py:30-43`

```python
class StockNewsAgent:
    """AI agent that analyzes news and sentiment for specific stocks/companies"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the agent with Gemini API

        Args:
            model_name: Gemini model tier ('high', 'mid', 'low') or specific model name
                       Defaults to 'mid' if not specified
        """
        self.model_name = model_name or 'mid'  # Default: gemini-2.5-flash
        self.chat_history = []
```

**Key Attributes:**
- `model_name`: Model tier selection (default: 'mid' → gemini-2.5-flash)
- `chat_history`: Conversation history (currently unused, reserved for future)

### Model Configuration

**Default Model:** gemini-2.5-flash (MID tier)

**Resolution Priority:**
1. `GEMINI_TEST_MODEL` env var (test override)
2. Constructor `model_name` parameter
3. `GEMINI_MID_MODEL` env var → `gemini-2.5-flash` (default)

**Token Pricing:**
- Input: $0.075 per million tokens
- Output: $0.30 per million tokens

**Source:** `utils/metrics_collector.py:75-78`, `config/llm_pricing.json`

### Comparison with Other Agents

| Agent | Model Tier | Typical Cost/Call | Primary Function |
|-------|------------|-------------------|------------------|
| **Stock News** | MID (flash) | $0.0018 | News sentiment analysis |
| Portfolio Manager | HIGH (pro) | $0.0275 | Portfolio oversight |
| Market Research | MID (flash) | $0.0017 | Market trend research |
| Stock Screening | MID (flash) | $0.0012 | Fundamental screening |

---

## Detailed Workflow

### High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                           │
│         "Analyze news for Reliance Industries"          │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│           Iteration Loop (max 10 iterations)            │
│  ┌────────────────────────────────────────────────┐    │
│  │  Call Gemini LLM with:                         │    │
│  │  - System prompt (tools, workflow, sources)    │    │
│  │  - Conversation history                        │    │
│  │  - User query                                  │    │
│  └──────────────────┬─────────────────────────────┘    │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────┐        │
│  │       Parse LLM Response (JSON)             │        │
│  └──────────────────┬──────────────────────────┘        │
│                     │                                    │
│           ┌─────────┴─────────┐                         │
│           │                   │                         │
│   ┌───────▼──────┐    ┌──────▼───────┐                 │
│   │ final_answer │    │  call_tool   │                 │
│   └───────┬──────┘    └──────┬───────┘                 │
│           │                   │                         │
│       ┌───▼───┐      ┌────────▼─────────┐              │
│       │ EXIT  │      │ Execute Tool:    │              │
│       └───────┘      │ - scrape_news    │              │
│                      │ - extract_article│              │
│                      └────────┬─────────┘              │
│                               │                         │
│                    ┌──────────▼──────────┐             │
│                    │ Add result to       │             │
│                    │ conversation        │             │
│                    └──────────┬──────────┘             │
│                               │                         │
│                      Next Iteration                     │
│                               │                         │
└───────────────────────────────┴─────────────────────────┘
```

### Initialization Phase

**File:** `agents/stock_news_agent.py:205-210`

```python
conversation = [
    types.Content(role="user", parts=[types.Part.from_text(text=self._create_system_prompt())]),
    types.Content(role="model", parts=[types.Part.from_text(text="I understand. I'm ready to help...")]),
    types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
]
```

**Initial Messages:**
1. **System Prompt** (role: user) - Complete tool definitions and workflow
2. **Acknowledgment** (role: model) - Confirms agent readiness
3. **User Query** (role: user) - Actual analysis request

### Iteration Loop

**File:** `agents/stock_news_agent.py:212-300`

**Loop Control:**
```python
iteration = 0
while iteration < max_iterations:
    time.sleep(3)  # 3-second throttle
    iteration += 1
```

**Parameters:**
- `max_iterations`: Default 10 (configurable)
- `iteration_delay`: 3 seconds between calls
- Total possible runtime: ~30-40 seconds for 10 iterations (plus LLM time)

**Each Iteration:**
1. Call Gemini LLM with full conversation
2. Parse response for action type
3. Execute action:
   - `final_answer` → Return result and EXIT
   - `call_tool` → Execute tool, add result to conversation, CONTINUE
   - Unknown action → Return response and EXIT

### Stopping Conditions

The agent stops when:

1. **Agent Returns Final Answer** (`agents/stock_news_agent.py:241-252`)
   ```python
   if action == "final_answer":
       final_answer = parsed.get("answer", response_text)
       return final_answer
   ```

2. **Maximum Iterations Reached** (`agents/stock_news_agent.py:301-306`)
   ```python
   # Max iterations reached
   return f"Maximum iterations reached. Last response: {response_text[:500]}"
   ```

3. **Parse Error** (`agents/stock_news_agent.py:290-299`)
   ```python
   else:  # Unknown action
       return f"Completed. Response: {response_text[:500]}"
   ```

**No Early Stopping:** Currently no confidence-based early exit mechanism.

---

## LLM Call Pattern Analysis

### Why 38 Calls in Portfolio Manager Run?

Based on metrics from `logs/portfolio_agent_20251231_140043.log`:
- **Stock News Agent:** 38 LLM calls
- **News Scraper Tool:** 17 calls
- **Article Extractor Tool:** 6 calls

**Most Likely Scenario:** Multiple stock analysis in sequence

**Hypothesis:**
- Portfolio has 10 stocks
- Average 3.8 calls per stock (38 / 10 = 3.8)
- Typical pattern per stock:
  1. **Call 1:** Request news search
  2. **Call 2:** Extract article 1
  3. **Call 3:** Extract article 2 (if needed)
  4. **Call 4:** Final analysis and synthesis

**Alternative Scenario:** Retry logic inflation
- API failures trigger retries (max 3 retries per call)
- If 10 stocks × 2.5 calls = 25 base calls
- With 50% failure rate: 25 + (12 × 1 retry avg) = ~38 calls

### Conversation History Accumulation

**File:** `agents/stock_news_agent.py:263, 279`

```python
# Add model response to history
conversation.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

# Add tool result to history
result_message = f"Tool execution result:\n{json.dumps(limited_result, indent=2)}"
conversation.append(types.Content(role="user", parts=[types.Part.from_text(text=result_message)]))
```

**Growth Pattern:**
- **Call 1:** System prompt + query = 3,000 tokens
- **Call 3:** + 2 exchanges (model + tool results) = 8,000 tokens
- **Call 5:** + 4 exchanges = 15,000 tokens
- **Call 8:** + 7 exchanges = 25,000+ tokens

**Critical Issue:** No truncation or sliding window implemented
- Full conversation history sent every iteration
- By iteration 8-10, history dominates token count

### Average 22,947 Input Tokens Per Call

**Token Breakdown:**

| Component | Tokens | % of Total | Notes |
|-----------|--------|------------|-------|
| System Prompt | 1,500-2,000 | 7-9% | Fixed, includes all tool definitions |
| Conversation History | 10,000-15,000 | 44-65% | Accumulates each iteration |
| Tool Results | 3,000-8,000 | 13-35% | Article content, news lists |
| JSON Formatting | 500-1,000 | 2-4% | Structure overhead |
| Current Query | 200-500 | 1-2% | User context |
| **TOTAL** | **~22,947** | **100%** | Varies by iteration |

**Key Driver:** Conversation history accumulation accounts for 44-65% of tokens.

---

## Tool Integration

### Tool 1: scrape_news

**Purpose:** Search Google News for articles

**File:** `tools/news_scraper.py:110-357`

**Parameters:**
```python
def scrape_news(
    query: str,                      # Required: Stock/company name
    from_date: Optional[str] = None, # Optional: Start date (MM/DD/YYYY)
    to_date: Optional[str] = None,   # Optional: End date (MM/DD/YYYY)
    period: Optional[str] = None,    # Optional: Time period (1h, 1d, 7d, 1m, 1y)
    language: str = 'en',            # Default: English
    region: str = 'US',              # Default: United States
    max_results: Optional[int] = None
) -> Dict[str, Any]:
```

**Return Format:**
```python
{
    'total_results': 47,
    'query': 'Reliance Industries stock',
    'search_mode': 'period',
    'period': '7d',
    'from_date': '12/24/2025',
    'to_date': '12/31/2025',
    'articles': [
        {
            'title': 'Reliance Industries Q3 Results: Net Profit Rises 12%',
            'media': 'Economic Times',
            'date': '2 hours ago',
            'datetime': '2025-12-31T10:00:00+00:00',
            'desc': 'Reliance reported strong quarterly results...',
            'link': 'https://economictimes.indiatimes.com/...',
            'img': 'https://img.etimg.com/...'
        },
        # ... up to 10 articles (truncated if >10)
    ]
}
```

**Token Reduction Strategy:**
- Limits to first 10 articles (`agents/stock_news_agent.py:269`)
- Truncates descriptions to 200 chars (`line 275`)
- Typical result: 2,000-4,000 tokens

### Tool 2: extract_article

**Purpose:** Extract full article content and metadata

**File:** `tools/article_extractor.py:216-355`

**Parameters:**
```python
def extract_article(
    url: str,                     # Required: Article URL
    language: str = 'en',         # Default: English
    perform_nlp: bool = True      # Default: Enable NLP analysis
) -> Dict[str, Any]:
```

**Return Format:**
```python
{
    'url': 'https://economictimes.indiatimes.com/article-123',
    'title': 'Reliance Industries Q3 Results...',
    'authors': ['Jane Reporter', 'John Analyst'],
    'publish_date': '2025-12-31T08:00:00',
    'text': 'Mumbai: Reliance Industries reported...',  # FULL ARTICLE (3,000-10,000 tokens!)
    'top_image': 'https://img.etimg.com/...',
    'images': ['url1', 'url2', ...],
    'videos': [],
    'keywords': ['Reliance', 'Q3 results', 'profit', 'growth'],  # NLP-extracted
    'summary': 'Reliance Industries posted strong Q3 results...',  # Auto-generated
    'meta_description': 'Reliance Q3 profit rises 12%...',
    'meta_keywords': 'Reliance, earnings, stock',
    'meta_lang': 'en',
    'canonical_link': 'https://economictimes.indiatimes.com/article-123',
    'html': '<html>...</html>',  # Raw HTML
    'extraction_time': '2025-12-31T14:30:00',
    'extraction_method': 'newspaper4k'  # or 'trafilatura'
}
```

**Token Impact:**
- **Full Article Text:** 3,000-10,000 tokens (NOT truncated)
- **Metadata:** 500-1,000 tokens
- **Total per extraction:** 3,500-11,000 tokens

**Critical Bottleneck:** Full article content significantly inflates token counts.

### Tool Execution Flow

**File:** `agents/stock_news_agent.py:157-186`

```python
def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the requested tool"""
    if tool_name == "scrape_news":
        logger.debug(f"Query: {parameters.get('query', 'N/A')}")
        result = scrape_news(**parameters)
        logger.info(f"Found {result['total_results']} articles")
        return result

    elif tool_name == "extract_article":
        url = parameters.get('url', 'N/A')
        logger.info_preview("URL", url, preview_len=80)
        result = extract_article(**parameters)
        logger.info_preview("Extracted article", result['title'], preview_len=60)
        logger.debug(f"Content length: {len(result['text'])} characters")
        return result
```

**Result Limiting:**
```python
# Limit article content to avoid token limits
limited_result = tool_result.copy()
if 'articles' in limited_result and len(limited_result['articles']) > 10:
    limited_result['articles'] = limited_result['articles'][:10]
    limited_result['note'] = f"Showing 10 of {tool_result['total_results']} articles"

# Truncate descriptions to 200 chars
for article in limited_result.get('articles', []):
    if 'desc' in article and article['desc']:
        article['desc'] = article['desc'][:200]
```

**Note:** Limiting only applies to `scrape_news` results. `extract_article` returns full content untruncated.

---

## System Prompts & Instructions

### Complete System Prompt

**File:** `agents/stock_news_agent.py:48-142`

**Structure:**

#### 1. Role Definition (lines 50-51)
```
You are a stock news analysis AI agent specializing in analyzing news and sentiment for specific stocks and companies in the Indian equity market.
```

#### 2. Tool Definitions (lines 52-84)

**TOOL 1: scrape_news**
```
DESCRIPTION: Search Google News for articles based on query with flexible date options

PARAMETERS:
  - query (required): Search query for news articles
    Example: "Reliance Industries stock", "Indian IT sector news"

  - period OR from_date/to_date (optional): Date filtering
    period options: '1h', '1d', '7d', '1m', '1y'
    from_date/to_date format: 'MM/DD/YYYY'
    IMPORTANT: Cannot use both period and date range together

  - language (optional): 'en', 'hi', 'es', etc. Default: 'en'
  - region (optional): 'US', 'IN', 'GB', etc. Default: 'US'
  - max_results (optional): Limit number of results
```

**TOOL 2: extract_article**
```
DESCRIPTION: Extract full article content and metadata from a news URL

PARAMETERS:
  - url (required): Full URL of the article
  - language (optional): Language code, default 'en'
  - perform_nlp (optional): Enable NLP analysis (keywords, summary), default True
```

#### 3. Workflow Instructions (lines 85-93)
```
WORKFLOW:
1. First, determine the appropriate time frame for news (recent = use 'period', specific range = use 'from_date'/'to_date')
2. Use 'period' for recent news (recommended for current market updates)
3. Use 'from_date' and 'to_date' for analyzing news within specific date ranges
4. Execute news search using scrape_news
5. Analyze the article titles and descriptions from search results
6. If deeper analysis is needed, extract full article content using extract_article
7. Provide insights on sentiment, key developments, and potential market impact
```

#### 4. Source Reliability Guidance (lines 95-120)

**Data-Driven Source Quality Matrix:**

**HIGHLY RELIABLE (100% extraction success):**
- Markets Mojo (`marketsmojo.com`)
- scanx.trade (`scanx.trade`)
- ET Now (`etnownews.com`)
- Zee Business (`zeebiz.com`)

**MODERATELY RELIABLE (50%+ success):**
- Business Standard (`business-standard.com`)
- Business Today (`businesstoday.in`)
- Outlook Money (`outlookmoney.com`)
- BusinessLine (`thehindubusinessline.com`)

**PROBLEMATIC (0% success):**
- mint / LiveMint (`livemint.com`)
- The Financial Express (`financialexpress.com`)
- The Economic Times (`economictimes.indiatimes.com`)

**Strategy Guidance:**
```
STRATEGY:
- Prioritize highly reliable sources for single article extraction
- For problematic sources, extract multiple articles to increase chances
- Use article descriptions from scrape_news when extraction fails
```

#### 5. JSON Output Format (lines 121-138)

**For Tool Calls:**
```json
{
  "action": "call_tool",
  "tool": "scrape_news",
  "parameters": {
    "query": "Tesla stock news",
    "period": "7d",
    "language": "en",
    "region": "US"
  }
}
```

**For Final Answer:**
```json
{
  "action": "final_answer",
  "answer": "Based on recent news analysis for Tesla stock over the past 7 days..."
}
```

#### 6. Temporal Context (line 140)
```
Current date: {datetime.now().strftime('%Y-%m-%d')}
```

#### 7. Tone Guidance (line 142)
```
Be analytical, identify trends, and provide actionable insights.
```

### Prompt Philosophy

**Minimal Prescriptiveness:**
- Explains tools and provides workflow suggestions
- Does NOT dictate exact sequence
- Allows agent flexibility:
  - How many articles to analyze
  - Which sources to prioritize
  - Depth of analysis required
  - When to return final answer

**Strategic Source Guidance:**
- Rather than blocking unreliable sources
- Provides empirical reliability data
- Suggests adaptive strategies (extract multiple articles from problematic sources)
- Balances quality with flexibility

---

## Token Consumption Deep Dive

### Component Breakdown by Iteration

**Iteration 1 (First LLM Call):**
| Component | Tokens |
|-----------|--------|
| System Prompt | 1,800 |
| Model Acknowledgment | 50 |
| User Query | 300 |
| **TOTAL** | **2,150** |

**Iteration 3 (After 2 tool calls):**
| Component | Tokens |
|-----------|--------|
| System Prompt | 1,800 |
| Model Acknowledgment | 50 |
| User Query | 300 |
| Exchange 1 (model response) | 500 |
| Exchange 1 (news search result) | 3,000 |
| Exchange 2 (model response) | 600 |
| Exchange 2 (article extraction) | 7,000 |
| **TOTAL** | **13,250** |

**Iteration 6 (Heavy analysis):**
| Component | Tokens |
|-----------|--------|
| System Prompt | 1,800 |
| Model Acknowledgment | 50 |
| User Query | 300 |
| 5 Model Responses | 2,500 |
| 2 News Searches | 6,000 |
| 3 Article Extractions | 21,000 |
| **TOTAL** | **31,650** |

**Observed Average: 22,947 tokens** (likely around iteration 4-5)

### Why History Dominates Token Count

**No Sliding Window Implementation:**
- Current code: Full conversation sent every iteration
- Alternative (not implemented): Keep only last N exchanges

**Accumulation Math:**
```
Call 1: 2,000 tokens (baseline)
Call 2: 2,000 + 3,500 (+ 1 exchange) = 5,500 tokens
Call 3: 2,000 + 7,000 (+ 2 exchanges) = 9,000 tokens
Call 4: 2,000 + 10,500 (+ 3 exchanges) = 12,500 tokens
Call 5: 2,000 + 14,000 (+ 4 exchanges) = 16,000 tokens
...
Call 8: 2,000 + 23,000 (+ 7 exchanges) = 25,000 tokens
```

**Exponential Growth:** Each iteration adds 3,000-7,000 tokens to cumulative history.

### Article Extraction Token Impact

**Typical Article Metrics:**
- Business news article: 800-2,000 words
- Token ratio: ~5-7 tokens per word
- **Token count: 4,000-14,000 tokens per article**

**Multi-Article Scenario:**
- Extract 3 articles: 12,000-42,000 tokens
- With conversation history: Total can exceed 50,000+ tokens

**Currently NO truncation** of article text before passing to LLM.

---

## Real-World Performance Metrics

### Portfolio Manager Run (Dec 31, 2025)

**Source:** `logs/portfolio_agent_20251231_140043.log`

**Stock News Agent Metrics:**

| Metric | Value | Notes |
|--------|-------|-------|
| **Total LLM Calls** | 38 | 84.4% of all portfolio manager calls |
| **Input Tokens** | 872,001 | 87% of all input tokens |
| **Output Tokens** | 15,096 | 82% of all output tokens |
| **LLM Time** | 244.8s | 81% of total LLM time (302.4s) |
| **Cost** | $0.0699 | 64.9% of total cost ($0.1077) |
| **Avg Input/Call** | 22,947 | Very high due to history accumulation |
| **Avg Output/Call** | 397 | Reasonable output size |

**Tool Metrics:**

| Tool | Calls | Time (s) | Avg Time/Call |
|------|-------|----------|---------------|
| news_scraper | 17 | 23.1 | 1.4s |
| article_extractor | 6 | 27.5 | 4.6s |

**Efficiency Analysis:**

- **LLM Calls per Tool Call:** 38 LLM / 23 tool calls = 1.65 LLM calls per tool
- **Interpretation:** Agent iterates 1-2 times per tool execution (reasonable)

**Cost Breakdown:**
```
Input cost:  872,001 × $0.075 / 1M = $0.0654
Output cost:  15,096 × $0.30 / 1M  = $0.0045
TOTAL:                              = $0.0699
```

**Time Breakdown:**
```
LLM time:   244.8s (81%)
Tool time:   50.6s (17%)
Other:        5-10s (2%) - parsing, logging, delays
TOTAL:      ~300s (5 minutes)
```

### Comparison: Portfolio Manager Run

**All Agents:**

| Agent | Calls | Input Tokens | Output Tokens | Time (s) | Cost ($) | % of Total Cost |
|-------|-------|--------------|---------------|----------|----------|-----------------|
| stock_news_agent | 38 | 872,001 | 15,096 | 244.8 | $0.0699 | **64.9%** |
| market_research_agent | 6 | 128,538 | 2,326 | 32.3 | $0.0103 | 9.6% |
| portfolio_manager_agent | 1 | 2,195 | 934 | 25.3 | $0.0275 | 25.5% |
| **TOTAL** | **45** | **1,002,734** | **18,356** | **302.4** | **$0.1077** | **100%** |

**Key Insight:** Stock News Agent is the **primary cost driver** in portfolio management.

---

## Code Reference Guide

### Core Implementation

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| **Agent Class** | `agents/stock_news_agent.py` | 30-43 | Class definition and initialization |
| **System Prompt** | `agents/stock_news_agent.py` | 48-142 | Comprehensive tool and workflow guidance |
| **Main Loop** | `agents/stock_news_agent.py` | 188-306 | Iteration logic and control flow |
| **Tool Execution** | `agents/stock_news_agent.py` | 157-186 | Tool dispatch and parameter handling |
| **Response Parsing** | `agents/stock_news_agent.py` | 144-155 | JSON parsing with fallback |
| **Convenience Function** | `agents/stock_news_agent.py` | 309-330 | `run_stock_news()` wrapper with metrics |

### Tool Implementations

| Tool | File | Lines | Purpose |
|------|------|-------|---------|
| **scrape_news** | `tools/news_scraper.py` | 110-357 | Google News search implementation |
| **extract_article** | `tools/article_extractor.py` | 216-355 | Article content extraction |

### Supporting Infrastructure

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| **LLM Service** | `utils/llm_service.py` | 112-228 | Unified Gemini API interface |
| **JSON Parser** | `utils/json_parser.py` | 19-108 | Robust JSON extraction with fallbacks |
| **Metrics Collector** | `utils/metrics_collector.py` | 113-162 | Token tracking and cost calculation |
| **Logger** | `utils/logger.py` | Full file | Comprehensive logging framework |

### Example Usage

| Example | File | Lines | Purpose |
|---------|------|-------|---------|
| **Basic Usage** | `examples/run_stock_news.py` | 27-43 | Single query execution |
| **Multiple Queries** | `examples/run_stock_news.py` | 45-71 | Batch processing example |
| **Caller: Portfolio Manager** | `agents/portfolio_manager_agent.py` | 600-650 (approx) | Integration with portfolio analysis |
| **Caller: Portfolio Builder** | `agents/portfolio_builder_agent_simple.py` | 650-700 (approx) | Integration with portfolio construction |

---

## Appendix: Technical Details

### Retry Logic

**File:** `utils/llm_service.py:164-223`

```python
for attempt in range(max_retries):  # Default: 3 retries
    try:
        response = client.models.generate_content(...)
        return response.text
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(retry_delay)  # Exponential backoff
```

**Impact on Call Count:**
- Failed API calls are retried up to 3 times
- Can inflate total LLM calls by 200-400% if errors are frequent

### Metrics Integration

**File:** `agents/stock_news_agent.py:222-228, 332-337`

```python
# LLM call with metrics
response_text = generate_content(
    contents=conversation,
    model=self.model_name,
    temperature=0.7,
    verbose=verbose,
    agent_name="stock_news_agent"  # Metrics tracking
)

# Metrics printed at end
metrics_collector = get_metrics_collector()
metrics_collector.print_summary()
```

**Automatic Tracking:**
- Every LLM call automatically tracked
- Token counts, duration, cost calculated
- Summary printed at end of agent execution

### Configuration

**File:** `config.ini` (referenced in CLAUDE.md)

```ini
[AGENT_SETTINGS]
max_iterations = 10  # Default iterations for all agents
news_lookback_period = 7  # Days to look back for news
check_news_for_shortlisted = true  # Validate stocks with news
```

**Environment Variables:**
```bash
GEMINI_MID_MODEL=gemini-2.5-flash  # Default model for stock news agent
GEMINI_API_KEY=...                 # Google AI API key
LOG_LEVEL=INFO                     # Logging verbosity
```

---

## Summary & Key Takeaways

### Architecture Highlights

1. **Iterative Agentic Pattern:** Agent decides when to use tools and when to provide final answer
2. **Dual-Tool Arsenal:** News search + article extraction
3. **Comprehensive System Guidance:** Detailed tool docs, source reliability data, workflow suggestions
4. **No Early Stopping:** Always runs up to max iterations or until explicit final_answer
5. **Full History Preservation:** No truncation or sliding window (opportunity for optimization)

### Performance Characteristics

1. **High Token Consumption:** Avg 22,947 input tokens/call due to conversation history accumulation
2. **Primary Cost Driver:** 64.9% of portfolio manager costs
3. **Heavy Article Extraction:** Full article text (4K-14K tokens) significantly inflates costs
4. **Reasonable Tool Efficiency:** 1.65 LLM calls per tool call
5. **Fast Tools:** News scraping (1.4s/call), Article extraction (4.6s/call)

### Production Readiness

**Strengths:**
- ✅ Robust error handling with retries
- ✅ Comprehensive metrics tracking
- ✅ Data-driven source reliability guidance
- ✅ Flexible workflow (agent decides strategy)
- ✅ Dual logging (console + file)

**Optimization Opportunities:**
- ⚠️ No conversation history truncation
- ⚠️ Full article content not summarized
- ⚠️ No early stopping mechanism
- ⚠️ No batch processing for multiple stocks
- ⚠️ No context caching (Gemini API feature available)

---

**Document Version:** 1.0
**Last Updated:** January 1, 2026
**Author:** Auto-generated from codebase analysis
**Purpose:** Technical documentation for Stock News Agent architecture and performance
