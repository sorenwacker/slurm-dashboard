import { useEffect, useState } from 'react';

interface EditableCellProps {
  value: string;
  placeholder?: string;
  options?: readonly string[];
  onSave: (value: string) => Promise<void>;
}

/** Text shown as-is; click to edit in place. Enter or Save commits, Escape cancels. */
export function EditableCell({ value, placeholder = '', options, onSave }: EditableCellProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!editing) setDraft(value);
  }, [value, editing]);

  const commit = async () => {
    if (draft === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSave(draft);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <button type="button" className="cp-editable" onClick={() => setEditing(true)} title="Click to edit">
        {value || <span className="cp-placeholder">{placeholder || 'Add'}</span>}
      </button>
    );
  }

  return (
    <span className="cp-editable-form">
      {options ? (
        <select value={draft} onChange={(e) => setDraft(e.target.value)} disabled={saving} autoFocus>
          {options.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      ) : (
        <input
          value={draft}
          placeholder={placeholder}
          disabled={saving}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') setEditing(false);
          }}
        />
      )}
      <button type="button" className="cp-btn cp-btn-small" onClick={commit} disabled={saving}>
        {saving ? 'Saving' : 'Save'}
      </button>
      <button type="button" className="cp-btn cp-btn-small cp-btn-quiet" onClick={() => setEditing(false)} disabled={saving}>
        Cancel
      </button>
      {error && <span className="cp-inline-error">{error}</span>}
    </span>
  );
}
