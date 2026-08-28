import { clusterAdminApi } from '../../api/clusterAdminApi';
import { EditableCell } from './EditableCell';
import type { PartitionEntry } from './types';

interface PartitionsTabProps {
  cluster: string;
  partitions: Record<string, PartitionEntry>;
  onChanged: () => Promise<void>;
}

export function PartitionsTab({ cluster, partitions, onChanged }: PartitionsTabProps) {
  const names = Object.keys(partitions).sort();
  const save = (partition: string, field: 'display_name' | 'description') => async (value: string) => {
    await clusterAdminApi.updatePartition(cluster, partition, { [field]: value });
    await onChanged();
  };

  return (
    <div className="cp-table-wrap">
      <table className="cp-table">
        <thead>
          <tr>
            <th>Partition</th>
            <th className="cp-num">Nodes</th>
            <th className="cp-num">CPUs</th>
            <th>Max time</th>
            <th>State</th>
            <th>Display name</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {names.map((name) => {
            const entry = partitions[name];
            const facts = entry.slurm;
            return (
              <tr key={name}>
                <td className="cp-strong">
                  {name}
                  {facts?.default && <span className="cp-badge cp-badge-info cp-badge-inline">default</span>}
                </td>
                <td className="cp-num" title={facts?.nodes}>{facts?.total_nodes ?? ''}</td>
                <td className="cp-num">{facts?.total_cpus ?? ''}</td>
                <td>{facts?.max_time ?? ''}</td>
                <td>{facts?.state ?? ''}</td>
                <td><EditableCell value={entry.display_name ?? ''} onSave={save(name, 'display_name')} /></td>
                <td><EditableCell value={entry.description ?? ''} onSave={save(name, 'description')} /></td>
              </tr>
            );
          })}
          {names.length === 0 && (
            <tr><td colSpan={7} className="cp-empty">No partitions. Run sync-config on the cluster.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
