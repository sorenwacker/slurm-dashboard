import { adminClient } from './adminClient';
import type { AccountEntry, ClusterEntry, ClusterIdentity, ClusterStatus, NodeEntry, PartitionEntry } from '../pages/cluster/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: adminClient.authHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? response.statusText);
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const base = (cluster: string) => `/api/admin/clusters/by-name/${encodeURIComponent(cluster)}`;

export const clusterAdminApi = {
  status: (cluster: string) => request<ClusterStatus>(`${base(cluster)}/status`),
  config: (cluster: string) => request<ClusterEntry>(`${base(cluster)}/config`),
  updateIdentity: (cluster: string, changes: ClusterIdentity) =>
    request<ClusterIdentity>(`${base(cluster)}/identity`, { method: 'PATCH', body: JSON.stringify(changes) }),
  updateNode: (cluster: string, node: string, changes: Pick<NodeEntry, 'synonyms' | 'description' | 'type'>) =>
    request<NodeEntry>(`${base(cluster)}/nodes/${encodeURIComponent(node)}`, { method: 'PATCH', body: JSON.stringify(changes) }),
  updatePartition: (cluster: string, partition: string, changes: Pick<PartitionEntry, 'display_name' | 'description'>) =>
    request<PartitionEntry>(`${base(cluster)}/partitions/${encodeURIComponent(partition)}`, { method: 'PATCH', body: JSON.stringify(changes) }),
  updateAccount: (cluster: string, account: string, changes: Omit<AccountEntry, 'slurm'>) =>
    request<AccountEntry>(`${base(cluster)}/accounts/${encodeURIComponent(account)}`, { method: 'PATCH', body: JSON.stringify(changes) }),
  /** Whole-entry write used by the YAML tab. */
  replaceConfig: (cluster: string, entry: ClusterEntry) =>
    request<{ status: string }>(`/api/admin/config/${encodeURIComponent(cluster)}`, { method: 'PUT', body: JSON.stringify(entry) }),
  reload: () => request<{ status: string }>('/api/admin/config/reload', { method: 'POST' }),
};
