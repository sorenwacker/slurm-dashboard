import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminClient } from '../api/adminClient';
import './AdminUsers.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

export function AdminUsers() {
  const [adminEmails, setAdminEmails] = useState<string[]>([]);
  const [superadminEmails, setSuperadminEmails] = useState<string[]>([]);
  const [newAdminEmail, setNewAdminEmail] = useState('');
  const [newSuperadminEmail, setNewSuperadminEmail] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

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

    loadEmails();
  }, [navigate]);

  const loadEmails = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/admin-emails`, {
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to load admin emails');
      const data = await response.json();
      setAdminEmails(data.admin_emails || []);
      setSuperadminEmails(data.superadmin_emails || []);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load admin emails');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/admin-emails`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify({
          admin_emails: adminEmails,
          superadmin_emails: superadminEmails,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update admin emails');
      }

      setSuccess('Admin emails updated successfully! Restart the backend for changes to take effect.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update admin emails');
    } finally {
      setSaving(false);
    }
  };

  const handleAddAdminEmail = () => {
    if (newAdminEmail && !adminEmails.includes(newAdminEmail)) {
      setAdminEmails([...adminEmails, newAdminEmail]);
      setNewAdminEmail('');
    }
  };

  const handleAddSuperadminEmail = () => {
    if (newSuperadminEmail && !superadminEmails.includes(newSuperadminEmail)) {
      setSuperadminEmails([...superadminEmails, newSuperadminEmail]);
      setNewSuperadminEmail('');
    }
  };

  const handleRemoveAdminEmail = (email: string) => {
    setAdminEmails(adminEmails.filter(e => e !== email));
  };

  const handleRemoveSuperadminEmail = (email: string) => {
    setSuperadminEmails(superadminEmails.filter(e => e !== email));
  };

  const handleLogout = () => {
    adminClient.logout();
    navigate('/admin/login');
  };

  if (loading) {
    return (
      <div className="admin-config">
        <div className="admin-loading">
          <div className="admin-loading-spinner"></div>
          <p>Loading admin users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-config">
      {/* Header */}
      <div className="admin-header">
        <div className="admin-header-content">
          <div className="admin-header-title">
            <div>
              <h1>
                Admin Users
              </h1>
              <p className="admin-header-subtitle">Manage admin and superadmin access via SAML email addresses</p>
            </div>
          </div>
          <div className="admin-header-nav">
            <a href="/">Dashboard</a>
            <a href="/admin/clusters">Clusters</a>
            <a href="/admin/config">Configuration</a>
            <button onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </div>

      <div className="admin-container">
        {/* Messages */}
        {error && (
          <div className="admin-message admin-message-error">
            <span>{error}</span>
            <button onClick={() => setError('')} className="admin-message-close">×</button>
          </div>
        )}

        {success && (
          <div className="admin-message admin-message-success">
            <span>{success}</span>
            <button onClick={() => setSuccess('')} className="admin-message-close">×</button>
          </div>
        )}

        {/* Info Card */}
        <div style={{ background: 'linear-gradient(to right, #e7f3ff, #e7d6ff)', padding: '1.5rem', borderRadius: '8px', border: '1px solid #bee5eb', marginBottom: '2rem' }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>ℹ️</span> About Admin Access
          </h3>
          <ul style={{ fontSize: '0.875rem', marginLeft: '1.5rem', marginBottom: 0, color: '#004085' }}>
            <li><strong>Admin</strong>: Can manage clusters, view all data, and generate reports</li>
            <li><strong>Superadmin</strong>: Full access including cluster creation/deletion and API key rotation</li>
            <li>Users authenticate via SAML (TU Delft SSO) and receive permissions based on their email</li>
            <li>Changes require backend restart to take effect: <code style={{ background: '#d1ecf1', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>sudo systemctl restart slurm-usage-backend</code></li>
          </ul>
        </div>

        {/* Superadmin Emails */}
        <div className="admin-table-container" style={{ marginBottom: '2rem' }}>
          <div style={{ padding: '1.5rem', borderBottom: '1px solid #dee2e6' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              Superadmin Emails
            </h2>
            <p style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '1rem' }}>
              Users with these email addresses have full administrative access
            </p>

            {/* Add new email */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <input
                type="email"
                placeholder="email@example.com"
                value={newSuperadminEmail}
                onChange={(e) => setNewSuperadminEmail(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddSuperadminEmail()}
                style={{
                  flex: 1,
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #dee2e6',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                }}
              />
              <button
                onClick={handleAddSuperadminEmail}
                className="admin-btn admin-btn-success"
                style={{ padding: '0.5rem 1rem' }}
              >
                + Add
              </button>
            </div>

            {/* Email list */}
            {superadminEmails.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {superadminEmails.map((email) => (
                  <div
                    key={email}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.5rem 0.75rem',
                      background: '#f8f9fa',
                      border: '1px solid #dee2e6',
                      borderRadius: '4px',
                      fontSize: '0.875rem',
                    }}
                  >
                    <span>{email}</span>
                    <button
                      onClick={() => handleRemoveSuperadminEmail(email)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#dc3545',
                        cursor: 'pointer',
                        padding: '0',
                        fontSize: '1.25rem',
                        lineHeight: 1,
                      }}
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.875rem', color: '#6c757d', fontStyle: 'italic' }}>
                No superadmin emails configured
              </p>
            )}
          </div>
        </div>

        {/* Admin Emails */}
        <div className="admin-table-container" style={{ marginBottom: '2rem' }}>
          <div style={{ padding: '1.5rem', borderBottom: '1px solid #dee2e6' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              Admin Emails
            </h2>
            <p style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '1rem' }}>
              Users with these email addresses have standard administrative access
            </p>

            {/* Add new email */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <input
                type="email"
                placeholder="email@example.com"
                value={newAdminEmail}
                onChange={(e) => setNewAdminEmail(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddAdminEmail()}
                style={{
                  flex: 1,
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #dee2e6',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                }}
              />
              <button
                onClick={handleAddAdminEmail}
                className="admin-btn admin-btn-success"
                style={{ padding: '0.5rem 1rem' }}
              >
                + Add
              </button>
            </div>

            {/* Email list */}
            {adminEmails.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {adminEmails.map((email) => (
                  <div
                    key={email}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.5rem 0.75rem',
                      background: '#f8f9fa',
                      border: '1px solid #dee2e6',
                      borderRadius: '4px',
                      fontSize: '0.875rem',
                    }}
                  >
                    <span>{email}</span>
                    <button
                      onClick={() => handleRemoveAdminEmail(email)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#dc3545',
                        cursor: 'pointer',
                        padding: '0',
                        fontSize: '1.25rem',
                        lineHeight: 1,
                      }}
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.875rem', color: '#6c757d', fontStyle: 'italic' }}>
                No admin emails configured
              </p>
            )}
          </div>
        </div>

        {/* Save Button */}
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={handleSave}
            disabled={saving}
            className="admin-btn admin-btn-primary"
            style={{ padding: '0.75rem 1.5rem' }}
          >
            {saving ? 'Saving...' : '⎗ Save Changes'}
          </button>
          <button
            onClick={loadEmails}
            disabled={saving}
            className="admin-btn admin-btn-secondary"
            style={{ padding: '0.75rem 1.5rem' }}
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}
