# Frontend Design Skill

## Purpose
Guide Claude to create distinctive, sophisticated frontend designs that avoid generic "AI slop" aesthetics. Specifically tailored for financial/portfolio applications requiring trust, clarity, and visual impact.

## Core Problem
Claude tends to converge on statistically common design patterns (Inter fonts, purple gradients, generic card layouts) due to distributional sampling. This skill provides targeted guidance to break these patterns.

## Design Framework

### 1. Typography
**Avoid:** Inter, Roboto, Arial, default system fonts

**Use instead:**
- **Display/Headers:** Playfair Display, Bricolage Grotesque, Cabinet Grotesk, Space Grotesk
- **Body:** IBM Plex Sans, Work Sans, DM Sans, Instrument Sans
- **Monospace/Data:** JetBrains Mono, Fira Code, IBM Plex Mono

**Key principles:**
- Extreme weight contrasts (font-weight: 100 vs. 900)
- Size jumps of 3x+ between hierarchy levels (e.g., h1: 72px, body: 16px)
- Use variable fonts for fine-tuned weight control
- Financial data should use tabular numerals (`font-variant-numeric: tabular-nums`)

**Portfolio-specific:**
```css
/* Stock prices and metrics - precise alignment */
.metric-value {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}
```

### 2. Color & Theme
**Avoid:** Evenly-distributed color palettes, generic blue/purple, no thematic coherence

**Use instead:**
- Establish dominant color with sharp accents (80/20 rule)
- Draw from financial/trading aesthetics: deep navy, forest green, charcoal, gold accents
- Use CSS custom properties for consistency
- Consider market psychology: green (gains), red (losses), gold (premium), silver (neutral)

**Example palette:**
```css
:root {
  /* Dominant - Trust & Depth */
  --color-navy-950: #0a1628;
  --color-navy-900: #0f2744;
  --color-navy-800: #1a3a5c;

  /* Accent - Growth & Success */
  --color-emerald-500: #10b981;
  --color-emerald-600: #059669;

  /* Accent - Alert & Risk */
  --color-amber-500: #f59e0b;
  --color-rose-500: #f43f5e;

  /* Accent - Premium */
  --color-gold-500: #fbbf24;

  /* Neutrals - Sophistication */
  --color-slate-50: #f8fafc;
  --color-slate-800: #1e293b;
  --color-slate-900: #0f172a;
}
```

**Portfolio-specific:**
- Use color to encode meaning (profit/loss, risk level, allocation size)
- Avoid harsh reds/greens - use sophisticated emerald/rose variants
- Background should be deep and atmospheric, not stark white or black

### 3. Motion
**Avoid:** Scattered hover effects, generic fade-ins, uniform transitions

**Use instead:**
- Orchestrated page-load sequences with staggered reveals
- High-impact moments (page enter, data load, modal open)
- Animation delays for cascade effects
- Physics-based springs for organic feel

**Portfolio-specific:**
```css
/* Staggered stock card reveals */
.stock-card {
  animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) backwards;
}

.stock-card:nth-child(1) { animation-delay: 0.05s; }
.stock-card:nth-child(2) { animation-delay: 0.1s; }
.stock-card:nth-child(3) { animation-delay: 0.15s; }
/* Continue pattern... */

@keyframes slideUpFade {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Number counting animation for portfolio value */
@keyframes countUp {
  from { opacity: 0; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1); }
}
```

**Key principles:**
- Use `cubic-bezier(0.16, 1, 0.3, 1)` for smooth deceleration
- Delays should increment by 50-100ms
- Animate portfolio value changes with counting effects
- Consider reduced-motion preferences: `@media (prefers-reduced-motion: reduce)`

### 4. Backgrounds
**Avoid:** Solid white, single-color fills, flat backgrounds

**Use instead:**
- Layered CSS gradients for depth and atmosphere
- Subtle geometric patterns (grids, dots, lines)
- Radial highlights to guide focus
- Dark-mode-first approach for financial applications

**Portfolio-specific:**
```css
body {
  background:
    /* Radial highlight - top left */
    radial-gradient(circle at 20% 20%, rgba(16, 185, 129, 0.08) 0%, transparent 50%),
    /* Radial highlight - bottom right */
    radial-gradient(circle at 80% 80%, rgba(251, 191, 36, 0.06) 0%, transparent 50%),
    /* Base gradient - depth */
    linear-gradient(135deg, #0a1628 0%, #0f172a 100%);
}

/* Card glass-morphism */
.card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow:
    0 4px 6px rgba(0, 0, 0, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
```

## Critical Warnings

**You still tend to converge on common choices.** Avoid:
- Inter font + purple gradient + centered cards
- Generic blue buttons with border-radius: 8px
- Uniform spacing with gap-4 everywhere
- Stock photo hero sections
- Default Tailwind colors without customization

**Think outside the box!** Consider:
- Asymmetric layouts with visual tension
- Unexpected color combinations (gold + navy, emerald + charcoal)
- Typography-first design with minimal chrome
- Data visualization as primary visual element
- Dynamic theming based on portfolio performance

## Portfolio Application Checklist

When designing portfolio frontends:
- [ ] Stock prices use tabular numerals for alignment
- [ ] Profit/loss colors are sophisticated (emerald/rose, not bright green/red)
- [ ] Page loads with orchestrated animation sequence
- [ ] Background has atmospheric depth (gradients + patterns)
- [ ] Typography hierarchy is extreme (thin ultra-light headers + bold data)
- [ ] Cards have glass-morphism or depth effects
- [ ] Hover states reveal additional detail with smooth transitions
- [ ] Responsive design maintains visual hierarchy on mobile
- [ ] Dark mode optimized for extended viewing
- [ ] Loading states use skeleton screens or progressive reveal

## Technical Implementation

**Font Loading:**
```typescript
import { Playfair_Display, IBM_Plex_Sans, JetBrains_Mono } from 'next/font/google';

const playfair = Playfair_Display({
  subsets: ['latin'],
  weight: ['400', '700', '900'],
  variable: '--font-display'
});

const ibmPlex = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600'],
  variable: '--font-sans'
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-mono'
});
```

**CSS Custom Properties:**
Define all colors, spacing, and animation values as CSS variables for consistency and easy theming.

**Component Architecture:**
Build reusable components with design tokens baked in, not hardcoded Tailwind classes.

## Examples of Excellence

**Good:**
- Linear.app (minimalist, strong typography, purposeful motion)
- Stripe Dashboard (data-first, clear hierarchy, sophisticated colors)
- Robinhood (bold design, market-appropriate aesthetics)

**Avoid:**
- Generic admin templates
- Default component library styling
- Overdesigned with unnecessary embellishments

## Final Note

Design should serve the domain. Financial applications require:
- **Trust:** Professional, consistent, polished
- **Clarity:** Data legibility, obvious hierarchy
- **Focus:** Remove distractions, highlight critical metrics
- **Sophistication:** Avoid childish colors or playful fonts

Every design choice should reinforce credibility and usability.
