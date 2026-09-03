import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminClient, type Cluster } from '../api/adminClient';
import { AdminLayout } from '../components/AdminLayout';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

export function AdminClusters() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newAPIKey, setNewAPIKey] = useState<string | null>(null);
  const [reloading, setReloading] = useState(false);
  const [generatingDemo, setGeneratingDemo] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!adminClient.isAuthenticated()) {
      navigate('/admin/login');
      return;
    }

    loadClusters();
  }, [navigate]);

  const loadClusters = async () => {
    try {
      const data = await adminClient.getClusters();
      setClusters(data.clusters);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clusters');
    } finally {
      setLoading(false);
    }
  };

  const handleReloadData = async () => {
    setReloading(true);
    try {
      const result = await adminClient.reloadData();
      const ranges = Object.entries(result.date_ranges)
        .map(([name, range]) => `${name}: ${range.min_date} to ${range.max_date}`)
        .join('; ');
      setNotice(`${result.message}${ranges ? ` (${ranges})` : ''}`);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reload data');
    } finally {
      setReloading(false);
    }
  };

  const handleGenerateDemoCluster = async () => {
    if (!confirm('Generate a demo cluster with 2 years of synthetic data?\n\nThis will create:\n- DemoCluster with 100 users\n- 2 years of data (2023-2024)\n- 30 nodes (15 GPU, 15 CPU)\n- Seasonal patterns and simulated outages\n- ~110,000 realistic jobs')) {
      return;
    }

    setGeneratingDemo(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/generate-demo-cluster`, {
        method: 'POST',
        headers: adminClient.authHeaders(),
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate demo cluster');
      }

      const result = await response.json();
      setNotice(
        `Demo cluster ${result.cluster_name} generated: ${result.stats.total_jobs.toLocaleString()} jobs, ` +
          `${result.stats.users} users, ${result.stats.nodes} nodes, ${result.stats.date_range}.`
      );
      await handleReloadData();
      await loadClusters();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate demo cluster');
    } finally {
      setGeneratingDemo(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete cluster "${name}"?`)) {
      return;
    }

    try {
      await adminClient.deleteCluster(id);
      await loadClusters();
      await handleReloadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete cluster');
    }
  };

  const handleToggleActive = async (cluster: Cluster) => {
    try {
      await adminClient.updateCluster(cluster.id, { active: !cluster.active });
      await loadClusters();
      await handleReloadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update cluster');
    }
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setNotice('API key copied to clipboard.');
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <AdminLayout
      title="Cluster Management"
      subtitle="Manage SLURM clusters and API keys"
      actions={
        <button type="button" className="cp-btn cp-btn-small" onClick={handleReloadData} disabled={reloading}>
          {reloading ? 'Reloading...' : 'Reload data'}
        </button>
      }
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

      {newAPIKey && (
        <div className="cp-modal-overlay">
          <div className="cp-modal">
            <h3>New API key generated</h3>
            <p>This is the only time the full key is shown. Copy it now and store it securely.</p>
            <code className="cp-code">{newAPIKey}</code>
            <div className="cp-actions">
              <button type="button" className="cp-btn cp-btn-primary" onClick={() => copyToClipboard(newAPIKey)}>
                Copy to clipboard
              </button>
              <button type="button" className="cp-btn" onClick={() => setNewAPIKey(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="cp-actions-bar">
        <button type="button" className="cp-btn cp-btn-primary" onClick={() => setShowCreateForm(!showCreateForm)}>
          {showCreateForm ? 'Cancel' : 'Add cluster'}
        </button>
        <button type="button" className="cp-btn" onClick={handleGenerateDemoCluster} disabled={generatingDemo}>
          {generatingDemo ? 'Generating...' : 'Create demo cluster'}
        </button>
      </div>

      {showCreateForm && (
        <CreateClusterForm
          onSuccess={() => {
            setShowCreateForm(false);
            loadClusters();
          }}
          onCancel={() => setShowCreateForm(false)}
          onAPIKeyGenerated={(key) => setNewAPIKey(key)}
        />
      )}

      {loading ? (
        <p className="cp-muted">Loading</p>
      ) : (
        <div className="cp-table-wrap">
          <table className="cp-table">
            <thead>
              <tr>
                <th>Cluster</th>
                <th>Status</th>
                <th>Submissions</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clusters.length === 0 ? (
                <tr>
                  <td colSpan={4} className="cp-empty">
                    No clusters yet. Click Add cluster to get started.
                  </td>
                </tr>
              ) : (
                clusters.map((cluster) => (
                  <tr key={cluster.id}>
                    <td>
                      <div className="cp-strong">
                        <a href={`/admin/clusters/${encodeURIComponent(cluster.name)}`}>{cluster.name}</a>
                      </div>
                      {cluster.description && <div className="cp-muted">{cluster.description}</div>}
                      {cluster.contact_email && <div className="cp-muted">{cluster.contact_email}</div>}
                    </td>
                    <td>
                      <span className={`cp-badge ${cluster.active ? 'cp-badge-ok' : 'cp-badge-danger'}`}>
                        {cluster.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div>{cluster.total_jobs_submitted.toLocaleString()} jobs via API</div>
                      <div className="cp-muted">Last: {formatDate(cluster.last_submission)}</div>
                    </td>
                    <td className="cp-actions-cell">
                      <div className="cp-actions">
                        <a href={`/admin/clusters/${encodeURIComponent(cluster.name)}`} className="cp-btn cp-btn-small">
                          Open
                        </a>
                        <button type="button" className="cp-btn cp-btn-small" onClick={() => handleToggleActive(cluster)}>
                          {cluster.active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button type="button" className="cp-btn cp-btn-small cp-btn-danger" onClick={() => handleDelete(cluster.id, cluster.name)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </AdminLayout>
  );
}

interface CreateClusterFormProps {
  onSuccess: () => void;
  onCancel: () => void;
  onAPIKeyGenerated: (key: string) => void;
}

function CreateClusterForm({ onSuccess, onCancel, onAPIKeyGenerated }: CreateClusterFormProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const cluster = await adminClient.createCluster({
        name,
        description: description || undefined,
        contact_email: contactEmail || undefined,
        location: location || undefined,
      });

      if (cluster.api_key) onAPIKeyGenerated(cluster.api_key);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create cluster');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="cp-card">
      <h3>Add new cluster</h3>

      {error && <div className="cp-inline-error">{error}</div>}

      <form className="cp-form" onSubmit={handleSubmit}>
        <div className="cp-form-group">
          <label htmlFor="cluster-name">Cluster name</label>
          <input
            id="cluster-name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="hpc-cluster-01"
          />
          <p className="cp-form-hint">Hostname or identifier for the cluster; the agent submits data under this name</p>
        </div>

        <div className="cp-form-group">
          <label htmlFor="cluster-description">Description</label>
          <input
            id="cluster-description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Main HPC cluster for physics department"
          />
        </div>

        <div className="cp-form-group">
          <label htmlFor="cluster-contact">Contact email</label>
          <input
            id="cluster-contact"
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            placeholder="admin@example.com"
          />
        </div>

        <div className="cp-form-group">
          <label htmlFor="cluster-location">Location</label>
          <input
            id="cluster-location"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Building A, Room 101"
          />
        </div>

        <div className="cp-actions">
          <button type="submit" className="cp-btn cp-btn-primary" disabled={loading}>
            {loading ? 'Creating...' : 'Create cluster'}
          </button>
          <button type="button" className="cp-btn" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  );
}
