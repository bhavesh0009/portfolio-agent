# Portfolio Tracker Frontend

A beautiful, modern Next.js frontend for tracking and visualizing your AI-powered investment portfolio.

## Features

- **Real-time Portfolio Overview**: View your total capital, stock count, and sector distribution
- **Beautiful Stock Cards**: Each stock displayed with entry price, target, stop-loss, and key metrics
- **Detailed Stock View**: Click any stock to see comprehensive investment thesis, triggers, and rationale
- **Responsive Design**: Works beautifully on desktop, tablet, and mobile
- **Smooth Animations**: Elegant fade-in and slide-up animations for better UX
- **Sector Distribution Chart**: Visual representation of portfolio diversification

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **better-sqlite3** - Database connectivity
- **Lucide React** - Beautiful icons
- **Recharts** - Data visualization (ready for performance charts)

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Portfolio database exists at `../.cache/portfolio.db`

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
frontend/
├── src/
│   ├── app/                  # Next.js App Router
│   │   ├── api/             # API routes
│   │   │   ├── portfolio/   # Portfolio endpoints
│   │   │   └── stocks/      # Stock endpoints
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Home page
│   ├── components/          # React components
│   │   ├── PortfolioOverview.tsx  # Portfolio header/stats
│   │   ├── StockCard.tsx          # Stock summary cards
│   │   └── StockDetailModal.tsx   # Detailed stock view
│   ├── lib/                 # Utilities
│   │   ├── db.ts           # Database queries
│   │   └── utils.ts        # Helper functions
│   └── types/              # TypeScript types
│       └── index.ts        # Type definitions
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## API Endpoints

### GET `/api/portfolio`
Get the active portfolio with all stocks and statistics.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "profile": "aggressive",
    "total_capital": 500000,
    "stocks": [...],
    "stats": {
      "totalAllocated": 500000,
      "stockCount": 7,
      "sectorDistribution": {...}
    }
  }
}
```

### GET `/api/portfolio/[id]`
Get a specific portfolio by ID.

### GET `/api/stocks/[id]`
Get detailed information for a specific stock.

## UI Components

### PortfolioOverview
Displays portfolio metadata, statistics, and sector distribution with a beautiful gradient background.

**Props:**
- `portfolio`: Portfolio object
- `stats`: Portfolio statistics

### StockCard
Compact card showing stock summary with entry price, allocation, targets, and key metrics.

**Props:**
- `stock`: Stock object with details
- `onClick`: Function to open detail modal

### StockDetailModal
Full-screen modal with comprehensive stock information including investment thesis, triggers, and metrics.

**Props:**
- `stock`: Stock object or null
- `onClose`: Function to close modal

## Styling

The app uses Tailwind CSS with custom color scheme:

- **Primary**: Blue tones for main UI elements
- **Success**: Green for positive indicators (targets, gains)
- **Danger**: Red for risk indicators (stop-loss, alerts)
- **Custom animations**: fade-in, slide-up, pulse-slow

## Database Schema

The frontend reads from SQLite database with tables:
- `portfolios` - Portfolio metadata
- `stocks` - Stock positions
- `investment_views` - Investment thesis for each stock
- `key_metrics` - Financial metrics snapshot

## Future Enhancements

- [ ] Real-time price updates via API integration
- [ ] Performance tracking charts (using Recharts)
- [ ] Portfolio comparison view
- [ ] Export portfolio to PDF/CSV
- [ ] Mobile app version
- [ ] Dark mode support
- [ ] WebSocket for live updates
- [ ] Portfolio rebalancing suggestions
- [ ] News feed integration

## Build for Production

```bash
npm run build
npm start
```

## License

Part of the Portfolio Agent project - AI-Powered Portfolio Management System.
