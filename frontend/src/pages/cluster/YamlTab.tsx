import { useEffect, useState } from 'react';
import * as yaml from 'js-yaml';
import { clusterAdminApi } from '../../api/clusterAdminApi';
import type { ClusterEntry } from './types';

interface YamlTabProps {
  cluster: string;
  entry: ClusterEntry;
  onChanged: () => Promise<void>;
}

export function YamlTab({ cluster, entry, onChanged }: YamlTabProps) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setText(yaml.dump(entry, { indent: 2, lineWidth: -1 }));
  }, [entry]);

  const save = async () => {
    setError('');
    let parsed: unknown;
    try {
      parsed = yaml.load(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid YAML');
      return;
    }
    if (!parsed || typeof parsed !== 'object') {
      setError('The document must be a mapping.');
      return;
    }
    setSaving(true);
    try {
      await clusterAdminApi.replaceConfig(cluster, parsed as ClusterEntry);
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const download = () => {
    const blob = new Blob([text], { type: 'text/yaml' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${cluster}-${new Date().toISOString().slice(0, 10)}.yaml`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <div>
      <p className="cp-muted">
        Raw entry of this cluster in clusters.yaml. Use the other tabs for labels; edit here for anything they do not cover.
        Values under hardware, partitions, features and slurm are overwritten by the next sync-config run.
      </p>
      <textarea className="cp-yaml" value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} />
      {error && <div className="cp-inline-error">{error}</div>}
      <div className="cp-actions">
        <button type="button" className="cp-btn cp-btn-primary" onClick={save} disabled={saving}>
          {saving ? 'Saving' : 'Save'}
        </button>
        <button type="button" className="cp-btn" onClick={download}>Export</button>
      </div>
    </div>
  );
}
