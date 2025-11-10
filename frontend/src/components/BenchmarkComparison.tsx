'use client';

import { useState } from 'react';
import { BenchmarkComparison as BenchmarkComparisonType } from '@/types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Award } from 'lucide-react';

interface BenchmarkComparisonProps {
  comparison: BenchmarkComparisonType | null;
  loading?: boolean;
  onPeriodChange?: (period: '1M' | '3M' | '6M' | '1Y' | 'ALL') => void;
}

const PERIODS: Array<'1M' | '3M' | '6M' | '1Y' | 'ALL'> = ['1M', '3M', '6M', '1Y', 'ALL'];

export default function BenchmarkComparison({ comparison, loading, onPeriodChange }: BenchmarkComparisonProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<'1M' | '3M' | '6M' | '1Y' | 'ALL'>(comparison?.period || 'ALL');

  const handlePeriodChange = (period: '1M' | '3M' | '6M' | '1Y' | 'ALL') => {
    setSelectedPeriod(period);
    onPeriodChange?.(period);
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!comparison || comparison.benchmarks.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Benchmark Comparison</h3>
        <p className="text-gray-500 text-center py-8">
          No benchmark data available. Run the scheduler to generate comparisons.
        </p>
      </div>
    );
  }

  // Show only top 3 benchmarks in main view
  const topBenchmarks = comparison.benchmarks.slice(0, 3);

  // Prepare chart data
  const chartData = [
    {
      name: 'Portfolio',
      return: comparison.portfolio_return,
      type: 'portfolio'
    },
    ...topBenchmarks.map(b => ({
      name: b.index_name.replace('Nifty ', '').replace('100', ''),
      return: b.index_return,
      type: 'benchmark'
    }))
  ];

  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md p-6 mb-6">
      {/* Header with Period Selector */}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-bold text-gray-900">Benchmark Comparison</h3>

        <div className="flex gap-2">
          {PERIODS.map((period) => (
            <button
              key={period}
              onClick={() => handlePeriodChange(period)}
              className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                selectedPeriod === period
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* Portfolio Return Summary */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Portfolio Return ({selectedPeriod})</p>
            <p className={`text-3xl font-bold ${comparison.portfolio_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatPercent(comparison.portfolio_return)}
            </p>
          </div>
          <div className={`p-3 rounded-full ${comparison.portfolio_return >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
            {comparison.portfolio_return >= 0 ? (
              <TrendingUp className="h-8 w-8 text-green-600" />
            ) : (
              <TrendingDown className="h-8 w-8 text-red-600" />
            )}
          </div>
        </div>
      </div>

      {/* Comparison Chart */}
      <div className="mb-6">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="name"
              stroke="#6b7280"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              stroke="#6b7280"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              formatter={(value: number) => formatPercent(value)}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '8px'
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="return"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={{ r: 6, fill: '#3b82f6' }}
              name="Return (%)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Benchmark Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {topBenchmarks.map((benchmark, index) => (
          <BenchmarkCard
            key={benchmark.index_symbol}
            benchmark={benchmark}
            portfolioReturn={comparison.portfolio_return}
            rank={index + 1}
          />
        ))}
      </div>

      {/* Additional Benchmarks Summary */}
      {comparison.benchmarks.length > 3 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            {comparison.benchmarks.length - 3} more benchmarks available in detailed view
          </p>
        </div>
      )}
    </div>
  );
}

interface BenchmarkCardProps {
  benchmark: {
    index_symbol: string;
    index_name: string;
    index_return: number;
    alpha: number;
    outperformance: number;
  };
  portfolioReturn: number;
  rank: number;
}

function BenchmarkCard({ benchmark, portfolioReturn, rank }: BenchmarkCardProps) {
  const outperforming = benchmark.alpha > 0;
  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  return (
    <div className={`border rounded-lg p-4 transition-all duration-200 hover:shadow-lg ${
      outperforming ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
    }`}>
      {/* Rank Badge */}
      {rank === 1 && (
        <div className="flex justify-end mb-2">
          <Award className="h-5 w-5 text-yellow-500" />
        </div>
      )}

      {/* Index Name */}
      <h4 className="text-sm font-semibold text-gray-900 mb-2">
        {benchmark.index_name}
      </h4>

      {/* Index Return */}
      <div className="mb-3">
        <p className="text-xs text-gray-600">Index Return</p>
        <p className={`text-xl font-bold ${benchmark.index_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {formatPercent(benchmark.index_return)}
        </p>
      </div>

      {/* Alpha */}
      <div className="pt-3 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-gray-600">Alpha</p>
          <div className="flex items-center gap-1">
            {outperforming ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
            <p className={`text-sm font-bold ${outperforming ? 'text-green-600' : 'text-red-600'}`}>
              {formatPercent(benchmark.alpha)}
            </p>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {outperforming ? 'Outperforming' : 'Underperforming'} by {Math.abs(benchmark.alpha).toFixed(2)}%
        </p>
      </div>
    </div>
  );
}
