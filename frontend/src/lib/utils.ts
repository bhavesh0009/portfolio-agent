/**
 * Format a number as currency in INR
 * @param value - The number to format
 * @returns Formatted currency string
 */
export function formatCurrency(value: number | undefined | null): string {
  if (value === undefined || value === null) return '—';

  // For large numbers, show in lakhs/crores
  if (value >= 10000000) { // 1 crore = 10 million
    return `₹${(value / 10000000).toFixed(2)}Cr`;
  } else if (value >= 100000) { // 1 lakh = 100k
    return `₹${(value / 100000).toFixed(2)}L`;
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a number as percentage
 * @param value - The number to format (should be in decimal form, e.g., 0.15 for 15%)
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted percentage string
 */
export function formatPercent(value: number | undefined | null, decimals: number = 2): string {
  if (value === undefined || value === null) return '—';

  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format a number with commas for better readability
 * @param value - The number to format
 * @returns Formatted number string
 */
export function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return '—';

  return new Intl.NumberFormat('en-IN').format(value);
}

/**
 * Get color class based on value (for P&L display)
 * @param value - The value to check
 * @returns Tailwind color class
 */
export function getColorClass(value: number | undefined | null): string {
  if (value === undefined || value === null) return 'text-slate-400';
  if (value > 0) return 'text-emerald-500';
  if (value < 0) return 'text-rose-500';
  return 'text-slate-400';
}

/**
 * Combine class names
 * @param classes - Class names to combine
 * @returns Combined class string
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
