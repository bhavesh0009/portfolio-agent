'use client';

import { ManagerUpdate } from '@/types';
import { Clock, AlertCircle, CheckCircle, TrendingUp, Activity, Shield } from 'lucide-react';
import Link from 'next/link';

interface ManagerUpdateCardProps {
  update: ManagerUpdate | null;
  loading?: boolean;
}

export default function ManagerUpdateCard({ update, loading }: ManagerUpdateCardProps) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!update) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
        <h3 className="text-lg font-bold text-slate-900 mb-4">Today's Analysis</h3>
        <div className="text-center py-8">
          <Activity className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">
            No manager updates available yet.
          </p>
          <p className="text-slate-400 text-xs mt-1">
            The portfolio manager will analyze your holdings during the next scheduled run.
          </p>
        </div>

        {/* View All Updates Link */}
        <div className="mt-4 pt-4 border-t border-slate-200 text-center">
          <Link
            href="/updates"
            className="inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors group"
          >
            <span>View all updates</span>
            <svg
              className="w-4 h-4 transition-transform group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </div>
    );
  }

  const getPriorityBorderColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
      case 'HIGH':
        return 'border-amber-400';
      default:
        return 'border-blue-400';
    }
  };

  const getPriorityIconColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
      case 'HIGH':
        return 'bg-amber-100 text-amber-600';
      default:
        return 'bg-blue-100 text-blue-600';
    }
  };

  const getRecommendationIcon = (recommendation: string | null) => {
    switch (recommendation) {
      case 'BUY_MORE':
        return <TrendingUp className="h-5 w-5 text-green-600" />;
      case 'SELL':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      case 'REBALANCE':
        return <Activity className="h-5 w-5 text-blue-600" />;
      case 'HOLD':
        return <Shield className="h-5 w-5 text-gray-600" />;
      default:
        return <CheckCircle className="h-5 w-5 text-gray-400" />;
    }
  };

  const getRecommendationColor = (recommendation: string | null) => {
    switch (recommendation) {
      case 'BUY_MORE':
        return 'text-green-600 bg-green-100';
      case 'SELL':
        return 'text-red-600 bg-red-100';
      case 'REBALANCE':
        return 'text-blue-600 bg-blue-100';
      case 'HOLD':
        return 'text-gray-600 bg-gray-100';
      default:
        return 'text-gray-400 bg-gray-50';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Parse JSON description if it's a JSON string
  const parseDescription = (desc: string) => {
    try {
      const parsed = JSON.parse(desc);
      return parsed.summary || desc;
    } catch {
      return desc;
    }
  };

  return (
    <div className={`bg-white rounded-2xl border-l-4 shadow-md p-6 ${getPriorityBorderColor(update.priority)}`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full ${getPriorityIconColor(update.priority)}`}>
            <AlertCircle size={20} />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-lg">{update.title}</h3>
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
              <Clock size={12} />
              <span>{formatDate(update.update_date || update.created_at)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recommendation Badge */}
      {update.recommendation && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl mb-5 ${
          update.recommendation === 'REBALANCE' ? 'bg-blue-50 text-blue-900 border border-blue-100' :
          update.recommendation === 'BUY_MORE' ? 'bg-emerald-50 text-emerald-900 border border-emerald-100' :
          update.recommendation === 'SELL' ? 'bg-rose-50 text-rose-900 border border-rose-100' :
          'bg-slate-50 text-slate-900 border border-slate-100'
        }`}>
          <div className={`p-1.5 rounded-full ${
            update.recommendation === 'REBALANCE' ? 'bg-blue-200 text-blue-700' :
            update.recommendation === 'BUY_MORE' ? 'bg-emerald-200 text-emerald-700' :
            update.recommendation === 'SELL' ? 'bg-rose-200 text-rose-700' :
            'bg-slate-200 text-slate-700'
          }`}>
            {getRecommendationIcon(update.recommendation)}
          </div>
          <div>
            <span className="text-xs font-bold uppercase opacity-60 block mb-0.5">Recommendation</span>
            <span className="text-sm font-bold tracking-wide">{update.recommendation.replace('_', ' ')}</span>
          </div>
        </div>
      )}

      {/* Description */}
      <p className="text-slate-600 leading-relaxed mb-4 text-sm">
        {parseDescription(update.description)}
      </p>

      {/* Reasoning */}
      {update.reasoning && (
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Analysis</p>
          <p className="text-sm text-slate-700 italic">"{update.reasoning}"</p>
        </div>
      )}

      {/* Affected Stocks */}
      {update.affected_stocks && update.affected_stocks.length > 0 && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-100">
          <span className="text-xs text-slate-400 font-medium">Affected:</span>
          {update.affected_stocks.map((ticker) => (
            <span
              key={ticker}
              className="px-2 py-1 bg-white border border-slate-200 rounded text-xs font-semibold text-slate-600 shadow-sm"
            >
              {ticker}
            </span>
          ))}
        </div>
      )}

      {/* View All Updates Link */}
      <div className="mt-5 pt-4 border-t border-slate-200">
        <Link
          href="/updates"
          className="inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors group"
        >
          <span>View all updates</span>
          <svg
            className="w-4 h-4 transition-transform group-hover:translate-x-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
    </div>
  );
}
