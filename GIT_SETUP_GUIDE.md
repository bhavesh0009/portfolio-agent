# Git Repository Setup Guide

## ✅ Security Pre-Flight Checklist

Your repository has been prepared for safe Git push with the following protections:

### Protected Sensitive Files

All sensitive files are properly excluded via `.gitignore`:

- ✅ **Environment variables** (`.env`) - Contains API keys and credentials
- ✅ **Database files** (`*.db`, `*.sqlite`) - Contains user portfolio data
- ✅ **Cache directory** (`.cache/`) - Contains screening results, portfolios
- ✅ **Virtual environment** (`.venv/`) - Python packages
- ✅ **Node modules** (`frontend/node_modules/`) - Frontend dependencies
- ✅ **Log files** (`logs/`) - Runtime logs
- ✅ **Backup files** (`*.bak`) - Portfolio backups
- ✅ **Playwright auth** (`.playwright-mcp/`) - Session cookies

### Safe Template Provided

- ✅ `.env.example` - Template with placeholder values (safe to commit)

### No Hardcoded Secrets

- ✅ Verified: No API keys or credentials in code
- ✅ All secrets loaded from environment variables

---

## 🚀 Initialize Git Repository

### Step 1: Initialize Git

```bash
# Initialize git repository
git init

# Verify .gitignore is working
git status
```

**Expected output:** You should NOT see:
- `.env` file
- `.cache/` directory
- `portfolio.db` file
- `node_modules/` directory
- `.venv/` directory

If you see any of these, **STOP** and check your `.gitignore`.

### Step 2: Add Files

```bash
# Add all files (sensitive files are excluded by .gitignore)
git add .

# Verify what will be committed
git status
```

**Expected files to be committed:**
- Source code (`*.py`, `*.js`, `*.ts`, `*.tsx`)
- Configuration files (`config.ini`, `requirements.txt`, `package.json`)
- `.env.example` (template only)
- `.gitignore`
- Documentation (`*.md`)
- Empty directory markers (`logs/.gitkeep`)

**Files that should NOT appear:**
- `.env` (CRITICAL - contains real secrets)
- `.cache/` (contains portfolio data)
- `*.db` files (database)
- `node_modules/`
- `.venv/`
- `logs/*.log`

### Step 3: First Commit

```bash
# Create initial commit
git commit -m "Initial commit: Portfolio Agent System

- Multi-agent portfolio builder and manager
- Stock screening with screener.in (335+ metrics)
- News analysis and market research agents
- Symbol validation and price tracking
- Frontend dashboard with Next.js
- Automatic daily portfolio monitoring"
```

