'use client';

import React, { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  ColumnDef,
  flexRender,
  SortingState,
  ColumnFiltersState,
} from '@tanstack/react-table';
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  ChevronRight,
  Search,
  Download,
} from 'lucide-react';
import { StockDetail, StockPerformance } from '@/types';
import {
  formatCurrency,
  formatPercent,
  getNumberColorClass,
} from '@/utils/formatters';

// Extended type combining stock details with performance data
export interface PositionRow extends StockDetail {
  currentPrice?: number;
  pnlAbsolute?: number;
  pnlPct?: number;
}

interface PositionsTableProps {
  stocks: PositionRow[];
  onStockClick?: (stock: PositionRow) => void;
}

export default function PositionsTable({ stocks, onStockClick }: PositionsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({});

  // Define columns
  const columns = useMemo<ColumnDef<PositionRow>[]>(
    () => [
      {
        accessorKey: 'name',
        header: 'STOCK',
        cell: ({ row }) => (
          <div>
            <div className="font-medium text-gray-900">{row.original.name}</div>
            <div className="text-sm text-gray-500">{row.original.ticker}</div>
          </div>
        ),
        size: 200,
      },
      {
        accessorKey: 'entry_price',
        header: 'ENTRY',
        cell: ({ row }) => (
          <span className="tabular-nums text-gray-900">
            {formatCurrency(row.original.entry_price)}
          </span>
        ),
        size: 120,
      },
      {
        accessorKey: 'currentPrice',
        header: 'CURRENT',
        cell: ({ row }) => (
          <span className="tabular-nums text-gray-900">
            {row.original.currentPrice
              ? formatCurrency(row.original.currentPrice)
              : '-'}
          </span>
        ),
        size: 120,
      },
      {
        accessorKey: 'pnlAbsolute',
        header: 'P&L (₹)',
        cell: ({ row }) => {
          const pnl = row.original.pnlAbsolute || 0;
          return (
            <span className={`tabular-nums font-medium ${getNumberColorClass(pnl)}`}>
              {formatCurrency(pnl, true)}
            </span>
          );
        },
        size: 140,
      },
      {
        accessorKey: 'pnlPct',
        header: 'P&L (%)',
        cell: ({ row }) => {
          const pnlPct = row.original.pnlPct || 0;
          return (
            <span className={`tabular-nums font-medium ${getNumberColorClass(pnlPct)}`}>
              {formatPercent(pnlPct)}
            </span>
          );
        },
        size: 100,
      },
      {
        accessorKey: 'allocation_amount',
        header: 'ALLOCATION',
        cell: ({ row }) => (
          <div>
            <div className="tabular-nums text-gray-900">
              {formatCurrency(row.original.allocation_amount)}
            </div>
            <div className="text-sm text-gray-500">
              {row.original.allocation_pct.toFixed(1)}%
            </div>
          </div>
        ),
        size: 140,
      },
      {
        accessorKey: 'stop_loss_price',
        header: 'STOP LOSS',
        cell: ({ row }) => (
          <span className="tabular-nums text-danger-600">
            {formatCurrency(row.original.stop_loss_price)}
          </span>
        ),
        size: 120,
      },
      {
        accessorKey: 'target_price',
        header: 'TARGET',
        cell: ({ row }) => (
          <span className="tabular-nums text-success-600">
            {formatCurrency(row.original.target_price)}
          </span>
        ),
        size: 120,
      },
      {
        accessorKey: 'sector',
        header: 'SECTOR',
        cell: ({ row }) => (
          <span className="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-xs font-medium text-gray-700">
            {row.original.sector || 'Unknown'}
          </span>
        ),
        size: 140,
      },
    ],
    []
  );

  const table = useReactTable({
    data: stocks,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const toggleRowExpanded = (stockId: number) => {
    setExpandedRows((prev) => ({
      ...prev,
      [stockId]: !prev[stockId],
    }));
  };

  const exportToCSV = () => {
    const headers = ['Name', 'Ticker', 'Entry', 'Current', 'P&L (₹)', 'P&L (%)', 'Allocation', 'Stop Loss', 'Target', 'Sector'];
    const rows = stocks.map((stock) => [
      stock.name,
      stock.ticker,
      stock.entry_price,
      stock.currentPrice || '',
      stock.pnlAbsolute || '',
      stock.pnlPct || '',
      stock.allocation_amount,
      stock.stop_loss_price,
      stock.target_price,
      stock.sector || '',
    ]);

    const csv = [headers, ...rows].map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'portfolio-positions.csv';
    a.click();
  };

  return (
    <div className="w-full">
      {/* Table Header with Search and Actions */}
      <div className="flex items-center justify-between mb-4">
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search stocks..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-info-500 focus:border-transparent"
          />
        </div>
        <button
          onClick={exportToCSV}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <Download size={16} />
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            {/* Table Header */}
            <thead className="bg-gray-50 border-b-2 border-gray-200">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  <th className="w-12 px-4 py-3"></th>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left text-caption uppercase text-gray-500 font-semibold cursor-pointer hover:bg-gray-100 transition-colors"
                      style={{ width: header.column.getSize() }}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center gap-2">
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {header.column.getIsSorted() ? (
                          header.column.getIsSorted() === 'asc' ? (
                            <ChevronUp size={14} />
                          ) : (
                            <ChevronDown size={14} />
                          )
                        ) : (
                          <ChevronsUpDown size={14} className="text-gray-300" />
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>

            {/* Table Body */}
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td colSpan={columns.length + 1} className="px-4 py-12 text-center text-gray-500">
                    No stocks found
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <React.Fragment key={row.id}>
                    {/* Main Row */}
                    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <button
                          onClick={() => toggleRowExpanded(row.original.id)}
                          className="p-1 hover:bg-gray-200 rounded transition-colors"
                        >
                          <ChevronRight
                            size={16}
                            className={`text-gray-500 transition-transform ${
                              expandedRows[row.original.id] ? 'rotate-90' : ''
                            }`}
                          />
                        </button>
                      </td>
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3 text-sm">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>

                    {/* Expanded Row */}
                    {expandedRows[row.original.id] && (
                      <tr className="bg-gray-50 border-b border-gray-100">
                        <td colSpan={columns.length + 1} className="px-4 py-6">
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Investment Thesis */}
                            {row.original.rationale && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-2">
                                  Investment Thesis
                                </h4>
                                <p className="text-sm text-gray-600 leading-relaxed">
                                  {row.original.rationale}
                                </p>
                              </div>
                            )}

                            {/* Investment View */}
                            {row.original.investment_view && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-2">
                                  Investment View
                                </h4>
                                <div className="space-y-2 text-sm">
                                  <div>
                                    <span className="text-gray-500">Market Outlook:</span>{' '}
                                    <span className="text-gray-900">
                                      {row.original.investment_view.market_outlook}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-gray-500">Holding Period:</span>{' '}
                                    <span className="text-gray-900">
                                      {row.original.investment_view.holding_period}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Key Metrics */}
                            {row.original.key_metrics && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-2">
                                  Key Metrics
                                </h4>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  {Object.entries(row.original.key_metrics.metrics).map(
                                    ([key, value]) => (
                                      <div key={key}>
                                        <span className="text-gray-500">{key}:</span>{' '}
                                        <span className="text-gray-900 font-medium">{value}</span>
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}

                            {/* News Sentiment */}
                            {row.original.news_sentiment && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-2">
                                  News Sentiment
                                </h4>
                                <p className="text-sm text-gray-600 leading-relaxed">
                                  {row.original.news_sentiment}
                                </p>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Table Footer */}
      <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
        <div>
          Showing {table.getRowModel().rows.length} of {stocks.length} positions
        </div>
      </div>
    </div>
  );
}
