'use client';

import React, { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';
import {
  formatCurrency,
  formatCompactCurrency,
  formatPercent,
  formatDateCompact,
  getNumberColorClass,
} from '@/utils/formatters';

export interface PortfolioHistoryPoint {
  date: string;
  value: number;
  pnl_pct: number;
}

interface PortfolioValueChartProps {
  initialCapital: number;
  currentValue: number;
  totalPnlPct: number;
  totalPnlAbsolute: number;
  dayReturnPct?: number;
  dayReturnAbsolute?: number;
  historyData: PortfolioHistoryPoint[];
  loading?: boolean;
}

type TimePeriod = '1M' | '3M' | '6M' | '1Y' | 'ALL';

export default function PortfolioValueChart({
  initialCapital,
  currentValue,
  totalPnlPct,
  totalPnlAbsolute,
  dayReturnPct = 0,
  dayReturnAbsolute = 0,
  historyData,
  loading = false,
}: PortfolioValueChartProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>('ALL');

  // Filter data based on selected period
  const filteredData = React.useMemo(() => {
    if (!historyData || historyData.length === 0) return [];

    const now = new Date();
    let cutoffDate: Date;

    switch (selectedPeriod) {
      case '1M':
        cutoffDate = new Date(now.setMonth(now.getMonth() - 1));
        break;
      case '3M':
        cutoffDate = new Date(now.setMonth(now.getMonth() - 3));
        break;
      case '6M':
        cutoffDate = new Date(now.setMonth(now.getMonth() - 6));
        break;
      case '1Y':
        cutoffDate = new Date(now.setFullYear(now.getFullYear() - 1));
        break;
      case 'ALL':
      default:
        return historyData;
    }

    return historyData.filter((point) => new Date(point.date) >= cutoffDate);
  }, [historyData, selectedPeriod]);

  // Calculate period return
  const periodReturn = React.useMemo(() => {
    if (filteredData.length < 2) return 0;
    const startValue = filteredData[0].value;
    const endValue = filteredData[filteredData.length - 1].value;
    return ((endValue - startValue) / startValue) * 100;
  }, [filteredData]);

  const periodButtons: TimePeriod[] = ['1M', '3M', '6M', '1Y', 'ALL'];

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-48 mb-4"></div>
        <div className="h-64 bg-gray-100 rounded"></div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-card">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between mb-6 gap-4">
        {/* Portfolio Value Display */}
        <div>
          <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">
            Total Portfolio Value
          </h2>
          <div className="flex items-baseline gap-4">
            <span className="text-display text-gray-900 tabular-nums">
              {formatCompactCurrency(currentValue)}
            </span>
            <div className="flex flex-col">
              {/* Today's Change */}
              <div className={`flex items-center gap-1 text-sm ${getNumberColorClass(dayReturnAbsolute)}`}>
                {dayReturnAbsolute >= 0 ? (
                  <TrendingUp size={16} />
                ) : (
                  <TrendingDown size={16} />
                )}
                <span className="font-medium tabular-nums">
                  {formatCurrency(dayReturnAbsolute, true)}
                </span>
                <span className="tabular-nums">
                  ({formatPercent(dayReturnPct)})
                </span>
                <span className="text-gray-500 ml-1">today</span>
              </div>
              {/* Total Change */}
              <div className={`flex items-center gap-1 text-sm ${getNumberColorClass(totalPnlAbsolute)}`}>
                {totalPnlAbsolute >= 0 ? (
                  <TrendingUp size={16} />
                ) : (
                  <TrendingDown size={16} />
                )}
                <span className="font-medium tabular-nums">
                  {formatCurrency(totalPnlAbsolute, true)}
                </span>
                <span className="tabular-nums">
                  ({formatPercent(totalPnlPct)})
                </span>
                <span className="text-gray-500 ml-1">total</span>
              </div>
            </div>
          </div>
        </div>

        {/* Period Filters */}
        <div className="flex gap-2">
          {periodButtons.map((period) => (
            <button
              key={period}
              onClick={() => setSelectedPeriod(period)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedPeriod === period
                  ? 'bg-info-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {filteredData.length > 0 ? (
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={filteredData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateCompact}
              tick={{ fill: '#6B7280', fontSize: 12 }}
              stroke="#E5E7EB"
            />
            <YAxis
              tickFormatter={(value) => formatCompactCurrency(value)}
              tick={{ fill: '#6B7280', fontSize: 12 }}
              stroke="#E5E7EB"
              width={80}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '8px',
                padding: '12px',
              }}
              labelStyle={{ color: '#111827', fontWeight: 600, marginBottom: '4px' }}
              formatter={(value: number) => [formatCurrency(value), 'Value']}
              labelFormatter={(label) => `Date: ${label}`}
            />
            {/* Reference line for initial capital */}
            <ReferenceLine
              y={initialCapital}
              stroke="#9CA3AF"
              strokeDasharray="3 3"
              label={{
                value: 'Initial Capital',
                position: 'right',
                fill: '#6B7280',
                fontSize: 11,
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3B82F6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorValue)"
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-center">
            <p className="text-gray-500 mb-2">No historical data available</p>
            <p className="text-sm text-gray-400">
              Historical portfolio values will appear here as data is collected
            </p>
          </div>
        </div>
      )}

      {/* Period Stats */}
      {filteredData.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">Period Return</div>
              <div className={`text-lg font-semibold tabular-nums ${getNumberColorClass(periodReturn)}`}>
                {formatPercent(periodReturn)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">Initial Value</div>
              <div className="text-lg font-semibold text-gray-900 tabular-nums">
                {formatCompactCurrency(filteredData[0]?.value || initialCapital)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">Current Value</div>
              <div className="text-lg font-semibold text-gray-900 tabular-nums">
                {formatCompactCurrency(currentValue)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">Data Points</div>
              <div className="text-lg font-semibold text-gray-900 tabular-nums">
                {filteredData.length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
