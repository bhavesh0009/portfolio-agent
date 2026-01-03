# Claude Code Advanced Features for Portfolio Agent System

**Document Version:** 1.0
**Last Updated:** December 27, 2025
**Purpose:** Comprehensive guide to leveraging advanced Claude Code features for the portfolio agent multi-agent system

---

## Table of Contents

1. [Overview](#overview)
2. [Claude Skills](#claude-skills)
3. [Sub-agents](#sub-agents)
4. [MCP Servers](#mcp-servers)
5. [Hooks](#hooks)
6. [Claude Agent SDK](#claude-agent-sdk)
7. [Implementation Roadmap](#implementation-roadmap)
8. [Best Practices](#best-practices)

---

## Overview

Claude Code provides powerful advanced features that can significantly enhance the portfolio agent system. This document outlines:

- **What each feature is** and how it works
- **Why it's beneficial** for the portfolio agent architecture
- **How to implement it** with specific examples
- **Practical use cases** tailored to portfolio management

### Quick Reference: Feature Selection Matrix

| Need | Use This Feature | Benefit |
|------|------------------|---------|
| Teach Claude domain knowledge (market analysis, screening methodologies) | **Skills** | Consistent application of portfolio strategies |
| Delegate focused subtasks (stock screening, news analysis) | **Sub-agents** | Isolated context, specialized expertise |
| Connect to external services (databases, APIs, brokers) | **MCP Servers** | Seamless integration with data sources |
| Auto-execute actions (formatting, validation, logging) | **Hooks** | Automated quality control and compliance |
| Build production agent applications | **Agent SDK** | Programmatic control, deployment flexibility |

---

## Claude Skills

### What Are Skills?

Skills are reusable, composable capabilities taught to Claude through markdown files. Claude **automatically applies** relevant skills based on context—no manual invocation needed.

**Key Characteristics:**
- **Model-invoked**: Claude decides when to use them
- **Discoverable**: Via description metadata with trigger keywords
- **Progressive disclosure**: Keep main file <500 lines, link to detailed docs
- **Tool restrictions**: Limit tool access with `allowed-tools` field

### Why Skills for Portfolio Agent?

**Current Pain Points:**
- Market analysis methodologies scattered across agent prompts
- Screening criteria duplicated in multiple places
- Inconsistent application of investment frameworks

**Skills Solution:**
- **Centralized knowledge**: Single source of truth for strategies
- **Automatic application**: Claude applies relevant skills without prompting
- **Version control**: Team can review/update strategies via git
- **Reusability**: Same skills across all portfolio agents

### Recommended Skills for Portfolio Agent

#### 1. Market Analysis Skill

**File:** `.claude/skills/market-analysis/SKILL.md`

```yaml
---
name: market-analysis
description: Analyze Indian equity market trends, sector performance, economic indicators, and macroeconomic factors. Use when researching current market conditions, evaluating sector opportunities, or assessing economic factors affecting portfolio decisions.
allowed-tools: WebSearch, WebFetch, Read, Bash
model: inherit
---

# Market Analysis Skill for Indian Equity Markets

## Purpose
Provide comprehensive market research for portfolio construction and management decisions in Indian equity markets.

## Research Framework

### 1. Market Sentiment Analysis
- Evaluate current market indices (Nifty 50, Sensex, Nifty Midcap/Smallcap)
- Identify risk-on vs. risk-off sentiment
- Track FII/DII flows
- Assess volatility (VIX levels)

### 2. Sector Analysis
- Identify sector rotation patterns
- Compare sector valuations (P/E, P/B relative to historical)
- Analyze sector-specific catalysts or headwinds
- Track sector performance vs. benchmarks

### 3. Macroeconomic Factors
- GDP growth trends and forecasts
- Inflation data (CPI, WPI)
- Interest rate trajectory (RBI policy)
- Currency movements (USD/INR)
- Commodity prices (crude oil, metals)

### 4. Key Data Sources
**Primary Sources:**
- NSE/BSE official data
- RBI reports and bulletins
- Economic surveys
- SEBI filings

**News Sources:**
- Economic Times
- Business Standard
- Mint
- Moneycontrol
- Financial Express

**Rating:** Prioritize primary sources over news commentary

## Analysis Output

Provide structured output:

**Market Outlook:** [Bullish/Bearish/Neutral with conviction level]

**Key Drivers:**
- Factor 1: Description and impact
- Factor 2: Description and impact
- ...

**Sector Opportunities:** Top 3 sectors with rationale

**Risk Factors:** Key risks to monitor

**Investment Implications:**
- Aggressive investor: Recommendations
- Defensive investor: Recommendations

## Usage Examples

**Query:** "Analyze current Indian market conditions for a new portfolio"
**Query:** "Research Indian IT sector trends for the next 6-12 months"
**Query:** "Evaluate macroeconomic factors affecting defensive sectors"
```

#### 2. Fundamental Stock Screening Skill

**File:** `.claude/skills/fundamental-screening/SKILL.md`

```yaml
---
name: fundamental-screening
description: Screen stocks using fundamental metrics like market cap, valuation ratios, quality metrics, growth rates, and debt levels. Use when selecting stocks for portfolio allocation based on financial criteria or filtering stock universe.
allowed-tools: Bash, Read, Write, Grep, Glob
model: inherit
---

# Fundamental Stock Screening Skill

## Purpose
Apply systematic fundamental analysis to screen stocks for portfolio construction.

## Screening Methodology

### 1. Quality Metrics (Primary Filter)
**Profitability:**
- ROE (Return on Equity) > 15% (aggressive) or > 12% (defensive)
- ROCE (Return on Capital Employed) > 15%
- Operating Profit Margin > 10%

**Efficiency:**
- Asset turnover trends
- Inventory/receivables management

**Safety:**
- Debt-to-Equity < 1.0 (defensive) or < 1.5 (aggressive)
- Interest Coverage Ratio > 3x
- Current Ratio > 1.5

### 2. Valuation Metrics (Secondary Filter)
**Relative Valuation:**
- P/E ratio vs. sector median
- P/B ratio for capital-intensive sectors
- EV/EBITDA for comparisons

**Absolute Valuation:**
- Avoid overly expensive stocks (>50 P/E unless justified)
- Look for reasonable valuations (15-25 P/E range)

### 3. Growth Metrics (Selection Criteria)
**Revenue Growth:**
- 3-year CAGR > 15% (aggressive) or > 10% (defensive)
- Consistent growth vs. erratic

**Earnings Growth:**
- EPS growth aligned with revenue growth
- Earnings quality (cash flow conversion)

**Future Outlook:**
- Order book trends
- Management guidance

### 4. Market Capitalization Segmentation

**Large Cap:** Market Cap > ₹20,000 Cr
- Lower risk, stable businesses
- Suitable for defensive portfolios
- Typically 40-60% allocation

**Mid Cap:** Market Cap ₹5,000-₹20,000 Cr
- Moderate risk, growth potential
- Suitable for balanced allocations
- Typically 30-40% allocation

**Small Cap:** Market Cap < ₹5,000 Cr
- Higher risk, higher growth
- Suitable for aggressive portfolios
- Typically 10-20% allocation

## Screening Query Construction

**Always use exact configuration names:**
- ✅ "Market Capitalization" (NOT "Market Cap")
- ✅ "Return on equity" (NOT "ROE")
- ✅ "Sales growth 3Years" (NOT "Sales growth 3years")

**Example Queries:**

**Aggressive Portfolio:**
```
Market Capitalization > 5000 AND
Return on equity > 15 AND
Sales growth 3Years > 15 AND
Debt to equity < 1.5
```

**Defensive Portfolio:**
```
Market Capitalization > 10000 AND
Return on equity > 12 AND
Debt to equity < 1.0 AND
Current ratio > 1.5
```

## Column Selection

**Essential Columns:**
- Name
- Market Capitalization
- Current Price
- Return on equity
- Return on capital employed
- Sales growth 3Years
- Debt to equity
- Interest Coverage Ratio
- Operating Profit Margin

**Optional Enrichment:**
- Industry (via Supabase enrichment)
- Sector (via Supabase enrichment)
- 52-week high/low
- Promoter holding

## Result Analysis

**Quality Assessment:**
- High ROE + High ROCE = Efficient capital allocation
- Low Debt + High Interest Coverage = Financial safety
- Consistent growth = Predictable business

**Red Flags:**
- Declining margins despite revenue growth
- Rising debt levels
- Deteriorating working capital
- Promoter pledging

**Portfolio Fit:**
- Aggressive: Growth + Moderate debt acceptable
- Defensive: Stability + Low debt mandatory

## Usage Examples

**Query:** "Screen high-quality large-cap stocks for defensive portfolio"
**Query:** "Find growth stocks in IT sector with ROE > 20%"
**Query:** "Identify undervalued mid-caps with strong fundamentals"
```

#### 3. Portfolio Review Skill

**File:** `.claude/skills/portfolio-review/SKILL.md`

```yaml
---
name: portfolio-review
description: Review and evaluate portfolio performance, allocation drift, risk metrics, and rebalancing needs. Use when analyzing existing portfolios, tracking performance, or generating rebalancing recommendations.
allowed-tools: Read, Bash, Grep, Glob
model: inherit
---

# Portfolio Review Skill

## Purpose
Systematic portfolio monitoring and rebalancing decision framework.

## Review Framework

### 1. Performance Tracking

**Absolute Returns:**
- Calculate portfolio returns since inception
- Compare entry price vs. current price per stock
- Track realized vs. unrealized gains/losses

**Relative Performance:**
- Benchmark comparison (Nifty 50 for large-cap heavy)
- Sector benchmark comparison
- Peer portfolio comparison

**Time-based Analysis:**
- 1-month, 3-month, 6-month, 1-year returns
- Volatility (standard deviation of returns)
- Maximum drawdown

### 2. Allocation Drift Analysis

**Position Sizing:**
- Current allocation % vs. target allocation %
- Identify positions that have grown >50% above target
- Identify positions that have shrunk >30% below target

**Sector Allocation:**
- Current sector exposure vs. intended diversification
- Concentration risk (any sector >30%?)

**Market Cap Drift:**
- Large/Mid/Small cap breakdown
- Compare against investor profile targets

### 3. Risk Assessment

**Stop-Loss Monitoring:**
- Identify positions breaching stop-loss levels
- Calculate current loss % from entry price
- Determine if stop-loss action is warranted

**Target Achievement:**
- Identify positions hitting target prices
- Assess if profit booking is appropriate
- Consider re-rating potential vs. booking gains

**Fundamental Deterioration:**
- Check if key metrics have changed materially
- Evaluate news/events impacting investment thesis
- Assess exit triggers from investment view

### 4. Investment Thesis Validation

**Review Triggers:**
- Has the market outlook changed significantly?
- Are sector fundamentals still intact?
- Has the stock's competitive position changed?

**Exit Triggers:**
- Fundamental deterioration (declining margins, rising debt)
- Management issues (governance concerns, accounting red flags)
- Structural industry headwinds
- Better opportunities elsewhere

### 5. Rebalancing Recommendations

**When to Rebalance:**
- Allocation drift >25% from target
- Stop-loss breach (capital preservation)
- Target achieved (profit booking)
- Investment thesis invalidated

**Rebalancing Actions:**
- **Trim:** Reduce overweight positions
- **Add:** Increase underweight positions
- **Exit:** Remove positions with breached stop-loss or invalidated thesis
- **Enter:** Add new positions if opportunities exist

**Execution Considerations:**
- Tax implications (STCG vs. LTCG)
- Transaction costs
- Market timing (avoid panic selling/buying)

## Output Format

**Portfolio Summary:**
- Total portfolio value: ₹X
- Total returns: Y%
- Number of holdings: N
- Top 5 performers
- Bottom 5 performers

**Allocation Status:**
- Current vs. Target allocation table
- Sector distribution chart (if possible)
- Drift analysis

**Action Items:**
1. **Immediate Actions:** (stop-loss breaches, critical issues)
2. **Rebalancing Recommendations:** (trim/add positions)
3. **Watch List:** (positions nearing triggers)
4. **Research Required:** (unclear situations needing deeper analysis)

**Risk Alerts:**
- Positions at risk
- Concentration risks
- Market-level risks

## Usage Examples

**Query:** "Review my aggressive portfolio for rebalancing opportunities"
**Query:** "Check if any positions have breached stop-loss levels"
**Query:** "Analyze sector allocation drift and recommend adjustments"
```

### Creating Skills

**Step-by-step:**

```bash
# 1. Create skill directory
mkdir -p .claude/skills/market-analysis

# 2. Create SKILL.md file
# (Use content from above examples)

# 3. Test the skill
# Claude will automatically detect and use it when relevant
```

**Verification:**
```
> Analyze current market conditions for portfolio building

# Claude should automatically invoke the market-analysis skill
```

---

## Sub-agents

### What Are Sub-agents?

Pre-configured AI personalities with their own context windows, custom prompts, and specific tool access. Sub-agents are **specialized experts** that Claude delegates tasks to.

**Key Benefits:**
- **Context Preservation:** Each operates independently, no context pollution
- **Specialized Expertise:** Fine-tuned instructions for specific domains
- **Reusability:** Works across projects and sessions
- **Flexible Permissions:** Different tool access per agent

### Why Sub-agents for Portfolio Agent?

**Current Architecture:**
```
Portfolio Builder Agent
  ├─ Market Research Agent
  ├─ Stock Screening Agent
  └─ Stock News Agent
```

**Problem:** All agents share same conversation context, leading to:
- Context window pollution
- Mixed instructions bleeding across agents
- Difficulty in maintaining agent-specific state

**Sub-agents Solution:**
- **Isolated contexts**: Each agent has clean context
- **Specialized prompts**: Tailored instructions per agent
- **Consistent behavior**: Same agent behaves identically across invocations
- **Better debugging**: Trace agent-specific issues

### Built-in Sub-agents

Claude Code provides three built-in sub-agents:

| Agent | Purpose | Tools | Model |
|-------|---------|-------|-------|
| **Explore** | Quick codebase searches | Read, Glob, Grep, Bash (read-only) | Haiku (fast) |
| **Plan** | Research before implementation | Read, Glob, Grep, Bash (read-only) | Sonnet |
| **General-purpose** | Complex multi-step tasks | All tools | Sonnet |

**Example Usage:**
```
> Explore the codebase to find all database queries

# Claude automatically invokes Explore agent
# Fast, read-only, focused search
```

### Custom Sub-agents for Portfolio System

#### 1. Code Reviewer Agent

**File:** `.claude/agents/code-reviewer.md`

```markdown
---
name: code-reviewer
description: Expert code reviewer for Python financial applications. Reviews code for quality, security, performance, and maintainability. Use proactively after writing or modifying code in the portfolio agent system.
tools: Read, Grep, Glob, Bash, Edit
model: inherit
permissionMode: acceptEdits
---

# Code Reviewer Agent for Portfolio Agent System

You are a senior code reviewer specializing in Python financial applications, with expertise in:
- AI/LLM agent systems (Gemini API, multi-agent architectures)
- Financial data processing (Pandas, NumPy)
- Database operations (Supabase PostgreSQL, SQLAlchemy)
- Web scraping (Playwright, BeautifulSoup, newspaper4k)
- API integrations (REST APIs, async operations)

## Review Methodology

**When invoked:**
1. Run `git diff` to see recent changes (if git repo)
2. Identify modified files
3. Focus review on changes, not entire codebase
4. Provide immediate, actionable feedback

## Review Checklist

### Code Quality
- ✅ Clear, descriptive function/variable names
- ✅ Proper docstrings for public functions
- ✅ No code duplication (DRY principle)
- ✅ Appropriate comments for complex logic
- ✅ Consistent code style (PEP 8 for Python)

### Security
- ✅ No hardcoded credentials or API keys
- ✅ Proper input validation (especially for user queries)
- ✅ No SQL injection vulnerabilities
- ✅ Secure handling of sensitive data
- ✅ API rate limiting and retry logic
- ✅ No exposure of internal system details in logs

### Performance
- ✅ Efficient database queries (avoid N+1 problems)
- ✅ Proper use of async/await for I/O operations
- ✅ Caching strategies for expensive operations
- ✅ Pagination for large result sets
- ✅ Resource cleanup (file handles, connections)

### Error Handling
- ✅ Proper exception handling with specific catches
- ✅ Graceful degradation on failures
- ✅ Informative error messages
- ✅ Logging at appropriate levels
- ✅ Validation of external API responses

### Testing
- ✅ Unit test coverage for critical functions
- ✅ Edge case handling
- ✅ Mock external dependencies
- ✅ Integration test considerations

### Financial Application Specific
- ✅ Numerical precision (Decimal for money calculations)
- ✅ Data validation for financial metrics
- ✅ Proper handling of market data timestamps
- ✅ Currency/percentage calculations accuracy
- ✅ Audit trail for portfolio decisions

## Feedback Format

**Provide prioritized feedback:**

**🔴 Critical (Must Fix):**
- Security vulnerabilities
- Data integrity issues
- Breaking bugs

**🟡 Warnings (Should Fix):**
- Performance concerns
- Maintainability issues
- Missing error handling

**🟢 Suggestions (Nice to Improve):**
- Code style improvements
- Refactoring opportunities
- Documentation enhancements

**Example:**
```
🔴 Critical: Line 45 - API key hardcoded in source code
   Fix: Move to environment variable and load via .env

🟡 Warning: Lines 78-92 - Complex nested logic, hard to understand
   Suggestion: Extract to separate function with descriptive name

🟢 Suggestion: Line 120 - Consider using f-string instead of .format()
   Benefit: More readable and slightly faster
```

## Agent Behavior

- **Proactive**: Automatically review code after significant changes
- **Focused**: Review only changed code, not entire project
- **Actionable**: Provide specific line numbers and fixes
- **Balanced**: Don't be overly pedantic; focus on impactful issues
- **Educational**: Explain *why* something is an issue

## No-Review Scenarios

Skip review if:
- Only documentation/markdown files changed
- Configuration files (.ini, .json) changed without code impact
- Test data or cache files modified
```

#### 2. Portfolio Analyst Agent

**File:** `.claude/agents/portfolio-analyst.md`

```markdown
---
name: portfolio-analyst
description: Specialized portfolio analysis expert. Analyzes portfolio performance, allocation drift, risk metrics, and generates rebalancing recommendations. Use when reviewing existing portfolios or monitoring performance.
tools: Read, Bash, Grep, Glob, WebFetch
model: inherit
---

# Portfolio Analyst Agent

You are a senior portfolio analyst specializing in Indian equity markets with expertise in:
- Portfolio performance analysis
- Risk management and allocation strategies
- Fundamental analysis and valuation
- Technical indicators and market trends
- Rebalancing strategies

## Core Responsibilities

### 1. Performance Analysis
- Calculate absolute and relative returns
- Benchmark against relevant indices
- Track individual position performance
- Identify top/bottom performers

### 2. Risk Assessment
- Monitor stop-loss breaches
- Evaluate target achievement
- Assess allocation drift
- Identify concentration risks

### 3. Rebalancing Recommendations
- Determine trim/add/exit/enter actions
- Consider tax implications
- Evaluate market timing
- Prioritize recommendations

## Analysis Framework

**Step 1: Load Portfolio State**
- Read latest portfolio file from `.cache/portfolios/latest_*.json`
- Extract holdings, entry prices, allocations, guidance

**Step 2: Gather Current Data**
- Fetch current market prices (if available)
- Review recent news for holdings
- Check fundamental metric changes

**Step 3: Performance Calculation**
```python
# For each stock:
current_return_pct = ((current_price - entry_price) / entry_price) * 100
position_status = compare_vs_stop_loss_and_target(current_price, stop_loss_price, target_price)
allocation_drift_pct = ((current_allocation - target_allocation) / target_allocation) * 100
```

**Step 4: Generate Insights**
- Performance summary (best/worst performers)
- Risk alerts (stop-loss breaches, concentration)
- Rebalancing needs (drift >25%)
- Investment thesis validation

## Output Format

### Portfolio Performance Report

**Executive Summary:**
- Total portfolio value: ₹X (Entry: ₹Y)
- Absolute return: Z%
- Duration: N days
- Holdings: M stocks

**Performance Breakdown:**

| Stock | Entry Price | Current Price | Return % | Status |
|-------|-------------|---------------|----------|--------|
| ABC   | ₹100        | ₹125          | +25%     | ✅ Target |
| XYZ   | ₹200        | ₹180          | -10%     | ⚠️ Watch |

**Allocation Status:**

| Stock | Target % | Current % | Drift | Action |
|-------|----------|-----------|-------|--------|
| ABC   | 10%      | 15%       | +50%  | Trim   |
| XYZ   | 10%      | 7%        | -30%  | Add    |

**Recommendations:**

**🔴 Immediate Actions:**
1. Exit DEF - Stop-loss breached at ₹85 (Entry: ₹100, Stop: ₹85, Current: ₹82)

**🟡 Rebalancing:**
1. Trim ABC by 5% - Overweight due to price appreciation
2. Add XYZ by 3% - Underweight, fundamentals intact

**🟢 Watch List:**
1. Monitor GHI - Approaching stop-loss at ₹95 (Current: ₹98)
2. Review JKL - Nearing target at ₹148 (Target: ₹150)

**Risk Assessment:**
- Concentration risk: IT sector 35% (max recommended: 30%)
- Stop-loss breaches: 1 position
- Target achievements: 2 positions

## Decision Guidelines

**Stop-Loss Breach:**
- Recommend exit if price < stop-loss AND no strong fundamental reason to hold
- If holding despite breach, require clear justification

**Target Achievement:**
- Recommend profit booking if price >= target
- Consider holding if fundamentals improved beyond initial thesis

**Allocation Drift:**
- Rebalance if drift >25% from target
- Trim winners, add to losers (contrarian rebalancing)

**Investment Thesis:**
- Exit if thesis invalidated (fundamental deterioration)
- Review if market outlook changed materially

## Agent Behavior

- **Data-driven**: Base recommendations on quantitative metrics
- **Risk-aware**: Highlight risk factors prominently
- **Actionable**: Provide specific buy/sell/hold recommendations
- **Conservative**: Default to capital preservation when uncertain
- **Transparent**: Show calculations and reasoning
```

#### 3. Security Review Agent

**File:** `.claude/agents/security-reviewer.md`

```markdown
---
name: security-reviewer
description: Security specialist for financial applications. Reviews code for security vulnerabilities, data protection issues, credential management, and compliance concerns. Use when adding authentication, API integrations, or handling sensitive data.
tools: Read, Grep, Glob, Bash
model: inherit
---

# Security Review Agent for Financial Applications

You are a security specialist focusing on Python financial applications with expertise in:
- OWASP Top 10 vulnerabilities
- API security (authentication, authorization, rate limiting)
- Data protection and encryption
- Secure credential management
- Financial application compliance (audit trails, data integrity)

## Security Review Checklist

### 1. Credential Management
**Check for:**
- ❌ Hardcoded API keys, passwords, tokens in source code
- ❌ Credentials in git history or committed files
- ❌ Credentials in log files or error messages
- ✅ All credentials loaded from environment variables
- ✅ `.env` file in `.gitignore`
- ✅ Example `.env.example` file without real credentials

**Review files:**
- All `.py` files for string literals that look like keys/passwords
- `.env` file (should not be in git)
- `config.ini` for sensitive data
- Log files for credential leakage

### 2. Input Validation
**Check for:**
- ❌ SQL injection vulnerabilities (raw SQL with user input)
- ❌ Command injection (user input in shell commands)
- ❌ Path traversal (user-controlled file paths)
- ❌ XSS vulnerabilities (if web interface exists)
- ✅ Parameterized queries for database operations
- ✅ Input sanitization for user queries
- ✅ Whitelisting for allowed values

**Critical areas:**
- User input to database queries
- File path construction
- Shell command execution
- API parameter construction

### 3. API Security
**Check for:**
- ❌ Missing authentication on API endpoints
- ❌ No rate limiting on external API calls
- ❌ API keys transmitted in URLs (use headers)
- ❌ No timeout settings on requests
- ✅ Proper error handling without info leakage
- ✅ Retry logic with exponential backoff
- ✅ API key rotation capability

**Review:**
- Gemini API calls (authentication, error handling)
- Supabase API calls (authentication, connection pooling)
- screener.in session management (secure storage)

### 4. Data Protection
**Check for:**
- ❌ Sensitive data in logs (prices, holdings, PII)
- ❌ Unencrypted storage of sensitive data
- ❌ Sensitive data in error messages
- ❌ Portfolio data accessible without authorization
- ✅ Minimal logging of sensitive information
- ✅ Secure file permissions on data files
- ✅ Database connection encryption (SSL/TLS)

**Review:**
- Logging statements in all agents
- Portfolio JSON files in `.cache/`
- Database connection strings
- Error message content

### 5. Financial Application Specific
**Check for:**
- ❌ Missing audit trail for portfolio decisions
- ❌ No validation of financial calculations
- ❌ Timestamp manipulation possibilities
- ❌ Price/allocation tampering risks
- ✅ Immutable audit logs for transactions
- ✅ Validation of numerical inputs (Decimal for money)
- ✅ Tamper-evident portfolio state files
- ✅ Signature/checksum for critical data

**Review:**
- Portfolio builder output files
- Database migration scripts
- Price/metric calculation code

### 6. Dependency Security
**Check for:**
- ❌ Outdated dependencies with known vulnerabilities
- ❌ Unused dependencies increasing attack surface
- ❌ Dependencies from untrusted sources
- ✅ Regular dependency updates
- ✅ Minimal dependency footprint
- ✅ Dependency pinning in requirements.txt

**Actions:**
```bash
# Check for outdated packages
pip list --outdated

# Security audit (if available)
pip-audit
```

### 7. Error Handling & Logging
**Check for:**
- ❌ Stack traces exposed to users
- ❌ Sensitive data in exception messages
- ❌ Overly verbose error messages
- ✅ Generic error messages to users
- ✅ Detailed errors logged securely
- ✅ Proper log rotation and retention

## Security Review Process

**Step 1: Automated Scans**
```bash
# Search for common issues
grep -r "api_key\s*=\s*['\"]" --include="*.py"  # Hardcoded keys
grep -r "password\s*=\s*['\"]" --include="*.py"  # Hardcoded passwords
grep -r "execute.*%.*" --include="*.py"  # SQL injection risks

# Check .env in git
git ls-files | grep "\.env$"  # Should return nothing

# Review secrets in git history
git log --all --full-history --source -- .env
```

**Step 2: Manual Code Review**
- Focus on authentication/authorization code
- Review database interaction code
- Check API integration points
- Validate error handling paths

**Step 3: Configuration Review**
- `.gitignore` includes sensitive files
- File permissions on sensitive files (600)
- Environment variable usage
- Database connection security

## Output Format

**Security Assessment Report**

**🔴 Critical Vulnerabilities:**
1. File: `agents/portfolio_builder.py:45`
   Issue: API key hardcoded in source
   Risk: Key exposure if code is shared
   Fix: Move to environment variable

**🟡 Medium Risk:**
1. File: `utils/database.py:78`
   Issue: SQL query uses string formatting
   Risk: Potential SQL injection if user input ever added
   Fix: Use parameterized queries

**🟢 Low Risk / Recommendations:**
1. File: `tools/news_scraper.py:120`
   Issue: No timeout on HTTP requests
   Risk: Hanging requests
   Fix: Add timeout parameter

**Security Posture Summary:**
- Critical issues: N
- Medium issues: M
- Low issues: L
- Overall risk: [High/Medium/Low]

**Remediation Priority:**
1. Fix all critical issues immediately
2. Address medium issues before production
3. Low issues can be backlog items

## Agent Behavior

- **Conservative**: Flag potential issues even if uncertain
- **Specific**: Provide exact file paths and line numbers
- **Actionable**: Include code snippets for fixes
- **Educational**: Explain security implications
- **Comprehensive**: Check multiple vulnerability categories
```

### Using Sub-agents

**Manual Invocation:**
```
> Use the code-reviewer agent to review recent changes
> Use the portfolio-analyst agent to analyze my defensive portfolio
> Use the security-reviewer agent to audit the API integration
```

**Automatic Invocation:**
Claude will automatically invoke sub-agents when descriptions match the task:
```
> Review this code for security issues
# Claude invokes security-reviewer agent

> Analyze my portfolio performance
# Claude invokes portfolio-analyst agent
```

### Sub-agent vs Skill: When to Use What?

| Scenario | Use Skill | Use Sub-agent |
|----------|-----------|---------------|
| Teaching methodology (how to analyze markets) | ✅ | ❌ |
| Executing analysis task (analyze this portfolio) | ❌ | ✅ |
| Reusable knowledge (screening criteria) | ✅ | ❌ |
| Isolated task with separate context | ❌ | ✅ |
| Read-only guidance | ✅ | ❌ |
| Task requiring tool execution | ❌ | ✅ |

---

## MCP Servers

### What Are MCP Servers?

MCP (Model Context Protocol) is an open standard for connecting Claude to external tools, databases, APIs, and data sources. Think of it as "plugins" for Claude.

**Key Capabilities:**
- Database connections (PostgreSQL, MySQL, SQLite)
- API integrations (GitHub, Slack, Jira)
- Browser automation (Playwright)
- File systems and search
- Custom integrations via stdio/HTTP

### Current MCP Servers in Portfolio Agent

Your project already has three MCP servers configured:

```json
// From .mcp.json
{
  "mcpServers": {
    "supabase": { ... },      // PostgreSQL database
    "playwright": { ... },    // Browser automation
    "ide": { ... }            // IDE integration
  }
}
```

**Current Usage:**
1. **Supabase**: Portfolio storage, stock data, company enrichment
2. **Playwright**: screener.in web automation, session management
3. **IDE**: Code diagnostics, error checking

### Recommended Additional MCP Servers

#### 1. GitHub MCP Server (Code Management)

**Purpose:** Automate git workflows, PR management, issue tracking

**Installation:**
```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
```

**Use Cases:**
- Automated PR creation for portfolio changes
- Issue tracking for portfolio review tasks
- Code review workflow automation
- Release management

**Example Usage:**
```
> Create a PR for the new portfolio builder changes
> Review comments on PR #45
> Create an issue to investigate XYZ stock performance drop
```

#### 2. PostgreSQL MCP Server (Advanced Database Operations)

**Purpose:** Direct database access with advanced query capabilities

**Installation:**
```bash
# If you want more advanced DB features beyond Supabase MCP
claude mcp add --transport stdio postgres -- \
  npx -y @modelcontextprotocol/server-postgres \
  postgresql://user:pass@host:5432/portfolio_db
```

**Use Cases:**
- Complex analytical queries
- Database migrations
- Performance analysis
- Backup/restore operations

**Example Usage:**
```
> Show me the distribution of portfolio allocations over time
> Optimize the database indexes for portfolio queries
> Export portfolio data for external analysis
```

#### 3. Filesystem Search MCP Server (Enhanced Code Navigation)

**Purpose:** Advanced file and content search capabilities

**Installation:**
```bash
claude mcp add --transport stdio search -- \
  npx -y @modelcontextprotocol/server-search
```

**Use Cases:**
- Cross-repository code search
- Finding similar code patterns
- Dependency analysis
- Documentation search

#### 4. Slack MCP Server (Notifications & Collaboration)

**Purpose:** Send portfolio alerts and collaborate with team

**Installation:**
```bash
claude mcp add --transport http slack https://slack.com/api/mcp \
  --env SLACK_TOKEN=your-token
```

**Use Cases:**
- Send stop-loss breach alerts to Slack
- Daily portfolio summary notifications
- Team collaboration on portfolio decisions
- Alert on significant market movements

**Example Usage:**
```python
# In portfolio manager agent:
# If stop-loss breached, send Slack alert
if position.current_price < position.stop_loss_price:
    slack.send_message(
        channel="#portfolio-alerts",
        message=f"🔴 ALERT: {position.name} breached stop-loss at ₹{position.current_price}"
    )
```

#### 5. Python REPL MCP Server (Live Calculations)

**Purpose:** Execute Python code for live calculations and analysis

**Installation:**
```bash
claude mcp add --transport stdio python -- \
  npx -y @modelcontextprotocol/server-python
```

**Use Cases:**
- Quick portfolio calculations
- Data transformations
- Statistical analysis
- Backtesting simulations

**Example Usage:**
```
> Calculate the Sharpe ratio for this portfolio
> Run a Monte Carlo simulation on allocation strategies
> Analyze correlation between holdings
```

### MCP Server Configuration Best Practices

**Scope Selection:**

```
Local scope (~/.claude.json):     Personal/sensitive servers
Project scope (.claude/mcp.json): Team-shared servers
User scope (~/.claude.json):      All-projects servers
```

**For Portfolio Agent:**
```bash
# Project scope (team shared)
cd /path/to/portfolio-agent
claude mcp add --scope project github https://...
claude mcp add --scope project slack https://...

# Local scope (personal database credentials)
claude mcp add --scope local postgres postgresql://...
```

**Security Considerations:**

```bash
# Use environment variables for sensitive data
{
  "mcpServers": {
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }
  }
}

# Set environment variable
export DATABASE_URL="postgresql://user:pass@host:5432/db"
```

### Managing MCP Servers

```bash
# List all configured servers
claude mcp list

# Get server details
claude mcp get supabase

# Remove a server
claude mcp remove server-name

# Reset project-specific approvals
claude mcp reset-project-choices
```

---

## Hooks

### What Are Hooks?

Hooks are custom scripts that run at specific points in Claude Code's lifecycle. They provide **deterministic control** - ensuring actions always happen, rather than relying on Claude to choose.

**Key Benefit:** Automation, compliance, and quality control enforced at the system level.

### Hook Events

| Event | When it fires | Use cases |
|-------|---------------|-----------|
| **PreToolUse** | Before any tool call | Block dangerous operations, validate inputs |
| **PostToolUse** | After tool execution | Format code, run linters, audit changes |
| **PermissionRequest** | Before permission dialog | Auto-approve/deny specific actions |
| **UserPromptSubmit** | When user submits prompt | Add context, validate input, logging |
| **Notification** | When Claude needs attention | Custom notifications |
| **Stop** | After Claude finishes response | Post-processing, logging |
| **SessionStart** | At session initialization | Setup environment, logging |
| **SessionEnd** | At session termination | Cleanup, logging |

### Practical Hooks for Portfolio Agent

#### 1. Auto-format Python Code (PostToolUse)

**Purpose:** Ensure all Python code follows PEP 8 standards

**Configuration:** `~/.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | { read file_path; if echo \"$file_path\" | grep -q '\\.py$'; then black --line-length 100 \"$file_path\" 2>/dev/null || true; fi; }"
          }
        ]
      }
    ]
  }
}
```

**Benefit:** All code automatically formatted, consistent style across team

#### 2. Auto-format Portfolio JSON Files (PostToolUse)

**Purpose:** Keep portfolio JSON files properly formatted for git diffs

**Configuration:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | { read file; if echo \"$file\" | grep -q 'portfolio.*\\.json$'; then jq --indent 2 '.' \"$file\" > \"${file}.tmp\" && mv \"${file}.tmp\" \"$file\"; fi; }"
          }
        ]
      }
    ]
  }
}
```

**Benefit:** Clean git diffs, easy code review of portfolio changes

#### 3. Protect Sensitive Files (PreToolUse)

**Purpose:** Prevent accidental modification of critical files

**Configuration:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -c \"import json, sys; data=json.load(sys.stdin); path=data.get('tool_input',{}).get('file_path',''); protected=['.env', 'config.ini', '.git/', '.cache/portfolios/']; sys.exit(2) if any(p in path for p in protected) else sys.exit(0)\""
          }
        ]
      }
    ]
  }
}
```

**Benefit:** Prevents accidental overwrite of production portfolios or credentials

#### 4. Audit Portfolio Changes (PostToolUse)

**Purpose:** Log all portfolio file changes for audit trail

**Configuration:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '\"[\\(.timestamp // now)] Modified: \\(.tool_input.file_path // \"unknown\")\"' | { read line; if echo \"$line\" | grep -q 'portfolio.*\\.json'; then echo \"$line\" >> .cache/audit_log.txt; fi; }"
          }
        ]
      }
    ]
  }
}
```

**Benefit:** Complete audit trail of who changed what portfolio data

#### 5. Run Tests After Code Changes (PostToolUse)

**Purpose:** Automatically run tests when agent code is modified

**Configuration:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | { read file; if echo \"$file\" | grep -q 'agents/.*\\.py$'; then pytest tests/ -v --tb=short 2>&1 | head -20; fi; }"
          }
        ]
      }
    ]
  }
}
```

