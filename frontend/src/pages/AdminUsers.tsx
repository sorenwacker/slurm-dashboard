import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminClient } from '../api/adminClient';
import { AdminLayout } from '../components/AdminLayout';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

interface EmailListProps {
  title: string;
  description: string;
  emails: string[];
  onChange: (emails: string[]) => void;
}

function EmailList({ title, description, emails, onChange }: EmailListProps) {
  const [draft, setDraft] = useState('');

  const add = () => {
    const email = draft.trim();
    if (email && !emails.includes(email)) {
      onChange([...emails, email]);
      setDraft('');
    }
  };

  return (
    <section className="cp-card">
      <h3>{title}</h3>
      <p className="cp-muted">{description}</p>
      <div className="cp-inline-form">
        <input
          type="email"
          placeholder="email@example.com"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              add();
            }
          }}
        />
        <button type="button" className="cp-btn" onClick={add}>
          Add
        </button>
      </div>
      {emails.length > 0 ? (
        <div className="cp-chips">
          {emails.map((email) => (
            <span key={email} className="cp-chip">
              {email}
              <button type="button" title="Remove" onClick={() => onChange(emails.filter((e) => e !== email))}>
                ×
              </button>
            </span>
          ))}
        </div>
      ) : (
        <p className="cp-muted">None configured</p>
      )}
    </section>
  );
}

export function AdminUsers() {
  const [adminEmails, setAdminEmails] = useState<string[]>([]);
  const [superadminEmails, setSuperadminEmails] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const loadEmails = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/admin-emails`, {
        headers: adminClient.authHeaders(),
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
  }, []);

  useEffect(() => {
    if (!adminClient.isAuthenticated()) {
      navigate('/admin/login');
      return;
    }

    loadEmails();
  }, [navigate, loadEmails]);

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/admin-emails`, {
        method: 'POST',
        headers: { ...adminClient.authHeaders(), 'Content-Type': 'application/json' },
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

      setSuccess('Admin emails updated. Restart the backend for the change to take effect.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update admin emails');
    } finally {
      setSaving(false);
    }
  };

  return (
    <AdminLayout title="Admin Users" subtitle="Manage admin and superadmin access by SAML email address">
      {error && (
        <div className="cp-message cp-message-error">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')}>Dismiss</button>
        </div>
      )}
      {success && (
        <div className="cp-message cp-message-ok">
          <span>{success}</span>
          <button type="button" onClick={() => setSuccess('')}>Dismiss</button>
        </div>
      )}

      <section className="cp-card cp-card-info">
        <h3>About admin access</h3>
        <ul>
          <li><strong>Admin</strong>: can manage clusters, view all data, and generate reports</li>
          <li><strong>Superadmin</strong>: full access including cluster creation, deletion, and API key rotation</li>
          <li>Users authenticate through SAML and receive permissions based on their email address</li>
          <li>Changes take effect after a backend restart: <code>sudo systemctl restart slurm-usage-backend</code></li>
        </ul>
      </section>

      {loading ? (
        <p className="cp-muted">Loading</p>
      ) : (
        <>
          <EmailList
            title="Superadmin emails"
            description="Users with these email addresses have full administrative access"
            emails={superadminEmails}
            onChange={setSuperadminEmails}
          />
          <EmailList
            title="Admin emails"
            description="Users with these email addresses have standard administrative access"
            emails={adminEmails}
            onChange={setAdminEmails}
          />
          <div className="cp-actions">
            <button type="button" className="cp-btn cp-btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save changes'}
            </button>
            <button type="button" className="cp-btn" onClick={loadEmails} disabled={saving}>
              Reset
            </button>
          </div>
        </>
      )}
    </AdminLayout>
  );
}
