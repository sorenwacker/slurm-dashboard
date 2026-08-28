import { describe, expect, it } from 'vitest';
import { maskKey } from './CredentialsPanel';

describe('maskKey', () => {
  it('shows only the last four characters', () => {
    expect(maskKey('abcdefghij')).toBe('******ghij');
    expect(maskKey('JjIrA-BaL6I6spmpoDNxvsmdS_E4P6_KJlmaDnCpdkM')).toMatch(/^\*{24}pdkM$/);
  });

  it('never reveals short keys', () => {
    expect(maskKey('abc')).toBe('****');
  });
});