**Benefit:** Immediate feedback on test failures

#### 6. Log All Bash Commands (PreToolUse)

**Purpose:** Track all shell commands executed by agents

**Configuration:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '\"[\" + (now | strftime(\"%Y-%m-%d %H:%M:%S\")) + \"] \" + .tool_input.command' >> ~/.claude/bash_commands.log"
          }
        ]
      }
    ]
  }
}
```

**Benefit:** Security audit, debugging, tracking agent actions

#### 7. Validate Portfolio Schema (PostToolUse)

**Purpose:** Ensure portfolio JSON files match expected schema

**Script:** `scripts/validate_portfolio.py`

```python
#!/usr/bin/env python3
import json
import sys

# Read hook input
hook_data = json.load(sys.stdin)
file_path = hook_data.get('tool_input', {}).get('file_path', '')

if 'portfolio' not in file_path or not file_path.endswith('.json'):
    sys.exit(0)  # Not a portfolio file, skip

# Validate schema
try:
    with open(file_path, 'r') as f:
        portfolio = json.load(f)

    required_fields = ['profile', 'total_capital', 'stocks']
    stock_required = ['name', 'ticker', 'entry_price', 'allocation_pct', 'stop_loss_price', 'target_price']

    # Check top-level fields
    for field in required_fields:
        if field not in portfolio:
            print(f"❌ Missing required field: {field}")
            sys.exit(2)  # Block action

    # Check stock fields
    for stock in portfolio.get('stocks', []):
        for field in stock_required:
            if field not in stock:
                print(f"❌ Stock missing field: {field}")
                sys.exit(2)

    print(f"✅ Portfolio schema valid: {file_path}")
    sys.exit(0)

