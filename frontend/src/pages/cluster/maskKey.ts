/** Keys are hidden by default; only the last four characters identify which key is installed. */
export function maskKey(key: string): string {
  return key.length <= 4 ? '****' : `${'*'.repeat(Math.min(key.length - 4, 24))}${key.slice(-4)}`;
}
