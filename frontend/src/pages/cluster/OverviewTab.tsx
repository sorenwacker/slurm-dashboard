import { useCallback, useEffect, useState } from 'react';
import { adminClient, type Cluster } from '../../api/adminClient';
import { clusterAdminApi } from '../../api/clusterAdminApi';
import { CredentialsPanel } from './CredentialsPanel';
import { EditableCell } from './EditableCell';
import type { ClusterIdentity, ClusterStatus } from './types';

interface OverviewTabProps {
  status: ClusterStatus;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
}

const IDENTITY_FIELDS: { key: keyof ClusterIdentity; label: string }[] = [
  { key: 'display_name', label: 'Display name' },
  { key: 'description', label: 'Description' },
  { key: 'location', label: 'Location' },
  { key: 'owner', label: 'Owner' },
  { key: 'contact', label: 'Contact' },
  { key: 'url', label: 'URL' },
];

function formatDate(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : 'never';
}

export function OverviewTab({ status, onChanged, onError }: OverviewTabProps) {
  const [record, setRecord] = useState<Cluster | null>(null);

  const loadRecord = useCallback(async () => {
    if (!status.id) return;
    try {
      setRecord(await adminClient.getCluster(status.id));
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to load cluster record');
    }
  }, [status.id, onError]);

  useEffect(() => {
    loadRecord();
  }, [loadRecord]);

  const saveIdentity = (key: keyof ClusterIdentity) => async (value: string) => {
    await clusterAdminApi.updateIdentity(status.name, { [key]: value });
    await onChanged();
    await loadRecord();
  };

  const { sync, data } = status;
  const syncCommand = 'slurm-dashboard sync-config --config config.json';

  return (
    <div className="cp-grid">
      <section className="cp-card">
        <h3>Identity</h3>
        <dl className="cp-dl">
          {IDENTITY_FIELDS.map(({ key, label }) => (
            <div key={key} className="cp-dl-row">
              <dt>{label}</dt>
              <dd>
                <EditableCell value={status.identity[key] ?? ''} onSave={saveIdentity(key)} />
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="cp-card">
        <h3>SLURM sync</h3>
        {sync.last_sync ? (
          <dl className="cp-dl">
            <div className="cp-dl-row"><dt>Last sync</dt><dd>{formatDate(sync.last_sync)}</dd></div>
            <div className="cp-dl-row"><dt>SLURM version</dt><dd>{sync.slurm_version ?? 'not reported'}</dd></div>
            <div className="cp-dl-row"><dt>SLURM cluster name</dt><dd>{sync.slurm_cluster_name ?? 'not reported'}</dd></div>
            <div className="cp-dl-row"><dt>Nodes with SLURM hardware</dt><dd>{sync.nodes_synced}</dd></div>
            <div className="cp-dl-row"><dt>Nodes known from job data only</dt><dd>{sync.nodes_from_data_only}</dd></div>
            <div className="cp-dl-row"><dt>Partitions</dt><dd>{sync.partitions}</dd></div>
            <div className="cp-dl-row"><dt>Accounts</dt><dd>{sync.accounts}</dd></div>
          </dl>
        ) : (
          <div>
            <p>This cluster has never been synced. Hardware, partitions and accounts are unknown until the agent uploads them. Run on the cluster:</p>
            <pre>{syncCommand}</pre>
            {sync.nodes_from_data_only > 0 && (
              <p className="cp-muted">{sync.nodes_from_data_only} nodes are known from job data only.</p>
            )}
          </div>
        )}
      </section>

      <section className="cp-card">
        <h3>Data</h3>
        <dl className="cp-dl">
          <div className="cp-dl-row"><dt>First job</dt><dd>{data.min_date ?? 'no data'}</dd></div>
          <div className="cp-dl-row"><dt>Last job</dt><dd>{data.max_date ?? 'no data'}</dd></div>
          <div className="cp-dl-row"><dt>Jobs submitted via API</dt><dd>{data.total_jobs_submitted.toLocaleString()}</dd></div>
          <div className="cp-dl-row"><dt>Last submission</dt><dd>{formatDate(data.last_submission)}</dd></div>
        </dl>
      </section>

      {record && <CredentialsPanel cluster={record} onChanged={loadRecord} onError={onError} />}
    </div>
  );
}