except Exception as e:
    print(f"❌ Schema validation failed: {str(e)}")
    sys.exit(2)
```

**Hook Configuration:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 scripts/validate_portfolio.py"
          }
        ]
      }
    ]
  }
}
```

**Benefit:** Prevents malformed portfolio files, ensures data integrity

### Hook Return Values

**Exit Codes:**
- **0**: Success, continue
- **2**: Block action, provide feedback to Claude
- **Other**: Error, Claude will see the error message

**JSON Response (Advanced):**
```bash
# Return structured feedback
echo '{"action": "blocked", "reason": "Attempting to modify production portfolio", "suggestion": "Create a backup first"}' | jq
exit 2
```

### Managing Hooks

**Via CLI:**
```bash
# Interactive hook configuration
/hooks

# Follow prompts to add/remove hooks
```

**Via JSON:**
Edit `~/.claude/settings.json` directly for fine-grained control

---

## Claude Agent SDK

### What Is the Agent SDK?

The Agent SDK provides a **programmatic interface** to Claude Code. Build autonomous agents in Python or TypeScript with full control over tools, permissions, and execution flow.

**Key Benefits:**
- **Production deployment**: Run agents as services, cron jobs, or APIs
- **Programmatic control**: Full control over agent behavior
- **Custom integrations**: Embed in existing applications
- **Batch processing**: Run multiple portfolio analyses in sequence

