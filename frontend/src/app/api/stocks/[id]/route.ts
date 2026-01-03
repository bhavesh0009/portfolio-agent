import { NextResponse } from 'next/server';
import { getStockDetail } from '@/lib/db';
import type { ApiResponse, StockDetail } from '@/types';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const stockId = parseInt(params.id);

    if (isNaN(stockId)) {
      return NextResponse.json<ApiResponse<null>>({
        success: false,
        error: 'Invalid stock ID',
      }, { status: 400 });
    }

    const stock = await getStockDetail(stockId);

    if (!stock) {
      return NextResponse.json<ApiResponse<null>>({
        success: false,
        error: 'Stock not found',
      }, { status: 404 });
    }

    return NextResponse.json<ApiResponse<StockDetail>>({
      success: true,
      data: stock,
    });
  } catch (error) {
    console.error('Error fetching stock:', error);
    return NextResponse.json<ApiResponse<null>>({
      success: false,
      error: 'Failed to fetch stock',
    }, { status: 500 });
  }
}
