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
  Target,
  AlertTriangle,
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
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300 border border-slate-700 group-hover:border-emerald-500/50 transition-colors">
              {row.original.ticker?.[0] || 'S'}
            </div>
            <div>
              <div className="font-bold text-slate-200">{row.original.name}</div>
              <div className="text-xs text-emerald-500 font-mono">{row.original.ticker}</div>
            </div>
          </div>
        ),
        size: 200,
      },
      {
        accessorKey: 'entry_price',
        header: 'ENTRY',
        cell: ({ row }) => (
          <span className="font-mono metric-value tabular-nums font-bold text-slate-200">
            {formatCurrency(row.original.entry_price)}
          </span>
        ),
        size: 120,
      },
      {
        accessorKey: 'currentPrice',
        header: 'CURRENT',
        cell: ({ row }) => (
          <span className="font-mono metric-value tabular-nums font-bold text-slate-200">
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
            <span className={`font-mono metric-value tabular-nums font-bold ${
              pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}>
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
            <span className={`font-mono metric-value tabular-nums font-bold ${
              pnlPct >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}>
              {formatPercent(pnlPct)}
            </span>
          );
        },
        size: 100,
      },
      {
        accessorKey: 'shares',
        header: 'SHARES',
        cell: ({ row }) => {
          const shares = row.original.shares;
          if (shares !== undefined && shares !== null) {
            return (
              <div className="font-mono metric-value tabular-nums font-bold text-primary-400">
                {shares.toLocaleString()}
              </div>
            );
          }
          return <span className="text-slate-600 text-sm">-</span>;
        },
        size: 100,
      },
      {
        accessorKey: 'allocation_amount',
        header: 'ALLOCATION',
        cell: ({ row }) => (
          <div>
            <div className="font-mono metric-value tabular-nums font-bold text-slate-200">
              {formatCurrency(row.original.allocation_amount)}
            </div>
            <div className="text-sm text-slate-500 font-mono tabular-nums">
              {row.original.allocation_pct.toFixed(1)}%
            </div>
          </div>
        ),
        size: 140,
      },
      {
        accessorKey: 'sector',
        header: 'SECTOR',
        cell: ({ row }) => (
          <span className="inline-flex items-center px-2 py-1 rounded-md bg-slate-800/50 border border-slate-700 text-xs font-medium text-slate-300">
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

  return (
    <div className="w-full">
      {/* Table Header with Search */}
      <div className="mb-4">
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500" size={18} />
          <input
            type="text"
            placeholder="Search stocks..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#0a1628]/80 backdrop-blur-xl border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full">
            {/* Table Header */}
            <thead className="bg-[#0f172a] border-b border-slate-800">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  <th className="w-12 px-4 py-3"></th>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-6 py-4 text-left text-xs uppercase text-slate-400 font-bold cursor-pointer hover:text-slate-200 transition-colors tracking-wider"
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
                            <ChevronUp size={14} className="text-emerald-400" />
                          ) : (
                            <ChevronDown size={14} className="text-emerald-400" />
                          )
                        ) : (
                          <ChevronsUpDown size={14} className="text-slate-600" />
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
                  <td colSpan={columns.length + 1} className="px-4 py-12 text-center text-slate-400">
                    No stocks found
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <React.Fragment key={row.id}>
                    {/* Main Row */}
                    <tr className="border-b border-slate-800 hover:bg-slate-800/40 transition-colors cursor-pointer group">
                      <td className="px-6 py-4">
                        <button
                          onClick={() => toggleRowExpanded(row.original.id)}
                          className="p-1 hover:bg-slate-700/50 rounded transition-colors"
                        >
                          <ChevronRight
                            size={16}
                            className={`text-slate-600 group-hover:text-emerald-400 transition-all ${
                              expandedRows[row.original.id] ? 'rotate-90' : ''
                            }`}
                          />
                        </button>
                      </td>
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-6 py-4 text-sm">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>

                    {/* Expanded Row */}
                    {expandedRows[row.original.id] && (
                      <tr className="bg-slate-900/50 border-b border-slate-800">
                        <td colSpan={columns.length + 1} className="px-4 py-6">
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Price Targets Section */}
                            <div className="lg:col-span-2 mb-6">
                              <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                Price Targets & Risk Management
                              </h4>
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                {/* Entry Price Reference */}
                                <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-4">
                                  <div className="flex items-center gap-2 mb-2">
                                    <div className="w-2 h-2 rounded-full bg-blue-400"></div>
                                    <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Entry Price</p>
                                  </div>
                                  <p className="text-xl font-mono font-bold tabular-nums text-slate-200">
                                    {formatCurrency(row.original.entry_price)}
                                  </p>
                                  <p className="text-xs text-slate-500 mt-1">Initial purchase price</p>
                                </div>

                                {/* Stop Loss */}
                                <div className="bg-rose-900/20 border border-rose-800/50 rounded-lg p-4">
                                  <div className="flex items-center gap-2 mb-2">
                                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                                    <p className="text-xs text-rose-300 uppercase tracking-wider font-medium">Stop Loss</p>
                                  </div>
                                  <p className="text-xl font-mono font-bold tabular-nums text-rose-400">
                                    {formatCurrency(row.original.stop_loss_price)}
                                  </p>
                                  <p className="text-xs text-rose-400/70 mt-1">
                                    {((row.original.stop_loss_price - row.original.entry_price) / row.original.entry_price * 100).toFixed(1)}% from entry
                                  </p>
                                </div>

                                {/* Target Price */}
                                <div className="bg-emerald-900/20 border border-emerald-800/50 rounded-lg p-4">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Target className="w-4 h-4 text-emerald-400" />
                                    <p className="text-xs text-emerald-300 uppercase tracking-wider font-medium">Target Price</p>
                                  </div>
                                  <p className="text-xl font-mono font-bold tabular-nums text-emerald-400">
                                    {formatCurrency(row.original.target_price)}
                                  </p>
                                  <p className="text-xs text-emerald-400/70 mt-1">
                                    +{((row.original.target_price - row.original.entry_price) / row.original.entry_price * 100).toFixed(1)}% upside potential
                                  </p>
                                </div>
                              </div>
                            </div>

                            {/* Investment Thesis */}
                            {row.original.rationale && (
                              <div>
                                <h4 className="text-sm font-semibold text-slate-200 mb-2 uppercase tracking-wider">
                                  Investment Thesis
                                </h4>
                                <p className="text-sm text-slate-400 leading-relaxed">
                                  {row.original.rationale}
                                </p>
                              </div>
                            )}

                            {/* Investment View */}
                            {row.original.investment_view && (
                              <div>
                                <h4 className="text-sm font-semibold text-slate-200 mb-2 uppercase tracking-wider">
                                  Investment View
                                </h4>
                                <div className="space-y-2 text-sm">
                                  <div>
                                    <span className="text-slate-500">Market Outlook:</span>{' '}
                                    <span className="text-slate-300">
                                      {row.original.investment_view.market_outlook}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-slate-500">Holding Period:</span>{' '}
                                    <span className="text-slate-300">
                                      {row.original.investment_view.holding_period}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Key Metrics */}
                            {row.original.key_metrics && (
                              <div>
                                <h4 className="text-sm font-semibold text-slate-200 mb-2 uppercase tracking-wider">
                                  Key Metrics
                                </h4>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  {Object.entries(row.original.key_metrics.metrics).map(
                                    ([key, value]) => (
                                      <div key={key}>
                                        <span className="text-slate-500">{key}:</span>{' '}
                                        <span className="text-slate-300 font-medium font-mono">{value}</span>
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}

                            {/* News Sentiment */}
                            {row.original.news_sentiment && (
                              <div>
                                <h4 className="text-sm font-semibold text-slate-200 mb-2 uppercase tracking-wider">
                                  News Sentiment
                                </h4>
                                <p className="text-sm text-slate-400 leading-relaxed">
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
      <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
        <div>
          Showing <span className="text-slate-300 font-medium">{table.getRowModel().rows.length}</span> of <span className="text-slate-300 font-medium">{stocks.length}</span> positions
        </div>
      </div>
    </div>
  );
}
