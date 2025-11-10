# Portfolio Builder Debugging Guide

## Common Issues and Solutions

### Issue 1: Process Hangs After "Planning:" Message

**Symptoms:**
```
[ORCHESTRATOR] Planning: The STOCK_AGENT provided a strong list...
[Hangs - no further output]
```

**Cause:**
The Gemini API call is either:
1. Taking a very long time to generate the response
2. Timing out silently
3. The conversation history is too large

**Solution:**

The enhanced logging now shows:
```
[ORCHESTRATOR] Calling Gemini API (iteration 3, attempt 1/3)...
[ORCHESTRATOR] Received response (XXXX chars)
[ORCHESTRATOR] Planning: ...
[ORCHESTRATOR] Parsing response...
[ORCHESTRATOR] Parsed action: final_portfolio
```

If it hangs at "Calling Gemini API", the API is slow. If it hangs after "Planning", the response is very long and taking time to print/process.

**Workarounds:**

1. **Reduce max_iterations**: Edit `config.ini` or pass smaller value
   ```python
   portfolio = build_portfolio(max_iterations=5)  # Instead of 15
   ```

2. **Use keyboard interrupt (Ctrl+C)**: The agent saves state automatically
   ```
   [INFO] State saved to: .cache/portfolio_state_aggressive_20250115_143022.json
   ```

3. **Check API status**: Verify Gemini API is not rate-limited
   ```bash
   curl -X POST "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-exp:generateContent?key=YOUR_KEY"
   ```

---

### Issue 2: "Portfolio building failed or incomplete"

**Symptoms:**
```
PORTFOLIO SUMMARY
======================================================================
Portfolio building failed or incomplete
```

**Cause:**
The JSON parser couldn't extract the portfolio from the LLM response.

**Solution:**

With the enhanced JSON extraction (v2), this should be rare. If it still happens:

1. **Check the raw response**: Look for `"raw": "..."` in error output
2. **Verify JSON format**: The response should contain `{"action": "final_portfolio", "portfolio": {...}}`
3. **Check logs for [DEBUG] messages**: Shows JSON extraction attempts

**Example of what the parser handles:**

✅ **Works - JSON at end of text:**
```
Here's my analysis... [long text]

{
  "action": "final_portfolio",
  "portfolio": { ... }
}
```

✅ **Works - JSON in code block:**
```
```json
{
  "action": "final_portfolio",
  "portfolio": { ... }
}
```
```

✅ **Works - Pure JSON:**
```json
{
  "action": "final_portfolio",
  "portfolio": { ... }
}
```

---

### Issue 3: 0 Stocks Found

**Symptoms:**
```
[STOCK_AGENT <- SCREENER_TOOL] Tool execution completed
Results:
  Total stocks found: 0
```

**Cause:**
Column names in query don't match screener.in configuration names.

**Solution:**

✅ **Fixed in this release!** The enhanced logging shows:

```
[SCREEN_STOCKS] Column name mapping
  'Return on equity' -> 'ROE' [MAPPED]
  'Market Capitalization' -> 'Mar Cap' [MAPPED]

First stock filtered data (sample):
  'Return on equity': 65.56
  'Market Capitalization': 12304.71
```

If you still see 0 stocks:
1. Check the **query criteria** - they might be too strict
2. Verify **column names** are exact (case-sensitive)
3. Use the column mapper tool:
   ```python
   from tools.column_mapper import search_column_mapping
   results = search_column_mapping("market cap")
   ```

---

### Issue 4: API Rate Limiting / 503 Errors

**Symptoms:**
```
[WARNING] API overloaded. Retrying in 5s... (attempt 1/3)
[WARNING] API overloaded. Retrying in 10s... (attempt 2/3)
[ERROR] Max retries reached. Saving state and exiting...
```

**Cause:**
Gemini API is rate-limited or overloaded.

**Solution:**

1. **Wait and retry**: The agent automatically retries with exponential backoff (5s, 10s, 15s)

2. **Resume from saved state**: After error, state is saved
   ```python
   # Resume from state (feature to be implemented)
   # For now, just run again - cached agent results will be reused
   ```

