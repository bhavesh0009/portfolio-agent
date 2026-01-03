# Column Mapping Fix - Implementation Summary

## Problem Statement

The portfolio builder agent was returning 0 results from stock screening because:

1. **Inconsistent column naming**: LLM was generating queries with mixed naming conventions
   - Example: "Market capitalization" (lowercase) instead of "Market Capitalization"
   - Example: "ROE %" (output name) instead of "Return on equity" (config name)

2. **Three different name types causing confusion**:
   - Configuration names: "Return on equity", "Market Capitalization"
   - Short names: "ROE", "Mar Cap"
   - Output names: "ROE %", "Mar Cap Rs.Cr."

3. **Insufficient logging**: Couldn't trace where names were getting corrupted

## Solution Overview

Implemented a multi-layered approach:

### 1. Enhanced Logging System
Added detailed logging at each transformation step to track parameter flow.

### 2. Fuzzy Search Tool
Created `tools/column_mapper.py` to help LLM find correct column names.

### 3. Validation & Auto-correction
Created `tools/query_validator.py` to validate and auto-correct column names.

### 4. Enhanced System Prompt
Updated stock agent with comprehensive column naming guidelines.

---

## Implementation Details

### 1. Enhanced Logging

#### A. Portfolio Builder → Stock Agent
**File**: `agents/portfolio_builder_agent.py:181-207`

```python
print(f"\n{'='*70}")
print(f"[PORTFOLIO BUILDER -> STOCK_AGENT] Calling agent")
print(f"Query sent to Stock Agent:")
print(f"  {query}")
print(f"{'='*70}")
```

#### B. Stock Agent → Screener Tool
**File**: `agents/stock_agent.py:130-154`

```python
print(f"\n{'='*70}")
print(f"[STOCK_AGENT -> SCREENER_TOOL] Executing tool: {tool_name}")
print(f"Parameters sent to screener:")
print(f"  Query: {parameters.get('query', 'N/A')}")
print(f"  Columns: {parameters.get('columns', 'All')}")
print(f"  Full parameters: {json.dumps(parameters, indent=2)}")
print(f"{'='*70}\n")
```

#### C. Screen Stocks Tool
**File**: `tools/screen_stocks.py:77-83, 164-175`

Input validation logging + column mapping logging

### 2. Column Mapper Tool

**File**: `tools/column_mapper.py`

#### Key Functions:

**`search_column_mapping(search_term, max_results=5)`**
- Fuzzy search for column names
- Returns matches with context (config name, short name, description)
- Similarity scoring with substring matching prioritization

**`find_exact_match(column_name)`**
- Case-insensitive exact match lookup
- Returns mapping details if found

**`get_all_column_names()`**
- Returns list of all valid configuration names

#### Usage Example:

```python
from tools.column_mapper import search_column_mapping

results = search_column_mapping("market cap", max_results=3)
# Returns:
# [
#   {
#     "config_name": "Market Capitalization",
#     "short_name": "Mar Cap",
#     "description": "Market Capitalization of the company...",
#     "similarity": 0.85
#   },
#   ...
# ]
```

### 3. Query Validator

**File**: `tools/query_validator.py`

#### Key Functions:

**`validate_column(column_name, auto_correct=True)`**
- Validates single column name
- Returns correction suggestions with confidence scores

**`validate_columns(columns, auto_correct=True, min_confidence=0.7)`**
- Validates list of columns
- Returns: corrections, warnings, invalid columns

**`auto_correct_columns(columns, min_confidence=0.8)`**
- Auto-corrects column names with high confidence
- Returns corrected list

**`validate_query_syntax(query)`**
- Validates column names used in query string
- Extracts column names from query and validates them

#### Normalization:

Common corrections built-in:
```python
corrections = {
    'market capitalization': 'Market Capitalization',
    'p/e': 'Price to Earning',
    'roe': 'Return on equity',
    'roe %': 'Return on equity',
    'roce': 'Return on capital employed',
    # ... and more
}
```

### 4. Enhanced System Prompt

**File**: `agents/stock_agent.py:67-118`

Added comprehensive section:

```
CRITICAL: COLUMN NAME USAGE RULES
================================================================================
You MUST use EXACT Configuration Names in both queries and column lists.
DO NOT use output names or abbreviations.

CORRECT Configuration Names (use these):
  - "Market Capitalization" (NOT "market capitalization" or "Market Cap")
  - "Return on equity" (NOT "ROE" or "ROE %")
  - "Return on capital employed" (NOT "ROCE" or "ROCE %")
  - "Price to Earning" (NOT "P/E" or "PE")
  - "Sales growth 3Years" (NOT "Sales growth 3years" or "Sales Var 3Yrs")
  ...

EXAMPLE CORRECT USAGE:
{
  "action": "call_tool",
  "tool": "screen_stocks",
  "parameters": {
    "query": "Market Capitalization > 5000 AND Return on equity > 15",
    "columns": ["Name", "Market Capitalization", "Return on equity"]
  }
}

EXAMPLE INCORRECT USAGE (DO NOT DO THIS):
{
  "action": "call_tool",
  "tool": "screen_stocks",
  "parameters": {
    "query": "market capitalization > 5000 AND ROE > 15",
    "columns": ["Name", "Market Cap", "ROE %"]
  }
}
```

