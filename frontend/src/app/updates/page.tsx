'use client';

import { useState, useEffect } from 'react';
import { ManagerUpdate, ManagerUpdatesResponse } from '@/types';
import { Clock, AlertCircle, CheckCircle, TrendingUp, Activity, Shield, Filter, ChevronDown } from 'lucide-react';
import Link from 'next/link';

export default function UpdatesTimelinePage() {
  const [portfolioId, setPortfolioId] = useState<number | null>(null);
  const [updates, setUpdates] = useState<ManagerUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [filterPriority, setFilterPriority] = useState<string | null>(null);

  // Fetch active portfolio on mount
  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await fetch('/api/portfolio');
        const data = await response.json();
        if (data.success && data.data?.id) {
          setPortfolioId(data.data.id);
        }
      } catch (error) {
        console.error('Failed to fetch portfolio:', error);
      }
    };
    fetchPortfolio();
  }, []);

  // Fetch updates when portfolio ID or filters change
  useEffect(() => {
    if (portfolioId) {
      fetchUpdates();
    }
  }, [portfolioId, filterStatus, filterPriority]);

  const fetchUpdates = async () => {
    if (!portfolioId) return;

    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus) params.append('status', filterStatus);
      if (filterPriority) params.append('priority', filterPriority);
      params.append('limit', '50');

      const response = await fetch(`/api/manager-updates/${portfolioId}?${params}`);
      const data: ManagerUpdatesResponse = await response.json();

      setUpdates(data.updates || []);
    } catch (error) {
      console.error('Failed to fetch updates:', error);
    } finally {
      setLoading(false);
    }
  };

  // Group updates by date
  const groupedUpdates = updates.reduce((groups, update) => {
    const date = new Date(update.update_date).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(update);
    return groups;
  }, {} as Record<string, ManagerUpdate[]>);

  return (
    <div className="min-h-screen text-slate-50 selection:bg-emerald-500/30">
      {/* Dynamic Background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-blue-900/20 to-transparent pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-emerald-900/10 rounded-full blur-[100px] pointer-events-none" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="text-sm text-emerald-400 hover:text-emerald-300 mb-2 inline-flex items-center gap-1 transition-colors"
          >
            ← Back to Dashboard
          </Link>
          <h1 className="text-4xl md:text-5xl font-bold font-serif text-transparent bg-clip-text bg-gradient-to-r from-slate-50 to-slate-400 mb-2">
            Portfolio Manager Updates
          </h1>
          <p className="text-slate-400 text-lg font-light">
            Complete history of AI-powered portfolio analysis and recommendations
          </p>
        </div>

        {/* Filters */}
        <div className="bg-[#0f172a]/60 backdrop-blur-md border border-slate-800 rounded-xl shadow-sm p-4 mb-6">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-slate-400" />
              <span className="text-sm font-medium text-slate-300">Filters:</span>
            </div>

            {/* Status Filter */}
            <select
              value={filterStatus || ''}
              onChange={(e) => setFilterStatus(e.target.value || null)}
              className="px-3 py-1.5 bg-[#1e293b] border border-slate-700 text-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Status</option>
              <option value="PENDING">Pending</option>
              <option value="EXECUTED">Executed</option>
              <option value="IGNORED">Ignored</option>
            </select>

            {/* Priority Filter */}
            <select
              value={filterPriority || ''}
              onChange={(e) => setFilterPriority(e.target.value || null)}
              className="px-3 py-1.5 bg-[#1e293b] border border-slate-700 text-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Priority</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            {(filterStatus || filterPriority) && (
              <button
                onClick={() => {
                  setFilterStatus(null);
                  setFilterPriority(null);
                }}
                className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Timeline */}
        {loading ? (
          <div className="space-y-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-6 bg-slate-700 rounded w-48 mb-4"></div>
                <div className="bg-[#0f172a]/60 backdrop-blur-md border border-slate-800 rounded-xl p-6">
                  <div className="h-4 bg-slate-700 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-slate-700 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        ) : Object.keys(groupedUpdates).length === 0 ? (
          <div className="bg-[#0f172a]/60 backdrop-blur-md border border-slate-800 rounded-xl p-12 text-center">
            <Activity className="h-16 w-16 text-emerald-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-50 mb-2">No updates found</h3>
            <p className="text-slate-400">
              {filterStatus || filterPriority
                ? 'Try adjusting your filters'
                : 'Portfolio manager updates will appear here after the next scheduled run'}
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {Object.entries(groupedUpdates).map(([date, dayUpdates]) => (
              <div key={date}>
                {/* Date Header */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-1 h-px bg-slate-700"></div>
                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">
                    {date}
                  </h2>
                  <div className="flex-1 h-px bg-slate-700"></div>
                </div>

                {/* Updates for this date */}
                <div className="space-y-4">
                  {dayUpdates.map((update) => (
                    <TimelineUpdateCard key={update.id} update={update} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface TimelineUpdateCardProps {
  update: ManagerUpdate;
}

function TimelineUpdateCard({ update }: TimelineUpdateCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
      case 'HIGH':
        return 'border-amber-400';
      case 'MEDIUM':
        return 'border-blue-400';
      default:
        return 'border-slate-600';
    }
  };

  const getRecommendationIcon = (recommendation: string | null) => {
    switch (recommendation) {
      case 'BUY_MORE':
        return <TrendingUp className="h-4 w-4 text-emerald-400" />;
      case 'SELL':
        return <AlertCircle className="h-4 w-4 text-rose-400" />;
      case 'REBALANCE':
        return <Activity className="h-4 w-4 text-blue-400" />;
      case 'HOLD':
        return <Shield className="h-4 w-4 text-slate-400" />;
      default:
        return null;
    }
  };

  const formatTime = (dateStr: string) => {
    // Convert UTC to IST (UTC+5:30)
    const utcDate = new Date(dateStr);
    const istDate = new Date(utcDate.getTime() + (5.5 * 60 * 60 * 1000));
    return istDate.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  const parseDescription = (desc: string) => {
    // Try to parse JSON description
    try {
      const parsed = JSON.parse(desc);
      if (parsed.summary) {
        return parsed.summary;
      }
      if (parsed.title && parsed.summary) {
        return `${parsed.title}: ${parsed.summary}`;
      }
      return desc;
    } catch {
      // Not JSON, return as-is
      return desc;
    }
  };

  return (
    <div className={`bg-[#0f172a]/60 backdrop-blur-md border-l-4 ${getPriorityColor(update.priority)} rounded-lg shadow-md hover:shadow-xl transition-all`}>
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-4 w-4 text-slate-400" />
              <span className="text-xs text-slate-400">{formatTime(update.created_at)}</span>
              {update.priority === 'CRITICAL' && (
                <span className="px-2 py-0.5 bg-rose-600 text-white text-xs font-bold rounded-full">
                  URGENT
                </span>
              )}
            </div>
            <h3 className="text-base font-semibold text-slate-50">{update.title}</h3>
          </div>

          {update.recommendation && (
            <div className="flex items-center gap-1 px-2 py-1 bg-slate-800/50 border border-slate-700 rounded-md">
              {getRecommendationIcon(update.recommendation)}
              <span className="text-xs font-medium text-slate-300">
                {update.recommendation.replace('_', ' ')}
              </span>
            </div>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-slate-300 mb-3">{parseDescription(update.description)}</p>

        {/* Affected Stocks */}
        {update.affected_stocks && update.affected_stocks.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {update.affected_stocks.map((stock) => (
              <span
                key={stock}
                className="px-2 py-0.5 bg-slate-800 border border-slate-700 text-emerald-400 font-mono rounded text-xs font-medium"
              >
                {stock}
              </span>
            ))}
          </div>
        )}

        {/* Expandable Reasoning */}
        {update.reasoning && (
          <div className="mb-3">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
            >
              <span>{isExpanded ? 'Hide' : 'Show'} Analysis</span>
              <ChevronDown className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
            </button>

            {isExpanded && (
              <div className="mt-2 p-3 bg-slate-800/50 border border-slate-700 rounded-md">
                <p className="text-sm text-slate-300">{update.reasoning}</p>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center gap-2 text-xs">
          <span className={`px-2 py-1 rounded border ${
            update.status === 'EXECUTED' ? 'bg-emerald-900/30 text-emerald-400 border-emerald-700' :
            update.status === 'PENDING' ? 'bg-amber-900/30 text-amber-400 border-amber-700' :
            'bg-slate-800 text-slate-400 border-slate-700'
          }`}>
            {update.status}
          </span>
          <span className="text-slate-500">Priority: <span className="font-medium text-slate-300">{update.priority}</span></span>
        </div>
      </div>
    </div>
  );
}
