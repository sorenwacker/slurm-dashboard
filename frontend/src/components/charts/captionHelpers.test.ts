import { describe, expect, it } from 'vitest';
import { dimensionLabel, stackedBy } from './captionHelpers';

describe('dimensionLabel', () => {
  it('maps dimensions to caption wording', () => {
    expect(dimensionLabel('Account')).toBe('account');
    expect(dimensionLabel('State')).toBe('job state');
    expect(dimensionLabel('QOS')).toBe('QoS');
    expect(dimensionLabel(null)).toBeNull();
    expect(dimensionLabel('')).toBeNull();
  });
});

describe('stackedBy', () => {
  it('appends the dimension only when one is active', () => {
    expect(stackedBy('Jobs submitted per period.', 'account')).toBe('Jobs submitted per period, stacked by account.');
    expect(stackedBy('Jobs submitted per period.', null)).toBe('Jobs submitted per period.');
  });
});
