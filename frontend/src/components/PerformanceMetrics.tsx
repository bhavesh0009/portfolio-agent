'use client';

import { PortfolioPerformance } from '@/types';
import { TrendingUp, TrendingDown, DollarSign, Activity, Shield, BarChart3, Wallet } from 'lucide-react';

interface PerformanceMetricsProps {
  performance: PortfolioPerformance | null;
  loading?: boolean;
}

export default function PerformanceMetrics({ performance, loading }: PerformanceMetricsProps) {
  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-24"></div>
                <div className="h-10 bg-gray-200 rounded w-full"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!performance) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-6">
        <p className="text-gray-500 text-center">No performance data available</p>
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
    <div className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 rounded-lg shadow-md p-6 mb-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Portfolio Performance</h2>
        <p className="text-sm text-gray-500 mt-1">
          Last updated: {performance.calculated_at ? new Date(performance.calculated_at).toLocaleString('en-IN') : 'Not available'}
        </p>
      </div>

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        {/* Current Value */}
        <MetricCard
          title="Current Value"
          value={formatCurrency(performance.current_value)}
          icon={<DollarSign className="h-5 w-5" />}
          iconColor="bg-blue-100 text-blue-600"
        />

        {/* Total P&L */}
        <MetricCard
          title="Total P&L"
          value={formatCurrency(performance.pnl_absolute)}
          subtitle={formatPercent(performance.pnl_pct)}
          icon={isPositive(performance.pnl_pct) ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
          iconColor={isPositive(performance.pnl_pct) ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}
          trend={isPositive(performance.pnl_pct) ? 'positive' : 'negative'}
        />

        {/* Day Return */}
        <MetricCard
          title="Day Return"
          value={formatCurrency(performance.day_return_absolute)}
          subtitle={formatPercent(performance.day_return_pct)}
          icon={<Activity className="h-5 w-5" />}
          iconColor={isPositive(performance.day_return_pct) ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}
          trend={isPositive(performance.day_return_pct) ? 'positive' : 'negative'}
        />

        {/* Sharpe Ratio */}
        <MetricCard
          title="Sharpe Ratio"
          value={performance.sharpe_ratio !== null && performance.sharpe_ratio !== undefined ? performance.sharpe_ratio.toFixed(2) : 'N/A'}
          subtitle="Risk-adjusted return"
          icon={<Shield className="h-5 w-5" />}
          iconColor="bg-purple-100 text-purple-600"
        />

        {/* Cash Balance */}
        <MetricCard
          title="Cash Balance"
          value={formatCurrency(performance.cash_balance ?? 0)}
          subtitle={`${((performance.cash_balance ?? 0) / performance.current_value * 100).toFixed(1)}% of portfolio`}
          icon={<Wallet className="h-5 w-5" />}
          iconColor="bg-amber-100 text-amber-600"
        />
      </div>

      {/* Risk Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <RiskMetricCard
          title="Volatility"
          value={formatPercent(performance.volatility)}
          description="Annualized standard deviation"
        />

        <RiskMetricCard
          title="Max Drawdown"
          value={performance.max_drawdown !== null && performance.max_drawdown !== undefined && !isNaN(performance.max_drawdown)
            ? `-${performance.max_drawdown.toFixed(2)}%`
            : 'N/A'}
          description="Largest peak-to-trough decline"
        />

        <RiskMetricCard
          title="Holdings"
          value={`${performance.num_stocks} stocks`}
          description={`Initial capital: ${formatCurrency(performance.initial_capital)}`}
        />
      </div>
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
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between mb-3">
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <div className={`p-2 rounded-lg ${iconColor}`}>
          {icon}
        </div>
      </div>
      <div>
        <p className={`text-2xl font-bold ${trend === 'positive' ? 'text-green-600' : trend === 'negative' ? 'text-red-600' : 'text-gray-900'}`}>
          {value}
        </p>
        {subtitle && (
          <p className={`text-sm mt-1 ${trend === 'positive' ? 'text-green-600' : trend === 'negative' ? 'text-red-600' : 'text-gray-500'}`}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}

interface RiskMetricCardProps {
  title: string;
  value: string;
  description: string;
}

function RiskMetricCard({ title, value, description }: RiskMetricCardProps) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{title}</p>
      <p className="text-xl font-bold text-gray-900 mb-1">{value}</p>
      <p className="text-xs text-gray-600">{description}</p>
    </div>
  );
}
