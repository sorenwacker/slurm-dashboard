export interface DateRange {
  min_date: string;
  max_date: string;
}

const DEFAULT_WINDOW_DAYS = 42; // 6 weeks

function shiftDays(isoDate: string, days: number): string {
  const date = new Date(isoDate);
  date.setDate(date.getDate() + days);
  return date.toISOString().split('T')[0];
}

/** Keep a date inside the cluster's data range; empty bounds are ignored. */
export function clampDate(date: string, range: DateRange | null | undefined): string {
  if (!date || !range) return date;
  if (range.min_date && date < range.min_date) return range.min_date;
  if (range.max_date && date > range.max_date) return range.max_date;
  return date;
}

/** Initial selection: the last six weeks of data, never earlier than the first data point. */
export function defaultDateRange(range: DateRange | null | undefined): { start: string; end: string } | null {
  if (!range || !range.max_date) return null;
  const end = range.max_date;
  return { start: clampDate(shiftDays(end, -DEFAULT_WINDOW_DAYS), range), end };
}
