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
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-6">
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
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Today's Analysis</h3>
        <div className="text-center py-8">
          <Activity className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">
            No manager updates available yet.
          </p>
          <p className="text-gray-400 text-xs mt-1">
            The portfolio manager will analyze your holdings during the next scheduled run.
          </p>
        </div>
      </div>
    );
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
        return 'border-red-300 bg-red-50';
      case 'HIGH':
        return 'border-orange-300 bg-orange-50';
      case 'MEDIUM':
        return 'border-yellow-300 bg-yellow-50';
      default:
        return 'border-blue-300 bg-blue-50';
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
    const now = new Date();
    const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  };

  return (
    <div className={`border-2 rounded-lg shadow-md p-6 mb-6 ${getPriorityColor(update.priority)}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-lg font-bold text-gray-900">{update.title}</h3>
            {update.priority === 'CRITICAL' && (
              <span className="px-2 py-0.5 bg-red-600 text-white text-xs font-bold rounded-full animate-pulse">
                URGENT
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Clock className="h-4 w-4" />
            <span>{formatDate(update.created_at)}</span>
            <span className="text-gray-400">•</span>
            <span className="capitalize">{update.update_type.replace('_', ' ').toLowerCase()}</span>
          </div>
        </div>

        {update.recommendation && (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${getRecommendationColor(update.recommendation)}`}>
            {getRecommendationIcon(update.recommendation)}
            <span className="text-sm font-semibold">
              {update.recommendation.replace('_', ' ')}
            </span>
          </div>
        )}
      </div>

      {/* Description */}
      <p className="text-gray-700 mb-4 leading-relaxed">
        {update.description}
      </p>

      {/* Affected Stocks */}
      {update.affected_stocks && update.affected_stocks.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-600 mb-2">Affected Stocks:</p>
          <div className="flex flex-wrap gap-2">
            {update.affected_stocks.map((stock) => (
              <span
                key={stock}
                className="px-2 py-1 bg-white border border-gray-300 rounded-md text-xs font-medium text-gray-700"
              >
                {stock}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning */}
      {update.reasoning && (
        <div className="bg-white/50 border border-gray-300 rounded-lg p-3 mb-4">
          <p className="text-xs font-medium text-gray-600 mb-1">Analysis:</p>
          <p className="text-sm text-gray-700">{update.reasoning}</p>
        </div>
      )}

      {/* Confidence Score */}
      {update.confidence_score !== null && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-medium text-gray-600">Confidence</span>
            <span className="font-bold text-gray-900">{update.confidence_score}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                update.confidence_score >= 75 ? 'bg-green-500' :
                update.confidence_score >= 50 ? 'bg-yellow-500' :
                'bg-orange-500'
              }`}
              style={{ width: `${update.confidence_score}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-300">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-md text-xs font-medium ${
            update.status === 'EXECUTED' ? 'bg-green-100 text-green-700' :
            update.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
            'bg-gray-100 text-gray-700'
          }`}>
            {update.status}
          </span>
          <span className="text-xs text-gray-500">
            Priority: <span className="font-medium">{update.priority}</span>
          </span>
        </div>

        <Link
          href="/updates"
          className="text-sm text-blue-600 hover:text-blue-700 font-medium hover:underline"
        >
          View All Updates →
        </Link>
      </div>
    </div>
  );
}
