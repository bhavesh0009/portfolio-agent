import { NextRequest, NextResponse } from 'next/server';
import { getDatabase } from '@/lib/db';

export interface PortfolioSnapshot {
  id: number;
  portfolio_id: number;
  snapshot_date: string;
  total_value: number;
  pnl_absolute: number;
  pnl_pct: number;
  created_at: string;
}

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

    const db = getDatabase();

    // Check if portfolio_snapshots table exists
    const tableExists = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_snapshots'"
      )
      .get();

    if (!tableExists) {
      // Table doesn't exist yet, return empty data
      return NextResponse.json({
        portfolio_id: portfolioId,
        snapshots: [],
        count: 0,
        period,
        fetched_at: new Date().toISOString(),
      });
    }

    // Calculate date filter based on period
    let dateFilter = '';
    const now = new Date();

    switch (period) {
      case '1M': {
        const oneMonthAgo = new Date(now.setMonth(now.getMonth() - 1));
        dateFilter = `AND snapshot_date >= '${oneMonthAgo.toISOString().split('T')[0]}'`;
        break;
      }
      case '3M': {
        const threeMonthsAgo = new Date(now.setMonth(now.getMonth() - 3));
        dateFilter = `AND snapshot_date >= '${threeMonthsAgo.toISOString().split('T')[0]}'`;
        break;
      }
      case '6M': {
        const sixMonthsAgo = new Date(now.setMonth(now.getMonth() - 6));
        dateFilter = `AND snapshot_date >= '${sixMonthsAgo.toISOString().split('T')[0]}'`;
        break;
      }
      case '1Y': {
        const oneYearAgo = new Date(now.setFullYear(now.getFullYear() - 1));
        dateFilter = `AND snapshot_date >= '${oneYearAgo.toISOString().split('T')[0]}'`;
        break;
      }
      case 'ALL':
      default:
        dateFilter = '';
    }

    // Fetch snapshots
    const stmt = db.prepare(`
      SELECT
        snapshot_date as date,
        total_value as value,
        pnl_pct
      FROM portfolio_snapshots
      WHERE portfolio_id = ? ${dateFilter}
      ORDER BY snapshot_date ASC
    `);

    const snapshots = stmt.all(portfolioId) as Array<{
      date: string;
      value: number;
      pnl_pct: number;
    }>;

    return NextResponse.json({
      portfolio_id: portfolioId,
      snapshots,
      count: snapshots.length,
      period,
      fetched_at: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching portfolio history:', error);
    return NextResponse.json(
      { error: 'Failed to fetch portfolio history' },
      { status: 500 }
    );
  }
}