### Installation

**Prerequisites:**
```bash
# Install Claude Code CLI first
brew install --cask claude-code
# or
npm install -g @anthropic-ai/claude-code
```

**Install SDK:**
```bash
# Python
pip install claude-agent-sdk

# TypeScript
npm install @anthropic-ai/claude-agent-sdk
```

**Set API Key:**
```bash
export ANTHROPIC_API_KEY=your-api-key
```

### Basic Agent Example

**Python:**
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Analyze the portfolio_builder_agent.py file for code quality",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep", "Glob"],
            permission_mode="default"
        )
    ):
        if hasattr(message, "result"):
            print(message.result)

asyncio.run(main())
```

**TypeScript:**
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Analyze the portfolio_builder_agent.py file for code quality",
  options: {
    allowedTools: ["Read", "Grep", "Glob"],
    permissionMode: "default"
  }
})) {
  if ("result" in message) console.log(message.result);
}
```

### Portfolio Agent SDK Implementation

#### 1. Automated Portfolio Builder Service

**File:** `services/portfolio_builder_service.py`

```python
import asyncio
import json
from datetime import datetime
from claude_agent_sdk import query, ClaudeAgentOptions

async def build_portfolio_automated(
    investor_profile: str,
    capital: float,
    output_dir: str = ".cache/portfolios"
):
    """
    Build portfolio using Claude Agent SDK with full automation

    Args:
        investor_profile: "aggressive" or "defensive"
        capital: Initial capital to deploy
        output_dir: Where to save portfolio JSON

    Returns:
        dict: Portfolio data
    """

    prompt = f"""
    Build an investment portfolio for an {investor_profile} investor with ₹{capital:,.0f} to deploy.

    Requirements:
    1. Conduct market research for current Indian market conditions
    2. Screen stocks using fundamental analysis (screener.in)
    3. Analyze news sentiment for shortlisted stocks
    4. Allocate capital with proper position sizing
    5. Set stop-loss and target prices based on profile
    6. Save final portfolio to {output_dir}/

    Use the portfolio builder agent tools and follow the established methodology.
    """

    portfolio_data = None

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[
                "Read", "Write", "Edit", "Bash",
                "Glob", "Grep", "WebSearch", "WebFetch"
            ],
            permission_mode="acceptEdits",  # Auto-approve file edits
            mcp_servers={
                "supabase": {
                    "command": "npx",
                    "args": ["-y", "@supabase/mcp"]
                },
                "playwright": {
                    "command": "npx",
                    "args": ["-y", "@playwright/mcp@latest"]
                }
            }
        )
    ):
        # Handle different message types
        if hasattr(message, "subtype"):
            if message.subtype == "tool_use":
                print(f"🔧 Tool: {message.tool_name}")
            elif message.subtype == "tool_result":
                # Check if portfolio was written
                if message.tool_name == "Write" and "portfolio" in str(message.result):
                    # Extract portfolio path from result
                    pass

        if hasattr(message, "result"):
            print(f"✅ Result: {message.result[:200]}...")
            # Parse result for portfolio data
            portfolio_data = message.result

    return portfolio_data

# Example usage
if __name__ == "__main__":
    result = asyncio.run(build_portfolio_automated(
        investor_profile="aggressive",
        capital=500000
    ))
    print(f"Portfolio built: {result}")
```

