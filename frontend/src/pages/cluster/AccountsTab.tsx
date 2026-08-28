import { clusterAdminApi } from '../../api/clusterAdminApi';
import { EditableCell } from './EditableCell';
import type { AccountEntry } from './types';

interface AccountsTabProps {
  cluster: string;
  accounts: Record<string, AccountEntry>;
  onChanged: () => Promise<void>;
}

const LABEL_FIELDS: { key: keyof Omit<AccountEntry, 'slurm'>; label: string }[] = [
  { key: 'display_name', label: 'Display name' },
  { key: 'short_name', label: 'Short name' },
  { key: 'faculty', label: 'Faculty' },
  { key: 'department', label: 'Department' },
];

export function AccountsTab({ cluster, accounts, onChanged }: AccountsTabProps) {
  const names = Object.keys(accounts).sort();
  const save = (account: string, field: keyof Omit<AccountEntry, 'slurm'>) => async (value: string) => {
    await clusterAdminApi.updateAccount(cluster, account, { [field]: value });
    await onChanged();
  };

  return (
    <div className="cp-table-wrap">
      <table className="cp-table">
        <thead>
          <tr>
            <th>Account</th>
            <th>SLURM description</th>
            <th>Organization</th>
            {LABEL_FIELDS.map(({ key, label }) => <th key={key}>{label}</th>)}
          </tr>
        </thead>
        <tbody>
          {names.map((name) => {
            const entry = accounts[name];
            return (
              <tr key={name}>
                <td className="cp-strong">{name}</td>
                <td>{entry.slurm?.description ?? ''}</td>
                <td>{entry.slurm?.organization ?? ''}</td>
                {LABEL_FIELDS.map(({ key }) => (
                  <td key={key}><EditableCell value={entry[key] ?? ''} onSave={save(name, key)} /></td>
                ))}
              </tr>
            );
          })}
          {names.length === 0 && (
            <tr><td colSpan={3 + LABEL_FIELDS.length} className="cp-empty">No accounts. Run sync-config on the cluster.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
