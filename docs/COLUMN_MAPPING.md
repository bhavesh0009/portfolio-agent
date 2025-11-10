# Column Name Mapping Guide

## Overview

Screener.in uses different names for columns in configuration vs. display:
- **Configuration Name**: Used when selecting columns (e.g., "Sales growth 3Years")
- **Table Header Name**: Displayed in results (e.g., "Sales Var 3Yrs %")

This tool provides **automatic mapping** between these names for AI-agent friendliness.

## How It Works

### 1. Column Mapping File

**File:** `data/column_name_mapping.json`

Contains mapping for all 368 columns (365 + 3 always-present):

```json
{
  "Sales growth 3Years": {
    "short_name": "Sales Var 3Yrs",
    "description": "Compounded Sales Growth (CAGR) over last 3 years.",
    "group": "annual_pl most_used"
  },
  "Price to Sales": {
    "short_name": "CMP / Sales",
    "description": "Price to Sales",
    "group": "user_ratio most_used"
  }
}
```

**Note:** Table headers often add suffixes:
- `"Sales Var 3Yrs"` → `"Sales Var 3Yrs %"`
- `"ROCE"` → `"ROCE %"`
- `"Sales Qtr"` → `"Sales Qtr Rs.Cr."`

### 2. Using Configuration Names (Recommended for AI Agents)

```python
from tools.screen_stocks import screen_stocks

result = screen_stocks(
    query="Market cap > 5000",
    columns=["Price to Sales", "Sales growth 3Years"]  # Config names
)

# Tool returns mapping transparency
print(result['column_mapping'])
# Output:
# {
#   "Price to Sales": "CMP / Sales",
#   "Sales growth 3Years": "Sales Var 3Yrs"
# }

# Check actual table headers
print(result['available_columns'])
# Output: ['S.No.', 'Name', 'CMP Rs.', 'CMP / Sales', 'Sales Var 3Yrs %', ...]
```

### 3. Using Table Header Names (Precise Filtering)

```python
result = screen_stocks(
    query="Market cap > 5000",
    columns=["CMP / Sales", "Sales Var 3Yrs %"],  # Exact table names
    auto_configure_columns=False  # Skip auto-configuration
)
```

## For AI Agents

### Best Practice Workflow

1. **Request columns using configuration names** (natural, readable)
2. **Tool auto-configures** the columns on screener.in
3. **Check `result['column_mapping']`** to see how names map
4. **Use actual table header names** from `result['available_columns']` for precise filtering

### Example

```python
# Step 1: AI requests with config names
result = screen_stocks(
    query="Market cap > 5000",
    columns=["Return on capital employed", "Debt to equity"]
)

# Step 2: Check mapping
mapping = result['column_mapping']
# {
#   "Return on capital employed": "ROCE",
#   "Debt to equity": "Debt / Eq"
# }

# Step 3: AI now knows actual table headers
# "ROCE" appears as "ROCE %" in table
# "Debt / Eq" appears as "Debt / Eq" in table

# Step 4: AI can extract data using either name
for stock in result['stocks']:
    print(stock.get('ROCE %'))  # Use table header name
```

## Common Mappings

| Configuration Name | Short Name | Table Header (with suffix) |
|-------------------|------------|---------------------------|
| Sales growth 3Years | Sales Var 3Yrs | Sales Var 3Yrs % |
| Price to Sales | CMP / Sales | CMP / Sales |
| Return on capital employed | ROCE | ROCE % |
| Debt to equity | Debt / Eq | Debt / Eq |
| Return on equity | ROE | ROE % |
| Profit growth 5Years | Profit Var 5Yrs | Profit Var 5Yrs % |
| Market Capitalization | Mar Cap | Mar Cap Rs.Cr. |
| YOY Quarterly sales growth | Qtr Sales Var | Qtr Sales Var % |

## Regenerating the Mapping

If screener.in changes column names, regenerate the mapping:

```bash
python build_column_mapping.py
```

This will:
1. Scrape Edit Columns page (365 columns)
2. Extract `data-name` and `data-short-name` attributes
3. Save to `data/column_name_mapping.json`

## Files

- `data/column_name_mapping.json` - Complete mapping (368 columns)
- `tools/column_utils.py` - Utility functions for mapping
- `build_column_mapping.py` - One-time scraper script
- `test_ai_agent_usage.py` - Demonstration of AI agent workflow

## Summary

**KISS Approach:**
- 368 columns mapped from screener.in
- Config names → Short names (base table headers)
- Table headers = Short names + suffixes (%, Rs.Cr., etc.)
- AI agents get transparency via `column_mapping` in results
- Simple, effective, no complex pattern matching needed