#### 2. Scheduled Portfolio Manager Service

**File:** `services/portfolio_manager_service.py`

```python
import asyncio
import schedule
import time
from claude_agent_sdk import query, ClaudeAgentOptions
from datetime import datetime

async def review_portfolio_automated(profile: str):
    """
    Daily portfolio review using Claude Agent SDK

    Args:
        profile: Investor profile ("aggressive" or "defensive")

    Returns:
        dict: Review report with recommendations
    """

    prompt = f"""
    Review the latest {profile} portfolio and provide rebalancing recommendations.

    Tasks:
    1. Load portfolio from .cache/portfolios/latest_{profile}.json
    2. Check current prices for all holdings
    3. Identify stop-loss breaches and target achievements
    4. Analyze allocation drift
    5. Review recent news for holdings
    6. Generate rebalancing recommendations
    7. Save review report to logs/

    Use the portfolio analyst agent capabilities.
    """

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Bash", "Grep", "Glob", "WebFetch", "Write"],
            permission_mode="acceptEdits",
            agents={
                "portfolio-analyst": {
                    "description": "Portfolio analysis expert",
                    "prompt": open(".claude/agents/portfolio-analyst.md").read(),
                    "tools": ["Read", "Bash", "Grep", "Glob", "WebFetch"]
                }
            }
        )
    ):
        if hasattr(message, "result"):
            print(f"📊 Review: {message.result[:300]}...")
            return message.result

def daily_portfolio_review():
    """Scheduled daily review"""
    print(f"[{datetime.now()}] Starting daily portfolio review...")

    # Review aggressive portfolio
    asyncio.run(review_portfolio_automated("aggressive"))

    # Review defensive portfolio
    asyncio.run(review_portfolio_automated("defensive"))

    print(f"[{datetime.now()}] Daily review complete.")

# Schedule daily review at 6:00 PM IST (after market close)
schedule.every().day.at("18:00").do(daily_portfolio_review)

if __name__ == "__main__":
    print("📅 Portfolio Manager Service Started")
    print("⏰ Scheduled: Daily at 6:00 PM IST")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
```

