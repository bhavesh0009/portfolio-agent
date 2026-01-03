import { NextResponse } from 'next/server';
import { getActivePortfolio, getPortfolioStockDetails, getPortfolioStats } from '@/lib/db';
import type { ApiResponse, PortfolioDetail } from '@/types';

// Disable Next.js caching for this route
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const portfolio = await getActivePortfolio();

    if (!portfolio) {
      return NextResponse.json<ApiResponse<null>>({
        success: false,
        error: 'No active portfolio found',
      }, { status: 404 });
    }

    const stocks = await getPortfolioStockDetails(portfolio.id);
    const stats = await getPortfolioStats(portfolio.id);

    const portfolioDetail: PortfolioDetail & { stats: any } = {
      ...portfolio,
      stocks,
      stats,
    };

    const response = NextResponse.json<ApiResponse<typeof portfolioDetail>>({
      success: true,
      data: portfolioDetail,
    });

    // Add no-cache headers
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');

    return response;
  } catch (error) {
    console.error('Error fetching portfolio:', error);
    return NextResponse.json<ApiResponse<null>>({
      success: false,
      error: 'Failed to fetch portfolio',
    }, { status: 500 });
  }
}
