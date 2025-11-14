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

  const fetchPerformance = async () => {
    try {
      const response = await fetch('/api/performance/1');
      const data = await response.json();
      setPerformance(data);
    } catch (err) {
      console.error('Failed to fetch performance:', err);
    }
  };

  const fetchBenchmarks = async (period: '1M' | '3M' | '6M' | '1Y' | 'ALL' = 'ALL') => {
    try {
      const response = await fetch(`/api/benchmarks/1?period=${period}`);
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

  const fetchLatestUpdate = async () => {
    try {
      const response = await fetch('/api/manager-updates/1?limit=1');
      const data = await response.json();
      if (data.updates && data.updates.length > 0) {
        setLatestUpdate(data.updates[0]);
      }
    } catch (err) {
      console.error('Failed to fetch updates:', err);
    }
  };

  const fetchPortfolioHistory = async () => {
    try {
      const response = await fetch('/api/portfolio-history/1');
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
    fetchPerformance();
    fetchBenchmarks();
    fetchLatestUpdate();
    fetchPortfolioHistory();
  }, []);

  // Merge stock data with performance data
  const positionsData = useMemo<PositionRow[]>(() => {
    if (!portfolio || !performance) return [];

    return portfolio.stocks.map((stock) => {
      const stockPerf = performance.stock_details.find(
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

        {/* Portfolio Value Chart */}
        {performance && (
          <div className="animate-fade-in-up animate-delay-100">
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

        {/* Performance Metrics */}
        <div className="animate-fade-in-up animate-delay-200">
          <PerformanceMetrics performance={performance} loading={!performance} />
        </div>

        {/* Benchmark Comparison */}
        <div className="animate-fade-in-up animate-delay-300">
          <BenchmarkComparison
            comparison={benchmarks}
            loading={!benchmarks}
            onPeriodChange={(period) => fetchBenchmarks(period)}
          />
        </div>

        {/* Latest Manager Update */}
        <div className="animate-fade-in-up animate-delay-400">
          <ManagerUpdateCard update={latestUpdate} loading={!latestUpdate} />
        </div>

        {/* Portfolio Holdings Table */}
        <div className="animate-fade-in-up animate-delay-500">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-heading-xl font-display text-slate-50">Portfolio Holdings</h2>
              <p className="text-sm text-slate-400 mt-1 font-light">
                {portfolio.stocks.length} position{portfolio.stocks.length !== 1 ? 's' : ''} • <span className="text-gold-400 font-medium">{portfolio.profile}</span> profile
              </p>
            </div>
            <button
              onClick={() => {
                fetchPortfolio();
                fetchPerformance();
                fetchBenchmarks();
                fetchLatestUpdate();
                fetchPortfolioHistory();
              }}
              className="glass-card glass-card-hover flex items-center gap-2 px-4 py-2 rounded-lg text-slate-200 text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh All
            </button>
          </div>

          <PositionsTable
            stocks={positionsData}
            onStockClick={(stock) => setSelectedStock(stock)}
          />
        </div>

        {/* Footer */}
        <div className="text-center text-slate-500 text-sm py-8 border-t border-slate-800 animate-fade-in-up animate-delay-600">
          <p className="font-medium text-slate-400">Portfolio Agent - AI-Powered Portfolio Management</p>
          <p className="mt-1 text-xs">Last updated: {new Date(portfolio.created_at).toLocaleString()}</p>
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
