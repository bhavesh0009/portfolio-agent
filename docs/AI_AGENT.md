# AI Agent Documentation

## Overview

The Stock Screening AI Agent uses Google's Gemini model to autonomously plan and execute stock screening queries. It provides a natural language interface for finding stocks based on complex criteria.

## Features

- **Natural Language Queries**: Ask questions in plain English
- **Autonomous Planning**: Agent creates execution plans to answer queries
- **Tool Integration**: Uses screen_stocks tool to fetch real data
- **Iterative Refinement**: Can refine queries based on results
- **Transparent Reasoning**: Provides explanations for recommendations

## Setup

### 1. Get Gemini API Key

Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. Configure Environment

Add to your `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MID_MODEL=gemini-2.0-flash-exp
```

### 3. Install Dependencies

```bash
pip install google-generativeai
```

## Basic Usage

### Simple Query

```python
from tools.agent import run_agent

answer = run_agent(
    "Find me 3 undervalued stocks with low P/E ratios"
)

print(answer)
```

### Custom Model

```python
from tools.agent import StockScreeningAgent

# Use a specific model
agent = StockScreeningAgent(model_name="gemini-2.0-pro")

answer = agent.run(
    "Suggest growth stocks with high sales growth",
    max_iterations=5,
    verbose=True
)
```

### Detailed Example

```python
from tools.agent import run_agent

query = """
Suggest a stock that has the potential to deliver at least 50% returns
in the next 12 months. Explain the reasoning behind your choice, including
key financial metrics and market trends that support this projection.
"""

answer = run_agent(query, verbose=True)
```

## How It Works

### Workflow

1. **User Query**: You ask a question in natural language
2. **Planning**: Agent analyzes the query and creates a plan
3. **Tool Execution**: Agent calls screen_stocks with appropriate parameters
4. **Analysis**: Agent analyzes the results
5. **Iteration**: Agent may refine queries or request additional data
6. **Final Answer**: Agent provides a comprehensive answer with reasoning

### Example Execution Flow

```
USER QUERY: Find undervalued stocks with strong fundamentals

--- Iteration 1 ---
[AGENT] Planning screening criteria...
[AGENT] Executing tool: screen_stocks
[AGENT] Query: Market capitalization > 500 AND Price to earning < 15 AND Return on equity > 15%
[AGENT] Found 12 stocks

--- Iteration 2 ---
[AGENT] Analyzing top results...
[AGENT] Executing tool: screen_stocks
[AGENT] Query: Market capitalization > 500 AND Price to earning < 15 AND Return on equity > 15% AND Debt to equity < 1
[AGENT] Found 8 stocks

FINAL ANSWER:
Based on the screening, here are 3 undervalued stocks with strong fundamentals:
...
```

## Agent Parameters

### StockScreeningAgent

```python
agent = StockScreeningAgent(model_name="gemini-2.0-flash-exp")
```

**Parameters**:
- `model_name` (str, optional): Gemini model to use
  - Default: Value from `GEMINI_MID_MODEL` in .env
  - Options: "gemini-2.0-flash-exp", "gemini-2.0-pro", etc.

### run() Method

```python
agent.run(
    user_query="...",
    max_iterations=5,
    verbose=True
)
```

**Parameters**:
- `user_query` (str): Natural language question about stocks
- `max_iterations` (int): Maximum planning/execution cycles (default: 5)
- `verbose` (bool): Print execution details (default: True)

**Returns**:
- `str`: Final answer with reasoning

## Example Queries

### Investment Recommendations

```python
# Growth stocks
run_agent("Find high-growth companies with strong profit margins")

# Value stocks
run_agent("Show me undervalued stocks trading below book value")

# Dividend stocks
run_agent("Find stocks with high dividend yield and consistent payouts")

# Quality stocks
run_agent("Suggest stocks with high ROE, low debt, and stable earnings")
```

### Comparative Analysis

```python
run_agent(
    "Compare companies in the IT sector with market cap > 10000 crores. "
    "Which one has the best growth potential?"
)
```

### Specific Criteria

```python
run_agent(
    "I want to invest 1 lakh in a stock that:\n"
    "- Has low P/E (below 20)\n"
    "- Strong sales growth (>20% in last 3 years)\n"
    "- Good return on capital (>25%)\n"
    "Suggest one stock with reasoning"
)
```

## Agent Capabilities

### The agent can:
- Understand natural language queries
- Create appropriate screening filters
- Request specific columns for analysis
- Analyze multiple stocks
- Refine queries based on results
- Provide reasoning for recommendations
- Handle complex multi-criteria requests

### The agent uses:
- **screen_stocks** tool with 335+ financial ratios
- Column name mapping for accurate data retrieval
- Iterative refinement to improve results

## Tips for Best Results

### 1. Be Specific

Good:
```python
"Find 3 stocks with P/E < 15, ROE > 20%, and market cap > 5000 crores"
```

Vague:
```python
"Find good stocks"
```

### 2. Specify Constraints

```python
"Find undervalued stocks with market cap between 1000-10000 crores,
excluding companies with high debt (debt to equity > 1)"
```

### 3. Ask for Reasoning

```python
"Suggest a stock for long-term investment and explain why based on
its financial metrics and growth potential"
```

### 4. Request Comparisons

```python
"Compare the top 5 stocks by market cap in the pharma sector.
Which one offers the best value?"
```

## Troubleshooting

### "GEMINI_API_KEY not found"
- Add `GEMINI_API_KEY` to your `.env` file
- Make sure `.env` is in the project root

### Agent returns generic answers
- Make your query more specific
- Include numerical criteria (P/E < 15, ROE > 20%, etc.)
- Ask for specific metrics in the response

### Agent exceeds max iterations
- Increase `max_iterations` parameter
- Simplify your query
- Break complex queries into multiple simpler ones

### Import errors
- Install: `pip install google-generativeai`
- Check Python version (3.8+ required)

## Advanced Usage

### Custom System Prompt

Modify `tools/agent.py` to customize the agent's behavior:

```python
def _create_system_prompt(self) -> str:
    return f"""Your custom system prompt here..."""
```

### Multiple Queries

```python
agent = StockScreeningAgent()

queries = [
    "Find growth stocks",
    "Find value stocks",
    "Find dividend stocks"
]

for query in queries:
    print(f"\nQuery: {query}")
    answer = agent.run(query, verbose=False)
    print(f"Answer: {answer}\n")
```

### Response Parsing

```python
answer = run_agent("Find 3 stocks with P/E < 15", verbose=False)

# Parse the response
if "stocks" in answer.lower():
    print("Agent found stocks!")
```

## Performance

### Model Selection

- **gemini-2.0-flash-exp**: Fast, cost-effective (recommended)
- **gemini-2.0-pro**: More accurate, slower, higher cost
- **gemini-2.0-flash-lite**: Fastest, simplest queries

### Optimization

- Use `verbose=False` for production
- Set appropriate `max_iterations` (3-5 typically sufficient)
- Cache common queries if needed

## Security

- Never commit `.env` with real API keys
- API key is loaded from environment variables only
- All API calls go directly to Google's servers
- No data is stored by the agent

## Examples

See [examples/run_agent.py](../examples/run_agent.py) for complete working examples.

## API Reference

See inline documentation in [tools/agent.py](../tools/agent.py) for detailed API reference.
