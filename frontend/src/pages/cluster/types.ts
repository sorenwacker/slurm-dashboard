export interface GpuSpec {
  model?: string;
  count?: number;
  memory_gb?: number;
  nvlink?: boolean;
}

export interface NodeHardware {
  cpu?: { model?: string; cores?: number; sockets?: number; cores_per_socket?: number; threads_per_core?: number; threads?: number };
  ram?: { total_gb?: number; type?: string };
  gpus?: GpuSpec[];
}

export interface NodeEntry {
  synonyms?: string[];
  type?: string;
  description?: string;
  hardware?: NodeHardware;
  partitions?: string[];
  features?: string[];
}

export interface PartitionEntry {
  display_name?: string;
  description?: string;
  slurm?: { nodes?: string; total_cpus?: number; total_nodes?: number; max_time?: string; default?: boolean; state?: string };
}

export interface AccountEntry {
  display_name?: string;
  short_name?: string;
  faculty?: string;
  department?: string;
  slurm?: { description?: string; organization?: string };
}

export interface ClusterEntry {
  display_name?: string;
  description?: string;
  metadata?: Record<string, string | undefined>;
  node_labels?: Record<string, NodeEntry>;
  partition_labels?: Record<string, PartitionEntry>;
  account_labels?: Record<string, AccountEntry>;
}

export interface ClusterIdentity {
  display_name?: string | null;
  description?: string | null;
  location?: string | null;
  owner?: string | null;
  contact?: string | null;
  url?: string | null;
}

export interface ClusterStatus {
  name: string;
  id: string | null;
  config_present: boolean;
  identity: ClusterIdentity;
  sync: {
    last_sync: string | null;
    slurm_version: string | null;
    slurm_cluster_name: string | null;
    nodes_synced: number;
    nodes_from_data_only: number;
    partitions: number;
    accounts: number;
  };
  data: {
    min_date: string | null;
    max_date: string | null;
    last_submission: string | null;
    total_jobs_submitted: number;
  };
}

export type NodeSource = 'slurm' | 'data';
