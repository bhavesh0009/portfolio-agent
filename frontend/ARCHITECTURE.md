# Frontend Architecture

## Overview

A modern, responsive Next.js dashboard for visualizing AI-powered portfolio data stored in SQLite.

## Technology Decisions

### Why Next.js?
- Server-side rendering for better performance
- App Router for modern React patterns
- Built-in API routes (no separate backend needed)
- Excellent TypeScript support
- Great developer experience

### Why better-sqlite3?
- Synchronous API (simpler than async)
- Better performance than other SQLite libraries
- No external dependencies
- Works great with Next.js API routes

### Why Tailwind CSS?
- Utility-first approach for rapid development
- Built-in responsive design
- Easy to create custom animations
- Small bundle size with tree-shaking
- Consistent design system

## Architecture Layers

### 1. Data Layer (`lib/db.ts`)

**Purpose**: Abstract SQLite database operations

**Functions**:
- `getDatabase()` - Get database connection
- `getPortfolios()` - Fetch all portfolios
- `getActivePortfolio()` - Get current portfolio
- `getStocksByPortfolioId()` - Get stocks for portfolio
- `getInvestmentViewByStockId()` - Get investment thesis
- `getKeyMetricsByStockId()` - Get financial metrics
- `getPortfolioStats()` - Calculate aggregations

**Design Pattern**: Repository pattern
- Encapsulates all database logic
- Returns typed objects
- Handles JSON parsing of stored fields

### 2. API Layer (`app/api/`)

**Purpose**: Expose data via REST API

**Endpoints**:

```
GET /api/portfolio
→ Returns active portfolio with stocks and stats

GET /api/portfolio/[id]
→ Returns specific portfolio by ID

GET /api/stocks/[id]
→ Returns detailed stock information
```

**Response Format**:
```typescript
{
  success: boolean;
  data?: T;
  error?: string;
}
```

**Error Handling**:
- 404 for not found
- 400 for invalid parameters
- 500 for server errors

### 3. Component Layer (`components/`)

**PortfolioOverview** - Header component
- Displays total capital, stocks, top sector
- Shows sector distribution chart
- Gradient background design
- Responsive layout

**StockCard** - Grid item component
- Shows key stock information
- Hover effects and animations
- Click handler for modal
- Color-coded price levels

**StockDetailModal** - Full-screen modal
- Complete investment details
- Scrollable content
- Sticky header
- Close on backdrop click

**Design Pattern**: Presentational components
- Pure React components
- Props-based rendering
- No business logic
- Reusable and testable

### 4. Page Layer (`app/page.tsx`)

**Purpose**: Main dashboard orchestration

**Responsibilities**:
- Fetch portfolio data on mount
- Manage loading and error states
- Handle stock selection for modal
- Coordinate component rendering

**State Management**:
```typescript
const [portfolio, setPortfolio] = useState<PortfolioDetail | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
const [selectedStock, setSelectedStock] = useState<StockDetail | null>(null);
```

**Data Flow**:
```
mount → fetchPortfolio() → API call → setState → render
click → setSelectedStock() → modal opens
```

## Type Safety

### TypeScript Configuration

```json
{
  "strict": true,
  "noEmit": true,
  "paths": {
    "@/*": ["./src/*"]
  }
}
```

### Type Definitions (`types/index.ts`)

**Base Types**:
- Portfolio
- Stock
- InvestmentView
- KeyMetrics

**Composite Types**:
- StockDetail (Stock + InvestmentView + KeyMetrics)
- PortfolioDetail (Portfolio + Stock[])

**API Types**:
- ApiResponse<T> - Generic response wrapper

**Benefits**:
- Compile-time type checking
- IDE autocomplete
- Refactoring safety
- Self-documenting code

## Styling System

### Tailwind Configuration

**Custom Colors**:
```javascript
primary: {
  500: '#0ea5e9',
  600: '#0284c7',
  // ... more shades
}
success: { 500: '#10b981' }
danger: { 500: '#ef4444' }
```

