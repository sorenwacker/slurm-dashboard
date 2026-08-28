import { describe, expect, it } from 'vitest';
import { clampDate, defaultDateRange } from './dateRange';

const range = { min_date: '2026-08-20', max_date: '2026-08-28' };

describe('clampDate', () => {
  it('moves a date before the first data point to the first data point', () => {
    expect(clampDate('2026-03-01', range)).toBe('2026-08-20');
  });

  it('moves a date after the last data point to the last data point', () => {
    expect(clampDate('2026-12-31', range)).toBe('2026-08-28');
  });

  it('keeps dates inside the range and empty inputs as they are', () => {
    expect(clampDate('2026-08-25', range)).toBe('2026-08-25');
    expect(clampDate('', range)).toBe('');
    expect(clampDate('2026-03-01', null)).toBe('2026-03-01');
    expect(clampDate('2026-03-01', { min_date: '', max_date: '' })).toBe('2026-03-01');
  });
});

describe('defaultDateRange', () => {
  it('uses six weeks before the last data point when enough data exists', () => {
    expect(defaultDateRange({ min_date: '2025-01-01', max_date: '2026-08-28' })).toEqual({
      start: '2026-07-17',
      end: '2026-08-28',
    });
  });

  it('starts at the first data point when the cluster has less than six weeks of data', () => {
    expect(defaultDateRange(range)).toEqual({ start: '2026-08-20', end: '2026-08-28' });
  });

  it('returns null without a last data point', () => {
    expect(defaultDateRange({ min_date: '', max_date: '' })).toBeNull();
    expect(defaultDateRange(undefined)).toBeNull();
  });
});
