import { NextResponse } from 'next/server';
import { ManagerUpdatesResponse } from '@/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const portfolioId = params.id;
    const { searchParams } = new URL(request.url);

    // Build query parameters
    const queryParams = new URLSearchParams();
    const status = searchParams.get('status');
    const priority = searchParams.get('priority');
    const limit = searchParams.get('limit') || '20';

    if (status) queryParams.append('status', status);
    if (priority) queryParams.append('priority', priority);
    queryParams.append('limit', limit);

    // Call FastAPI backend
    const response = await fetch(
      `${BACKEND_URL}/api/manager-updates/${portfolioId}?${queryParams}`,
      {
        cache: 'no-store',
      }
    );

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data: ManagerUpdatesResponse = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching manager updates:', error);
    return NextResponse.json(
      { error: 'Failed to fetch manager updates' },
      { status: 500 }
    );
  }
}
