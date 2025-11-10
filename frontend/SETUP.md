# Portfolio Tracker - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## What You'll See

### Portfolio Overview (Top Section)
- **Total Capital**: Amount deployed across all stocks
- **Total Stocks**: Number of positions in portfolio
- **Top Sector**: Highest allocated sector
- **Sector Distribution**: Visual breakdown of allocations

### Stock Cards (Grid)
Each card shows:
- Stock name, ticker, sector
- Entry price and allocation
- Target price (upside potential)
- Stop-loss price (risk management)
- Key metrics: ROCE, ROE, D/E
- Investment rationale

### Stock Details (Click any card)
- Full investment thesis
- Market outlook and stock rationale
- Holding period recommendation
- Exit triggers (when to sell)
- Review triggers (when to reassess)
- Complete financial metrics
- News sentiment

## Tech Stack

- **Next.js 14** - React framework (App Router)
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **better-sqlite3** - Database
- **Lucide Icons** - UI icons

## Database Connection

The app reads from: `../.cache/portfolio.db`

Make sure you've run the portfolio builder:
```bash
cd ..
python agents/portfolio_builder_agent_simple.py
```

## Build for Production

```bash
npm run build
npm run start
```

## Color Scheme

- **Primary**: Blue gradient (portfolio header)
- **Success**: Green (targets, positive metrics)
- **Danger**: Red (stop-loss, exit triggers)
- **Warning**: Yellow (review triggers)
- **Neutral**: Gray (general info)

## Responsive Design

- Mobile: Single column
- Tablet: 2 columns
- Desktop: 3 columns

## Troubleshooting

**"No active portfolio found"**
- Run the portfolio builder agent first
- Check `../.cache/portfolio.db` exists

**Module errors**
- Run `npm install` in the frontend directory

**Port 3000 already in use**
- Use `npm run dev -- -p 3001` to use different port
