import { useMemo } from 'react';
import type { AggregatedChartsResponse, ClusterUtilization } from '../types';
import { processNodeChart, type ProcessedNodeChart } from '../utils/nodeChart';

export interface ProcessedNodeData {
  cpu: ProcessedNodeChart | null;
  gpu: ProcessedNodeChart | null;
  memory: ProcessedNodeChart | null;
}

export function useProcessedNodeData(
  data: AggregatedChartsResponse | undefined,
  hideUnusedNodes: boolean,
  sortByUsage: boolean,
  normalizeNodeUsage: boolean
): ProcessedNodeData {
  return useMemo(() => {
    if (!data) return { cpu: null, gpu: null, memory: null };
    const options = { hideUnused: hideUnusedNodes, sortByUsage, normalize: normalizeNodeUsage };
    return {
      cpu: data.node_cpu_usage ? processNodeChart(data.node_cpu_usage, 'cpu', options) : null,
      gpu: data.node_gpu_usage ? processNodeChart(data.node_gpu_usage, 'gpu', options) : null,
      memory: data.node_memory_usage ? processNodeChart(data.node_memory_usage, 'memory', options) : null,
    };
  }, [data, hideUnusedNodes, sortByUsage, normalizeNodeUsage]);
}

const NO_UTILIZATION: ClusterUtilization = { cpu: null, gpu: null, memory: null, memory_coverage: 0 };

/** Below this share of jobs with memory data the memory gauge is shown with a warning. */
export const MEMORY_COVERAGE_THRESHOLD = 0.9;

/** Capacity-weighted utilization over all configured nodes, computed by the server; shown only when normalizing. */
export function useClusterUtilization(
  data: AggregatedChartsResponse | undefined,
  normalizeNodeUsage: boolean
): ClusterUtilization {
  return useMemo(() => {
    if (!data || !normalizeNodeUsage || !data.cluster_utilization) return NO_UTILIZATION;
    return data.cluster_utilization;
  }, [data, normalizeNodeUsage]);
}
