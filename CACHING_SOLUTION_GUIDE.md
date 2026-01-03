# Browser Caching Solution Guide

## Problem Overview

**Symptom:** Dashboard displayed `Entry Price = Current Price` for all stocks, even though actual prices had changed.

**Example:**
- Database: INFY entry ₹1656.1 → current ₹1653.5 ✅
- Browser:  INFY entry ₹1656.1 → current ₹1656.1 ❌ (cached)

---

## Root Cause Analysis

Browser and Next.js were caching API responses, causing the frontend to display stale data even though the backend had fresh data.

---

## Debugging Process

### Step 1: Verify Database (Source of Truth)
```sql
-- Used Supabase MCP to query database
SELECT ticker, entry_price, dp.close_price as current_price
FROM stocks s
LEFT JOIN daily_prices dp ON s.id = dp.stock_id AND dp.price_date = '2025-12-29'
WHERE s.portfolio_id = 42;

-- Result: INFY entry 1656.1, current 1653.5 ✅ Correct
```

### Step 2: Test Backend API Directly
```bash
# Terminal curl (bypasses browser cache)
curl http://localhost:8000/api/performance/42 | jq '.stock_details[0]'

# Result: "current_price": 1653.5 ✅ Backend correct
```

### Step 3: Test Browser Fetch
```javascript
// Playwright browser evaluation
await fetch('/api/performance/42')

// Result: "current_price": 1656.1 ❌ Browser cached stale data
```

### Step 4: Force Cache Bypass
```javascript
// Browser fetch with cache disabled
await fetch('/api/performance/42', { cache: 'no-store' })

// Result: "current_price": 1653.5 ✅ Correct after bypass
```

**Conclusion:** Browser was caching API responses.

---

## Solutions Implemented

### 1. Backend: Add No-Cache Headers (FastAPI)

**File:** `api/price_service.py`

Added middleware to set cache-control headers on all API responses:

```python
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Add cache-control headers to prevent browser caching of API responses"""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
```

**What it does:**
- `no-store`: Browser must not store response
- `no-cache`: Must revalidate with server before using
- `must-revalidate`: Once stale, must revalidate
- `max-age=0`: Consider stale immediately
- `Pragma: no-cache`: HTTP/1.0 backwards compatibility
- `Expires: 0`: Response already expired

### 2. Frontend: Disable Next.js Route Caching

**File:** `frontend/src/app/api/performance/[id]/route.ts`

```typescript
// Disable Next.js caching for this route
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: Request, { params }: { params: { id: string } }) {
  // Fetch with cache disabled
  const response = await fetch(`${API_BASE}/api/performance/${portfolioId}`, {
    cache: 'no-store',
    headers: { 'Cache-Control': 'no-cache' }
  });

  // Return with no-cache headers
  const nextResponse = NextResponse.json(data);
  nextResponse.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
  nextResponse.headers.set('Pragma', 'no-cache');
  nextResponse.headers.set('Expires', '0');
  return nextResponse;
}
```

**What it does:**
- `export const dynamic = 'force-dynamic'`: Force dynamic rendering
- `export const revalidate = 0`: Never cache
- `cache: 'no-store'` in fetch: Don't cache the fetch request
- Response headers: Prevent browser from caching response

**Updated Files:**
- ✅ `frontend/src/app/api/performance/[id]/route.ts`
- ✅ `frontend/src/app/api/portfolio/route.ts`

### 3. Additional Best Practices

#### A. Update All API Routes
Apply the same pattern to all API routes that return dynamic data:

```typescript
// Template for all dynamic API routes
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  // ... fetch data ...

  const response = NextResponse.json(data);
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
  response.headers.set('Pragma', 'no-cache');
  response.headers.set('Expires', '0');
  return response;
}
```

#### B. Client-Side Fetch Configuration
For critical real-time data, add cache headers to client-side fetches:

```typescript
// In React components
const fetchData = async () => {
  const response = await fetch('/api/performance/42', {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache'
    }
  });
  return response.json();
};
```

---

## Verification

### Test Backend Headers
```bash
curl -I http://localhost:8000/api/performance/42

# Expected headers:
# cache-control: no-store, no-cache, must-revalidate, max-age=0
# pragma: no-cache
# expires: 0
```

### Test Frontend Headers
```bash
curl -I http://localhost:3000/api/portfolio

# Expected headers:
# cache-control: no-store, no-cache, must-revalidate, max-age=0
# pragma: no-cache
# expires: 0
```

### Browser DevTools
1. Open Chrome DevTools → Network tab
2. Click "Disable cache" checkbox
3. Refresh page
4. Check Response Headers for API calls
5. Verify `Cache-Control: no-store`

---

## When to Use Caching vs No-Cache

### Use Caching (Cache-Control: public, max-age=...)
- ✅ Static assets (images, CSS, JS bundles)
- ✅ Historical data that won't change
- ✅ Reference data (sector lists, etc.)

### Disable Caching (Cache-Control: no-store)
- ✅ Real-time prices
- ✅ Portfolio performance metrics
- ✅ User-specific data
- ✅ Authentication state
- ✅ Any data that changes frequently

---

## Production Considerations

### 1. CDN Configuration
If using a CDN (Cloudflare, Vercel, etc.), ensure:
- Bypass cache for `/api/*` routes
- Configure cache rules in CDN settings
- Test cache behavior after deployment

### 2. Reverse Proxy (nginx/Apache)
Add headers in proxy configuration:

```nginx
# nginx example
location /api/ {
    proxy_pass http://localhost:8000;
    add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0";
    add_header Pragma "no-cache";
    add_header Expires "0";
}
```

### 3. Development vs Production
Consider different caching strategies:

```typescript
// Environment-aware caching
const isDevelopment = process.env.NODE_ENV === 'development';

export const revalidate = isDevelopment ? 0 : 60; // Cache 60s in production
```

---

## Troubleshooting

### Issue: Still seeing stale data
**Solutions:**
1. Hard refresh browser: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
2. Clear browser cache: DevTools → Application → Clear storage
3. Incognito/Private window test
4. Check Response Headers in Network tab
5. Restart backend server to apply middleware changes

### Issue: Next.js production build still caching
**Solutions:**
1. Delete `.next` folder: `rm -rf .next`
2. Rebuild: `npm run build`
3. Verify `export const dynamic = 'force-dynamic'` in route files

### Issue: API returns 304 Not Modified
**Cause:** Browser sending `If-None-Match` or `If-Modified-Since` headers

**Solution:**
```python
# FastAPI: Remove ETag headers
response.headers.pop("ETag", None)
response.headers.pop("Last-Modified", None)
```

---

## Summary

**Root Cause:** Browser and Next.js caching API responses

**Solutions:**
1. ✅ Backend middleware: Add no-cache headers to all responses
2. ✅ Frontend routes: Disable Next.js caching with `dynamic = 'force-dynamic'`
3. ✅ Fetch requests: Use `cache: 'no-store'` option
4. ✅ Response headers: Set Cache-Control on all JSON responses

**Result:** Dashboard now shows real-time current prices without caching issues

---

## Files Modified

1. `api/price_service.py` - Added no-cache middleware
2. `frontend/src/app/api/performance/[id]/route.ts` - Disabled caching
3. `frontend/src/app/api/portfolio/route.ts` - Disabled caching

**Test Coverage:** All portfolio and performance endpoints now return fresh data
