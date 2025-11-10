// Portfolio Types
export interface Portfolio {
  id: number;
  profile: 'aggressive' | 'defensive';
  total_capital: number;
  created_at: string;
  timestamp: string;
  json_path: string | null;
  notes: string | null;
  is_active: boolean;
}

// Stock Types
export interface Stock {
  id: number;
  portfolio_id: number;
  name: string;
  ticker: string;
  sector: string | null;
  entry_price: number;
  allocation_pct: number;
  allocation_amount: number;
  stop_loss_pct: number;
  stop_loss_price: number;
  target_pct: number;
  target_price: number;
  rationale: string | null;
  news_sentiment: string | null;
  added_at: string;
}

// Investment View Types
export interface InvestmentView {
  id: number;
  stock_id: number;
  market_outlook: string;
  stock_rationale: string;
  holding_period: string;
  exit_triggers: string[];
  review_triggers: string[];
  created_at: string;
}

// Key Metrics Types
export interface KeyMetrics {
  id: number;
  stock_id: number;
  metrics: {
    'Market Capitalization'?: string;
    'Sales growth 3Years'?: string;
    'Profit growth 3Years'?: string;
    'ROCE'?: string;
    'ROE'?: string;
    'D/E'?: string;
    [key: string]: string | undefined;
  };
  created_at: string;
}

// Combined Stock with all details
export interface StockDetail extends Stock {
  investment_view?: InvestmentView;
  key_metrics?: KeyMetrics;
}

// Portfolio with stocks
export interface PortfolioDetail extends Portfolio {
  stocks: StockDetail[];
}

// Performance metrics (for future use)
export interface PerformanceMetric {
  id: number;
  portfolio_id: number;
  stock_id: number | null;
  metric_date: string;
  portfolio_value: number | null;
  stock_value: number | null;
  daily_return_pct: number | null;
  cumulative_return_pct: number | null;
  status: string | null;
  created_at: string;
}

// Portfolio Performance (from /api/performance endpoint)
export interface PortfolioPerformance {
  portfolio_id: number;
  current_value: number;
  initial_capital: number;
  pnl_absolute: number;
  pnl_pct: number;
  num_stocks: number;
  calculated_at: string;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  day_return_pct: number;
  day_return_absolute: number;
  stock_details: StockPerformance[];
}

// Individual stock performance
export interface StockPerformance {
  stock_id: number;
  ticker: string;
  name: string;
  entry_price: number;
  current_price: number;
  shares: number;
  initial_value: number;
  current_value: number;
  pnl_absolute: number;
  pnl_pct: number;
  allocation_pct: number;
}

// Benchmark Comparison (from /api/benchmarks endpoint)
export interface BenchmarkComparison {
  portfolio_id: number;
  period: '1M' | '3M' | '6M' | '1Y' | 'ALL';
  portfolio_return: number;
  benchmarks: BenchmarkData[];
  fetched_at: string;
}

export interface BenchmarkData {
  index_symbol: string;
  index_name: string;
  index_return: number;
  alpha: number;
  outperformance: number;
}

// Manager Updates (from /api/manager-updates endpoint)
export interface ManagerUpdate {
  id: number;
  portfolio_id: number;
  update_date: string;
  update_type: 'DAILY_REVIEW' | 'SIGNAL_GENERATED' | 'DECISION_MADE';
  title: string;
  description: string;
  affected_stocks: string[] | null;
  recommendation: 'HOLD' | 'BUY_MORE' | 'SELL' | 'REBALANCE' | null;
  reasoning: string | null;
  confidence_score: number | null;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'PENDING' | 'EXECUTED' | 'IGNORED';
  created_at: string;
  executed_at: string | null;
}

export interface ManagerUpdatesResponse {
  portfolio_id: number;
  total_updates: number;
  updates: ManagerUpdate[];
  updates_by_date: Record<string, ManagerUpdate[]>;
  fetched_at: string;
}

// Risk Metrics (from /api/risk-metrics endpoint)
export interface RiskMetrics {
  portfolio_id: number;
  period_days: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  annualized_return: number;
  total_return_pct: number;
  calculated_at: string;
}

// Price History (from /api/price-history endpoint)
export interface PriceHistoryPoint {
  id: number;
  stock_id: number;
  price_date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number | null;
  created_at: string;
}

export interface PriceHistoryResponse {
  stock_id: number;
  prices: PriceHistoryPoint[];
  count: number;
  fetched_at: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
