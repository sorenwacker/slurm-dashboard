import type { NodeEntry, NodeSource } from './types';

export interface NodeRow {
  name: string;
  entry: NodeEntry;
  source: NodeSource;
  cpus: number;
  memoryGb: number;
  gpus: string;
  gpuCount: number;
}

export interface NodeFilter {
  search: string;
  type: string;
  partition: string;
  dataOnly: boolean;
}

/** A node counts as SLURM-sourced when the agent sync wrote hardware for it. */
export function nodeSource(entry: NodeEntry): NodeSource {
  return entry.hardware?.cpu?.cores ? 'slurm' : 'data';
}

export function describeGpus(entry: NodeEntry): string {
  const gpus = entry.hardware?.gpus ?? [];
  return gpus.map((g) => `${g.count ?? '?'}x ${g.model ?? 'gpu'}`).join(', ');
}

export function toNodeRows(nodes: Record<string, NodeEntry>): NodeRow[] {
  return Object.entries(nodes)
    .map(([name, entry]) => ({
      name,
      entry,
      source: nodeSource(entry),
      cpus: entry.hardware?.cpu?.cores ?? 0,
      memoryGb: entry.hardware?.ram?.total_gb ?? 0,
      gpus: describeGpus(entry),
      gpuCount: (entry.hardware?.gpus ?? []).reduce((sum, g) => sum + (g.count ?? 0), 0),
    }))
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
}

export function filterNodeRows(rows: NodeRow[], filter: NodeFilter): NodeRow[] {
  const search = filter.search.trim().toLowerCase();
  return rows.filter((row) => {
    if (filter.type !== 'all' && (row.entry.type ?? '') !== filter.type) return false;
    if (filter.partition !== 'all' && !(row.entry.partitions ?? []).includes(filter.partition)) return false;
    if (filter.dataOnly && row.source !== 'data') return false;
    if (!search) return true;
    const haystack = [row.name, row.entry.description ?? '', ...(row.entry.synonyms ?? [])].join(' ').toLowerCase();
    return haystack.includes(search);
  });
}

export function partitionsOf(rows: NodeRow[]): string[] {
  return [...new Set(rows.flatMap((row) => row.entry.partitions ?? []))].sort();
}

export const NODE_TYPES = ['cpu', 'gpu', 'login', 'storage'] as const;
