'use client';

import type { StockDetail } from '@/types';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Target, AlertTriangle } from 'lucide-react';

interface StockCardProps {
  stock: StockDetail;
  onClick?: () => void;
}

export default function StockCard({ stock, onClick }: StockCardProps) {
  const targetGain = ((stock.target_price - stock.entry_price) / stock.entry_price) * 100;
  const stopLossDistance = ((stock.entry_price - stock.stop_loss_price) / stock.entry_price) * 100;

  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300',
        'border border-gray-200 hover:border-primary-400',
        'p-6 cursor-pointer hover:-translate-y-1',
        'animate-fade-in'
      )}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-900">{stock.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm font-medium text-gray-500">{stock.ticker}</span>
            {stock.sector && (
              <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded-full">
                {stock.sector}
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-500">Allocation</div>
          <div className="text-2xl font-bold text-gray-900">{stock.allocation_pct}%</div>
          <div className="text-sm text-gray-600">{formatCurrency(stock.allocation_amount)}</div>
        </div>
      </div>

      {/* Price Info */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">Entry Price</div>
          <div className="text-lg font-semibold text-gray-900">
            {formatCurrency(stock.entry_price)}
          </div>
        </div>
        <div className="bg-success-50 rounded-lg p-3">
          <div className="text-xs text-success-700 mb-1 flex items-center gap-1">
            <Target className="w-3 h-3" />
            Target
          </div>
          <div className="text-lg font-semibold text-success-700">
            {formatCurrency(stock.target_price)}
          </div>
          <div className="text-xs text-success-600">{formatPercent(targetGain)}</div>
        </div>
        <div className="bg-danger-50 rounded-lg p-3">
          <div className="text-xs text-danger-700 mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Stop Loss
          </div>
          <div className="text-lg font-semibold text-danger-700">
            {formatCurrency(stock.stop_loss_price)}
          </div>
          <div className="text-xs text-danger-600">{formatPercent(-stopLossDistance)}</div>
        </div>
      </div>

      {/* Key Metrics */}
      {stock.key_metrics && (
        <div className="grid grid-cols-3 gap-2 mb-4 text-sm">
          {stock.key_metrics.metrics['ROCE'] && (
            <div className="text-center">
              <div className="text-gray-500 text-xs">ROCE</div>
              <div className="font-semibold text-primary-700">
                {stock.key_metrics.metrics['ROCE']}
              </div>
            </div>
          )}
          {stock.key_metrics.metrics['ROE'] && (
            <div className="text-center">
              <div className="text-gray-500 text-xs">ROE</div>
              <div className="font-semibold text-primary-700">
                {stock.key_metrics.metrics['ROE']}
              </div>
            </div>
          )}
          {stock.key_metrics.metrics['D/E'] && (
            <div className="text-center">
              <div className="text-gray-500 text-xs">D/E</div>
              <div className="font-semibold text-gray-700">
                {stock.key_metrics.metrics['D/E']}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Rationale */}
      {stock.rationale && (
        <div className="border-t pt-3 mt-3">
          <div className="text-xs text-gray-500 mb-1">Investment Thesis</div>
          <p className="text-sm text-gray-700 line-clamp-2">{stock.rationale}</p>
        </div>
      )}

      {/* News Sentiment */}
      {stock.news_sentiment && (
        <div className="mt-3 pt-3 border-t">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-success-600" />
            <span className="text-xs text-gray-500">Sentiment:</span>
            <span className="text-xs text-gray-700 line-clamp-1">{stock.news_sentiment}</span>
          </div>
        </div>
      )}
    </div>
  );
}
