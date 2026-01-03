import type { Portfolio, Stock, InvestmentView, KeyMetrics, StockDetail } from '@/types';

// API base URL - defaults to localhost:8000 if not set
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generic API fetch helper
 */
async function apiFetch<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    cache: 'no-store', // Disable Next.js fetch caching
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Get all portfolios
 */
export async function getPortfolios(): Promise<Portfolio[]> {
  return apiFetch<Portfolio[]>('/api/portfolios');
}

/**
 * Get active portfolio
 * @param profile - Investor profile ('aggressive', 'moderate', or 'defensive')
 */
export async function getActivePortfolio(profile: string = 'moderate'): Promise<Portfolio | null> {
  try {
    return await apiFetch<Portfolio>(`/api/portfolios/active?profile=${profile}`);
  } catch (error) {
    // Return null if no active portfolio found (404)
    if (error instanceof Error && error.message.includes('404')) {
      return null;
    }
    throw error;
  }
}

/**
 * Get portfolio by ID
 */
export async function getPortfolioById(id: number): Promise<Portfolio | null> {
  const portfolios = await getPortfolios();
  return portfolios.find(p => p.id === id) || null;
}

/**
 * Get stocks for a portfolio
 */
export async function getStocksByPortfolioId(portfolioId: number): Promise<Stock[]> {
  return apiFetch<Stock[]>(`/api/portfolios/${portfolioId}/stocks`);
}

/**
 * Get investment view for a stock
 * Note: This is now part of getStockDetail(), kept for backward compatibility
 */
export async function getInvestmentViewByStockId(stockId: number): Promise<InvestmentView | null> {
  const stockDetail = await getStockDetail(stockId);
  return stockDetail?.investment_view || null;
}

/**
 * Get key metrics for a stock
 * Note: This is now part of getStockDetail(), kept for backward compatibility
 */
export async function getKeyMetricsByStockId(stockId: number): Promise<KeyMetrics | null> {
  const stockDetail = await getStockDetail(stockId);
  return stockDetail?.key_metrics || null;
}

/**
 * Get stock with all details (investment view + key metrics)
 */
export async function getStockDetail(stockId: number): Promise<StockDetail | null> {
  try {
    return await apiFetch<StockDetail>(`/api/stocks/${stockId}`);
  } catch (error) {
    // Return null if stock not found (404)
    if (error instanceof Error && error.message.includes('404')) {
      return null;
    }
    throw error;
  }
}

/**
 * Get all stocks with details for a portfolio
 */
export async function getPortfolioStockDetails(portfolioId: number): Promise<StockDetail[]> {
  const stocks = await getStocksByPortfolioId(portfolioId);

  // Fetch detailed information for each stock
  const stockDetails = await Promise.all(
    stocks.map(async (stock) => {
      const detail = await getStockDetail(stock.id);
      return detail || stock as StockDetail;
    })
  );

  return stockDetails;
}

/**
 * Get portfolio statistics
 */
export async function getPortfolioStats(portfolioId: number) {
  return apiFetch<{
    portfolio_id: number;
    total_allocated: number;
    cash_balance?: number;
    total_value?: number;
    stock_count: number;
    sector_distribution: Record<string, number>;
    average_allocation: number;
    calculated_at: string;
  }>(`/api/portfolios/${portfolioId}/stats`);
}

// Legacy functions removed (no longer needed):
// - getDatabase() - no longer using SQLite
// - closeDatabase() - no connection to close with API calls
