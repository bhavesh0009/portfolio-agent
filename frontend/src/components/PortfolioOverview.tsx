'use client';

import type { Portfolio } from '@/types';
import { formatCurrency, formatDate, cn } from '@/lib/utils';
import { TrendingUp, Calendar, Target, PieChart, Wallet } from 'lucide-react';

interface PortfolioOverviewProps {
  portfolio: Portfolio;
  stats: {
    totalAllocated: number;
    cashBalance?: number;
    totalValue?: number;
    stockCount: number;
    sectorDistribution: Record<string, number>;
    averageAllocation: number;
  };
}

export default function PortfolioOverview({ portfolio, stats }: PortfolioOverviewProps) {
  const sectors = Object.entries(stats.sectorDistribution).sort((a, b) => b[1] - a[1]);

  return (
    <div className="bg-gradient-to-br from-primary-600 to-primary-800 rounded-2xl shadow-2xl p-8 text-white animate-slide-up">
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Portfolio Dashboard</h1>
          <div className="flex items-center gap-4 text-primary-100">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span className="text-sm">Created {formatDate(portfolio.created_at)}</span>
            </div>
            <div className="px-3 py-1 bg-white/20 rounded-full text-sm font-medium">
              {portfolio.profile.toUpperCase()}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm text-primary-100 mb-1">Total Capital</div>
          <div className="text-3xl font-bold">{formatCurrency(stats.totalValue || stats.totalAllocated)}</div>
          {stats.cashBalance !== undefined && stats.cashBalance > 0 && (
            <div className="text-xs text-primary-100 mt-1">
              {formatCurrency(stats.totalAllocated)} invested + {formatCurrency(stats.cashBalance)} cash
            </div>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Total Stocks */}
        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white/20 rounded-lg">
              <PieChart className="w-5 h-5" />
            </div>
            <div className="text-sm text-primary-100">Total Stocks</div>
          </div>
          <div className="text-3xl font-bold">{stats.stockCount}</div>
          <div className="text-xs text-primary-100 mt-1">
            Avg: {formatCurrency(stats.averageAllocation)}
          </div>
        </div>

        {/* Top Sector */}
        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white/20 rounded-lg">
              <Target className="w-5 h-5" />
            </div>
            <div className="text-sm text-primary-100">Top Sector</div>
          </div>
          <div className="text-2xl font-bold">{sectors[0]?.[0] || 'N/A'}</div>
          <div className="text-xs text-primary-100 mt-1">
            {sectors[0]?.[1].toFixed(1)}% allocation
          </div>
        </div>

        {/* Performance */}
        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white/20 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div className="text-sm text-primary-100">Status</div>
          </div>
          <div className="text-2xl font-bold">Active</div>
          <div className="text-xs text-primary-100 mt-1">
            Monitoring {stats.stockCount} positions
          </div>
        </div>

        {/* Cash Balance */}
        {stats.cashBalance !== undefined && stats.cashBalance > 0 && (
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-white/20 rounded-lg">
                <Wallet className="w-5 h-5" />
              </div>
              <div className="text-sm text-primary-100">Cash Balance</div>
            </div>
            <div className="text-2xl font-bold">{formatCurrency(stats.cashBalance)}</div>
            <div className="text-xs text-primary-100 mt-1">
              {((stats.cashBalance / (stats.totalValue || stats.totalAllocated)) * 100).toFixed(2)}% unallocated
            </div>
          </div>
        )}
      </div>

      {/* Sector Distribution */}
      <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <PieChart className="w-5 h-5" />
          Sector Distribution
        </h3>
        <div className="space-y-3">
          {sectors.map(([sector, percentage]) => (
            <div key={sector}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-primary-100">{sector}</span>
                <span className="font-semibold">{percentage.toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-white to-primary-200 rounded-full transition-all duration-500"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
