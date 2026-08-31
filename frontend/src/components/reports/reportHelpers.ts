/**
 * Helper functions for report generation
 */

/**
 * Align previous period dates with current period for overlay comparison
 */
export const alignPreviousPeriodDates = <T extends { date: string }>(
  currentTimeline: Array<{ date: string }>,
  previousTimeline: T[]
): T[] => {
  if (!currentTimeline.length || !previousTimeline.length) return previousTimeline;

  // Take up to the same number of data points as current period
  const alignedData = previousTimeline.slice(0, currentTimeline.length);

  // Map previous period data to current period dates
  return alignedData.map((prev, index) => ({
    ...prev,
    date: currentTimeline[index]?.date || prev.date,
  }));
};

/**
 * Format a number with thousand separators
 */
export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('en-US').format(num);
};

/**
 * Format hours with max 2 decimal places
 */
export const formatHours = (hours: number): string => {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(hours);
};

/**
 * Format numbers in compact notation (K, M)
 */
export const formatCompact = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  // For numbers < 1000, display as integer (no decimal places)
  return Math.round(num).toString();
};

/**
 * Get period label based on report type
 */
export const getPeriodLabel = (reportType: 'monthly' | 'quarterly' | 'annual'): string => {
  switch (reportType) {
    case 'monthly':
      return 'month';
    case 'quarterly':
      return 'quarter';
    case 'annual':
      return 'year';
    default:
      return 'period';
  }
};
