export interface JobRecord {
  JobID: string;
  User: string;
  Account: string;
  Partition: string;
  State: string;
  QOS?: string;
  Submit: string;
  Start?: string;
  End?: string;
  CPUHours: number;
  GPUHours: number;
  AllocCPUS: number;
  AllocGPUS: number;
  AllocNodes: number;
  NodeList?: string;
  SubmitYearMonth?: string;
  SubmitYearWeek?: string;
  SubmitYear?: number;
}

export interface FilterRequest {
  hostname: string;
  start_date?: string;
  end_date?: string;
  partitions?: string[];
  accounts?: string[];
  users?: string[];
  qos?: string[];
  states?: string[];
  complete_periods_only?: boolean;
  period_type?: string;
  color_by?: string;
  account_segments?: number;
  normalize_node_usage?: boolean;  // Normalize node CPU/GPU usage to 100% capacity
  // Note: hide_unused_nodes and sort_by_usage removed - handled client-side
}

export interface FilterResponse {
  total_jobs: number;
  total_cpu_hours: number;
  total_gpu_hours: number;
  total_users: number;
  data: JobRecord[];
}

export interface MetadataResponse {
  hostnames: string[];
  partitions: Record<string, string[]>;
  accounts: Record<string, string[]>;
  users: Record<string, string[]>;
  qos: Record<string, string[]>;
  states: Record<string, string[]>;
  date_ranges: Record<string, { min_date: string; max_date: string }>;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  data_loaded: boolean;
  hostnames: string[];
}

export interface ClusterStats {
  hostname: string;
  total_jobs: number;
  total_cpu_hours: number;
  total_gpu_hours: number;
  total_users: number;
  partitions: string[];
}

export interface SeriesData {
  name: string;
  data: number[];
}

export interface NodeHardwareConfig {
  cpu_cores?: number;
  gpu_count?: number;
  memory_gb?: number;  // 0 or absent when the node's memory is not configured
  known?: boolean;     // false when the values are type defaults, not synced or configured hardware
}

export interface ClusterUtilization {
  cpu: number | null;
  gpu: number | null;
  memory: number | null;
  memory_coverage: number;  // share of jobs with known requested memory
}

export interface ChartData {
  x: (string | number)[];
  y?: (string | number)[];  // Optional for backward compatibility
  series?: SeriesData[];    // For multi-series stacked charts
  mean?: number;            // For histogram mode (when no color_by filter)
  median?: number;          // For histogram mode (when no color_by filter)
  average?: number;         // Alternative to mean (some charts use this)
  type?: string;            // Chart type indicator (e.g., 'histogram', 'pie', 'bar')
  bin_labels?: string[];    // For histogram hover text
  labels?: string[];        // For pie charts
  values?: number[];        // For pie charts
  total_periods?: number;   // For user activity frequency chart
  total_users?: number;     // For user activity frequency chart
  period_label?: string;    // For user activity frequency chart (e.g., 'days', 'weeks')
  normalized?: boolean;     // For node usage charts (indicates values are %)
  hardware_config?: Record<string, NodeHardwareConfig>;  // Per-node hardware specs for hover info
  total_hours?: number;     // Total hours in time range (for client-side normalization)
}

export interface TrendData {
  x: (string | number)[];
  series?: SeriesData[];  // Optional for grouped trend data
  stats: {
    mean: number[];
    median: number[];
    max: number[];
    p25: number[];
    p50: number[];
    p75: number[];
    p90: number[];
    p95: number[];
    p99: number[];
  };
}

export interface PieChartData {
  labels: string[];
  values: number[];
}

export interface AggregatedChartsResponse {
  summary: {
    total_jobs: number;
    total_cpu_hours: number;
    total_gpu_hours: number;
    total_memory_gb_hours: number;
    total_users: number;
  };
  cpu_usage_over_time: ChartData;
  gpu_usage_over_time: ChartData;
  active_users_over_time: ChartData;
  active_users_distribution: ChartData;
  jobs_over_time: ChartData;
  jobs_distribution: ChartData;
  jobs_by_account: ChartData;
  jobs_by_partition: ChartData;
  jobs_by_state: PieChartData;
  waiting_times_hist: ChartData;
  waiting_times_stacked: ChartData;
  job_duration_hist: ChartData;
  job_duration_stacked: ChartData;
  waiting_times_over_time: ChartData;
  job_duration_over_time: ChartData;
  waiting_times_trends: TrendData;
  job_duration_trends: TrendData;
  cpus_per_job: ChartData;
  gpus_per_job: ChartData;
  nodes_per_job: ChartData;
  cpu_hours_by_account: ChartData;
  gpu_hours_by_account: ChartData;
  node_cpu_usage: ChartData;
  node_gpu_usage: ChartData;
  memory_usage_over_time: ChartData;
  memory_hours_by_account: ChartData;
  memory_efficiency_over_time: ChartData;
  memory_per_job: ChartData;
  node_memory_usage: ChartData;
  cluster_utilization: ClusterUtilization;
  user_activity_frequency: ChartData;
}
