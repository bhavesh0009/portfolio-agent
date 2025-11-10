import { NextResponse } from 'next/server';
import { PortfolioPerformance } from '@/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const portfolioId = params.id;

    // Call FastAPI backend
    const response = await fetch(`${BACKEND_URL}/api/performance/${portfolioId}`, {
      cache: 'no-store', // Always get fresh data
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data: PortfolioPerformance = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching performance data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch performance data' },
      { status: 500 }
    );
  }
}
