import { NextResponse } from 'next/server';
import { BenchmarkComparison } from '@/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const portfolioId = params.id;
    const { searchParams } = new URL(request.url);
    const period = searchParams.get('period') || 'ALL';

    // Call FastAPI backend
    const response = await fetch(
      `${BACKEND_URL}/api/benchmarks/${portfolioId}?period=${period}`,
      {
        cache: 'no-store',
      }
    );

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data: BenchmarkComparison = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching benchmark data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch benchmark data' },
      { status: 500 }
    );
  }
}
