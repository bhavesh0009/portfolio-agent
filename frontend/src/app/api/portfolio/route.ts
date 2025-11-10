import { NextResponse } from 'next/server';
import { getActivePortfolio, getPortfolioStockDetails, getPortfolioStats } from '@/lib/db';
import type { ApiResponse, PortfolioDetail } from '@/types';

export async function GET() {
  try {
    const portfolio = getActivePortfolio();

    if (!portfolio) {
      return NextResponse.json<ApiResponse<null>>({
        success: false,
        error: 'No active portfolio found',
      }, { status: 404 });
    }

    const stocks = getPortfolioStockDetails(portfolio.id);
    const stats = getPortfolioStats(portfolio.id);

    const portfolioDetail: PortfolioDetail & { stats: any } = {
      ...portfolio,
      stocks,
      stats,
    };

    return NextResponse.json<ApiResponse<typeof portfolioDetail>>({
      success: true,
      data: portfolioDetail,
    });
  } catch (error) {
    console.error('Error fetching portfolio:', error);
    return NextResponse.json<ApiResponse<null>>({
      success: false,
      error: 'Failed to fetch portfolio',
    }, { status: 500 });
  }
}