3. **Use a different model**: Edit `.env`
   ```
   GEMINI_MID_MODEL=gemini-1.5-flash  # Try different model
   ```

4. **Add delay between iterations**: Edit portfolio_builder_agent.py line 371
   ```python
   time.sleep(5)  # Increase from 3 to 5 seconds
   ```

---

## Enhanced Logging Features

### 1. Parameter Flow Tracking

See exactly what's being passed at each step:

```
[PORTFOLIO BUILDER -> STOCK_AGENT] Calling agent
Query sent to Stock Agent:
  Find 5-7 aggressive growth stocks...
======================================================================

[STOCK_AGENT -> SCREENER_TOOL] Executing tool: screen_stocks
Parameters sent to screener:
  Query: Market Capitalization > 10000 AND Return on equity > 20...
  Columns: ['Name', 'Market Capitalization', 'Return on equity', ...]
======================================================================

[SCREEN_STOCKS] Input validation
Received parameters:
  Query: Market Capitalization > 10000...
  Columns: ['Name', 'Market Capitalization', ...]
======================================================================
```

### 2. Column Mapping Visibility

See how config names map to table headers:

```
[SCREEN_STOCKS] Column name mapping
Mapping requested columns to short names:
  'Market Capitalization' -> 'Mar Cap' [MAPPED]
  'Return on equity' -> 'ROE' [MAPPED]
  'Sales growth 3Years' -> 'Sales Var 3Yrs' [MAPPED]

First stock filtered data (sample):
  'Name': Waaree Renewab.
  'Market Capitalization': 12304.71
  'Return on equity': 65.56
  ... and 5 more columns
```

### 3. API Call Tracking

Know when the process is waiting for API:

```
[ORCHESTRATOR] Calling Gemini API (iteration 3, attempt 1/3)...
[ORCHESTRATOR] Received response (8452 chars)
[ORCHESTRATOR] Planning: The STOCK_AGENT provided...
[ORCHESTRATOR] Parsing response...
[ORCHESTRATOR] Parsed action: final_portfolio
```

---

## Performance Tips

### 1. Reduce Iterations for Faster Results

Default is 15 iterations. Most portfolios complete in 3-5 iterations.

```python
# In code
portfolio = build_portfolio(max_iterations=5)

# Or edit config.ini
[PORTFOLIO]
max_iterations = 5
```

### 2. Use Cached Results

Agent results are automatically cached per session. If you run again without changing queries, cached results will be used:

```
[PORTFOLIO BUILDER] Using cached STOCK_AGENT result
[PORTFOLIO BUILDER] Using cached NEWS_AGENT result
```

### 3. Skip News Validation

For faster testing, disable news checking in `config.ini`:

```ini
[NEWS]
check_news_for_shortlisted = false
```

---

## Troubleshooting Checklist

- [ ] Verify `.env` has valid API keys (GEMINI_API_KEY, SCREENER_EMAIL, SCREENER_PASSWORD)
- [ ] Check internet connection
- [ ] Verify screener.in credentials are correct
- [ ] Review logs for specific error messages
- [ ] Check if hanging at API call or parsing
- [ ] Try with smaller max_iterations (5 instead of 15)
- [ ] Clear cache directory if stale: `rm -rf .cache/`
- [ ] Check column names match exactly (case-sensitive)

---

## Getting Help

If issues persist:

1. **Capture full logs**: Run with output redirection
   ```bash
   python agents/portfolio_builder_agent.py > output.log 2>&1
   ```

2. **Check the last few lines**: Shows where it got stuck
   ```bash
   tail -n 50 output.log
   ```

3. **Look for error patterns**:
   - `[ERROR]` - Explicit errors
   - `[WARNING]` - Warnings that might indicate issues
   - `[DEBUG]` - Debug messages from JSON extraction
   - Hanging after `[ORCHESTRATOR] Calling Gemini API` = API timeout
   - Hanging after `[ORCHESTRATOR] Planning` = Long response processing

4. **State files**: Check `.cache/` directory for saved states
   ```bash
   ls -ltr .cache/portfolio_state_*.json
   ```