#### 3. Session-based Multi-step Analysis

**File:** `examples/sdk_session_example.py`

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def multi_step_portfolio_analysis():
    """
    Demonstrate session persistence across multiple queries
    """
    session_id = None

    # Step 1: Initial market research
    print("=== Step 1: Market Research ===")
    async for message in query(
        prompt="Research current Indian market trends and sector opportunities",
        options=ClaudeAgentOptions(
            allowed_tools=["WebSearch", "WebFetch", "Read", "Write"],
            permission_mode="acceptEdits"
        )
    ):
        if hasattr(message, 'subtype') and message.subtype == 'init':
            session_id = message.session_id
            print(f"📝 Session ID: {session_id}")

        if hasattr(message, "result"):
            print(f"✅ Market research complete")

    # Step 2: Stock screening (with context from Step 1)
    print("\n=== Step 2: Stock Screening ===")
    async for message in query(
        prompt="Based on the market research, screen high-quality stocks in identified sectors",
        options=ClaudeAgentOptions(
            resume=session_id,  # Continue with previous context
            allowed_tools=["Bash", "Read", "Write"]
        )
    ):
        if hasattr(message, "result"):
            print(f"✅ Stock screening complete")

    # Step 3: News analysis (with full context from Steps 1-2)
    print("\n=== Step 3: News Analysis ===")
    async for message in query(
        prompt="Analyze recent news for the shortlisted stocks",
        options=ClaudeAgentOptions(
            resume=session_id,  # Continue with all previous context
            allowed_tools=["WebSearch", "WebFetch", "Read", "Write"]
        )
    ):
        if hasattr(message, "result"):
            print(f"✅ News analysis complete")

    # Step 4: Final portfolio construction (with complete context)
    print("\n=== Step 4: Portfolio Construction ===")
    async for message in query(
        prompt="Build final portfolio with allocations, targets, and stop-losses",
        options=ClaudeAgentOptions(
            resume=session_id,
            allowed_tools=["Read", "Write", "Bash"]
        )
    ):
        if hasattr(message, "result"):
            print(f"✅ Portfolio construction complete")
            print(f"\n📊 Final Output:\n{message.result}")

