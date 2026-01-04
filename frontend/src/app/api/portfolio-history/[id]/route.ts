import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface PortfolioHistoryResponse {
  portfolio_id: number;
  snapshots: Array<{
    date: string;
    value: number;
    pnl_pct: number;
  }>;
  count: number;
  period?: string;
  fetched_at: string;
}

// Disable Next.js caching for this route
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const portfolioId = parseInt(params.id, 10);

    if (isNaN(portfolioId)) {
      return NextResponse.json(
        { error: 'Invalid portfolio ID' },
        { status: 400 }
      );
    }

    // Get period filter from query params
    const searchParams = request.nextUrl.searchParams;
    const period = searchParams.get('period') || 'ALL';

    // Fetch portfolio history from FastAPI backend
    const apiResponse = await fetch(
      `${API_BASE}/api/portfolio-history/${portfolioId}?period=${period}`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      }
    );

    if (!apiResponse.ok) {
      const errorText = await apiResponse.text();
      console.error('FastAPI error:', errorText);
      return NextResponse.json(
        { error: 'Failed to fetch portfolio history' },
        { status: apiResponse.status }
      );
    }

    const data = await apiResponse.json();

    const response = NextResponse.json(data);

    // Add no-cache headers
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');

    return response;
  } catch (error) {
    console.error('Error fetching portfolio history:', error);
    return NextResponse.json(
      { error: 'Failed to fetch portfolio history' },
      { status: 500 }
    );
  }
}
