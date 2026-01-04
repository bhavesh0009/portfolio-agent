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
    <div className="bg-[#0a1628] border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden group">
      {/* Background Gradient Effect */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 relative z-10">
        {/* Portfolio Value Display */}
        <div>
          <h2 className="text-lg font-bold text-slate-100 mb-1 font-serif">Portfolio Value</h2>
          <p className="text-sm text-slate-400">Net worth over time</p>
        </div>
        <div className="text-right mt-4 md:mt-0">
          <p className="text-2xl font-bold text-slate-50 font-mono tabular-nums">{formatCompactCurrency(currentValue)}</p>
          <div className="flex flex-col gap-0.5 mt-1">
            <p className={`text-sm font-medium ${
              totalPnlAbsolute >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}>
              {formatPercent(totalPnlPct)} All time
            </p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-[350px] w-full relative z-10">
        {filteredData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={filteredData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, {month:'short', day:'numeric'})}
                tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'monospace' }}
                stroke="#334155"
                axisLine={false}
                tickLine={false}
                dy={10}
              />
              <YAxis
                tickFormatter={(val) => `$${(val/1000).toFixed(0)}k`}
                tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'monospace' }}
                stroke="#334155"
                axisLine={false}
                tickLine={false}
                dx={-10}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.9)',
                  borderColor: 'rgba(148, 163, 184, 0.1)',
                  borderRadius: '8px',
                  backdropFilter: 'blur(8px)',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                }}
                itemStyle={{ color: '#10b981', fontFamily: 'monospace' }}
                labelStyle={{ color: '#e2e8f0', marginBottom: '0.25rem', fontSize: '0.75rem' }}
                formatter={(value: number) => [formatCurrency(value), 'Value']}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#10b981"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorValue)"
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-slate-400 mb-2 font-medium">No historical data available</p>
              <p className="text-sm text-slate-500 font-light">
                Historical portfolio values will appear here as data is collected
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Period Stats */}
      {filteredData.length > 0 && (
        <div className="mt-6 pt-6 border-t border-slate-800">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Period Return</div>
              <div className={`text-lg font-mono font-bold tabular-nums metric-value ${
                periodReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {formatPercent(periodReturn)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Initial Value</div>
              <div className="text-lg font-mono font-bold tabular-nums text-slate-200 metric-value">
                {formatCompactCurrency(filteredData[0]?.value || initialCapital)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Current Value</div>
              <div className="text-lg font-mono font-bold tabular-nums text-slate-200 metric-value">
                {formatCompactCurrency(currentValue)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Data Points</div>
              <div className="text-lg font-mono font-bold tabular-nums text-slate-200 metric-value">
                {filteredData.length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
