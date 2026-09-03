import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = join(__dirname, '..');

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const files = walk(SRC).filter((f) => /\.(css|tsx|ts)$/.test(f) && !f.endsWith('.test.ts'));
const declared = new Set<string>();
for (const file of files.filter((f) => f.endsWith('.css'))) {
  for (const match of readFileSync(file, 'utf8').matchAll(/--([\w-]+)\s*:/g)) declared.add(match[1]);
}

describe('CSS custom properties', () => {
  it('declares every var(--name) used in a stylesheet or component', () => {
    const missing: string[] = [];
    for (const file of files) {
      for (const match of readFileSync(file, 'utf8').matchAll(/var\(--([\w-]+)\)/g)) {
        if (!declared.has(match[1])) missing.push(`${relative(SRC, file)}: --${match[1]}`);
      }
    }
    expect([...new Set(missing)]).toEqual([]);
  });
});
