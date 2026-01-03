'use client';

import { useEffect, useState, useMemo } from 'react';
import type { PortfolioDetail, StockDetail, PortfolioPerformance, BenchmarkComparison as BenchmarkComparisonType, ManagerUpdate } from '@/types';
import PerformanceMetrics from '@/components/PerformanceMetrics';
import BenchmarkComparison from '@/components/BenchmarkComparison';
import ManagerUpdateCard from '@/components/ManagerUpdateCard';
import PortfolioValueChart, { PortfolioHistoryPoint } from '@/components/PortfolioValueChart';
import PositionsTable, { PositionRow } from '@/components/PositionsTable';
import StockDetailModal from '@/components/StockDetailModal';
import { RefreshCw, AlertCircle } from 'lucide-react';

export default function Home() {
  const [portfolio, setPortfolio] = useState<(PortfolioDetail & { stats: any }) | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [benchmarks, setBenchmarks] = useState<BenchmarkComparisonType | null>(null);
  const [latestUpdate, setLatestUpdate] = useState<ManagerUpdate | null>(null);
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioHistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStock, setSelectedStock] = useState<StockDetail | null>(null);

  const fetchPortfolio = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/portfolio');
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch portfolio');
      }

      setPortfolio(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformance = async (portfolioId: number) => {
    try {
      const response = await fetch(`/api/performance/${portfolioId}`);
      const data = await response.json();

      // Check if the response has an error
      if (data.error) {
        console.warn('Performance API returned error:', data.error);
        // Set null performance to avoid using stale data
        setPerformance(null);
      } else {
        setPerformance(data);
      }
    } catch (err) {
      console.error('Failed to fetch performance:', err);
      setPerformance(null);
    }
  };

  const fetchBenchmarks = async (portfolioId: number, period: '1M' | '3M' | '6M' | '1Y' | 'ALL' = 'ALL') => {
    try {
      const response = await fetch(`/api/benchmarks/${portfolioId}?period=${period}`);
      const data = await response.json();
      // Only set benchmarks if the response has the expected structure
      if (data && data.benchmarks) {
        setBenchmarks(data);
      } else {
        console.warn('Invalid benchmark data received:', data);
        setBenchmarks(null);
      }
    } catch (err) {
      console.error('Failed to fetch benchmarks:', err);
      setBenchmarks(null);
    }
  };

  const fetchLatestUpdate = async (portfolioId: number) => {
    try {
      const response = await fetch(`/api/manager-updates/${portfolioId}?limit=1`);
      const data = await response.json();
      if (data.updates && data.updates.length > 0) {
        setLatestUpdate(data.updates[0]);
      }
    } catch (err) {
      console.error('Failed to fetch updates:', err);
    }
  };

  const fetchPortfolioHistory = async (portfolioId: number) => {
    try {
      const response = await fetch(`/api/portfolio-history/${portfolioId}`);
      const data = await response.json();
      if (data.snapshots) {
        setPortfolioHistory(data.snapshots);
      }
    } catch (err) {
      console.error('Failed to fetch portfolio history:', err);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  useEffect(() => {
    if (portfolio?.id) {
      fetchPerformance(portfolio.id);
      fetchBenchmarks(portfolio.id);
      fetchLatestUpdate(portfolio.id);
      fetchPortfolioHistory(portfolio.id);
    }
  }, [portfolio]);

  // Merge stock data with performance data
  const positionsData = useMemo<PositionRow[]>(() => {
    if (!portfolio) return [];

    return portfolio.stocks.map((stock) => {
      // Safely access stock_details with optional chaining
      const stockPerf = performance?.stock_details?.find(
        (perf) => perf.stock_id === stock.id
      );

      return {
        ...stock,
        currentPrice: stockPerf?.current_price,
        pnlAbsolute: stockPerf?.pnl_absolute,
        pnlPct: stockPerf?.pnl_pct,
      };
    });
  }, [portfolio, performance]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-emerald-500 mx-auto mb-4"></div>
          <p className="text-slate-300 text-lg font-light">Loading your portfolio...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card rounded-xl p-8 max-w-md">
          <AlertCircle className="w-16 h-16 text-rose-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-slate-50 text-center mb-2">Error</h2>
          <p className="text-slate-300 text-center">{error}</p>
          <button
            onClick={fetchPortfolio}
            className="mt-6 w-full bg-emerald-600 text-white py-3 rounded-lg hover:bg-emerald-700 transition-all duration-300 flex items-center justify-center gap-2 font-medium"
          >
            <RefreshCw className="w-5 h-5" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card rounded-xl p-8 max-w-md text-center">
          <h2 className="text-2xl font-bold text-slate-50 mb-2">No Portfolio Found</h2>
          <p className="text-slate-300">Create a portfolio to get started.</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Page Header with orchestrated animation */}
        <div className="animate-fade-in-up">
          <h1 className="text-display-lg font-display font-black text-slate-50 mb-2 tracking-tight">
            Portfolio Dashboard
          </h1>
          <p className="text-slate-400 text-lg font-light">
            AI-Powered Portfolio Management
          </p>
        </div>

        {/* Performance Metrics */}
        <div className="animate-fade-in-up animate-delay-100">
          <PerformanceMetrics performance={performance} loading={!performance} />
        </div>

        {/* Portfolio Value Chart */}
        {performance && (
          <div className="animate-fade-in-up animate-delay-200">
            <PortfolioValueChart
              initialCapital={portfolio?.total_capital || 0}
              currentValue={performance.current_value}
              totalPnlPct={performance.pnl_pct}
              totalPnlAbsolute={performance.pnl_absolute}
              dayReturnPct={performance.day_return_pct}
              dayReturnAbsolute={performance.day_return_absolute}
              historyData={portfolioHistory}
              loading={!performance}
            />
          </div>
        )}

        {/* Benchmark Comparison */}
        <div className="animate-fade-in-up animate-delay-300">
          <BenchmarkComparison
            comparison={benchmarks}
            loading={!benchmarks}
            onPeriodChange={(period) => {
              if (portfolio?.id) fetchBenchmarks(portfolio.id, period);
            }}
            portfolioCreatedAt={portfolio?.created_at}
          />
        </div>

        {/* Latest Manager Update */}
        <div className="animate-fade-in-up animate-delay-400">
          <ManagerUpdateCard update={latestUpdate} loading={!latestUpdate} />
        </div>

        {/* Portfolio Holdings Table */}
        <div className="animate-fade-in-up animate-delay-500">
          <div className="mb-6">
            <h2 className="text-heading-xl font-display text-slate-50">Portfolio Holdings</h2>
            <p className="text-sm text-slate-400 mt-1 font-light">
              {portfolio.stocks.length} position{portfolio.stocks.length !== 1 ? 's' : ''} • <span className="text-gold-400 font-medium">{portfolio.profile}</span> profile
            </p>
          </div>

          <PositionsTable
            stocks={positionsData}
            onStockClick={(stock) => setSelectedStock(stock)}
          />
        </div>

        {/* Footer with Disclaimer - Refined Legal Notice */}
        <div className="relative py-12 border-t border-slate-800/50 animate-fade-in-up animate-delay-600">
          {/* Subtle gradient backdrop */}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-amber-950/5 to-transparent opacity-40"></div>

          <div className="relative max-w-4xl mx-auto">
            {/* Premium disclaimer card */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900/90 via-slate-900/80 to-slate-900/90 border border-amber-900/30 shadow-2xl backdrop-blur-xl">
              {/* Ambient glow effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 via-transparent to-amber-500/5"></div>

              {/* Content */}
              <div className="relative px-8 py-8 sm:px-12 sm:py-10">
                {/* Header with icon */}
                <div className="flex items-center justify-center gap-3 mb-6">
                  <div className="relative">
                    <div className="absolute inset-0 bg-amber-500/20 blur-xl rounded-full"></div>
                    <div className="relative flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-amber-500/20 to-amber-600/20 border border-amber-500/30">
                      <AlertCircle className="w-6 h-6 text-amber-400" strokeWidth={2.5} />
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-slate-100 tracking-tight" style={{ fontFamily: 'DM Sans, sans-serif' }}>
                    Important Disclaimer
                  </h3>
                </div>

                {/* Disclaimer text with refined typography */}
                <div className="space-y-4 text-center max-w-2xl mx-auto">
                  <p className="text-sm leading-relaxed text-slate-300" style={{ fontFamily: 'DM Sans, sans-serif' }}>
                    This application is designed{' '}
                    <span className="font-semibold text-amber-200 bg-amber-500/10 px-2 py-0.5 rounded">
                      for educational and learning purposes only
                    </span>
                    . The information, analysis, and recommendations provided by this AI-powered portfolio management system should{' '}
                    <span className="font-semibold text-rose-200 bg-rose-500/10 px-2 py-0.5 rounded">
                      NOT be considered as financial advice, investment recommendations, or trading tips
                    </span>
                    .
                  </p>

                  <div className="pt-4 border-t border-slate-700/50">
                    <p className="text-xs leading-relaxed text-slate-400" style={{ fontFamily: 'DM Sans, sans-serif' }}>
                      All investment decisions carry inherent risk. Past performance does not guarantee future results.
                      Always conduct your own independent research and consult with a qualified financial advisor before making any investment decisions.
                    </p>
                  </div>
                </div>

                {/* Subtle decorative bottom accent */}
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-32 h-px bg-gradient-to-r from-transparent via-amber-500/30 to-transparent"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stock Detail Modal */}
      <StockDetailModal
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
      />
    </main>
  );
}
