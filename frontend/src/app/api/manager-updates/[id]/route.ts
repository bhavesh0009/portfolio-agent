import { NextResponse } from 'next/server';
import { ManagerUpdatesResponse } from '@/types';

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
    const status = url.searchParams.get('status');
    const priority = url.searchParams.get('priority');
    const limit = url.searchParams.get('limit') || '20';

    // Build query string for FastAPI backend
    const queryParams = new URLSearchParams();
    if (status) queryParams.append('status', status);
    if (priority) queryParams.append('priority', priority);
    queryParams.append('limit', limit);

    // Call FastAPI backend
    const apiUrl = `${API_BASE}/api/manager-updates/${portfolioId}?${queryParams}`;
    const apiResponse = await fetch(apiUrl, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!apiResponse.ok) {
      throw new Error(`Backend API error: ${apiResponse.status}`);
    }

    const data = await apiResponse.json();

    const response = NextResponse.json(data);

    // Add no-cache headers
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');

    return response;
  } catch (error) {
    console.error('Error fetching manager updates:', error);
    return NextResponse.json(
      { error: 'Failed to fetch manager updates' },
      { status: 500 }
    );
  }
}
