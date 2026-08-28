import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { adminClient } from '../api/adminClient';
import * as yaml from 'js-yaml';
import './AdminConfig.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

interface ClusterConfig {
  display_name?: string;
  description?: string;
  metadata?: {
    location?: string;
    owner?: string;
    contact?: string;
    url?: string;
    last_hardware_sync?: string;
  };
  node_labels?: {
    [key: string]: NodeLabel;
  };
  account_labels?: {
    [key: string]: AccountLabel;
  };
  partition_labels?: {
    [key: string]: PartitionLabel;
  };
}

interface NodeLabel {
  synonyms?: string[];
  type?: string;
  description?: string;
  hardware?: {
    cpu?: {
      model?: string;
      cores?: number;
      threads?: number;
    };
    ram?: {
      total_gb?: number;
      type?: string;
    };
    gpus?: Array<{
      model?: string;
      count?: number;
      memory_gb?: number;
      nvlink?: boolean;
      nvlink_topology?: string;
    }>;
  };
}

interface AccountLabel {
  display_name?: string;
  short_name?: string;
  faculty?: string;
  department?: string;
}

interface PartitionLabel {
  display_name?: string;
  description?: string;
}

interface ConfigResponse {
  clusters: {
    [key: string]: ClusterConfig;
  };
  settings: {
    default_node_type?: string;
    case_sensitive?: boolean;
    auto_generate_labels?: boolean;
  };
}