if __name__ == "__main__":
    asyncio.run(multi_step_portfolio_analysis())
```

#### 4. Custom Hooks in SDK

**File:** `examples/sdk_hooks_example.py`

```python
import asyncio
from datetime import datetime
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher

async def audit_file_change(input_data, tool_use_id, context):
    """Hook: Log all portfolio file changes"""
    file_path = input_data.get('tool_input', {}).get('file_path', 'unknown')

    if 'portfolio' in file_path:
        with open('.cache/audit_log.txt', 'a') as f:
            f.write(f"[{datetime.now()}] Modified: {file_path}\n")

    return {}  # Empty return = allow action

async def validate_portfolio_json(input_data, tool_use_id, context):
    """Hook: Validate portfolio schema"""
    file_path = input_data.get('tool_input', {}).get('file_path', '')

    if 'portfolio' in file_path and file_path.endswith('.json'):
        # Read the new content
        new_content = input_data.get('tool_input', {}).get('content', '')

        try:
            import json
            portfolio = json.loads(new_content)

            # Validate required fields
            required = ['profile', 'total_capital', 'stocks']
            if not all(field in portfolio for field in required):
                return {
                    "action": "blocked",
                    "reason": "Portfolio missing required fields",
                    "suggestion": "Ensure portfolio has: profile, total_capital, stocks"
                }

            print(f"✅ Portfolio schema valid: {file_path}")

        except json.JSONDecodeError as e:
            return {
                "action": "blocked",
                "reason": f"Invalid JSON: {str(e)}",
                "suggestion": "Fix JSON syntax errors"
            }

    return {}

async def main():
    async for message in query(
        prompt="Build an aggressive portfolio with ₹500,000",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Bash", "WebSearch"],
            permission_mode="acceptEdits",
            hooks={
                "PostToolUse": [
                    HookMatcher(
                        matcher="Edit|Write",
                        hooks=[audit_file_change, validate_portfolio_json]
                    )
                ]
            }
        )
    ):
        if hasattr(message, "result"):
            print(message.result)

if __name__ == "__main__":
    asyncio.run(main())
```

### SDK Deployment Patterns

#### 1. REST API Service

**File:** `api/claude_agent_api.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

app = FastAPI(title="Portfolio Agent API")

class PortfolioBuildRequest(BaseModel):
    profile: str  # "aggressive" or "defensive"
    capital: float

class PortfolioReviewRequest(BaseModel):
    portfolio_id: str

@app.post("/api/portfolio/build")
async def build_portfolio(request: PortfolioBuildRequest):
    """Build a new portfolio via Claude Agent SDK"""

    prompt = f"""
    Build {request.profile} portfolio with ₹{request.capital:,.0f}.
    Follow standard methodology and save to .cache/portfolios/
    """

    result = None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Bash", "WebSearch", "WebFetch"],
            permission_mode="acceptEdits"
        )
    ):
        if hasattr(message, "result"):
            result = message.result

    if result:
        return {"status": "success", "portfolio": result}
    else:
        raise HTTPException(status_code=500, detail="Portfolio build failed")

@app.post("/api/portfolio/review")
async def review_portfolio(request: PortfolioReviewRequest):
    """Review existing portfolio via Claude Agent SDK"""

    prompt = f"""
    Review portfolio {request.portfolio_id}.
    Load from .cache/portfolios/, analyze performance, generate recommendations.
    """

    result = None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Bash", "WebFetch"],
            permission_mode="default"
        )
    ):
        if hasattr(message, "result"):
            result = message.result

    if result:
        return {"status": "success", "review": result}
    else:
        raise HTTPException(status_code=500, detail="Review failed")

# Run with: uvicorn api.claude_agent_api:app --reload
```

#### 2. CLI Tool

**File:** `cli/portfolio_cli.py`

```python
#!/usr/bin/env python3
import asyncio
import click
from claude_agent_sdk import query, ClaudeAgentOptions

@click.group()
def cli():
    """Portfolio Agent CLI powered by Claude Agent SDK"""
    pass

@cli.command()
@click.option("--profile", type=click.Choice(["aggressive", "defensive"]), required=True)
@click.option("--capital", type=float, required=True)
def build(profile, capital):
    """Build a new portfolio"""
    click.echo(f"🏗️  Building {profile} portfolio with ₹{capital:,.0f}...")

    async def run():
        async for message in query(
            prompt=f"Build {profile} portfolio with ₹{capital}",
            options=ClaudeAgentOptions(
                allowed_tools=["Read", "Write", "Bash", "WebSearch"],
                permission_mode="acceptEdits"
            )
        ):
            if hasattr(message, "result"):
                click.echo(f"✅ {message.result}")

    asyncio.run(run())

