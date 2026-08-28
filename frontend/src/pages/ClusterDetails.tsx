import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { adminClient, type Cluster } from '../api/adminClient';
import './AdminClusters.css';

const AGENT_PACKAGE = 'slurm-dashboard[agent]';
const AGENT_REPO = 'https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git';
const INSTALL_COMMANDS = [
  { label: 'uv', install: `uv tool install '${AGENT_PACKAGE} @ git+${AGENT_REPO}'` },
  { label: 'pip', install: `pip install 'git+${AGENT_REPO}#egg=${AGENT_PACKAGE}'` },
];

export function ClusterDetails() {
  const { clusterId } = useParams<{ clusterId: string }>();
  const [cluster, setCluster] = useState<Cluster | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rotatingKey, setRotatingKey] = useState(false);
  const [generatingDeployKey, setGeneratingDeployKey] = useState(false);
  const [newAPIKey, setNewAPIKey] = useState<string | null>(null);
  const [newDeployKey, setNewDeployKey] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!adminClient.isAuthenticated()) {
      navigate('/admin/login');
      return;
    }

    loadCluster();
  }, [navigate, clusterId]);

  const loadCluster = async () => {
    if (!clusterId) return;

    try {
      const data = await adminClient.getCluster(clusterId);
      setCluster(data);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cluster');
    } finally {
      setLoading(false);
    }
  };

  const handleRotateKey = async () => {
    if (!cluster) return;
    if (!confirm('Are you sure you want to rotate the API key? The old key will be immediately invalidated.')) {
      return;
    }

    try {
      setRotatingKey(true);
      const result = await adminClient.rotateAPIKey(cluster.id);
      setNewAPIKey(result.new_api_key);
      await loadCluster();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rotate API key');
    } finally {
      setRotatingKey(false);
    }
  };

  const handleGenerateDeployKey = async () => {
    if (!cluster) return;

    try {
      setGeneratingDeployKey(true);
      const result = await adminClient.generateDeployKey(cluster.id);
      setNewDeployKey(result.deploy_key);
      await loadCluster();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate deploy key');
    } finally {
      setGeneratingDeployKey(false);
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

  const getDeployKeyStatus = () => {
    if (!cluster || !cluster.deploy_key_created) {
      return { status: 'none', label: 'No Key', color: '#6c757d' };
    }

    if (cluster.deploy_key_used) {
      return { status: 'used', label: 'Used', color: '#17a2b8' };
    }

    if (cluster.deploy_key_expires_at) {
      const expiresAt = new Date(cluster.deploy_key_expires_at);
      const now = new Date();
      if (now > expiresAt) {
        return { status: 'expired', label: 'Expired', color: '#dc3545' };
      }
    }

    return { status: 'valid', label: 'Valid', color: '#28a745' };
  };

  if (loading) {
    return (
      <div className="clusters-container">
        <div className="clusters-loading">Loading...</div>
      </div>
    );
  }

  if (!cluster) {
    return (
      <div className="clusters-container">
        <div className="clusters-error">
          <div className="clusters-error-text">Cluster not found</div>
        </div>
      </div>
    );
  }

  const deployStatus = getDeployKeyStatus();

  return (
    <div className="clusters-container">
      {/* Header */}
      <div className="clusters-header">
        <div className="clusters-header-content">
          <div className="clusters-header-title">
            <h1>{cluster.name}</h1>
            <p className="clusters-header-subtitle">Cluster Security & Credentials</p>
          </div>
          <div className="clusters-header-nav">
            <a href="/admin/clusters">Back to Clusters</a>
            <a href="/">Dashboard</a>
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

        {/* New API Key Modal */}
        {newAPIKey && (
          <div className="clusters-modal-overlay">
            <div className="clusters-modal">
              <h3 className="clusters-modal-title">New API Key Generated</h3>
              <p className="clusters-modal-text">
                This is the only time the full key will be shown. Copy it now and update your cluster configuration.
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

        {/* Deploy Key Modal */}
        {newDeployKey && (
          <div className="clusters-modal-overlay">
            <div className="clusters-modal" style={{ maxWidth: '800px' }}>
              <h3 className="clusters-modal-title">One-Time Deploy Key Generated</h3>
              <p className="clusters-modal-text">
                Run this command on your cluster to set up the agent. The deploy key will be automatically exchanged for a permanent API key.
              </p>

              {INSTALL_COMMANDS.map(({ label, install }) => {
                const command = `${install} && slurm-dashboard setup --api-url ${window.location.origin} --deploy-key ${newDeployKey}`;
                return (
                  <div key={label} style={{ marginBottom: '1.5rem' }}>
                    <h4 style={{ marginBottom: '0.5rem', fontSize: '0.9rem', color: '#333' }}>Installation Command ({label}):</h4>
                    <div
                      className="clusters-modal-code"
                      style={{
                        backgroundColor: '#1e1e1e',
                        padding: '1rem',
                        borderRadius: '4px',
                        overflow: 'auto'
                      }}
                    >
                      <code style={{ color: '#d4d4d4', fontSize: '0.75rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                        {command}
                      </code>
                    </div>
                    <button
                      onClick={() => copyToClipboard(command)}
                      style={{
                        marginTop: '0.5rem',
                        padding: '0.5rem 1rem',
                        fontSize: '0.85rem',
                        backgroundColor: '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Copy {label} command
                    </button>
                  </div>
                );
              })}

              <div style={{ borderTop: '1px solid #ddd', paddingTop: '1rem', marginTop: '1rem' }}>
                <h4 style={{ marginBottom: '0.5rem', fontSize: '0.9rem', color: '#666' }}>Deploy Key (for manual setup):</h4>
                <div className="clusters-modal-code">
                  <code style={{ fontSize: '0.75rem' }}>{newDeployKey}</code>
                </div>
                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#666' }}>
                  This key expires in 7 days and can only be used once.
                </div>
              </div>

              <div className="clusters-modal-actions">
                <button
                  onClick={() => setNewDeployKey(null)}
                  className="clusters-form-cancel"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Cluster Info */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ padding: '1.5rem', backgroundColor: '#f8f9fa', borderRadius: '8px', marginBottom: '1rem' }}>
            <h3 style={{ marginTop: 0 }}>Cluster Information</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '0.75rem', fontSize: '0.9rem' }}>
              <strong>Name:</strong>
              <span>{cluster.name}</span>

              {cluster.description && (
                <>
                  <strong>Description:</strong>
                  <span>{cluster.description}</span>
                </>
              )}

              {cluster.location && (
                <>
                  <strong>Location:</strong>
                  <span>{cluster.location}</span>
                </>
              )}

              {cluster.contact_email && (
                <>
                  <strong>Contact:</strong>
                  <span>{cluster.contact_email}</span>
                </>
              )}

              <strong>Status:</strong>
              <span>
                <span className={`clusters-badge ${cluster.active ? 'clusters-badge-active' : 'clusters-badge-inactive'}`}>
                  {cluster.active ? 'Active' : 'Inactive'}
                </span>
              </span>

              <strong>Created:</strong>
              <span>{formatDate(cluster.created_at)}</span>
            </div>
          </div>
        </div>

        {/* API Key Section */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ padding: '1.5rem', border: '2px solid #ffc107', borderRadius: '8px', backgroundColor: '#fffbf0' }}>
            <h3 style={{ marginTop: 0, color: '#856404' }}>API Key</h3>
            <p style={{ color: '#856404', marginBottom: '1rem' }}>
              This is the permanent API key used by the cluster agent for authentication.
            </p>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <code style={{ flex: 1, padding: '0.75rem', backgroundColor: 'white', borderRadius: '4px', fontSize: '0.9rem' }}>
                  {cluster.api_key}
                </code>
                <button
                  onClick={() => copyToClipboard(cluster.api_key)}
                  className="clusters-copy-btn"
                  style={{ padding: '0.5rem 1rem' }}
                  title="Copy API key"
                >
                  Copy
                </button>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#666' }}>
                Created: {formatDate(cluster.api_key_created)}
              </div>
            </div>

            <button
              onClick={handleRotateKey}
              disabled={rotatingKey}
              className="clusters-action-btn action-warning"
              style={{ marginTop: '0.5rem' }}
            >
              {rotatingKey ? 'Rotating...' : 'Rotate API Key'}
            </button>
          </div>
        </div>

        {/* Deploy Key Section */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ padding: '1.5rem', border: '2px solid #17a2b8', borderRadius: '8px', backgroundColor: '#e7f6f8' }}>
            <h3 style={{ marginTop: 0, color: '#0c5460' }}>Deploy Key</h3>
            <p style={{ color: '#0c5460', marginBottom: '1rem' }}>
              One-time deployment key for initial agent setup. Expires in 7 days and can only be used once.
            </p>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span
                  className="clusters-badge"
                  style={{
                    backgroundColor: deployStatus.color,
                    color: 'white',
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem'
                  }}
                >
                  {deployStatus.label}
                </span>
              </div>

              {cluster.deploy_key_created && (
                <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
                  <div>Created: {formatDate(cluster.deploy_key_created)}</div>

                  {deployStatus.status === 'valid' && cluster.deploy_key_expires_at && (
                    <div style={{ color: '#28a745', fontWeight: 600 }}>
                      Expires: {formatDate(cluster.deploy_key_expires_at)}
                    </div>
                  )}

                  {deployStatus.status === 'expired' && cluster.deploy_key_expires_at && (
                    <div style={{ color: '#dc3545', fontWeight: 600 }}>
                      Expired: {formatDate(cluster.deploy_key_expires_at)}
                    </div>
                  )}

                  {deployStatus.status === 'used' && (
                    <>
                      <div style={{ color: '#17a2b8', fontWeight: 600 }}>
                        Used: {formatDate(cluster.deploy_key_used_at)}
                      </div>
                      {cluster.deploy_key_used_from_ip && (
                        <div>From IP: {cluster.deploy_key_used_from_ip}</div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

            <button
              onClick={handleGenerateDeployKey}
              disabled={generatingDeployKey}
              className="clusters-action-btn action-primary"
              style={{ marginTop: '0.5rem' }}
            >
              {generatingDeployKey ? 'Generating...' : 'Generate New Deploy Key'}
            </button>
          </div>
        </div>

        {/* Statistics */}
        <div style={{ padding: '1.5rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0 }}>Usage Statistics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '0.75rem', fontSize: '0.9rem' }}>
            <strong>Total Jobs Submitted:</strong>
            <span>{cluster.total_jobs_submitted.toLocaleString()}</span>

            <strong>Last Submission:</strong>
            <span>{formatDate(cluster.last_submission)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
