# Quick Start Guide

## Running Your Own Queries

The easiest way to test the tool is using `main.py`.

### Step 1: Activate Virtual Environment

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Step 2: Edit main.py

Open `main.py` and modify the query section:

```python
# Your screening query
query = """
Market capitalization > 5000 AND
Price to earning < 20 AND
Return on equity > 15%
"""

# Optional: Select specific columns
columns = [
    "Name",
    "CMP Rs.",
    "P/E",
    "ROE %",
    "Debt / Eq"
]
```

### Step 3: Run

```bash
python main.py
```

### Output

The script will:
1. **Display results** in the terminal (first 10 stocks by default)
2. **Save JSON** file: `results_YYYYMMDD_HHMMSS.json`
3. **Save CSV** file: `results_YYYYMMDD_HHMMSS.csv`

## Example Queries

### Large Cap Value Stocks
```python
query = "Market capitalization > 10000 AND Price to earning < 15 AND Debt to equity < 1"
```

### High Growth Stocks
```python
query = "Sales growth 3Years > 20 AND Profit growth 3Years > 20"
```

### High Quality Stocks
```python
query = "Return on equity > 20 AND Return on capital employed > 22 AND Debt to equity < 0.5"
```

### Dividend Stocks
```python
query = "Dividend yield > 3 AND Price to earning < 20"
```

### Recent Performers
```python
query = "Return over 3months > 15 AND Market capitalization > 1000"
```

## Query Syntax

```
<Ratio Name> <Operator> <Value> <Logical Operator> ...
```

**Operators:** `>`, `<`, `=`, `>=`, `<=`
**Logical Operators:** `AND`, `OR`
**Percentage values:** Include the `%` symbol

## All Available Ratios

See `data/screener_ratios.csv` for the complete list of 335 ratios.

Common ones:
- Market Capitalization
- Price to Earning (P/E)
- Price to book value (P/B)
- Return on equity (ROE)
- Return on capital employed (ROCE)
- Debt to equity
- Sales growth 3Years
- Dividend yield
- Current price

## Troubleshooting

**"No module named 'tools'"**
- Make sure you're in the `portfolio-agent` directory
- Activate the virtual environment

**Login fails**
- Check `.env` file has correct credentials
- Delete `.playwright-mcp/cookies.pkl` and try again

**No results**
- Try a less restrictive query
- Verify ratio names match those in `data/screener_ratios.csv`
