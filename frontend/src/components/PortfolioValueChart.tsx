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
      <div className="glass-card rounded-xl p-6 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-48 mb-4"></div>
        <div className="h-64 bg-slate-800 rounded"></div>
      </div>
    );
  }

  return (
    <div className="glass-card glass-card-hover rounded-xl p-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between mb-6 gap-4">
        {/* Portfolio Value Display */}
        <div>
          <h2 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
            Total Portfolio Value
          </h2>
          <div className="flex items-baseline gap-4">
            <span className="text-number-xl font-mono font-bold text-slate-50 metric-value animate-count-up">
              {formatCompactCurrency(currentValue)}
            </span>
            <div className="flex flex-col gap-1">
              {/* Today's Change */}
              <div className={`flex items-center gap-1 text-sm ${
                dayReturnAbsolute >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {dayReturnAbsolute >= 0 ? (
                  <TrendingUp size={16} strokeWidth={2.5} />
                ) : (
                  <TrendingDown size={16} strokeWidth={2.5} />
                )}
                <span className="font-mono font-semibold metric-value">
                  {formatCurrency(dayReturnAbsolute, true)}
                </span>
                <span className="font-mono metric-value">
                  ({formatPercent(dayReturnPct)})
                </span>
                <span className="text-slate-500 text-xs ml-1">today</span>
              </div>
              {/* Total Change */}
              <div className={`flex items-center gap-1 text-sm ${
                totalPnlAbsolute >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {totalPnlAbsolute >= 0 ? (
                  <TrendingUp size={16} strokeWidth={2.5} />
                ) : (
                  <TrendingDown size={16} strokeWidth={2.5} />
                )}
                <span className="font-mono font-semibold metric-value">
                  {formatCurrency(totalPnlAbsolute, true)}
                </span>
                <span className="font-mono metric-value">
                  ({formatPercent(totalPnlPct)})
                </span>
                <span className="text-slate-500 text-xs ml-1">total</span>
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
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
                selectedPeriod === period
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/20'
                  : 'bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 border border-slate-700'
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
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateCompact}
              tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'JetBrains Mono' }}
              stroke="#334155"
            />
            <YAxis
              tickFormatter={(value) => formatCompactCurrency(value)}
              tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'JetBrains Mono' }}
              stroke="#334155"
              width={80}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '12px',
                backdropFilter: 'blur(12px)',
              }}
              labelStyle={{ color: '#f8fafc', fontWeight: 600, marginBottom: '4px', fontFamily: 'JetBrains Mono' }}
              itemStyle={{ color: '#10b981', fontFamily: 'JetBrains Mono' }}
              formatter={(value: number) => [formatCurrency(value), 'Value']}
              labelFormatter={(label) => `Date: ${label}`}
            />
            {/* Reference line for initial capital */}
            <ReferenceLine
              y={initialCapital}
              stroke="#fbbf24"
              strokeDasharray="3 3"
              strokeWidth={1.5}
              label={{
                value: 'Initial Capital',
                position: 'right',
                fill: '#fbbf24',
                fontSize: 11,
                fontFamily: 'JetBrains Mono',
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#10b981"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#colorValue)"
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-64 flex items-center justify-center bg-slate-900/30 rounded-lg border border-slate-800">
          <div className="text-center">
            <p className="text-slate-400 mb-2 font-medium">No historical data available</p>
            <p className="text-sm text-slate-500 font-light">
              Historical portfolio values will appear here as data is collected
            </p>
          </div>
        </div>
      )}

      {/* Period Stats */}
      {filteredData.length > 0 && (
        <div className="mt-6 pt-6 border-t border-slate-800">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Period Return</div>
              <div className={`text-lg font-mono font-bold metric-value ${
                periodReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {formatPercent(periodReturn)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Initial Value</div>
              <div className="text-lg font-mono font-bold text-slate-200 metric-value">
                {formatCompactCurrency(filteredData[0]?.value || initialCapital)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Current Value</div>
              <div className="text-lg font-mono font-bold text-slate-200 metric-value">
                {formatCompactCurrency(currentValue)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Data Points</div>
              <div className="text-lg font-mono font-bold text-slate-200 metric-value">
                {filteredData.length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
