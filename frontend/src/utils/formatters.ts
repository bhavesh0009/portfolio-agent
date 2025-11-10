/**
 * Formatting utilities for financial data display
 * Follows Quin-style professional formatting with consistent typography
 */

/**
 * Format currency in Indian rupee format
 * Examples: ₹14,42,912.15, ₹1,850.28, -₹500.00
 */
export function formatCurrency(value: number, showSign: boolean = false): string {
  const isNegative = value < 0;
  const absValue = Math.abs(value);

  // Format with Indian numbering system (lakhs, crores)
  const formatted = absValue.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const sign = isNegative ? '-' : (showSign && value > 0 ? '+' : '');
  return `${sign}₹${formatted}`;
}

/**
 * Format currency in compact format (for large numbers)
 * Examples: ₹14.4L, ₹1.2Cr, ₹850
 */
export function formatCompactCurrency(value: number, showSign: boolean = false): string {
  const isNegative = value < 0;
  const absValue = Math.abs(value);

  let formatted: string;

  if (absValue >= 10000000) {
    // Crores (10 million+)
    formatted = `₹${(absValue / 10000000).toFixed(2)}Cr`;
  } else if (absValue >= 100000) {
    // Lakhs (100 thousand+)
    formatted = `₹${(absValue / 100000).toFixed(2)}L`;
  } else {
    // Thousands and below
    formatted = `₹${absValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  }

  const sign = isNegative ? '-' : (showSign && value > 0 ? '+' : '');
  return `${sign}${formatted}`;
}

/**
 * Format percentage with sign
 * Examples: +12.45%, -3.21%, 0.00%
 */
export function formatPercent(value: number, decimals: number = 2): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format percentage without sign (for neutral contexts)
 * Examples: 12.45%, 3.21%, 0.00%
 */
export function formatPercentNeutral(value: number, decimals: number = 2): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Format large numbers in compact notation
 * Examples: 14.4M, 1.2B, 850K
 */
export function formatCompactNumber(value: number): string {
  const absValue = Math.abs(value);
  const isNegative = value < 0;

  let formatted: string;

  if (absValue >= 1000000000) {
    formatted = `${(absValue / 1000000000).toFixed(2)}B`;
  } else if (absValue >= 1000000) {
    formatted = `${(absValue / 1000000).toFixed(2)}M`;
  } else if (absValue >= 1000) {
    formatted = `${(absValue / 1000).toFixed(2)}K`;
  } else {
    formatted = absValue.toFixed(2);
  }

  return isNegative ? `-${formatted}` : formatted;
}

/**
 * Get Tailwind color class for numeric values
 * Positive: green, Negative: red, Zero: gray
 */
export function getNumberColorClass(value: number): string {
  if (value > 0) return 'text-success-600';
  if (value < 0) return 'text-danger-600';
  return 'text-gray-600';
}

/**
 * Get Tailwind background color class for numeric values
 * Positive: light green, Negative: light red, Zero: gray
 */
export function getNumberBgColorClass(value: number): string {
  if (value > 0) return 'bg-success-50';
  if (value < 0) return 'bg-danger-50';
  return 'bg-gray-50';
}

/**
 * Format date to readable string
 * Examples: "Jan 15, 2025", "Nov 9, 2025"
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format date to compact string
 * Examples: "15 Jan", "9 Nov"
 */
export function formatDateCompact(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format time to readable string
 * Examples: "2:30 PM", "9:15 AM"
 */
export function formatTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Format date and time
 * Examples: "Jan 15, 2025 at 2:30 PM"
 */
export function formatDateTime(dateString: string): string {
  return `${formatDate(dateString)} at ${formatTime(dateString)}`;
}

/**
 * Get relative time string
 * Examples: "2 hours ago", "1 day ago", "Just now"
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;

  return formatDate(dateString);
}

/**
 * Format number with Indian lakh/crore system
 * Examples: "14,42,912", "1,50,000"
 */
export function formatIndianNumber(value: number): string {
  return value.toLocaleString('en-IN');
}

/**
 * Safely parse number from string or return default
 */
export function parseNumber(value: string | number | null | undefined, defaultValue: number = 0): number {
  if (value === null || value === undefined) return defaultValue;
  if (typeof value === 'number') return value;
  const parsed = parseFloat(value);
  return isNaN(parsed) ? defaultValue : parsed;
}
