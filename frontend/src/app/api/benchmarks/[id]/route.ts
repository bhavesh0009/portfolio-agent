import { NextResponse } from 'next/server';
import { BenchmarkComparison } from '@/types';

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

    // Extract query parameters
    const url = new URL(request.url);
    const period = url.searchParams.get('period') || 'ALL';

    // Call FastAPI backend
    const apiUrl = `${API_BASE}/api/benchmarks/${portfolioId}?period=${period}`;
    const apiResponse = await fetch(apiUrl, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!apiResponse.ok) {
      // If backend returns 404 or error, return graceful empty response
      const errorData = await apiResponse.json().catch(() => ({}));
      return NextResponse.json({
        portfolio_id: portfolioId,
        period: period,
        benchmarks: [],
        message: errorData.message || 'No benchmark data available. Run price update to generate comparisons.',
      });
    }

    const data = await apiResponse.json();

    const response = NextResponse.json(data);

    // Add no-cache headers
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');

    return response;
  } catch (error) {
    console.error('Error fetching benchmarks:', error);
    return NextResponse.json(
      { error: 'Failed to fetch benchmarks' },
      { status: 500 }
    );
  }
}
