import { NextResponse } from 'next/server';
import { getPortfolioById, getPortfolioStockDetails, getPortfolioStats } from '@/lib/db';
import type { ApiResponse, PortfolioDetail } from '@/types';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const portfolioId = parseInt(params.id);

    if (isNaN(portfolioId)) {
      return NextResponse.json<ApiResponse<null>>({
        success: false,
        error: 'Invalid portfolio ID',
      }, { status: 400 });
    }

    const portfolio = getPortfolioById(portfolioId);

    if (!portfolio) {
      return NextResponse.json<ApiResponse<null>>({
        success: false,
        error: 'Portfolio not found',
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
