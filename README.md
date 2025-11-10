# Portfolio Agent - Stock Screening & News Tools

A Python toolkit for screening Indian stocks using [screener.in](https://www.screener.in) with 335+ financial ratios and scraping Google News for market analysis.

## Features

### Stock Screening
- **AI Agent Integration**: Gemini-powered agent that can autonomously plan and execute stock screening queries
- **Automated Stock Screening**: Filter stocks based on multiple financial criteria
- **335+ Financial Ratios**: Access comprehensive metrics including:
  - Market Capitalization, P/E, P/B ratios
  - ROE, ROCE, ROA
  - Debt to Equity
  - Sales/Profit growth metrics
  - Quarterly performance indicators
  - And many more...
- **Automatic Column Configuration**: No manual setup needed - request any columns and the tool automatically configures them on screener.in
- **Column Name Mapping**: Transparent mapping between configuration names and table headers

### News Scraping
- **Google News Integration**: Scrape news articles from Google News
- **Date Range Support**: Search news by specific date ranges or time periods
- **Multi-Region Support**: Search news from different regions (US, IN, GB, etc.)
- **Multi-Language Support**: Search in different languages
- **Flexible Filtering**: Filter by source, date, and other criteria

### General
- **Session Management**: Automatic login and session persistence
- **Flexible Output**: Select specific columns or get all available data
- **Clean API**: Simple Python interface for AI agents or scripts

**Note on News Sources**: RSS feed integration was explored as alternative to Google News but most major Indian financial publishers (ET, Moneycontrol, Business Standard, etc.) have broken/malformed RSS feeds. Google News remains primary source. See CLAUDE.md for details.

**Note on LLM Service**: All agents use a centralized LLM service (`utils/llm_service.py`) for consistent Gemini API calls with built-in retry logic and error handling. Models can be tested easily via `GEMINI_TEST_MODEL` environment variable to override all agents at once (e.g., `export GEMINI_TEST_MODEL=gemini-2.5-pro`).

## Project Structure

```
portfolio-agent/
├── README.md                          # This file
├── requirements.txt                   # Dependencies
├── .env.example                      # Credentials template
│
├── tools/                            # Core tools
│   ├── screen_stocks.py              # Stock screening tool
│   ├── news_scraper.py               # Google News scraper
│   ├── article_extractor.py          # Article content extraction
│   ├── screener_session.py           # Session management
│   ├── column_manager.py             # Column mapping utilities (consolidated)
│   └── result_manager.py             # Result storage & analysis (consolidated)
│
├── agents/                           # AI Agents
│   ├── stock_screening_agent.py      # Stock screening agent
│   ├── stock_news_agent.py           # Stock news analysis agent
│   ├── market_research_agent.py      # Market research agent
│   ├── portfolio_builder_agent.py    # Portfolio orchestrator (detailed)
│   └── portfolio_builder_agent_simple.py  # Portfolio orchestrator (minimal)
│
├── data/                             # Data files
│   ├── screener_ratios.csv           # List of 335+ ratios
│   └── column_name_mapping.json      # Column name mappings
│
├── examples/                         # Example scripts
│   ├── main.py                       # Stock screening examples
│   ├── basic_usage.py                # Basic usage examples
│   ├── news_example.py               # News scraping examples
│   ├── article_example.py            # Article extraction examples
│   ├── run_agent.py                  # General agent examples
│   ├── run_stock_screening.py        # Stock screening agent examples
│   └── run_stock_news.py             # Stock news agent examples
│
├── docs/                             # Documentation
│   ├── SUMMARY.md                    # Implementation summary
│   ├── QUICK_START.md                # Quick start guide
│   ├── COLUMN_MAPPING.md             # Column mapping guide
│   └── AI_AGENT.md                   # AI agent documentation
│
├── scripts/                          # Utility scripts
│   └── build_column_mapping.py       # Column mapping builder
│
└── tests/                            # Test scripts
    ├── test_ai_agent_usage.py        # AI agent demonstration
    ├── test_column_config.py         # Column config tests
    ├── test_agent.py                 # Gemini agent tests
    └── test_news_scraper.py          # News scraper tests
```

## Setup Instructions

### 1. Clone or Setup Project

```bash
cd portfolio-agent
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
uv pip sync requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 4. Configure Credentials

```bash
# Copy the example env file
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux

# Edit .env and add your screener.in credentials
```

**`.env` file:**
```env
# Screener.in Credentials
SCREENER_EMAIL=your_email@example.com
SCREENER_PASSWORD=your_password_here

# Gemini API (for AI agent)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MID_MODEL=gemini-2.0-flash-exp
GEMINI_HIGH_MODEL=gemini-2.0-pro
GEMINI_LOW_MODEL=gemini-2.0-flash-lite
```

**Notes**:
- You need a free account on [screener.in](https://www.screener.in/register/) to use this tool
- For AI agent features, get a free Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Usage

### AI Agents (Recommended)

#### Stock Screening Agent

Use the Gemini-powered agent to ask natural language questions about stocks:

```python
from agents.stock_screening_agent import run_stock_screening

# Ask the agent to find stocks for you
answer = run_stock_screening(
    "Suggest a stock that has the potential to deliver at least 50% returns "
    "in the next 12 months. Explain the reasoning behind your choice, including "
    "key financial metrics and market trends that support this projection."
)

print(answer)
```

Run examples: `python examples/run_stock_screening.py`

#### Stock News Agent

Use the stock news agent to analyze news and sentiment for specific stocks:

```python
from agents.stock_news_agent import run_stock_news

# Ask the agent to analyze stock news
answer = run_stock_news(
    "What's the latest news about Tesla in the last week? "
    "Are there any major announcements or developments that could impact the stock price?"
)

print(answer)
```

Run examples: `python examples/run_stock_news.py`

#### Market Research Agent

Use the market research agent to analyze Indian market trends, sectors, and economic factors:

```python
from agents.market_research_agent import run_market_research

# Ask the agent to research market trends
answer = run_market_research(
    "What are the key trends in the Indian automobile sector over the last 3 months? "
    "Include market sentiment, government policies, and growth outlook."
)

print(answer)
```

**How agents work:**
1. Plan how to answer your question
2. Create appropriate tool queries (stocks or news)
3. Execute queries using the respective tools
4. Analyze results and iterate if needed
5. Provide a final answer with reasoning

### Quick Start with main.py

The fastest way to test direct queries:

1. **Edit `examples/main.py`** - Change the query section
2. **Run**: `python examples/main.py`
3. **Results** are displayed and saved to JSON/CSV files

See [docs/QUICK_START.md](docs/QUICK_START.md) for detailed instructions.

### Basic Example (Python Code)

```python
from tools.screen_stocks import screen_stocks

# Simple screening query
result = screen_stocks(
    query="Market capitalization > 500 AND Price to earning < 15 AND Return on capital employed > 22%"
)

print(f"Found {result['total_results']} stocks")
print(f"First stock: {result['stocks'][0]}")
```

### With Column Selection

```python
# Get specific columns only
result = screen_stocks(
    query="Market capitalization > 500 AND Price to earning < 15",
    columns=["Name", "CMP Rs.", "P/E", "ROE %", "ROCE %"]
)

for stock in result['stocks']:
    print(f"{stock['Name']}: P/E={stock['P/E']}, ROE={stock['ROE %']}")
```

### Automatic Column Configuration

The tool automatically configures screener.in to include any columns you request:

```python
# Request columns using their configuration names
result = screen_stocks(
    query="Market capitalization > 5000",
    columns=[
        "Sales growth 3Years",      # Will be auto-configured
        "Profit growth 5Years",     # Will be auto-configured
        "Return on capital employed",  # Will be auto-configured
        "Debt to equity"
    ],
    auto_configure_columns=True  # Default is True
)

# Note: Configuration names may differ from table header names
# e.g., "Sales growth 3Years" appears as "Sales Var 3Yrs %" in results
# Use result['available_columns'] to see actual column names

# Use table header names for filtering results
result = screen_stocks(
    query="Market capitalization > 5000",
    columns=["Name", "CMP Rs.", "Sales Var 3Yrs %", "ROCE %"],
    auto_configure_columns=False  # Already configured
)
```

### Complex Query Example

```python
query = """
Market capitalization > 1000 AND
Price to earning < 20 AND
Return on capital employed > 25% AND
Debt to equity < 0.5 AND
Sales growth 3Years > 15% AND
Return over 1year > 20%
"""

result = screen_stocks(query=query)
```

### Output Format

```python
{
    'total_results': 8,
    'query_url': 'https://www.screener.in/screen/raw/?query=...',
    'query': 'Market capitalization > 500 AND...',
    'available_columns': ['S.No.', 'Name', 'CMP Rs.', 'Mar Cap Rs.Cr.', ...],
    'stocks': [
        {
            'S.No.': '1.',
            'Name': 'Indosolar',
            'CMP Rs.': '558.50',
            'Mar Cap Rs.Cr.': '2323.57',
            'P/E': '13.16',
            'ROE %': '420.20',
            ...
        },
        ...
    ]
}
```

## Available Ratios

The tool supports 335+ ratios. Some commonly used ones:

### Valuation Ratios
- Market Capitalization
- Price to Earning (P/E)
- Price to book value (P/B)
- Price to Sales
- Dividend yield
- EV/EBITDA
- PEG Ratio

### Profitability Ratios
- Return on equity (ROE)
- Return on capital employed (ROCE)
- Return on assets (ROA)
- Operating profit margin (OPM)
- Net profit margin

### Financial Health
- Debt to equity
- Current ratio
- Interest Coverage Ratio
- Working capital

### Growth Metrics
- Sales growth (1Y, 3Y, 5Y, 10Y)
- Profit growth (1Y, 3Y, 5Y, 10Y)
- YOY Quarterly sales growth
- YOY Quarterly profit growth

### Price Performance
- Return over 3months/6months/1year/3years/5years/10years
- Current price

See `data/screener_ratios.csv` for the complete list.

## Query Syntax

Queries use natural language with logical operators:

```
<Ratio Name> <Operator> <Value> <Logical Operator> ...
```

**Operators**: `>`, `<`, `=`, `>=`, `<=`

**Logical Operators**: `AND`, `OR`

**Examples**:
- `Market capitalization > 500`
- `Price to earning < 15 AND Return on equity > 20%`
- `Debt to equity < 0.5 OR Current ratio > 2`

**Note**: Percentage values should include the `%` symbol.

## Advanced Usage

### Get All Available Ratios

```python
from tools.screen_stocks import get_available_ratios

ratios = get_available_ratios()
print(f"Total ratios available: {len(ratios)}")
print(ratios[:10])  # First 10 ratios
```

### Running with Visible Browser (for debugging)

```python
result = screen_stocks(
    query="Market capitalization > 500",
    headless=False  # Show browser window
)
```

## Error Handling

The tool includes comprehensive error handling:

```python
try:
    result = screen_stocks(query="Market capitalization > 500")
except ValueError as e:
    print(f"Invalid query: {e}")
except RuntimeError as e:
    print(f"Execution error: {e}")
```

Common errors:
- **ValueError**: Empty query or missing credentials
- **RuntimeError**: Login failure, network issues, or page loading errors

## Session Management

The tool automatically:
- Logs in to screener.in on first use
- Saves authentication state to `.playwright-mcp/auth.json`
- Reuses the session for subsequent requests
- Re-authenticates if session expires

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
pytest tests/
```

### News Scraping Examples

```python
from tools.news_scraper import scrape_news, scrape_news_by_period

# Search news by date range
result = scrape_news(
    query="Tesla stock",
    from_date="01/01/2025",
    to_date="01/31/2025"
)

print(f"Found {result['total_results']} articles")
for article in result['articles'][:5]:
    print(f"- {article['title']}")
    print(f"  Source: {article['media']}, Date: {article['date']}")

# Search news from last 7 days
result = scrape_news_by_period(
    query="Indian stock market",
    period="7d"
)

# Search with region
result = scrape_news_by_period(
    query="Nifty 50",
    period="1d",
    region="IN"  # India
)
```

Run examples: `python examples/news_example.py`

### Project Dependencies

- `playwright`: Browser automation
- `python-dotenv`: Environment variable management
- `requests`: HTTP requests (fallback)
- `beautifulsoup4`: HTML parsing (fallback)
- `pandas`: Data handling
- `google-generativeai`: Gemini AI integration
- `GoogleNews`: Google News scraping

## Limitations

- Requires screener.in account (free tier supported)
- Export to CSV/Excel requires Premium subscription (use JSON output instead)
- Rate limiting may apply for excessive requests
- Some advanced features (custom columns, industry filters) may require Premium

## Security Notes

- Never commit your `.env` file to version control
- The `.gitignore` file already excludes `.env` and auth files
- Credentials are stored locally and never shared

## Troubleshooting

### "Login failed" error
- Verify credentials in `.env` file
- Check if your screener.in account is active
- Try logging in manually on the website first

### "Browser not started" error
- Ensure Playwright is installed: `playwright install chromium`
- Check if chromium browser is available

### No results returned
- Verify your query syntax
- Try the query manually on screener.in website
- Check if the criteria are too restrictive

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

This tool is for educational and research purposes. Always verify stock data from official sources before making investment decisions.
