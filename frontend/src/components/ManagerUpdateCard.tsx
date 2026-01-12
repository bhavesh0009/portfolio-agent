'use client';

import { ManagerUpdate } from '@/types';
import { Clock, AlertCircle, CheckCircle, TrendingUp, Activity, Shield } from 'lucide-react';
import Link from 'next/link';

import ReactMarkdown from 'react-markdown';

interface ManagerUpdateCardProps {
  update: ManagerUpdate | null;
  loading?: boolean;
}

export default function ManagerUpdateCard({ update, loading }: ManagerUpdateCardProps) {
  if (loading) {
    return (
      <div className="bg-[#0a1628]/80 backdrop-blur-md border border-slate-800 rounded-2xl shadow-sm p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-800 rounded w-48 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-slate-800 rounded"></div>
            <div className="h-4 bg-slate-800 rounded w-3/4"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!update) {
    return (
      <div className="bg-[#0a1628]/80 backdrop-blur-md border border-slate-800 rounded-2xl shadow-sm p-6">
        <h3 className="text-lg font-bold text-slate-100 mb-4">Today's Analysis</h3>
        <div className="text-center py-8">
          <Activity className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 text-sm">
            No manager updates available yet.
          </p>
          <p className="text-slate-500 text-xs mt-1">
            The portfolio manager will analyze your holdings during the next scheduled run.
          </p>
        </div>

        {/* View All Updates Link */}
        <div className="mt-4 pt-4 border-t border-slate-800 text-center">
          <Link
            href="/updates"
            className="inline-flex items-center gap-2 text-sm font-semibold text-blue-400 hover:text-blue-300 transition-colors group"
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
        return 'border-l-amber-400';
      default:
        return 'border-l-blue-400';
    }
  };

  const getPriorityIconColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-400';
      default:
        return 'bg-blue-500/20 text-blue-400';
    }
  };

  const getRecommendationIcon = (recommendation: string | null) => {
    switch (recommendation) {
      case 'BUY_MORE':
        return <TrendingUp className="h-5 w-5 text-emerald-400" />;
      case 'SELL':
        return <AlertCircle className="h-5 w-5 text-rose-400" />;
      case 'REBALANCE':
        return <Activity className="h-5 w-5 text-blue-400" />;
      case 'HOLD':
        return <Shield className="h-5 w-5 text-slate-400" />;
      default:
        return <CheckCircle className="h-5 w-5 text-slate-500" />;
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
    <div className="bg-[#0a1628] rounded-2xl border border-slate-800 shadow-2xl p-6 relative overflow-hidden">
      {/* Subtle decorative effect matching PortfolioChart */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>

      {/* Header */}
      <div className="flex justify-between items-start mb-6 relative z-10">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 text-slate-400">
            <AlertCircle size={24} />
          </div>
          <div>
            <h3 className="font-bold font-serif text-slate-100 text-xl">{update.title}</h3>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
              <Clock size={12} />
              <span>{formatDate(update.update_date || update.created_at)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recommendation Badge */}
      {update.recommendation && (
        <div className="flex items-center gap-4 px-5 py-4 rounded-xl mb-6 bg-slate-900/30 border border-slate-800 relative z-10">
          <div className={`p-2 rounded-lg ${update.recommendation === 'REBALANCE' ? 'bg-blue-500/10' :
            update.recommendation === 'BUY_MORE' ? 'bg-emerald-500/10' :
              update.recommendation === 'SELL' ? 'bg-rose-500/10' :
                'bg-slate-500/10'
            }`}>
            {getRecommendationIcon(update.recommendation)}
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase text-slate-500 tracking-wider block mb-0.5">Recommendation</span>
            <span className={`text-sm font-bold tracking-wide ${update.recommendation === 'REBALANCE' ? 'text-blue-400' :
              update.recommendation === 'BUY_MORE' ? 'text-emerald-400' :
                update.recommendation === 'SELL' ? 'text-rose-400' :
                  'text-slate-300'
              }`}>{update.recommendation.replace('_', ' ')}</span>
          </div>
        </div>
      )}

      {/* Description */}
      <div className="mb-8 prose prose-invert max-w-none border-b border-slate-800 pb-6">
        <ReactMarkdown
          components={{
            p: ({ node, ...props }) => <p className="text-base text-slate-300 font-serif leading-loose mb-4 last:mb-0" {...props} />,
          }}
        >
          {parseDescription(update.description)}
        </ReactMarkdown>
      </div>

      {/* Reasoning */}
      {update.reasoning && (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Analysis</p>
          <div className="prose prose-invert max-w-none">
            <ReactMarkdown
              components={{
                p: ({ node, ...props }) => <p className="text-base text-slate-300 font-serif leading-loose mb-4 last:mb-0" {...props} />,
                strong: ({ node, ...props }) => <span className="font-bold text-slate-100" {...props} />,
                ul: ({ node, ...props }) => <ul className="list-none space-y-3 my-4" {...props} />,
                li: ({ node, ...props }) => <li className="text-base text-slate-300 font-serif leading-loose pl-4 border-l-2 border-slate-700" {...props} />
              }}
            >
              {update.reasoning}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Affected Stocks */}
      {update.affected_stocks && update.affected_stocks.length > 0 && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Affected:</span>
          {update.affected_stocks.map((ticker) => (
            <span
              key={ticker}
              className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs font-semibold text-slate-300 shadow-sm"
            >
              {ticker}
            </span>
          ))}
        </div>
      )}

      {/* View All Updates Link */}
      <div className="mt-5 pt-4 border-t border-slate-800">
        <Link
          href="/updates"
          className="inline-flex items-center gap-2 text-sm font-semibold text-blue-400 hover:text-blue-300 transition-colors group"
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
