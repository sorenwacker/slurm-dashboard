import { describe, expect, it } from 'vitest';
import { nodeCapacity, processNodeChart } from './nodeChart';

const chart = {
  x: ['n1', 'n2', 'idle', 'unknown'],
  y: [48, 24, 0, 10],
  total_hours: 10,
  hardware_config: {
    n1: { cpu_cores: 8, gpu_count: 2, memory_gb: 64, known: true },
    n2: { cpu_cores: 8, gpu_count: 0, memory_gb: 0, known: true },
    idle: { cpu_cores: 4, gpu_count: 0, memory_gb: 32, known: true },
    unknown: { cpu_cores: 64, gpu_count: 0, memory_gb: 0, known: false },
  },
};
const raw = { hideUnused: false, sortByUsage: false, normalize: false };

describe('nodeCapacity', () => {
  it('returns null for defaults and zero capacities', () => {
    expect(nodeCapacity(chart.hardware_config.n1, 'cpu')).toBe(8);
    expect(nodeCapacity(chart.hardware_config.n2, 'gpu')).toBeNull();
    expect(nodeCapacity(chart.hardware_config.n2, 'memory')).toBeNull();
    expect(nodeCapacity(chart.hardware_config.unknown, 'cpu')).toBeNull();
    expect(nodeCapacity(undefined, 'cpu')).toBeNull();
  });
});

describe('processNodeChart', () => {
  it('keeps raw hours when not normalizing', () => {
    const result = processNodeChart(chart, 'cpu', raw);
    expect(result.x).toEqual(['n1', 'n2', 'idle', 'unknown']);
    expect(result.y).toEqual([48, 24, 0, 10]);
    expect(result.normalized).toBe(false);
    expect(result.unknownCapacity).toEqual([]);
  });

  it('hides unused nodes and sorts by usage', () => {
    const result = processNodeChart(chart, 'cpu', { hideUnused: true, sortByUsage: true, normalize: false });
    expect(result.x).toEqual(['n1', 'n2', 'unknown']);
  });

  it('normalizes against known capacity and drops unknown nodes', () => {
    const result = processNodeChart(chart, 'cpu', { ...raw, normalize: true });
    expect(result.x).toEqual(['n1', 'n2', 'idle']);
    expect(result.y).toEqual([60, 30, 0]);
    expect(result.unknownCapacity).toEqual(['unknown']);
    expect(result.normalized).toBe(true);
  });

  it('normalizes stacked series and caps at 100', () => {
    const stacked = { ...chart, y: undefined, series: [{ name: 'a', data: [60, 24, 0, 10] }, { name: 'b', data: [60, 0, 0, 0] }] };
    const result = processNodeChart(stacked, 'cpu', { ...raw, normalize: true });
    expect(result.series?.map((s) => s.data)).toEqual([[75, 30, 0], [75, 0, 0]]);
  });

  it('does not normalize without a window length', () => {
    const result = processNodeChart({ ...chart, total_hours: 0 }, 'cpu', { ...raw, normalize: true });
    expect(result.normalized).toBe(false);
    expect(result.y).toEqual([48, 24, 0, 10]);
  });
});
