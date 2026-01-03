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

    // Fetch portfolio snapshots from Supabase via custom query
    // Note: FastAPI backend doesn't have a portfolio history endpoint yet,
    // so we'll query the portfolio_snapshots table directly
    const { createClient } = await import('@supabase/supabase-js');
    const supabase = createClient(
      process.env.SUPABASE_URL!,
      process.env.SUPABASE_API_KEY!
    );

    const { data: snapshots, error } = await supabase
      .from('portfolio_snapshots')
      .select('snapshot_date, total_value, total_return_pct')
      .eq('portfolio_id', portfolioId)
      .order('snapshot_date', { ascending: true });

    if (error) {
      console.error('Supabase error:', error);
      return NextResponse.json(
        { error: 'Failed to fetch portfolio history' },
        { status: 500 }
      );
    }

    // Transform data to match frontend expectations
    const transformedSnapshots = (snapshots || []).map((snapshot) => ({
      date: snapshot.snapshot_date,
      value: snapshot.total_value,
      pnl_pct: snapshot.total_return_pct || 0,
    }));

    const response = NextResponse.json({
      portfolio_id: portfolioId,
      snapshots: transformedSnapshots,
      count: transformedSnapshots.length,
      period,
      fetched_at: new Date().toISOString(),
    });

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
