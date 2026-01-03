# Portfolio Tracker - Feature Overview

## Visual Design

### Color Palette
- **Primary Blue**: `#0ea5e9` - Portfolio header, accent elements
- **Success Green**: `#10b981` - Targets, positive metrics
- **Danger Red**: `#ef4444` - Stop-loss, exit triggers
- **Warning Yellow**: `#eab308` - Review triggers
- **Neutral Gray**: Various shades for text and backgrounds

### Animations
- **Fade In**: All components fade in on load (0.5s)
- **Slide Up**: Portfolio overview slides up (0.5s)
- **Hover Effects**: Cards lift on hover (-4px translate)
- **Smooth Transitions**: All interactive elements (300ms)

## Components

### 1. Portfolio Overview (Header)
**Location**: Top of dashboard

**Features**:
- Gradient background (primary-600 to primary-800)
- Total capital in large display
- Portfolio profile badge (AGGRESSIVE/DEFENSIVE)
- Creation date
- Three stats cards:
  - Total Stocks with average allocation
  - Top Sector with percentage
  - Active status

**Sector Distribution Chart**:
- Horizontal bars showing each sector
- Gradient fill (white to primary-200)
- Percentage labels
- Sorted by allocation (highest first)
- Smooth animation on load

### 2. Stock Cards (Grid)
**Layout**: Responsive grid
- Mobile: 1 column
- Tablet: 2 columns
- Desktop: 3 columns

**Each Card Shows**:
- **Header**:
  - Stock name (bold, large)
  - Ticker symbol
  - Sector badge
  - Allocation percentage (large, right-aligned)
  - Allocation amount

- **Price Grid** (3 columns):
  - Entry Price (gray background)
  - Target Price (green background) with upside %
  - Stop Loss (red background) with downside %

- **Key Metrics** (3 columns):
  - ROCE percentage
  - ROE percentage
  - D/E ratio

- **Rationale**:
  - Investment thesis (truncated to 2 lines)

- **News Sentiment**:
  - Icon indicator
  - Sentiment text (truncated)

**Interactions**:
- Hover: Lift effect, shadow increase, border color change
- Click: Opens detail modal

### 3. Stock Detail Modal
**Trigger**: Click any stock card

**Layout**: Full-screen overlay with centered modal

**Sections**:

1. **Header** (Sticky)
   - Gradient background matching portfolio
   - Stock name and ticker
   - Sector badge
   - Close button (X)

2. **Price Grid** (4 columns)
   - Entry Price
   - Allocation (with % and amount)
   - Target Price (with upside %)
   - Stop Loss (with downside %)

3. **Key Metrics**
   - All available metrics in grid layout
   - Colored backgrounds for emphasis

4. **Investment View**
   - Market Outlook (primary blue background)
   - Stock Rationale (light blue background)
   - Holding Period (purple background with clock icon)

5. **Triggers** (2 columns)
   - Exit Triggers (red background, alert icon)
   - Review Triggers (yellow background, trending icon)
   - Bulleted lists

6. **Investment Thesis**
   - Full rationale text
   - Gradient background

7. **News Sentiment**
   - Full sentiment analysis
   - Green background

**Scroll Behavior**:
- Sticky header stays at top
- Smooth scrolling
- Custom scrollbar styling

## Data Flow

```
User opens page
    |
    v
Frontend calls GET /api/portfolio
    |
    v
API route uses db.ts utilities
    |
    v
better-sqlite3 queries portfolio.db
    |
    v
Returns: Portfolio + Stocks + Investment Views + Key Metrics
    |
    v
React renders components
    |
    v
User clicks stock card
    |
    v
Modal opens with full details
```

## API Responses

### GET /api/portfolio
```json
{
  "success": true,
  "data": {
    "id": 1,
    "profile": "aggressive",
    "total_capital": 500000,
    "created_at": "2025-11-08T10:03:54",
    "timestamp": "20251108_100354",
    "stocks": [...],
    "stats": {
      "totalAllocated": 500000,
      "stockCount": 7,
      "sectorDistribution": {...},
      "averageAllocation": 71428.57
    }
  }
}
```

### GET /api/stocks/[id]
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Waaree Energies",
    "ticker": "WAREE",
    "sector": "Renewable Energy",
    "entry_price": 3500,
    "allocation_pct": 15,
    "allocation_amount": 75000,
    "stop_loss_price": 2975,
    "target_price": 5250,
    "investment_view": {...},
    "key_metrics": {...}
  }
}
```

## Responsive Breakpoints

```css
mobile:   < 768px  (1 column)
tablet:   768px    (2 columns)
desktop:  1024px   (3 columns)
```

## Accessibility

- Semantic HTML5 elements
- ARIA labels where appropriate
- Keyboard navigation support
- Focus indicators on interactive elements
- Sufficient color contrast ratios
- Readable font sizes (minimum 14px)

## Performance

- Server-side rendering (Next.js App Router)
- Static generation where possible
- Optimized images (none currently, ready for future)
- Tree-shaking (unused code removal)
- Code splitting (automatic with Next.js)
- Minimal JavaScript bundle

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Future Enhancements

### Phase 1 (Next 2-4 weeks)
- [ ] Real-time price updates via API
- [ ] Performance tracking charts (Recharts)
- [ ] Portfolio comparison view
- [ ] Dark mode toggle

### Phase 2 (Next 1-2 months)
- [ ] News feed integration
- [ ] Alerts and notifications
- [ ] Export to PDF/Excel
- [ ] Historical performance graphs

### Phase 3 (Long-term)
- [ ] Multi-portfolio management
- [ ] What-if analysis tools
- [ ] Mobile app (React Native)
- [ ] Social sharing features