### Step 4: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (e.g., `portfolio-agent`)
3. **IMPORTANT:** Leave it empty (don't initialize with README)
4. Copy the repository URL

### Step 5: Push to GitHub

```bash
# Add remote (replace with your actual repository URL)
git remote add origin https://github.com/YOUR_USERNAME/portfolio-agent.git

# Verify remote
git remote -v

# Push to main branch
git branch -M main
git push -u origin main
```

---

## 🔒 Security Verification After Push

After pushing, verify no secrets were exposed:

### 1. Check GitHub Repository

Visit your repository on GitHub and verify:

- ❌ `.env` file is NOT visible
- ❌ `.cache/` directory is NOT visible
- ❌ `portfolio.db` is NOT visible
- ✅ `.env.example` IS visible (safe template)
- ✅ Source code IS visible

### 2. Search for Secrets (GitHub)

Use GitHub's search on your repository:

- Search for: `AIzaSy` (Gemini API key prefix)
- Search for: `SCREENER_PASSWORD`
- Search for: Your email address

**Expected:** No results found

### 3. Clone Test (Optional but Recommended)

```bash
# Clone to a different directory to test
cd /tmp
git clone https://github.com/YOUR_USERNAME/portfolio-agent.git test-clone
cd test-clone

# Verify .env does NOT exist
ls -la | grep .env

# Should only show .env.example
```

---

## 🛡️ What If Secrets Were Pushed?

If you accidentally pushed secrets (`.env` file or database), **DO NOT PANIC**:

### Immediate Actions

1. **Revoke compromised credentials immediately:**
   - Generate new Gemini API key: https://ai.google.dev/
   - Change screener.in password
   - Update `.env` with new credentials

2. **Remove secrets from Git history:**

```bash
# Install BFG Repo-Cleaner
# Download from: https://rtyley.github.io/bfg-repo-cleaner/

# Remove .env from entire Git history
java -jar bfg.jar --delete-files .env

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (overwrites GitHub history)
git push origin --force --all
```

3. **Verify removal on GitHub**

4. **Update all team members** to re-clone the repository

---

## 📋 Recommended `.gitignore` Sections

Your `.gitignore` now includes:

```gitignore
# Environment variables (CRITICAL)
.env
.env.local
.env.*.local

# Cache directory (CRITICAL - Contains portfolio data)
.cache/
*.cache

# Database files (CRITICAL - User data)
*.db
*.db-journal
*.sqlite

# Virtual environments
.venv/
venv/

# Frontend
frontend/node_modules/
frontend/.next/
frontend/out/

# Logs
logs/
*.log

# Backup files
*.bak

# Playwright sessions
.playwright-mcp/
```

---

## 🔄 Daily Git Workflow

After initial setup, use this workflow:

```bash
# Check status
git status

# Add changes
git add .

# Commit with descriptive message
git commit -m "Add feature: Stock symbol validation"

# Push to GitHub
git push
```

**Always verify before committing:**
```bash
# See what will be committed
git diff --cached

# See which files will be added
git status
```

---

## 🚨 Never Commit These Files

**CRITICAL - NEVER COMMIT:**

| File/Directory | Why | Contains |
|----------------|-----|----------|
| `.env` | Credentials | API keys, passwords, emails |
| `.cache/` | User data | Portfolios, screening results |
| `*.db` | Database | Stock prices, portfolio holdings |
| `.venv/` | Dependencies | 500MB+ of Python packages |
| `node_modules/` | Dependencies | 200MB+ of npm packages |
| `logs/` | Runtime data | Execution logs, debug info |
| `*.bak` | Backups | May contain sensitive data |

---

## 📝 Setting Up on New Machine

When someone clones the repository:

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/portfolio-agent.git
cd portfolio-agent

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Use your preferred editor (nano, vim, code, etc.)
nano .env

# Install Python dependencies
uv pip sync requirements.txt

# Install Playwright
playwright install chromium

# Install frontend dependencies
cd frontend
npm install
cd ..

# Create required directories
mkdir -p logs .cache

# Run the system
python examples/run_portfolio_builder.py
```

---

## 🔐 Environment Variables Reference

Required in `.env` (never commit this file):

```bash
# Screener.in (required for stock screening)
SCREENER_EMAIL=your_email@example.com
SCREENER_PASSWORD=your_password

# Google Gemini (required for AI agents)
GEMINI_API_KEY=your_api_key_here

# Model configuration (optional, has defaults)
GEMINI_HIGH_MODEL=gemini-2.5-pro
GEMINI_MID_MODEL=gemini-2.5-flash
GEMINI_LOW_MODEL=gemini-2.5-flash-lite
```

---

## ✅ Final Pre-Push Checklist

Before `git push`, verify:

- [ ] `.env` is in `.gitignore`
- [ ] `.cache/` is in `.gitignore`
- [ ] `*.db` is in `.gitignore`
- [ ] `.env.example` has NO real credentials
- [ ] `git status` shows NO sensitive files
- [ ] Ran `git diff --cached` to review changes
- [ ] Commit message is descriptive

---

## 📚 Additional Resources

- **Git Basics:** https://git-scm.com/book/en/v2/Getting-Started-Git-Basics
- **GitHub Docs:** https://docs.github.com/en/get-started
- **BFG Repo-Cleaner:** https://rtyley.github.io/bfg-repo-cleaner/ (for removing secrets)
- **.gitignore Templates:** https://github.com/github/gitignore

---

## 🆘 Need Help?

If you're unsure about anything:

1. **DO NOT PUSH** until you're confident
2. Run `git status` and review what will be committed
3. Check if any file paths look suspicious
4. Ask for a second review before pushing

**Remember:** It's easier to prevent secrets from being pushed than to remove them later!

---

**Last Updated:** 2025-01-09
**Status:** ✅ Ready for Initial Push
