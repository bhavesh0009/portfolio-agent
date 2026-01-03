import { NextResponse } from 'next/server';
import { PortfolioPerformance } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Disable Next.js caching for this route
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const portfolioId = parseInt(params.id);

    if (isNaN(portfolioId)) {
      return NextResponse.json(
        { error: 'Invalid portfolio ID' },
        { status: 400 }
      );
    }

    // Proxy to FastAPI backend with cache disabled
    const response = await fetch(`${API_BASE}/api/performance/${portfolioId}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
      }
    });
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || 'Failed to fetch performance data' },
        { status: response.status }
      );
    }

    // Return with no-cache headers
    const nextResponse = NextResponse.json(data);
    nextResponse.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
    nextResponse.headers.set('Pragma', 'no-cache');
    nextResponse.headers.set('Expires', '0');
    return nextResponse;
  } catch (error) {
    console.error('Error fetching performance data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch performance data' },
      { status: 500 }
    );
  }
}
