import { describe, expect, it } from 'vitest';
import { filterNodeRows, nodeSource, partitionsOf, toNodeRows } from './nodeRows';

const nodes = {
  gpu10: {
    type: 'gpu',
    synonyms: ['GPU10'],
    hardware: { cpu: { cores: 48 }, ram: { total_gb: 500 }, gpus: [{ model: 'a40', count: 3 }] },
    partitions: ['gpu', 'general'],
  },
  gpu2: { type: 'gpu', hardware: { cpu: { cores: 64 }, gpus: [{ model: 'a40', count: 2 }, { model: 'v100', count: 1 }] } },
  old01: { type: 'cpu', description: 'decommissioned in 2024' },
};

describe('nodeSource', () => {
  it('is slurm when hardware was synced and data otherwise', () => {
    expect(nodeSource(nodes.gpu10)).toBe('slurm');
    expect(nodeSource(nodes.old01)).toBe('data');
  });
});

describe('toNodeRows', () => {
  it('sorts naturally and summarises hardware', () => {
    const rows = toNodeRows(nodes);
    expect(rows.map((r) => r.name)).toEqual(['gpu2', 'gpu10', 'old01']);
    expect(rows[1]).toMatchObject({ cpus: 48, memoryGb: 500, gpus: '3x a40', gpuCount: 3, source: 'slurm' });
    expect(rows[0].gpus).toBe('2x a40, 1x v100');
    expect(rows[0].gpuCount).toBe(3);
    expect(rows[2]).toMatchObject({ cpus: 0, memoryGb: 0, gpus: '', source: 'data' });
  });
});

describe('filterNodeRows', () => {
  const rows = toNodeRows(nodes);
  const all = { search: '', type: 'all', partition: 'all', dataOnly: false };

  it('matches name, synonyms and description', () => {
    expect(filterNodeRows(rows, { ...all, search: 'GPU10' }).map((r) => r.name)).toEqual(['gpu10']);
    expect(filterNodeRows(rows, { ...all, search: 'decommissioned' }).map((r) => r.name)).toEqual(['old01']);
  });

  it('filters by type, partition and source', () => {
    expect(filterNodeRows(rows, { ...all, type: 'cpu' }).map((r) => r.name)).toEqual(['old01']);
    expect(filterNodeRows(rows, { ...all, partition: 'general' }).map((r) => r.name)).toEqual(['gpu10']);
    expect(filterNodeRows(rows, { ...all, dataOnly: true }).map((r) => r.name)).toEqual(['old01']);
  });

  it('lists the partitions seen on nodes', () => {
    expect(partitionsOf(rows)).toEqual(['general', 'gpu']);
  });
});
