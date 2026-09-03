import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { adminClient } from '../../api/adminClient';
import { clusterAdminApi } from '../../api/clusterAdminApi';
import { AdminLayout } from '../../components/AdminLayout';
import { AccountsTab } from './AccountsTab';
import { NodesTab } from './NodesTab';
import { OverviewTab } from './OverviewTab';
import { PartitionsTab } from './PartitionsTab';
import { YamlTab } from './YamlTab';
import type { ClusterEntry, ClusterStatus } from './types';

const TABS = ['overview', 'nodes', 'partitions', 'accounts', 'yaml'] as const;
type Tab = (typeof TABS)[number];
const TAB_LABELS: Record<Tab, string> = {
  overview: 'Overview',
  nodes: 'Nodes',
  partitions: 'Partitions',
  accounts: 'Accounts',
  yaml: 'YAML',
};

export function ClusterPage() {
  const { clusterName = '' } = useParams<{ clusterName: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ClusterStatus | null>(null);
  const [entry, setEntry] = useState<ClusterEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const tabParam = searchParams.get('tab');
  const tab: Tab = TABS.includes(tabParam as Tab) ? (tabParam as Tab) : 'overview';

  const load = useCallback(async () => {
    try {
      const nextStatus = await clusterAdminApi.status(clusterName);
      setStatus(nextStatus);
      setEntry(nextStatus.config_present ? await clusterAdminApi.config(clusterName) : null);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cluster');
    } finally {
      setLoading(false);
    }
  }, [clusterName]);

  useEffect(() => {
    if (!adminClient.isAuthenticated()) {
      navigate('/admin/login');
      return;
    }
    load();
  }, [navigate, load]);

  const createDefaultConfig = async () => {
    try {
      await clusterAdminApi.replaceConfig(clusterName, {
        display_name: clusterName,
        metadata: {},
        node_labels: {},
        partition_labels: {},
        account_labels: {},
      });
      setNotice('Configuration entry created.');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create configuration');
    }
  };

  const reloadConfig = async () => {
    try {
      await clusterAdminApi.reload();
      await load();
      setNotice('Configuration reloaded from disk.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reload failed');
    }
  };

  const counts = {
    nodes: Object.keys(entry?.node_labels ?? {}).length,
    partitions: Object.keys(entry?.partition_labels ?? {}).length,
    accounts: Object.keys(entry?.account_labels ?? {}).length,
  };

  const tabs = entry
    ? TABS.map((t) => (
        <button
          key={t}
          type="button"
          className={`cp-tab ${tab === t ? 'active' : ''}`}
          onClick={() => setSearchParams({ tab: t })}
        >
          {TAB_LABELS[t]}
          {t in counts && <span className="cp-tab-count">{counts[t as keyof typeof counts]}</span>}
        </button>
      ))
    : undefined;

  return (
    <AdminLayout
      title={status?.identity.display_name || clusterName}
      subtitle={status?.identity.description ?? undefined}
      breadcrumb={
        <>
          <a href="/admin/clusters">Clusters</a>
          <span>/</span>
          <span>{clusterName}</span>
        </>
      }
      actions={
        <button type="button" className="cp-btn cp-btn-small" onClick={reloadConfig}>
          Reload config
        </button>
      }
      tabs={tabs}
    >
        {error && (
          <div className="cp-message cp-message-error">
            <span>{error}</span>
            <button type="button" onClick={() => setError('')}>Dismiss</button>
          </div>
        )}
        {notice && (
          <div className="cp-message cp-message-ok">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice('')}>Dismiss</button>
          </div>
        )}

        {loading && <p className="cp-muted">Loading</p>}

        {!loading && status && !entry && (
          <section className="cp-card">
            <h3>No configuration for cluster {clusterName}</h3>
            <p>This cluster has a record and an API key but no entry in clusters.yaml. Create the entry, then run sync-config on the cluster to fill it.</p>
            <button type="button" className="cp-btn cp-btn-primary" onClick={createDefaultConfig}>Create configuration entry</button>
          </section>
        )}

        {!loading && status && entry && (
          <>
            {tab === 'overview' && <OverviewTab status={status} onChanged={load} onError={setError} />}
            {tab === 'nodes' && <NodesTab cluster={clusterName} nodes={entry.node_labels ?? {}} onChanged={load} />}
            {tab === 'partitions' && <PartitionsTab cluster={clusterName} partitions={entry.partition_labels ?? {}} onChanged={load} />}
            {tab === 'accounts' && <AccountsTab cluster={clusterName} accounts={entry.account_labels ?? {}} onChanged={load} />}
            {tab === 'yaml' && <YamlTab cluster={clusterName} entry={entry} onChanged={load} />}
          </>
        )}
    </AdminLayout>
  );
}