@cli.command()
@click.argument("profile")
def review(profile):
    """Review existing portfolio"""
    click.echo(f"📊 Reviewing {profile} portfolio...")

    async def run():
        async for message in query(
            prompt=f"Review latest {profile} portfolio",
            options=ClaudeAgentOptions(
                allowed_tools=["Read", "Bash", "WebFetch"]
            )
        ):
            if hasattr(message, "result"):
                click.echo(f"📈 {message.result}")

    asyncio.run(run())

if __name__ == "__main__":
    cli()

# Usage:
# ./cli/portfolio_cli.py build --profile aggressive --capital 500000
# ./cli/portfolio_cli.py review aggressive
```

---

## Implementation Roadmap

### Phase 1: Skills Setup (Week 1)

**Objective:** Create foundational skills for market analysis and screening

**Tasks:**
1. ✅ Create `.claude/skills/` directory structure
2. ✅ Implement `market-analysis` skill
3. ✅ Implement `fundamental-screening` skill
4. ✅ Implement `portfolio-review` skill
5. ✅ Test skills with sample queries
6. ✅ Document skill usage in CLAUDE.md

**Acceptance Criteria:**
- Skills automatically activate on relevant queries
- Consistent methodology applied across agents
- Team can review/update skills via git

**Estimated Effort:** 2-3 days

---

### Phase 2: Sub-agents Implementation (Week 2)

**Objective:** Convert existing agents to sub-agents for better isolation

**Tasks:**
1. ✅ Create `.claude/agents/` directory
2. ✅ Implement `code-reviewer` sub-agent
3. ✅ Implement `portfolio-analyst` sub-agent
4. ✅ Implement `security-reviewer` sub-agent
5. ✅ Test sub-agent invocation (manual and automatic)
6. ✅ Compare context isolation vs. current approach

**Acceptance Criteria:**
- Sub-agents properly isolate context
- Automatic invocation works based on descriptions
- No context pollution between agents

**Estimated Effort:** 3-4 days

---

### Phase 3: MCP Server Expansion (Week 3)

**Objective:** Add GitHub, Slack, and advanced database integrations

**Tasks:**
1. ✅ Install GitHub MCP server for PR workflows
2. ✅ Install Slack MCP server for alerts
3. ✅ Configure Slack webhooks for stop-loss alerts
4. ✅ Test GitHub PR creation workflow
5. ✅ Set up daily portfolio summary Slack notifications

**Acceptance Criteria:**
- GitHub PR workflows automated
- Slack alerts working for portfolio events
- Team receives daily summaries

**Estimated Effort:** 2-3 days

---

### Phase 4: Hooks for Automation (Week 4)

**Objective:** Implement hooks for code quality and compliance

**Tasks:**
1. ✅ Implement auto-format hooks (Python, JSON)
2. ✅ Implement file protection hooks (.env, portfolios)
3. ✅ Implement audit logging hooks
4. ✅ Implement portfolio schema validation hook
5. ✅ Test all hooks with sample operations

**Acceptance Criteria:**
- All code auto-formatted on save
- Sensitive files protected from modification
- Complete audit trail of portfolio changes
- Invalid portfolios blocked by validation

**Estimated Effort:** 2-3 days

---

### Phase 5: Agent SDK Production Services (Week 5-6)

**Objective:** Build production-ready services using Agent SDK

**Tasks:**
1. ✅ Implement automated portfolio builder service
2. ✅ Implement scheduled portfolio manager service
3. ✅ Build REST API for portfolio operations
4. ✅ Create CLI tool for manual operations
5. ✅ Set up cron jobs for daily reviews
6. ✅ Deploy to production environment

**Acceptance Criteria:**
- Portfolio builder runs fully automated
- Daily reviews execute via cron
- REST API accessible for frontend
- CLI tool functional for manual tasks

**Estimated Effort:** 5-7 days

---

## Best Practices

### 1. Skill Design

**✅ Do:**
- Include trigger keywords in descriptions
- Keep SKILL.md under 500 lines
- Use `allowed-tools` to restrict capabilities
- Version control skills via git
- Test skills with sample queries

**❌ Don't:**
- Make skills too generic (Claude won't know when to use)
- Include implementation code in skills (guidance only)
- Duplicate content across skills
- Create skills for one-time tasks

---

### 2. Sub-agent Design

**✅ Do:**
- Create specialized agents for focused tasks
- Use descriptive names matching trigger phrases
- Document agent capabilities clearly
- Test both manual and automatic invocation
- Use appropriate permission modes

**❌ Don't:**
- Create overlapping agents (confuses Claude)
- Give agents overly broad capabilities
- Forget to test context isolation
- Mix research and execution in same agent

---

### 3. MCP Server Management

**✅ Do:**
- Use project scope for team-shared servers
- Use environment variables for credentials
- Document all configured servers
- Test servers individually before integration
- Monitor server logs for issues

**❌ Don't:**
- Hardcode credentials in MCP config
- Add servers without testing
- Configure servers at wrong scope
- Ignore authentication failures

---

### 4. Hook Implementation

**✅ Do:**
- Start with simple hooks, add complexity gradually
- Test hooks thoroughly before enabling
- Use exit code 0 for success, 2 for blocking
- Provide helpful feedback messages
- Log hook execution for debugging

**❌ Don't:**
- Create hooks with side effects (idempotent only)
- Block critical operations without clear messages
- Forget to handle edge cases
- Make hooks slow (impacts UX)

---

### 5. Agent SDK Development

**✅ Do:**
- Use session persistence for multi-step flows
- Handle all message types properly
- Implement proper error handling
- Use appropriate permission modes
- Test with various prompts

**❌ Don't:**
- Ignore message subtypes (miss important events)
- Use `bypassPermissions` in production
- Forget to set timeouts on API calls
- Deploy without thorough testing

---

## Conclusion

Claude Code's advanced features provide powerful capabilities for enhancing the portfolio agent system:

1. **Skills** - Centralized domain knowledge for consistent strategy application
2. **Sub-agents** - Specialized experts with isolated contexts
3. **MCP Servers** - Seamless integration with external services
4. **Hooks** - Automated quality control and compliance
5. **Agent SDK** - Production-ready deployment flexibility

**Recommended Next Steps:**

1. **Immediate (This Week):**
   - Create the three core skills (market-analysis, fundamental-screening, portfolio-review)
   - Test skills with existing portfolio builder agent

2. **Short-term (Next 2-4 Weeks):**
   - Implement custom sub-agents (code-reviewer, portfolio-analyst, security-reviewer)
   - Add GitHub and Slack MCP servers
   - Set up critical hooks (auto-format, file protection)

3. **Medium-term (Next 1-2 Months):**
   - Build Agent SDK services for automation
   - Deploy scheduled portfolio manager
   - Create REST API for frontend integration

4. **Long-term (3+ Months):**
   - Expand MCP integrations (broker APIs, data providers)
   - Advanced hooks for compliance and auditing
   - Full production deployment with monitoring

By systematically implementing these features, the portfolio agent system will become more robust, maintainable, and production-ready.

---

**Document Version:** 1.0
**Last Updated:** December 27, 2025
**Author:** Portfolio Agent Development Team
**Next Review:** January 27, 2026