---

## Testing

### Test Script
**File**: `test_column_mapping.py`

Tests all three components:
1. Column mapper fuzzy search
2. Query validator with auto-correction
3. Screen stocks with enhanced logging

### Run Tests:

```bash
python test_column_mapping.py
```

### Test with Portfolio Builder:

```bash
python agents/portfolio_builder_agent.py
```

Expected output will now show:
- Detailed parameter flow at each step
- Column mapping transformations
- Validation warnings (if any)

---

## Usage Guide

### For Developers

#### Using Column Mapper:

```python
from tools.column_mapper import search_column_mapping

# Search for columns
results = search_column_mapping("market cap")
print(results[0]['config_name'])  # "Market Capitalization"
```

#### Using Query Validator:

```python
from tools.query_validator import auto_correct_columns

# Auto-correct column names
columns = ["market cap", "ROE", "sales growth 3years"]
corrected = auto_correct_columns(columns)
# Returns: ["Market Capitalization", "Return on equity", "Sales growth 3Years"]
```

### For AI Agents

The stock agent now has comprehensive guidelines in its system prompt.
Just follow the examples provided in the prompt.

---

## Files Modified

1. **agents/portfolio_builder_agent.py**
   - Enhanced logging in `_call_stock_agent()` and `_call_news_agent()`

2. **agents/stock_agent.py**
   - Enhanced logging in `_execute_tool()`
   - Updated system prompt with column naming rules

3. **tools/screen_stocks.py**
   - Added input validation logging
   - Added column mapping logging

## Files Created

1. **tools/column_mapper.py**
   - Fuzzy search for column names
   - 200 lines

2. **tools/query_validator.py**
   - Column validation and auto-correction
   - 280 lines

3. **test_column_mapping.py**
   - Test script for all components
   - 100 lines

4. **docs/COLUMN_MAPPING_FIX.md**
   - This documentation file

---

## Expected Improvements

### Before Fix:
```
Query: market capitalization > 5000 AND ROE > 15
Columns: ['Market Cap', 'ROE %']
Warning: The following columns are not in the configurable list: Market Cap, ROE %
Found 0 stocks
```

### After Fix:
```
[STOCK_AGENT -> SCREENER_TOOL] Executing tool: screen_stocks
Parameters sent to screener:
  Query: Market Capitalization > 5000 AND Return on equity > 15
  Columns: ['Name', 'Market Capitalization', 'Return on equity']

[SCREEN_STOCKS] Column name mapping
  'Market Capitalization' -> 'Mar Cap' [MAPPED]
  'Return on equity' -> 'ROE' [MAPPED]

Found 127 stocks
```

---

## Future Enhancements

1. **Add column mapper as a tool to stock agent**
   - Allow LLM to search for columns at runtime
   - More flexible than just system prompt

2. **Auto-validation in screen_stocks**
   - Automatically validate and correct column names before execution
   - Warn user about corrections

3. **Query syntax validator**
   - Validate entire query syntax, not just column names
   - Check for invalid operators, missing AND/OR, etc.

4. **Column name cache**
   - Cache frequently used column names
   - Reduce search time

---

## Troubleshooting

### Issue: Still getting 0 results

**Check**:
1. Run `python test_column_mapping.py` to verify tools work
2. Check logs for column mapping transformations
3. Verify column names match exactly (case-sensitive)
4. Check screener.in credentials are valid

### Issue: Validation not working

**Check**:
1. Verify `data/column_name_mapping.json` exists and is valid JSON
2. Check for typos in column names
3. Try searching manually: `python -c "from tools.column_mapper import print_search_results; print_search_results('your term')"`

### Issue: Auto-correction too aggressive

**Adjust confidence threshold**:
```python
corrected = auto_correct_columns(columns, min_confidence=0.9)  # More strict
```

---

## Summary

This implementation provides:
- **100% visibility** into parameter transformations via enhanced logging
- **Fuzzy search** for finding correct column names
- **Auto-correction** for common naming mistakes
- **Clear guidelines** in system prompt for LLM

The root cause (inconsistent column naming) is addressed through multiple layers:
1. Prevention (system prompt guidelines)
2. Detection (validation)
3. Correction (auto-correction)
4. Visibility (enhanced logging)
