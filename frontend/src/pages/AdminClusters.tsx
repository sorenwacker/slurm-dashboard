import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminClient, type Cluster } from '../api/adminClient';
import './AdminClusters.css';

export function AdminClusters() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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

  const handleLogout = () => {
    adminClient.logout();
    // Redirect to SAML logout endpoint which will clear the session
    window.location.href = '/saml/logout?redirect_to=/admin/login';
  };

  const handleReloadData = async () => {
    setReloading(true);
    try {
      const result = await adminClient.reloadData();
      alert(`Data reloaded successfully!\n\n${result.message}\n\nLatest dates: ${JSON.stringify(result.date_ranges, null, 2)}`);
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
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';
      const token = localStorage.getItem('admin_token');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/admin/generate-demo-cluster`, {
        method: 'POST',
        headers,
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate demo cluster');
      }

      const result = await response.json();
      alert(`Demo cluster generated successfully!\n\nCluster: ${result.cluster_name}\nJobs: ${result.stats.total_jobs.toLocaleString()}\nUsers: ${result.stats.users}\nNodes: ${result.stats.nodes}\nDate range: ${result.stats.date_range}\n\nThe cluster will appear in the dashboard after reloading data.`);

      // Reload data to show new cluster
      await handleReloadData();
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
      // Automatically reload dashboard data so the cluster disappears from the main dashboard
      await handleReloadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete cluster');
    }
  };

  const handleToggleActive = async (cluster: Cluster) => {
    try {
      await adminClient.updateCluster(cluster.id, { active: !cluster.active });
      await loadClusters();
      // Automatically reload dashboard data so the cluster appears/disappears from dropdown
      await handleReloadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update cluster');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  if (loading) {
    return (
      <div className="clusters-container">
        <div className="clusters-loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="clusters-container">
      {/* Header */}
      <div className="clusters-header">
        <div className="clusters-header-content">
          <div className="clusters-header-title">
            <h1>Cluster Management</h1>
            <p className="clusters-header-subtitle">Manage SLURM clusters and API keys</p>
          </div>
          <div className="clusters-header-nav">
            <a href="/">Dashboard</a>
            <a href="/admin/users">Users</a>
            <button onClick={handleReloadData} disabled={reloading}>
              {reloading ? 'Reloading...' : 'Reload Data'}
            </button>
            <button onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </div>

      <div className="clusters-content">
        {/* Error Message */}
        {error && (
          <div className="clusters-error">
            <div className="clusters-error-text">{error}</div>
            <button onClick={() => setError('')} className="clusters-error-close">
              ×
            </button>
          </div>
        )}

        {/* New API Key Modal (shown after creating a new cluster) */}
        {newAPIKey && (
          <div className="clusters-modal-overlay">
            <div className="clusters-modal">
              <h3 className="clusters-modal-title">New API Key Generated</h3>
              <p className="clusters-modal-text">
                This is the only time the full key will be shown. Copy it now and save it securely.
                You can also access it later by clicking "Manage Keys" for this cluster.
              </p>
              <div className="clusters-modal-code">
                <code>{newAPIKey}</code>
              </div>
              <div className="clusters-modal-actions">
                <button
                  onClick={() => copyToClipboard(newAPIKey)}
                  className="clusters-form-submit"
                >
                  Copy to Clipboard
                </button>
                <button
                  onClick={() => setNewAPIKey(null)}
                  className="clusters-form-cancel"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="clusters-actions">
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="clusters-btn-primary"
          >
            {showCreateForm ? 'Cancel' : '+ Add Cluster'}
          </button>
          <button
            onClick={handleGenerateDemoCluster}
            disabled={generatingDemo}
            className="clusters-btn-primary"
            style={{ background: '#17a2b8' }}
          >
            {generatingDemo ? 'Generating...' : 'Create Demo'}
          </button>
        </div>

        {/* Create Form */}
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

        {/* Clusters List */}
        <div className="clusters-table-container">
          <table className="clusters-table">
            <thead>
              <tr>
                <th>Cluster</th>
                <th>Status</th>
                <th>Statistics</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clusters.length === 0 ? (
                <tr>
                  <td colSpan={4} className="clusters-table-empty">
                    No clusters yet. Click "Add Cluster" to get started.
                  </td>
                </tr>
              ) : (
                clusters.map((cluster) => (
                  <tr key={cluster.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{cluster.name}</div>
                      {cluster.description && (
                        <div style={{ fontSize: '0.8125rem', color: '#6c757d' }}>{cluster.description}</div>
                      )}
                      {cluster.contact_email && (
                        <div style={{ fontSize: '0.75rem', color: '#adb5bd' }}>{cluster.contact_email}</div>
                      )}
                    </td>
                    <td>
                      <span className={`clusters-badge ${cluster.active ? 'clusters-badge-active' : 'clusters-badge-inactive'}`}>
                        {cluster.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div>API Submissions: {cluster.total_jobs_submitted.toLocaleString()}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6c757d' }}>Last: {formatDate(cluster.last_submission)}</div>
                    </td>
                    <td>
                      <div className="clusters-actions-menu">
                        <a
                          href={`/admin/clusters/${encodeURIComponent(cluster.name)}`}
                          className="clusters-action-btn action-primary"
                          style={{ textDecoration: 'none', fontWeight: 600 }}
                        >
                          Open
                        </a>
                        <button
                          onClick={() => handleToggleActive(cluster)}
                          className="clusters-action-btn action-primary"
                        >
                          {cluster.active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button
                          onClick={() => handleDelete(cluster.id, cluster.name)}
                          className="clusters-action-btn action-danger"
                        >
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
      </div>
    </div>
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

      onAPIKeyGenerated(cluster.api_key);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create cluster');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="clusters-form">
      <h3 className="clusters-form-title">Add New Cluster</h3>

      {error && (
        <div className="clusters-error" style={{ marginBottom: '1rem' }}>
          <div className="clusters-error-text">{error}</div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="clusters-form-group">
          <label className="clusters-form-label">
            Cluster Name *
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="clusters-form-input"
            placeholder="hpc-cluster-01"
          />
          <p className="clusters-form-hint">
            Hostname or identifier for the cluster
          </p>
        </div>

        <div className="clusters-form-group">
          <label className="clusters-form-label">
            Description
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="clusters-form-input"
            placeholder="Main HPC cluster for physics department"
          />
        </div>

        <div className="clusters-form-group">
          <label className="clusters-form-label">
            Contact Email
          </label>
          <input
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            className="clusters-form-input"
            placeholder="admin@example.com"
          />
        </div>

        <div className="clusters-form-group">
          <label className="clusters-form-label">
            Location
          </label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="clusters-form-input"
            placeholder="Building A, Room 101"
          />
        </div>

        <div className="clusters-form-actions">
          <button
            type="submit"
            disabled={loading}
            className="clusters-form-submit"
          >
            {loading ? 'Creating...' : 'Create Cluster'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="clusters-form-cancel"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
