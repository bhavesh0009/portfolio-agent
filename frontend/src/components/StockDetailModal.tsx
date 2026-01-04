'use client';

import type { StockDetail } from '@/types';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { X, TrendingUp, AlertTriangle, Target, Clock } from 'lucide-react';

interface StockDetailModalProps {
  stock: StockDetail | null;
  onClose: () => void;
}

export default function StockDetailModal({ stock, onClose }: StockDetailModalProps) {
  if (!stock) return null;

  const targetGain = ((stock.target_price - stock.entry_price) / stock.entry_price) * 100;
  const stopLossDistance = ((stock.entry_price - stock.stop_loss_price) / stock.entry_price) * 100;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[#0f172a]/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl animate-fade-in">
        {/* Modal Header */}
        <div className="sticky top-0 z-10 bg-gradient-to-r from-slate-900 to-slate-800 p-6 flex justify-between items-start text-white">
          <div>
            <h2 className="text-3xl font-bold font-serif mb-2">{stock.name}</h2>
            <div className="flex items-center gap-3">
              <span className="text-emerald-400 font-mono font-bold">{stock.ticker}</span>
              {stock.sector && (
                <span className="px-2 py-0.5 bg-white/10 rounded text-xs text-slate-300">
                  {stock.sector}
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="p-8 space-y-8 bg-slate-50">
          {/* Price Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs text-slate-500 mb-1">Entry Price</p>
              <p className="text-2xl font-bold text-slate-900 font-mono">{formatCurrency(stock.entry_price)}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs text-slate-500 mb-1">Allocation</p>
              <p className="text-2xl font-bold text-blue-900 font-mono">{stock.allocation_pct}%</p>
              <p className="text-xs text-blue-600 font-medium">{formatCurrency(stock.allocation_amount)}</p>
            </div>
            <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-100 shadow-sm">
              <div className="flex items-center gap-1.5 mb-1">
                <Target className="w-3 h-3 text-emerald-600" />
                <p className="text-xs text-emerald-700 font-semibold">Target</p>
              </div>
              <p className="text-2xl font-bold text-emerald-800 font-mono">{formatCurrency(stock.target_price)}</p>
              <p className="text-xs text-emerald-600 font-medium">+{targetGain.toFixed(1)}% upside</p>
            </div>
            <div className="bg-rose-50 p-4 rounded-xl border border-rose-100 shadow-sm">
              <div className="flex items-center gap-1.5 mb-1">
                <AlertTriangle className="w-3 h-3 text-rose-600" />
                <p className="text-xs text-rose-700 font-semibold">Stop Loss</p>
              </div>
              <p className="text-2xl font-bold text-rose-800 font-mono">{formatCurrency(stock.stop_loss_price)}</p>
              <p className="text-xs text-rose-600 font-medium">Risk Management</p>
            </div>
          </div>

          {/* Key Metrics */}
          {stock.key_metrics && (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Key Metrics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                {Object.entries(stock.key_metrics.metrics).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">{key}</div>
                    <div className="text-lg font-bold text-slate-800 font-mono">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Investment View */}
          {stock.investment_view && (
            <div className="space-y-4">
              <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-blue-900 mb-3">Market Outlook</h3>
                <p className="text-slate-700 leading-relaxed">
                  {stock.investment_view.market_outlook}
                </p>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-slate-900 mb-3">Stock Rationale</h3>
                <p className="text-slate-700 leading-relaxed">
                  {stock.investment_view.stock_rationale}
                </p>
              </div>

              <div className="bg-purple-50/50 border border-purple-100 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Clock className="w-5 h-5 text-purple-700" />
                  <h3 className="text-lg font-semibold text-purple-900">Holding Period</h3>
                </div>
                <p className="text-slate-700">{stock.investment_view.holding_period}</p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-rose-50/50 border border-rose-100 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className="w-5 h-5 text-rose-700" />
                    <h3 className="text-lg font-semibold text-rose-900">Exit Triggers</h3>
                  </div>
                  <ul className="space-y-2">
                    {stock.investment_view.exit_triggers.map((trigger, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                        <span className="text-rose-600 mt-1 font-bold">•</span>
                        <span>{trigger}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-amber-50/50 border border-amber-100 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-5 h-5 text-amber-700" />
                    <h3 className="text-lg font-semibold text-amber-900">Review Triggers</h3>
                  </div>
                  <ul className="space-y-2">
                    {stock.investment_view.review_triggers.map((trigger, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                        <span className="text-amber-600 mt-1 font-bold">•</span>
                        <span>{trigger}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Rationale */}
          {stock.rationale && (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-3">Investment Thesis</h3>
              <p className="text-slate-700 leading-relaxed">{stock.rationale}</p>
            </div>
          )}

          {/* News Sentiment */}
          {stock.news_sentiment && (
            <div className="bg-emerald-50/50 border border-emerald-100 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-emerald-900 mb-3">News Sentiment</h3>
              <p className="text-slate-700 leading-relaxed">{stock.news_sentiment}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
