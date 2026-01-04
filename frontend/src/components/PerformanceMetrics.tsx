'use client';

import { PortfolioPerformance } from '@/types';
import { TrendingUp, TrendingDown, DollarSign, Activity, Shield, BarChart3, Wallet, ArrowUpRight, ArrowDownRight, TrendingDown as Volatility, AlertTriangle } from 'lucide-react';

interface PerformanceMetricsProps {
  performance: PortfolioPerformance | null;
  loading?: boolean;
}

export default function PerformanceMetrics({ performance, loading }: PerformanceMetricsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="bg-[#0f172a]/60 backdrop-blur-md border border-slate-800 rounded-xl p-5 animate-pulse">
            <div className="h-4 bg-slate-700 rounded w-24 mb-4"></div>
            <div className="h-8 bg-slate-700 rounded w-full"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!performance) {
    return (
      <div className="bg-[#0f172a]/60 backdrop-blur-md border border-slate-800 rounded-xl p-8 text-center">
        <p className="text-slate-400">No performance data available</p>
      </div>
    );
  }

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined || isNaN(value)) {
      return 'N/A';
    }
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number | null | undefined, decimals: number = 2) => {
    if (value === null || value === undefined || isNaN(value)) {
      return 'N/A';
    }
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  };

  const isPositive = (value: number | null | undefined) => {
    if (value === null || value === undefined) return false;
    return value >= 0;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Row 1 - Card 1: Current Value */}
      <MetricCard
        title="Current Value"
        value={formatCurrency(performance.current_value)}
        icon={<DollarSign className="h-5 w-5" />}
        iconColor="bg-blue-100 text-blue-600"
      />

      {/* Row 1 - Card 2: Total P&L */}
      <MetricCard
        title="Total P&L"
        value={formatCurrency(performance.pnl_absolute)}
        subtitle={formatPercent(performance.pnl_pct)}
        icon={isPositive(performance.pnl_pct) ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
        iconColor={isPositive(performance.pnl_pct) ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}
        trend={isPositive(performance.pnl_pct) ? 'positive' : 'negative'}
      />

      {/* Row 1 - Card 3: Day Return */}
      <MetricCard
        title="Day Return"
        value={formatCurrency(performance.day_return_absolute)}
        subtitle={formatPercent(performance.day_return_pct)}
        icon={<Activity className="h-5 w-5" />}
        iconColor={isPositive(performance.day_return_pct) ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}
        trend={isPositive(performance.day_return_pct) ? 'positive' : 'negative'}
      />

      {/* Row 1 - Card 4: Sharpe Ratio */}
      <MetricCard
        title="Sharpe Ratio"
        value={performance.sharpe_ratio !== null && performance.sharpe_ratio !== undefined ? performance.sharpe_ratio.toFixed(2) : 'N/A'}
        subtitle="Risk-adjusted return"
        icon={<Shield className="h-5 w-5" />}
        iconColor="bg-purple-100 text-purple-600"
      />

      {/* Row 2 - Card 5: Volatility */}
      <MetricCard
        title="Volatility"
        value={formatPercent(performance.volatility)}
        subtitle="Annualized Std. Dev."
        icon={<BarChart3 className="h-5 w-5" />}
        iconColor="bg-slate-100 text-slate-600"
      />

      {/* Row 2 - Card 6: Max Drawdown */}
      <MetricCard
        title="Max Drawdown"
        value={performance.max_drawdown !== null && performance.max_drawdown !== undefined && !isNaN(performance.max_drawdown)
          ? `-${performance.max_drawdown.toFixed(2)}%`
          : 'N/A'}
        subtitle="Peak to Trough"
        icon={<AlertTriangle className="h-5 w-5" />}
        iconColor="bg-orange-100 text-orange-600"
      />

      {/* Row 2 - Card 7: Holdings */}
      <MetricCard
        title="Holdings"
        value={`${performance.num_stocks} stocks`}
        subtitle={`Capital: ${formatCurrency(performance.initial_capital)}`}
        icon={<BarChart3 className="h-5 w-5" />}
        iconColor="bg-indigo-100 text-indigo-600"
      />

      {/* Row 2 - Card 8: Cash Balance */}
      <MetricCard
        title="Cash Balance"
        value={formatCurrency(performance.cash_balance ?? 0)}
        subtitle={`${((performance.cash_balance ?? 0) / performance.current_value * 100).toFixed(1)}% of portfolio`}
        icon={<Wallet className="h-5 w-5" />}
        iconColor="bg-amber-100 text-amber-600"
      />
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  iconColor: string;
  trend?: 'positive' | 'negative';
}

function MetricCard({ title, value, subtitle, icon, iconColor, trend }: MetricCardProps) {
  return (
    <div className="bg-[#0f172a]/60 backdrop-blur-md border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all duration-300 hover:transform hover:-translate-y-1 hover:shadow-xl group">
      <div className="flex items-start justify-between mb-4">
        <p className="text-sm font-medium text-slate-400 group-hover:text-slate-300 transition-colors">{title}</p>
        <div className={`p-2.5 rounded-lg ${iconColor} bg-opacity-10 ring-1 ring-inset ring-opacity-20`}>
          {icon}
        </div>
      </div>
      <div>
        <p className={`text-2xl font-bold font-mono tabular-nums tracking-tight ${trend === 'positive' ? 'text-emerald-400' : trend === 'negative' ? 'text-rose-400' : 'text-slate-50'}`}>
          {value}
        </p>
        {subtitle && (
          <p className={`text-sm mt-1.5 font-medium flex items-center gap-1 ${trend === 'positive' ? 'text-emerald-500' : trend === 'negative' ? 'text-rose-500' : 'text-slate-500'}`}>
            {trend === 'positive' ? <ArrowUpRight className="w-3 h-3" /> : trend === 'negative' ? <ArrowDownRight className="w-3 h-3" /> : null}
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}

