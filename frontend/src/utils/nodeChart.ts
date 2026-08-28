import type { ChartData, NodeHardwareConfig } from '../types';

export type ResourceType = 'cpu' | 'gpu' | 'memory';

export interface NodeChartOptions {
  hideUnused: boolean;
  sortByUsage: boolean;
  normalize: boolean;
}

export interface ProcessedNodeChart extends ChartData {
  /** Nodes left out of the normalized chart because their capacity is not known. */
  unknownCapacity: string[];
}

/** Capacity of one node for a resource; null when unknown or zero. See docs/user-guide/utilization.md. */
export function nodeCapacity(hw: NodeHardwareConfig | undefined, resource: ResourceType): number | null {
  if (!hw || !hw.known) return null;
  const value = resource === 'cpu' ? hw.cpu_cores : resource === 'gpu' ? hw.gpu_count : hw.memory_gb;
  return value && value > 0 ? value : null;
}

function rowTotal(chart: ChartData, index: number): number {
  if (chart.series) return chart.series.reduce((sum, s) => sum + (s.data[index] || 0), 0);
  return chart.y ? Number(chart.y[index]) || 0 : 0;
}

/** Filter, sort and optionally normalize a per-node chart returned by the API. */
export function processNodeChart(chart: ChartData, resource: ResourceType, options: NodeChartOptions): ProcessedNodeChart {
  const totalHours = chart.total_hours || 0;
  const canNormalize = options.normalize && totalHours > 0;
  const capacityOf = (index: number): number | null =>
    canNormalize ? nodeCapacity(chart.hardware_config?.[String(chart.x[index])], resource) : null;
  const scale = (index: number, value: number): number => {
    const capacity = capacityOf(index);
    return capacity === null ? value : Math.min(100, (value / (capacity * totalHours)) * 100);
  };

  let indices = chart.x.map((_, i) => i);
  if (options.hideUnused) indices = indices.filter((i) => rowTotal(chart, i) > 0);

  const unknownCapacity: string[] = [];
  if (canNormalize) {
    indices = indices.filter((i) => {
      if (capacityOf(i) !== null) return true;
      unknownCapacity.push(String(chart.x[i]));
      return false;
    });
  }

  if (options.sortByUsage) indices.sort((a, b) => scale(b, rowTotal(chart, b)) - scale(a, rowTotal(chart, a)));

  const x = indices.map((i) => chart.x[i]);
  return {
    ...chart,
    x,
    y: chart.y ? indices.map((i) => scale(i, Number(chart.y![i]) || 0)) : undefined,
    series: chart.series?.map((s) => ({ ...s, data: indices.map((i) => scale(i, s.data[i] || 0)) })),
    normalized: canNormalize,
    hardware_config: chart.hardware_config
      ? Object.fromEntries(x.map((node) => [node, chart.hardware_config![String(node)]]).filter(([, hw]) => hw !== undefined))
      : undefined,
    unknownCapacity,
  };
}
