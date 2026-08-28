import { useState } from 'react';
import { adminClient, type Cluster } from '../../api/adminClient';

const AGENT_PACKAGE = 'slurm-dashboard[agent]';
const AGENT_REPO = 'https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git';
const INSTALL_COMMANDS = [
  { label: 'uv', install: `uv tool install --python 3.12 '${AGENT_PACKAGE} @ git+${AGENT_REPO}'` },
  { label: 'pip', install: `pip install 'git+${AGENT_REPO}#egg=${AGENT_PACKAGE}'` },
];

interface CredentialsPanelProps {
  cluster: Cluster;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
}

function formatDate(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : 'never';
}

function deployKeyState(cluster: Cluster): { label: string; className: string } {
  if (!cluster.deploy_key_created) return { label: 'none', className: 'cp-badge' };
  if (cluster.deploy_key_used) return { label: 'used', className: 'cp-badge cp-badge-info' };
  if (cluster.deploy_key_expires_at && new Date() > new Date(cluster.deploy_key_expires_at)) {
    return { label: 'expired', className: 'cp-badge cp-badge-danger' };
  }
  return { label: 'valid', className: 'cp-badge cp-badge-ok' };
}

export function CredentialsPanel({ cluster, onChanged, onError }: CredentialsPanelProps) {
  const [busy, setBusy] = useState(false);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [newDeployKey, setNewDeployKey] = useState<string | null>(null);
  const [copied, setCopied] = useState('');

  const copy = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(label);
    window.setTimeout(() => setCopied(''), 1500);
  };

  const rotate = async () => {
    if (!window.confirm('Rotate the API key? The current key stops working immediately.')) return;
    setBusy(true);
    try {
      const result = await adminClient.rotateAPIKey(cluster.id);
      setNewApiKey(result.new_api_key);
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to rotate API key');
    } finally {
      setBusy(false);
    }
  };

  const generateDeployKey = async () => {
    setBusy(true);
    try {
      const result = await adminClient.generateDeployKey(cluster.id);
      setNewDeployKey(result.deploy_key);
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to generate deploy key');
    } finally {
      setBusy(false);
    }
  };

  const deploy = deployKeyState(cluster);

  return (
    <section className="cp-card">
      <h3>Credentials</h3>
      <dl className="cp-dl">
        <dt>API key</dt>
        <dd>
          {newApiKey ? (
            <>
              <code className="cp-code">{newApiKey}</code>
              <button type="button" className="cp-btn cp-btn-small" onClick={() => copy(newApiKey, 'api')}>
                {copied === 'api' ? 'Copied' : 'Copy'}
              </button>
              <div className="cp-inline-error">Shown once. Copy it now; it cannot be displayed again.</div>
            </>
          ) : (
            <>
              <code className="cp-code">{cluster.api_key_prefix}…</code>
              <span className="cp-muted">prefix; the key is stored hashed and can only be replaced</span>
            </>
          )}
          <div>
            <button type="button" className="cp-btn cp-btn-small cp-btn-danger" onClick={rotate} disabled={busy}>
              Rotate
            </button>
          </div>
          <div className="cp-muted">Created {formatDate(cluster.api_key_created)}</div>
        </dd>
        <dt>Deploy key</dt>
        <dd>
          <span className={deploy.className}>{deploy.label}</span>
          {cluster.deploy_key_created && (
            <span className="cp-muted">
              {' '}created {formatDate(cluster.deploy_key_created)}
              {deploy.label === 'valid' && `, expires ${formatDate(cluster.deploy_key_expires_at)}`}
              {deploy.label === 'used' && `, used ${formatDate(cluster.deploy_key_used_at)}`}
              {deploy.label === 'used' && cluster.deploy_key_used_from_ip && ` from ${cluster.deploy_key_used_from_ip}`}
            </span>
          )}
          <div>
            <button type="button" className="cp-btn cp-btn-small" onClick={generateDeployKey} disabled={busy}>
              Generate new deploy key
            </button>
          </div>
          <div className="cp-muted">One-time key for the agent setup; expires after 7 days.</div>
        </dd>
      </dl>

      {newDeployKey && (
        <div className="cp-install">
          <h4>Install and set up the agent on the cluster</h4>
          {INSTALL_COMMANDS.map(({ label, install }) => {
            const command = `${install} && slurm-dashboard setup --api-url ${window.location.origin} --deploy-key ${newDeployKey}`;
            return (
              <div key={label} className="cp-install-block">
                <div className="cp-install-label">
                  <span>{label}</span>
                  <button type="button" className="cp-btn cp-btn-small" onClick={() => copy(command, label)}>
                    {copied === label ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <pre>{command}</pre>
              </div>
            );
          })}
          <p className="cp-muted">Then run <code>slurm-dashboard sync-config --config config.json</code> to upload the cluster configuration.</p>
        </div>
      )}
    </section>
  );
}