**Custom Animations**:
```javascript
'fade-in': 'fadeIn 0.5s ease-in-out'
'slide-up': 'slideUp 0.5s ease-out'
'pulse-slow': 'pulse 3s infinite'
```

### Design Tokens

**Spacing**: Uses Tailwind's 4px base unit
**Typography**: System font stack
**Shadows**: Layered shadows for depth
**Borders**: Subtle borders with hover states

## Performance Optimizations

### 1. Server-Side Rendering
- Initial HTML rendered on server
- Faster First Contentful Paint
- Better SEO (if needed later)

### 2. Code Splitting
- Automatic with Next.js
- Components loaded on demand
- Smaller initial bundle

### 3. Database Connection
- Single connection instance
- Read-only mode for safety
- WAL mode for better concurrency

### 4. Minimal JavaScript
- No heavy libraries
- Tree-shaking removes unused code
- Efficient React rendering

## Security Considerations

### 1. Read-Only Database
```typescript
new Database(DB_PATH, { readonly: true })
```
- Prevents accidental writes
- Safe for concurrent reads
- No data corruption risk

### 2. No User Input to SQL
- All queries are parameterized
- No SQL injection risk
- Safe integer parsing

### 3. Error Handling
- Don't expose internal errors to client
- Generic error messages
- Detailed logs on server

## Responsive Design

### Breakpoints

```css
mobile:   < 768px  → 1 column
tablet:   768px    → 2 columns
desktop:  1024px   → 3 columns
```

### Mobile-First Approach
- Base styles for mobile
- Progressive enhancement for larger screens
- Touch-friendly hit areas

## Future Enhancements

### Phase 1 (Immediate)
- [ ] Add loading skeleton components
- [ ] Implement error boundary
- [ ] Add retry logic for failed fetches

### Phase 2 (Next Month)
- [ ] Real-time price updates (WebSocket)
- [ ] Performance charts (Recharts)
- [ ] Export to PDF (jsPDF)

### Phase 3 (Long-term)
- [ ] User authentication
- [ ] Multi-portfolio support
- [ ] Portfolio comparison
- [ ] Mobile app (React Native)

## Testing Strategy

### Unit Tests (Future)
- Test database functions
- Test utility functions
- Mock database for tests

### Integration Tests (Future)
- Test API routes
- Test component rendering
- Test user interactions

### E2E Tests (Future)
- Test full user flows
- Test responsive behavior
- Test error scenarios

## Development Workflow

### Local Development
```bash
npm run dev    # Start dev server
npm run build  # Build for production
npm run start  # Run production build
npm run lint   # Run ESLint
```

### File Watching
- Next.js auto-reloads on file changes
- Tailwind rebuilds CSS on changes
- TypeScript checks on save

### Debugging
- React DevTools
- Browser DevTools
- Console logging
- Network tab for API calls

## Deployment Considerations

### Build Output
```bash
npm run build
# → .next/ directory
```

### Environment Variables
None currently needed (database path is relative)

### Hosting Options
- Vercel (recommended for Next.js)
- Netlify
- AWS Amplify
- Self-hosted with Node.js

### Database Access
Ensure `.cache/portfolio.db` is accessible from deployed environment.

## Code Quality

### Linting
- ESLint with Next.js config
- React hooks rules
- TypeScript-specific rules

### Formatting
- Consistent style enforced
- Tailwind class ordering
- Import organization

### Best Practices
- Component composition over inheritance
- Props destructuring
- Meaningful variable names
- Comments for complex logic

## Maintenance

### Updating Dependencies
```bash
npm outdated        # Check for updates
npm update          # Update patch versions
npm install pkg@latest  # Update specific package
```

### Breaking Changes
Watch for:
- Next.js major version updates
- React major version updates
- Tailwind major version updates

### Database Schema Changes
If backend schema changes:
1. Update TypeScript types
2. Update db.ts functions
3. Test all API routes
4. Update components if needed

## Support & Resources

- Next.js Docs: https://nextjs.org/docs
- Tailwind CSS: https://tailwindcss.com
- TypeScript: https://www.typescriptlang.org
- better-sqlite3: https://github.com/WiseLibs/better-sqlite3
