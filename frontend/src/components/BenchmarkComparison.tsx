'use client';

import { useState, useEffect } from 'react';
import { BenchmarkComparison as BenchmarkComparisonType } from '@/types';
import { TrendingUp, TrendingDown, Target, BarChart2 } from 'lucide-react';
import BenchmarkChart from './BenchmarkChart';

interface BenchmarkComparisonProps {
  comparison: BenchmarkComparisonType | null;
  loading?: boolean;
  onPeriodChange?: (period: '1M' | '3M' | '6M' | '1Y' | 'ALL') => void;
  portfolioCreatedAt?: string; // NEW: Portfolio creation date for age calculation
}

const PERIODS: Array<'1M' | '3M' | '6M' | '1Y' | 'ALL'> = ['1M', '3M', '6M', '1Y', 'ALL'];

export default function BenchmarkComparison({ comparison, loading, onPeriodChange, portfolioCreatedAt }: BenchmarkComparisonProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<'1M' | '3M' | '6M' | '1Y' | 'ALL'>(comparison?.period || 'ALL');
  const [isVisible, setIsVisible] = useState(false);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [activeBenchmark, setActiveBenchmark] = useState<string>('^NSEI');
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  useEffect(() => {
    if (comparison?.portfolio_id) {
      fetchHistory(comparison.portfolio_id, activeBenchmark);
    }
  }, [comparison?.portfolio_id, activeBenchmark]);

  const fetchHistory = async (portfolioId: number, symbol: string) => {
    try {
      setLoadingHistory(true);
      const getApiUrl = () => {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        return `${baseUrl}/api/benchmark-history/${portfolioId}?index_symbol=${encodeURIComponent(symbol)}`;
      };

      const res = await fetch(getApiUrl());
      if (!res.ok) throw new Error('Failed to fetch history');
      const data = await res.json();
      setHistoryData(data.history || []);
    } catch (err) {
      console.error('Error fetching benchmark history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Calculate portfolio age in days
  const portfolioAge = portfolioCreatedAt
    ? Math.floor((Date.now() - new Date(portfolioCreatedAt).getTime()) / (1000 * 60 * 60 * 24))
    : 0;

  // Determine which periods are valid based on portfolio age
  const isValidPeriod = (period: '1M' | '3M' | '6M' | '1Y' | 'ALL') => {
    if (period === 'ALL') return true;
    if (period === '1M' && portfolioAge >= 30) return true;
    if (period === '3M' && portfolioAge >= 90) return true;
    if (period === '6M' && portfolioAge >= 180) return true;
    if (period === '1Y' && portfolioAge >= 365) return true;
    return false;
  };

  const handlePeriodChange = (period: '1M' | '3M' | '6M' | '1Y' | 'ALL') => {
    if (isValidPeriod(period)) {
      setSelectedPeriod(period);
      onPeriodChange?.(period);
    }
  };

  if (loading) {
    return (
      <div className="bg-[#0a1628]/80 backdrop-blur-md rounded-2xl shadow-sm border border-slate-800 p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-800 rounded-lg w-64 mb-6"></div>
          <div className="h-80 bg-slate-900/50 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (!comparison || !comparison.benchmarks || comparison.benchmarks.length === 0) {
    return (
      <div className="bg-[#0a1628]/80 backdrop-blur-md rounded-2xl shadow-sm border border-slate-800 p-6">
        <h3 className="text-xl font-bold text-slate-100 mb-4 font-serif">
          Benchmark Alpha
        </h3>
        <div className="flex flex-col items-center justify-center py-12">
          <Target className="h-16 w-16 text-slate-700 mb-4" />
          <p className="text-slate-400 text-center text-sm">
            No benchmark data available. Run the portfolio manager to generate comparisons.
          </p>
        </div>
      </div>
    );
  }

  // Backend already filters to 3 benchmarks, but we can verify here
  const filteredBenchmarks = comparison.benchmarks;

  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  // Get active benchmark name
  const activeBenchmarkName = comparison?.benchmarks.find(b => b.index_symbol === activeBenchmark)?.index_name || 'Benchmark';

  return (
    <div className={`bg-[#0a1628]/80 backdrop-blur-md rounded-2xl shadow-sm border border-slate-800 p-6 transition-all duration-500 transform ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <Target className="w-5 h-5 text-emerald-400" />
          Benchmark Comparison
        </h2>

        <div className="flex items-center gap-3">
          {/* Benchmark Selector */}
          <select
            value={activeBenchmark}
            onChange={(e) => setActiveBenchmark(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-md px-2 py-1 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
            disabled={loading}
          >
            {comparison?.benchmarks.map((b) => (
              <option key={b.index_symbol} value={b.index_symbol}>
                {b.index_name}
              </option>
            ))}
            {!comparison?.benchmarks.some(b => b.index_symbol === '^NSEI') && (
              <option value="^NSEI">Nifty 50</option>
            )}
          </select>

          {/* Period Selector */}
          <div className="flex bg-slate-900/50 rounded-lg p-1 border border-slate-800">
            {PERIODS.map((period) => {
              const valid = isValidPeriod(period);
              return (
                <button
                  key={period}
                  onClick={() => handlePeriodChange(period)}
                  disabled={!valid}
                  className={`
                    px-3 py-1 rounded-md text-xs font-medium transition-all duration-200
                    ${selectedPeriod === period
                      ? 'bg-emerald-500/10 text-emerald-400 shadow-sm'
                      : valid
                        ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                        : 'text-slate-700 cursor-not-allowed'}
                  `}
                  title={!valid ? `Portfolio too new for ${period} comparison` : ''}
                >
                  {period}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="mb-8">
        {loadingHistory ? (
          <div className="h-[300px] flex items-center justify-center bg-gray-900/20 rounded-lg border border-gray-800/50">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
          </div>
        ) : (
          <BenchmarkChart data={historyData} indexName={activeBenchmarkName} />
        )}
      </div>

      {/* Portfolio Return Summary */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-blue-900/20 rounded-xl p-5 mb-6 border border-slate-800/50">
        <div className="flex items-center justify-between relative z-10">
          <div>
            <p className="text-xs font-medium text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Target className="h-3.5 w-3.5" />
              Portfolio Return ({selectedPeriod})
            </p>
            <p className={`text-3xl font-bold tracking-tight ${comparison.portfolio_return >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
              {formatPercent(comparison.portfolio_return)}
            </p>
          </div>
          <div className={`p-3 rounded-xl backdrop-blur-sm ${comparison.portfolio_return >= 0
            ? 'bg-emerald-500/10 border border-emerald-500/20'
            : 'bg-rose-500/10 border border-rose-500/20'
            }`}>
            {comparison.portfolio_return >= 0 ? (
              <TrendingUp className="h-6 w-6 text-emerald-500" strokeWidth={2.5} />
            ) : (
              <TrendingDown className="h-6 w-6 text-rose-500" strokeWidth={2.5} />
            )}
          </div>
        </div>
        {/* Subtle decorative gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-blue-500/5 opacity-50"></div>
      </div>

      {/* Benchmark Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-900/50 border-b border-slate-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Index / Portfolio
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Return ({selectedPeriod})
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Alpha
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {/* Portfolio Row */}
            <tr className="bg-blue-900/10 hover:bg-blue-900/20 transition-colors">
              <td className="px-4 py-3 text-sm font-bold text-slate-200">
                Your Portfolio
              </td>
              <td className={`px-4 py-3 text-sm font-bold text-right ${comparison.portfolio_return >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                {formatPercent(comparison.portfolio_return)}
              </td>
              <td className="px-4 py-3 text-sm text-right text-slate-500 font-medium">
                -
              </td>
              <td className="px-4 py-3 text-sm text-center">
                <span className="inline-flex px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                  Active
                </span>
              </td>
            </tr>

            {/* Benchmark Rows */}
            {filteredBenchmarks.map((benchmark) => (
              <tr key={benchmark.index_symbol} className="hover:bg-slate-800/30 transition-colors">
                <td className="px-4 py-3 text-sm font-semibold text-slate-300">
                  {benchmark.index_name}
                </td>
                <td className={`px-4 py-3 text-sm font-semibold text-right ${benchmark.index_return >= 0 ? 'text-emerald-500' : 'text-rose-500'
                  }`}>
                  {formatPercent(benchmark.index_return)}
                </td>
                <td className={`px-4 py-3 text-sm font-bold text-right font-mono ${benchmark.alpha >= 0 ? 'text-emerald-500' : 'text-rose-500'
                  }`}>
                  {formatPercent(benchmark.alpha)}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  {benchmark.alpha >= 0 ? (
                    <span className="inline-flex px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      Outperforming
                    </span>
                  ) : (
                    <span className="inline-flex px-2.5 py-0.5 text-xs font-semibold rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">
                      Underperforming
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Portfolio Age Notice (only show if less than 30 days) */}
      {portfolioAge < 30 && (
        <div className="mt-6 p-4 bg-amber-900/20 border border-amber-900/30 rounded-lg">
          <p className="text-sm text-amber-200">
            <span className="font-semibold">Note:</span> Your portfolio is {portfolioAge} days old.
            Period tabs (1M, 3M, 6M, 1Y) will be enabled as your portfolio ages.
          </p>
        </div>
      )}
    </div>
  );
}
