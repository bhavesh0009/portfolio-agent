# Agent and Tool Mapping

This document provides a comprehensive mapping of agents and tools in the portfolio-agent system.

## Overview

The system contains 3 agents that orchestrate 7 tools (consolidated from 13 original files) to build investment portfolios.

## Consolidation Summary

**Before:** 13 files (10 tools + 3 agents)
**After:** 10 files (7 tools + 3 agents)
**Reduction:** 30% fewer tool files

### Consolidated Tools:
1. **column_manager.py** (merged 3 files):
   - column_utils.py
   - column_mapper.py
   - query_validator.py

2. **result_manager.py** (merged 2 files):
   - result_storage.py
   - data_analyzer.py

3. **Deleted:** agent.py (deprecated legacy tool)

## Mapping Table

| Tool | Used By | Status | Purpose |
|------|---------|--------|---------|
| **news_scraper.py** | news_agent | IN USE | Scrapes Google News articles based on search queries |
| **article_extractor.py** | news_agent | IN USE | Extracts full article content and metadata from news URLs |
| **screen_stocks.py** | stock_agent, portfolio_builder_agent | IN USE | Screens stocks from screener.in using financial ratios |
| **screener_session_simple.py** | screen_stocks | IN USE | Manages authenticated sessions with screener.in |
| **column_manager.py** | screen_stocks | IN USE | Consolidated column operations (mapping, search, validation) |
| **result_manager.py** | screen_stocks | IN USE | Consolidated result storage and analysis |
| ~~agent.py~~ | - | DELETED | Legacy tool (replaced by stock_agent.py in agents/) |

## Detailed Agent Breakdown

### 1. NewsAnalysisAgent (news_agent.py)

**Location:** `agents/news_agent.py`

**Direct Tools:**
- `news_scraper.py` - Searches Google News with flexible date options
- `article_extractor.py` - Extracts full article content from URLs

**Purpose:** Analyzes news and provides market insights using Google News data

**Workflow:**
1. Receives user query about news/market
2. Determines appropriate time frame (period vs date range)
3. Uses `scrape_news()` to search Google News
4. Optionally uses `extract_article()` for deep analysis of specific articles
5. Returns insights and sentiment analysis

---

### 2. StockScreeningAgent (stock_agent.py)

**Location:** `agents/stock_agent.py`

**Direct Tools:**
- `screen_stocks.py` - Main screening tool

**Indirect Tools (via screen_stocks):**
- `screener_session_simple.py` - Session management
- `column_manager.py` - Column name operations (mapping, search, validation)
- `result_manager.py` - Result storage and analysis

**Purpose:** Screens stocks from screener.in using 335+ financial ratios

**Workflow:**
1. Receives natural language query about stocks
2. Generates screening query with appropriate filters
3. Calls `screen_stocks()` which:
   - Validates column names via `column_manager`
   - Configures screener.in columns
   - Fetches paginated results
   - Stores large result sets via `result_manager`
   - Analyzes data with coding agent via `result_manager`
4. Returns filtered stock data with analysis

---

### 3. PortfolioBuilderAgent (portfolio_builder_agent.py)

**Location:** `agents/portfolio_builder_agent.py`

**Sub-Agents:**
- `StockScreeningAgent` - For finding candidate stocks
- `NewsAnalysisAgent` - For validating stocks with news sentiment

**Indirect Tools:** All tools from both sub-agents

**Purpose:** Orchestrates stock screening and news analysis to build investment portfolios

**Workflow:**
1. Receives investor profile (aggressive/defensive) and capital
2. Uses `stock_agent` to find candidate stocks
3. Uses `news_agent` to validate each stock with recent news
4. Selects final stocks based on fundamentals + news sentiment
5. Allocates capital based on conviction and profile
6. Returns complete portfolio with rationale

---

## Tool Details

### Core News Tools

#### news_scraper.py
- **Function:** `scrape_news(query, period, from_date, to_date, language, region, max_results)`
- **Returns:** Dictionary with articles list, metadata, and search parameters
- **Dependencies:** GoogleNews library

#### article_extractor.py
- **Function:** `extract_article(url, language, perform_nlp)`
- **Returns:** Full article content, metadata, keywords, and summary
- **Dependencies:** newspaper4k library

### Core Stock Screening Tools

#### screen_stocks.py
- **Main Function:** `screen_stocks(query, columns, auto_configure_columns, fetch_all_pages, max_pages, page_delay, max_results_to_return, enable_storage, enable_analysis)`
- **Returns:** Stock data with optional sampling and analysis
- **Key Features:**
  - Automatic pagination
  - Column name validation and mapping
  - Large result set management
  - Statistical analysis integration

