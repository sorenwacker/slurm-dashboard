import type { AggregatedChartsResponse } from '../../types';
import { SECTION_COLORS } from './chartHelpers';
import type { ResourceSectionConfig } from './sections/ResourceSection';

const NODE_CAPTION = (what: string, capacity: string) =>
  `${what} per node from jobs overlapping the range, split equally over a job's nodes. Normalized: percentage of the node's known ${capacity} over the range.`;

export const RESOURCE_SECTIONS: ResourceSectionConfig[] = [
  {
    title: 'CPU',
    color: SECTION_COLORS.cpu,
    unit: 'CPU Hours',
    overTimeKey: 'cpu_usage_over_time',
    byDimKey: 'cpu_hours_by_account',
    perJobKey: 'cpus_per_job',
    efficiencyKey: 'cpu_efficiency_over_time',
    gaugeKey: 'cpu',
    totalLabel: (data: AggregatedChartsResponse) => `${Math.round(data.summary.total_cpu_hours).toLocaleString()} hours`,
    overTimeCaption: 'CPU-hours (allocated CPUs times elapsed time) of jobs starting in the period.',
    byDimCaption: 'CPU-hours split by the colour dimension; without one, the distribution of CPU-hours per period.',
    perJobTitle: 'CPUs per Job',
    perJobXTitle: 'Number of CPUs',
    perJobCaption: 'Number of jobs per allocated CPU count.',
    nodeTitle: 'CPU Usage by Node',
    nodeCaption: NODE_CAPTION('CPU-hours', 'core count'),
    efficiencyTitle: 'CPU Efficiency',
    efficiencyCaption:
      'Consumed core-time (sacct TotalCPU) divided by allocated core-time, per period, over jobs reporting both. GPU efficiency is not available from SLURM accounting.',
    gaugeTitle: 'CPU allocation',
  },
  {
    title: 'GPU',
    color: SECTION_COLORS.gpu,
    unit: 'GPU Hours',
    overTimeKey: 'gpu_usage_over_time',
    byDimKey: 'gpu_hours_by_account',
    perJobKey: 'gpus_per_job',
    gaugeKey: 'gpu',
    totalLabel: (data: AggregatedChartsResponse) => `${Math.round(data.summary.total_gpu_hours).toLocaleString()} hours`,
    overTimeCaption: 'GPU-hours (allocated GPUs times elapsed time) of jobs starting in the period.',
    byDimCaption: 'GPU-hours split by the colour dimension; without one, the distribution of GPU-hours per period.',
    perJobTitle: 'GPUs per Job',
    perJobXTitle: 'Number of GPUs',
    perJobCaption: 'Number of jobs per allocated GPU count; jobs without GPUs are not shown.',
    nodeTitle: 'GPU Usage by Node',
    nodeCaption: NODE_CAPTION('GPU-hours', 'GPU count'),
    gaugeTitle: 'GPU allocation',
  },
  {
    title: 'Memory',
    color: SECTION_COLORS.memory,
    unit: 'GB-Hours',
    overTimeKey: 'memory_usage_over_time',
    byDimKey: 'memory_hours_by_account',
    perJobKey: 'memory_per_job',
    efficiencyKey: 'memory_efficiency_over_time',
    gaugeKey: 'memory',
    totalLabel: (data: AggregatedChartsResponse) => `${Math.round(data.summary.total_memory_gb_hours).toLocaleString()} GB-hours`,
    overTimeCaption:
      'Memory-hours (requested memory in GB times elapsed time) of jobs starting in the period; jobs without memory data are excluded.',
    byDimCaption: 'Memory-hours split by the colour dimension; without one, the distribution of memory-hours per period.',
    perJobTitle: 'Memory per Job',
    perJobXTitle: 'Requested Memory (GB)',
    perJobCaption: 'Number of jobs per requested memory size in GB (20 most common sizes).',
    nodeTitle: 'Memory Allocated by Node',
    nodeCaption: NODE_CAPTION('Requested memory-hours', 'memory'),
    efficiencyTitle: 'Memory Efficiency',
    efficiencyCaption:
      'Peak memory used over requested memory, weighted by job runtime, per period, over jobs reporting both. Peak-based, so an upper bound.',
    gaugeTitle: 'Memory allocation',
  },
];
