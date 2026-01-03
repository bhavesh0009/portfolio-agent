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
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-primary-600 to-primary-700 text-white p-6 rounded-t-2xl">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-3xl font-bold mb-2">{stock.name}</h2>
              <div className="flex items-center gap-3">
                <span className="text-primary-100">{stock.ticker}</span>
                {stock.sector && (
                  <span className="px-3 py-1 bg-white/20 rounded-full text-sm">
                    {stock.sector}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Price Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-xl p-4">
              <div className="text-sm text-gray-500 mb-1">Entry Price</div>
              <div className="text-2xl font-bold text-gray-900">
                {formatCurrency(stock.entry_price)}
              </div>
            </div>
            <div className="bg-primary-50 rounded-xl p-4">
              <div className="text-sm text-primary-700 mb-1">Allocation</div>
              <div className="text-2xl font-bold text-primary-700">{stock.allocation_pct}%</div>
              <div className="text-sm text-primary-600">
                {formatCurrency(stock.allocation_amount)}
              </div>
            </div>
            <div className="bg-success-50 rounded-xl p-4">
              <div className="text-sm text-success-700 mb-1 flex items-center gap-1">
                <Target className="w-4 h-4" />
                Target
              </div>
              <div className="text-2xl font-bold text-success-700">
                {formatCurrency(stock.target_price)}
              </div>
              <div className="text-sm text-success-600">{formatPercent(targetGain)}</div>
            </div>
            <div className="bg-danger-50 rounded-xl p-4">
              <div className="text-sm text-danger-700 mb-1 flex items-center gap-1">
                <AlertTriangle className="w-4 h-4" />
                Stop Loss
              </div>
              <div className="text-2xl font-bold text-danger-700">
                {formatCurrency(stock.stop_loss_price)}
              </div>
              <div className="text-sm text-danger-600">{formatPercent(-stopLossDistance)}</div>
            </div>
          </div>

          {/* Key Metrics */}
          {stock.key_metrics && (
            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Metrics</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(stock.key_metrics.metrics).map(([key, value]) => (
                  <div key={key} className="bg-white rounded-lg p-3">
                    <div className="text-sm text-gray-500">{key}</div>
                    <div className="text-lg font-semibold text-gray-900">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Investment View */}
          {stock.investment_view && (
            <div className="space-y-4">
              <div className="bg-primary-50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-primary-900 mb-3">Market Outlook</h3>
                <p className="text-gray-700 leading-relaxed">
                  {stock.investment_view.market_outlook}
                </p>
              </div>

              <div className="bg-blue-50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-blue-900 mb-3">Stock Rationale</h3>
                <p className="text-gray-700 leading-relaxed">
                  {stock.investment_view.stock_rationale}
                </p>
              </div>

              <div className="bg-purple-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Clock className="w-5 h-5 text-purple-700" />
                  <h3 className="text-lg font-semibold text-purple-900">Holding Period</h3>
                </div>
                <p className="text-gray-700">{stock.investment_view.holding_period}</p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-danger-50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className="w-5 h-5 text-danger-700" />
                    <h3 className="text-lg font-semibold text-danger-900">Exit Triggers</h3>
                  </div>
                  <ul className="space-y-2">
                    {stock.investment_view.exit_triggers.map((trigger, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                        <span className="text-danger-600 mt-1">•</span>
                        <span>{trigger}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-yellow-50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-5 h-5 text-yellow-700" />
                    <h3 className="text-lg font-semibold text-yellow-900">Review Triggers</h3>
                  </div>
                  <ul className="space-y-2">
                    {stock.investment_view.review_triggers.map((trigger, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                        <span className="text-yellow-600 mt-1">•</span>
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
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Investment Thesis</h3>
              <p className="text-gray-700 leading-relaxed">{stock.rationale}</p>
            </div>
          )}

          {/* News Sentiment */}
          {stock.news_sentiment && (
            <div className="bg-success-50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-success-900 mb-3">News Sentiment</h3>
              <p className="text-gray-700 leading-relaxed">{stock.news_sentiment}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