#### screener_session_simple.py
- **Class:** `ScreenerSession`
- **Purpose:** Handles authentication, navigation, and data extraction from screener.in
- **Key Methods:**
  - `start()` - Login and session management
  - `navigate()` - Fetch single page
  - `navigate_all_pages()` - Fetch paginated results
  - `extract_table_data()` - Parse HTML tables
  - `configure_columns()` - Update column preferences

### Consolidated Tools

#### column_manager.py (NEW - Merged 3 tools)
**Combines:** column_utils.py, column_mapper.py, query_validator.py

**Section 1: Core Mapping**
- `get_short_name(config_name)` - Get short name for a config name
- `map_to_short_names(config_names)` - Bulk mapping
- `get_all_column_names()` - List all valid columns
- `load_column_mapping()` - Load mapping data (cached)

**Section 2: Search & Discovery**
- `search_column_mapping(search_term, max_results, min_similarity)` - Fuzzy search
- `find_exact_match(column_name)` - Exact match lookup
- `calculate_similarity(str1, str2)` - String similarity scoring
- `print_search_results(search_term, max_results)` - Debug output

**Section 3: Validation & Auto-Correction**
- `validate_column(column_name, auto_correct)` - Validate single column
- `validate_columns(columns, auto_correct, min_confidence)` - Validate multiple
- `auto_correct_columns(columns, min_confidence)` - Auto-correct column list
- `normalize_column_name(column_name)` - Handle common variations
- `validate_query_syntax(query)` - Validate query string
- `print_validation_report(columns, auto_correct)` - Debug output

**Purpose:** Single source of truth for all column name operations

#### result_manager.py (NEW - Merged 2 tools)
**Combines:** result_storage.py, data_analyzer.py

**Class:** `ResultManager`

**Section 1: Storage**
- `save(results, query, metadata)` - Save results to JSON
- `load(filepath)` - Load saved results
- `list_results(limit)` - List recent files
- `cleanup_old_results(days)` - Clean old files

**Section 2: Analysis**
- `analyze(stocks, query)` - Analyze stock data and generate summary
- `format_analysis_markdown(analysis)` - Format results as markdown
- `_generate_analysis_code(stocks)` - Dynamic code generation
- `_execute_code(code, local_vars)` - Safe code execution

**Section 3: Combined Operations**
- `save_and_analyze(results, query, metadata)` - One-call storage + analysis

**Convenience Functions:**
- `save_screening_results(results, query, metadata)` - Quick save
- `load_screening_results(filepath)` - Quick load
- `analyze_screening_results(stocks, query)` - Quick analysis

**Purpose:** Unified interface for result management and analysis

## Data Flow

```
User Query
    |
    v
Portfolio Builder Agent
    |
    +---> Stock Agent
    |       |
    |       +---> screen_stocks.py
    |               |
    |               +---> screener_session_simple.py (auth, navigation)
    |               +---> column_manager.py (mapping, search, validation)
    |               +---> result_manager.py (storage, analysis)
    |
    +---> News Agent
            |
            +---> news_scraper.py (search news)
            +---> article_extractor.py (extract content)
```

## Tool Dependencies

```
screen_stocks.py
  -> screener_session_simple.py
  -> column_manager.py (consolidated)
  -> result_manager.py (consolidated)

news_agent.py
  -> news_scraper.py
  -> article_extractor.py

stock_agent.py
  -> screen_stocks.py (and all its dependencies)

portfolio_builder_agent.py
  -> stock_agent.py (and all its dependencies)
  -> news_agent.py (and all its dependencies)
```

## Summary

### Current State
- **Total Tools:** 7 (all in use)
- **Total Agents:** 3 (all in use)
- **Agent Hierarchy:** Portfolio Builder -> Stock Agent + News Agent

### Tool Categories
- **News Tools:** 2 (news_scraper, article_extractor)
- **Stock Screening Tools:** 3 (screen_stocks, screener_session_simple, column_manager)
- **Result Management:** 1 (result_manager)
- **Consolidated:** 1 (column_manager)

### Consolidation Benefits
1. **Reduced file count:** 13 → 10 files (23% reduction)
2. **Clearer architecture:** Related functions grouped logically
3. **Easier maintenance:** Fewer files to track and update
4. **Better discoverability:** One place for column operations, one for results
5. **Reduced imports:** Simpler dependency structure
6. **No circular dependencies:** Clean, linear dependency graph

### Migration Notes
- All old tool imports automatically replaced
- Old files deleted: agent.py, column_utils.py, column_mapper.py, query_validator.py, result_storage.py, data_analyzer.py
- No API changes: All functions retained with same signatures
- Backward compatible: Convenience functions preserved