export function AdminConfig() {
  const [searchParams] = useSearchParams();
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [autoGenerating, setAutoGenerating] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'nodes' | 'accounts' | 'partitions' | 'overview' | 'yaml'>('overview');
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>('all');
  const [yamlContent, setYamlContent] = useState('');
  const [yamlError, setYamlError] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  // Read cluster from URL query parameter
  useEffect(() => {
    const clusterParam = searchParams.get('cluster');
    if (clusterParam) {
      setSelectedCluster(clusterParam);
      setActiveTab('overview'); // Show overview/stats tab
    }
  }, [searchParams]);

  const getAuthHeaders = (): HeadersInit => {
    const token = localStorage.getItem('admin_token');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add Bearer token if admin_token exists (username/password login)
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    // If no token, rely on cookie-based SAML authentication

    return headers;
  };

  useEffect(() => {
    if (!adminClient.isAuthenticated()) {
      navigate('/admin/login');
      return;
    }

    loadConfig();
  }, [navigate]);

  const loadConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/config`, {
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to load configuration');
      const data = await response.json();
      setConfig(data);

      // Only pick a default when the URL did not name a cluster; a named
      // cluster that is missing from the YAML must show as missing, not as another cluster.
      if (data.clusters && Object.keys(data.clusters).length > 0 && !searchParams.get('cluster')) {
        setSelectedCluster((current) => current || Object.keys(data.clusters)[0]);
      }

      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDefaultConfig = async (clusterName: string) => {
    setError('');
    setSuccess('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/config/${encodeURIComponent(clusterName)}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify({
          display_name: clusterName,
          description: `${clusterName} Cluster`,
          metadata: {},
          node_labels: {},
          account_labels: {},
          partition_labels: {},
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create configuration');
      }
      setSuccess(`Default configuration created for cluster ${clusterName}`);
      await loadConfig();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create configuration');
    }
  };

  const handleAutoGenerate = async (clusterName: string) => {
    if (!confirm(`Auto-generate configuration for cluster "${clusterName}"? This will merge with existing configuration.`)) {
      return;
    }

    setAutoGenerating(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/config/${clusterName}/auto-generate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to auto-generate configuration');
      }

      const result = await response.json();
      setSuccess(`Configuration auto-generated! Nodes: ${result.stats.nodes}, Accounts: ${result.stats.accounts}, Partitions: ${result.stats.partitions}`);
      await loadConfig();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to auto-generate configuration');
    } finally {
      setAutoGenerating(false);
    }
  };

  const handleReload = async () => {
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/config/reload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
      });

      if (!response.ok) throw new Error('Failed to reload configuration');

      await loadConfig();
      setSuccess('Configuration reloaded successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reload configuration');
    }
  };

  const handleExport = () => {
    if (!config) return;

    const yamlStr = yaml.dump(config, { indent: 2, lineWidth: -1 });
    const dataBlob = new Blob([yamlStr], { type: 'application/x-yaml' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `cluster-config-${selectedCluster}-${new Date().toISOString().split('T')[0]}.yaml`;
    link.click();
    URL.revokeObjectURL(url);
    setSuccess('Configuration exported successfully!');
  };

  const handleLogout = () => {
    adminClient.logout();
    // Redirect to SAML logout endpoint which will clear the session
    window.location.href = '/saml/logout?redirect_to=/admin/login';
  };

  const loadYAMLContent = () => {
    if (clusterConfig) {
      const yamlStr = yaml.dump(clusterConfig, { indent: 2, lineWidth: -1 });
      setYamlContent(yamlStr);
      setYamlError('');
    }
  };

  const handleSaveYAML = async () => {
    if (!selectedCluster) return;

    try {
      setSaving(true);
      setYamlError('');

      // Parse YAML to validate
      const parsedConfig = yaml.load(yamlContent);

      // Save to backend
      const response = await fetch(`${API_BASE_URL}/api/admin/config/${selectedCluster}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(parsedConfig),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save configuration');
      }

      await loadConfig();
      setSuccess('Configuration saved successfully!');
      setActiveTab('overview');
    } catch (err) {
      if (err instanceof Error) {
        setYamlError(err.message);
      } else {
        setYamlError('Invalid YAML format or save failed');
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-config">
        <div className="admin-loading">
          <div className="admin-loading-spinner"></div>
          <p>Loading configuration...</p>
        </div>
      </div>
    );
  }

  const clusterConfig: ClusterConfig | undefined = selectedCluster && config?.clusters[selectedCluster] ? config.clusters[selectedCluster] : undefined;

  // Filter nodes based on search and type
  const filteredNodes: [string, NodeLabel][] = clusterConfig?.node_labels
    ? Object.entries(clusterConfig.node_labels).filter(([name, info]) => {
        const nodeInfo = info as NodeLabel;
        const matchesSearch = searchTerm === '' ||
          name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          nodeInfo.description?.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = nodeTypeFilter === 'all' || nodeInfo.type === nodeTypeFilter;
        return matchesSearch && matchesType;
      }) as [string, NodeLabel][]
    : [];

  // Statistics
  const stats = clusterConfig ? {
    totalNodes: Object.keys(clusterConfig.node_labels || {}).length,
    gpuNodes: Object.values(clusterConfig.node_labels || {}).filter(n => n.type === 'gpu').length,
    cpuNodes: Object.values(clusterConfig.node_labels || {}).filter(n => n.type === 'cpu').length,
    totalAccounts: Object.keys(clusterConfig.account_labels || {}).length,
    totalPartitions: Object.keys(clusterConfig.partition_labels || {}).length,
  } : null;

  return (
    <div className="admin-config">
      {/* Enhanced Header */}
      <div className="admin-header">
        <div className="admin-header-content">
          <div className="admin-header-title">
            <div>
              <h1>
                <span className="emoji">⚙️</span>
                Cluster Configuration
              </h1>
              <p className="admin-header-subtitle">Manage YAML cluster configuration, labels, and hardware specs</p>
            </div>
          </div>
          <div className="admin-header-nav">
            <a href="/">Dashboard</a>
            <a href="/admin/clusters">Clusters</a>
            <a href="/admin/users">Users</a>
            <button onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </div>

      <div className="admin-container">
        {/* Messages */}
        {error && (
          <div className="admin-message admin-message-error">
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={() => setError('')} className="admin-message-close">×</button>
          </div>
        )}

        {success && (
          <div className="admin-message admin-message-success">
            <span>✓</span>
            <span>{success}</span>
            <button onClick={() => setSuccess('')} className="admin-message-close">×</button>
          </div>
        )}

        {/* Control Panel */}
        <div className="admin-control-panel">
          <div className="admin-controls">
            {/* Cluster Name Display */}
            <div className="admin-cluster-display">
              <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                {config && selectedCluster && config.clusters[selectedCluster]
                  ? config.clusters[selectedCluster].display_name || selectedCluster
                  : 'No cluster selected'}
              </h2>
            </div>

            {/* Action Buttons */}
            <div className="admin-button-group">
              <button
                onClick={handleReload}
                className="admin-btn admin-btn-primary"
              >
                Reload
              </button>
              {selectedCluster && (
                <button
                  onClick={() => handleAutoGenerate(selectedCluster)}
                  disabled={autoGenerating}
                  className="admin-btn admin-btn-success"
                >
                  <span>✨</span> {autoGenerating ? 'Generating...' : 'Auto-Generate'}
                </button>
              )}
              <button
                onClick={handleExport}
                className="admin-btn admin-btn-secondary"
              >
                <span>📥</span> Export
              </button>
            </div>
          </div>
        </div>

        {clusterConfig ? (
          <>
            {/* Statistics Cards */}
            {stats && (
              <div className="admin-stats-grid">
                <div className="admin-stat-card stat-primary">
                  <div className="admin-stat-label">Total Nodes</div>
                  <div className="admin-stat-value">{stats.totalNodes}</div>
                </div>
                <div className="admin-stat-card stat-purple">
                  <div className="admin-stat-label">GPU Nodes</div>
                  <div className="admin-stat-value">{stats.gpuNodes}</div>
                </div>
                <div className="admin-stat-card stat-blue">
                  <div className="admin-stat-label">CPU Nodes</div>
                  <div className="admin-stat-value">{stats.cpuNodes}</div>
                </div>
                <div className="admin-stat-card stat-orange">
                  <div className="admin-stat-label">Accounts</div>
                  <div className="admin-stat-value">{stats.totalAccounts}</div>
                </div>
                <div className="admin-stat-card stat-indigo">
                  <div className="admin-stat-label">Partitions</div>
                  <div className="admin-stat-value">{stats.totalPartitions}</div>
                </div>
              </div>
            )}

            {/* Tab Navigation */}
            <div className="admin-tabs">
              {[
                { id: 'overview', label: 'Overview', icon: '' },
                { id: 'nodes', label: `Nodes (${stats?.totalNodes || 0})`, icon: '' },
                { id: 'accounts', label: `Accounts (${stats?.totalAccounts || 0})`, icon: '' },
                { id: 'partitions', label: `Partitions (${stats?.totalPartitions || 0})`, icon: '' },
                { id: 'yaml', label: 'Edit YAML', icon: '' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id as any);
                    if (tab.id === 'yaml') {
                      loadYAMLContent();
                    }
                  }}
                  className={`admin-tab ${activeTab === tab.id ? 'active' : ''}`}
                >
                  <span>{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'overview' && (
              <div className="admin-table-container" style={{ padding: '1.5rem' }}>
                {/* Cluster Info */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>🏢</span> Cluster Information
                  </h2>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
                    <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6c757d' }}>Display Name</div>
                      <div style={{ marginTop: '0.25rem', fontWeight: 600 }}>{clusterConfig.display_name || 'N/A'}</div>
                    </div>
                    <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6c757d' }}>Description</div>
                      <div style={{ marginTop: '0.25rem' }}>{clusterConfig.description || 'N/A'}</div>
                    </div>
                    {clusterConfig.metadata && (
                      <>
                        <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6c757d' }}>Location</div>
                          <div style={{ marginTop: '0.25rem' }}>{clusterConfig.metadata.location || 'N/A'}</div>
                        </div>
                        <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6c757d' }}>Owner</div>
                          <div style={{ marginTop: '0.25rem' }}>{clusterConfig.metadata.owner || 'N/A'}</div>
                        </div>
                        <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6c757d' }}>Contact</div>
                          <div style={{ marginTop: '0.25rem' }}>{clusterConfig.metadata.contact || 'N/A'}</div>
                        </div>
                        <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6c757d' }}>Hardware synced</div>
                          <div style={{ marginTop: '0.25rem' }}>
                            {clusterConfig.metadata.last_hardware_sync
                              ? new Date(clusterConfig.metadata.last_hardware_sync).toLocaleString()
                              : 'Never (run slurm-dashboard sync-config on the cluster)'}
                          </div>
                        </div>
                        {clusterConfig.metadata.url && (
                          <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6c757d' }}>URL</div>
                            <div style={{ marginTop: '0.25rem' }}>
                              <a href={clusterConfig.metadata.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none' }}>
                                {clusterConfig.metadata.url}
                              </a>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Config File Info */}
                <div style={{ background: 'linear-gradient(to right, #e7f3ff, #e7d6ff)', padding: '1.5rem', borderRadius: '8px', border: '1px solid #bee5eb' }}>
                  <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>📄</span> Configuration File
                  </h3>
                  <p style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 500 }}>Location:</span> <code style={{ background: '#d1ecf1', padding: '0.25rem 0.75rem', borderRadius: '4px', fontSize: '0.8125rem', marginLeft: '0.5rem' }}>config/clusters.yaml</code>
                  </p>
                  <p style={{ fontSize: '0.8125rem', marginTop: '0.75rem', color: '#004085' }}>
                    💡 To manually edit the configuration, modify the YAML file directly and click "Reload Configuration" to apply changes.
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'nodes' && (
              <div className="admin-table-container">
                {/* Search and Filter */}
                <div className="admin-search-filters">
                  <div className="admin-search-grid">
                    <input
                      type="text"
                      placeholder="Search nodes..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="admin-search-input"
                    />
                    <select
                      value={nodeTypeFilter}
                      onChange={(e) => setNodeTypeFilter(e.target.value)}
                      className="admin-filter-select"
                    >
                      <option value="all">All Types</option>
                      <option value="gpu">GPU Only</option>
                      <option value="cpu">CPU Only</option>
                      <option value="login">Login Only</option>
                      <option value="storage">Storage Only</option>
                    </select>
                  </div>
                  <div className="admin-filter-result">
                    Showing {filteredNodes.length} of {Object.keys(clusterConfig.node_labels || {}).length} nodes
                  </div>
                </div>

                {/* Nodes Table */}
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Node</th>
                      <th>Type</th>
                      <th>Description</th>
                      <th>Synonyms</th>
                      <th>Hardware</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredNodes.map(([nodeName, nodeInfo]) => (
                      <tr key={nodeName}>
                        <td style={{ fontWeight: 600 }}>{nodeName}</td>
                        <td>
                          <span className={`admin-badge ${
                            nodeInfo.type === 'gpu' ? 'admin-badge-purple' :
                            nodeInfo.type === 'cpu' ? 'admin-badge-blue' :
                            nodeInfo.type === 'login' ? 'admin-badge-green' :
                            'admin-badge-gray'
                          }`}>
                            {nodeInfo.type || 'N/A'}
                          </span>
                        </td>
                        <td>{nodeInfo.description || 'N/A'}</td>
                        <td>
                          {nodeInfo.synonyms && nodeInfo.synonyms.length > 0 ? (
                            <div className="admin-synonym-pills">
                              {nodeInfo.synonyms.slice(0, 3).map((syn, idx) => (
                                <span key={idx} className="admin-synonym-pill">{syn}</span>
                              ))}
                              {nodeInfo.synonyms.length > 3 && (
                                <span style={{ fontSize: '0.75rem', color: '#6c757d' }}>+{nodeInfo.synonyms.length - 3} more</span>
                              )}
                            </div>
                          ) : (
                            <span style={{ color: '#adb5bd' }}>None</span>
                          )}
                        </td>
                        <td>
                          {nodeInfo.hardware ? (
                            <div className="admin-hardware-cards">
                              {nodeInfo.hardware.cpu && (
                                <div className="admin-hardware-card hw-cpu">
                                  <span className="admin-hardware-label">CPU:</span> {nodeInfo.hardware.cpu.model || 'N/A'}
                                  <br />
                                  {nodeInfo.hardware.cpu.cores || 'N/A'} cores, {nodeInfo.hardware.cpu.threads || 'N/A'} threads
                                </div>
                              )}
                              {nodeInfo.hardware.ram && (
                                <div className="admin-hardware-card hw-ram">
                                  <span className="admin-hardware-label">RAM:</span> {nodeInfo.hardware.ram.total_gb || 'N/A'} GB {nodeInfo.hardware.ram.type || ''}
                                </div>
                              )}
                              {nodeInfo.hardware.gpus && nodeInfo.hardware.gpus.length > 0 && (
                                <div className="admin-hardware-card hw-gpu">
                                  <span className="admin-hardware-label">GPU:</span> {nodeInfo.hardware.gpus[0].count || 'N/A'}x {nodeInfo.hardware.gpus[0].model || 'N/A'}
                                  <br />
                                  {nodeInfo.hardware.gpus[0].memory_gb || 'N/A'} GB
                                  {nodeInfo.hardware.gpus[0].nvlink && ' • NVLink'}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span style={{ color: '#adb5bd', fontSize: '0.8125rem' }}>No hardware info</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'accounts' && clusterConfig.account_labels && Object.keys(clusterConfig.account_labels).length > 0 && (
              <div className="admin-table-container">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Display Name</th>
                      <th>Short Name</th>
                      <th>Faculty</th>
                      <th>Department</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(clusterConfig.account_labels).map(([account, info]) => (
                      <tr key={account}>
                        <td style={{ fontWeight: 600 }}>{account}</td>
                        <td>{info.display_name || 'N/A'}</td>
                        <td>
                          <span className="admin-badge admin-badge-blue">
                            {info.short_name || 'N/A'}
                          </span>
                        </td>
                        <td>{info.faculty || 'N/A'}</td>
                        <td>{info.department || 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'partitions' && clusterConfig.partition_labels && Object.keys(clusterConfig.partition_labels).length > 0 && (
              <div className="admin-table-container">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Partition</th>
                      <th>Display Name</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(clusterConfig.partition_labels).map(([partition, info]) => (
                      <tr key={partition}>
                        <td style={{ fontWeight: 600 }}>{partition}</td>
                        <td>{info.display_name || 'N/A'}</td>
                        <td>{info.description || 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'yaml' && (
              <div className="admin-table-container" style={{ padding: '1.5rem' }}>
                <div style={{ marginBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>✎</span> Edit YAML Configuration
                  </h2>
                  <p style={{ fontSize: '0.875rem', color: '#6c757d' }}>
                    Edit the YAML configuration for <strong>{selectedCluster}</strong> cluster. Changes will be saved to config/clusters.yaml
                  </p>
                </div>

                {yamlError && (
                  <div className="admin-message admin-message-error" style={{ marginBottom: '1rem' }}>
                    <span>⚠️</span>
                    <span>{yamlError}</span>
                    <button onClick={() => setYamlError('')} className="admin-message-close">×</button>
                  </div>
                )}

                <textarea
                  value={yamlContent}
                  onChange={(e) => setYamlContent(e.target.value)}
                  style={{
                    width: '100%',
                    minHeight: '500px',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    padding: '1rem',
                    border: '1px solid #dee2e6',
                    borderRadius: '8px',
                    background: '#f8f9fa',
                    color: 'var(--secondary)',
                    resize: 'vertical',
                  }}
                  spellCheck={false}
                />

                <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem' }}>
                  <button
                    onClick={handleSaveYAML}
                    disabled={saving}
                    className="admin-btn admin-btn-success"
                  >
                    {saving ? 'Saving...' : '⎗ Save Configuration'}
                  </button>
                  <button
                    onClick={() => {
                      loadYAMLContent();
                      setYamlError('');
                    }}
                    className="admin-btn admin-btn-secondary"
                    disabled={saving}
                  >
                    Reset
                  </button>
                  <button
                    onClick={() => setActiveTab('overview')}
                    className="admin-btn admin-btn-secondary"
                    disabled={saving}
                  >
                    Cancel
                  </button>
                </div>

                <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#e7f3ff', border: '1px solid #bee5eb', borderRadius: '8px' }}>
                  <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, marginBottom: '0.5rem', color: '#004085' }}>
                    💡 Tips for editing YAML
                  </h3>
                  <ul style={{ fontSize: '0.8125rem', color: '#004085', marginLeft: '1.5rem', marginBottom: 0 }}>
                    <li>Use 2 spaces for indentation (not tabs)</li>
                    <li>Be careful with YAML syntax - invalid syntax will cause errors</li>
                    <li>A backup is automatically created before saving</li>
                    <li>Changes take effect immediately after saving</li>
                  </ul>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="admin-empty">
            <div className="admin-empty-icon">📋</div>
            <div className="admin-empty-message">
              {selectedCluster ? `No configuration for cluster "${selectedCluster}"` : 'No Configuration Available'}
            </div>
            <p style={{ marginTop: '0.5rem', color: '#6c757d' }}>
              {selectedCluster
                ? 'This cluster has no entry in clusters.yaml. Create a default entry, then upload data or run sync-config on the cluster.'
                : 'Create a configuration file or select a different cluster.'}
            </p>
            {selectedCluster && (
              <button
                onClick={() => handleCreateDefaultConfig(selectedCluster)}
                className="admin-btn admin-btn-primary"
                style={{ marginTop: '1rem' }}
              >
                Create default configuration
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
