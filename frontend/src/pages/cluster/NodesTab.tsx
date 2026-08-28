import { useMemo, useState } from 'react';
import { clusterAdminApi } from '../../api/clusterAdminApi';
import { EditableCell } from './EditableCell';
import { NODE_TYPES, filterNodeRows, partitionsOf, toNodeRows, type NodeFilter } from './nodeRows';
import type { NodeEntry } from './types';

interface NodesTabProps {
  cluster: string;
  nodes: Record<string, NodeEntry>;
  onChanged: () => Promise<void>;
}

export function NodesTab({ cluster, nodes, onChanged }: NodesTabProps) {
  const [filter, setFilter] = useState<NodeFilter>({ search: '', type: 'all', partition: 'all', dataOnly: false });
  const rows = useMemo(() => toNodeRows(nodes), [nodes]);
  const visible = useMemo(() => filterNodeRows(rows, filter), [rows, filter]);
  const partitions = useMemo(() => partitionsOf(rows), [rows]);

  const save = (node: string, changes: Pick<NodeEntry, 'synonyms' | 'description' | 'type'>) => async () => {
    await clusterAdminApi.updateNode(cluster, node, changes);
    await onChanged();
  };

  return (
    <div>
      <div className="cp-toolbar">
        <input
          type="search"
          placeholder="Search name, synonym, description"
          value={filter.search}
          onChange={(e) => setFilter({ ...filter, search: e.target.value })}
        />
        <select value={filter.type} onChange={(e) => setFilter({ ...filter, type: e.target.value })}>
          <option value="all">All types</option>
          {NODE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={filter.partition} onChange={(e) => setFilter({ ...filter, partition: e.target.value })}>
          <option value="all">All partitions</option>
          {partitions.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <label className="cp-check">
          <input type="checkbox" checked={filter.dataOnly} onChange={(e) => setFilter({ ...filter, dataOnly: e.target.checked })} />
          Not reported by SLURM
        </label>
        <span className="cp-muted">{visible.length} of {rows.length} nodes</span>
      </div>

      <div className="cp-table-wrap">
        <table className="cp-table">
          <thead>
            <tr>
              <th>Node</th>
              <th>Type</th>
              <th className="cp-num">CPUs</th>
              <th className="cp-num">Memory (GB)</th>
              <th>GPUs</th>
              <th>Partitions</th>
              <th>Features</th>
              <th>Source</th>
              <th>Synonyms</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.name}>
                <td className="cp-strong">{row.name}</td>
                <td>
                  <EditableCell
                    value={row.entry.type ?? ''}
                    options={NODE_TYPES}
                    onSave={(value) => save(row.name, { type: value })()}
                  />
                </td>
                <td className="cp-num">{row.cpus || ''}</td>
                <td className="cp-num">{row.memoryGb || ''}</td>
                <td>{row.gpus}</td>
                <td>{(row.entry.partitions ?? []).join(', ')}</td>
                <td className="cp-muted">{(row.entry.features ?? []).join(', ')}</td>
                <td>
                  <span className={row.source === 'slurm' ? 'cp-badge cp-badge-ok' : 'cp-badge cp-badge-warn'}>
                    {row.source === 'slurm' ? 'SLURM' : 'job data'}
                  </span>
                </td>
                <td>
                  <EditableCell
                    value={(row.entry.synonyms ?? []).join(', ')}
                    placeholder="comma-separated"
                    onSave={(value) =>
                      save(row.name, { synonyms: value.split(',').map((s) => s.trim()).filter(Boolean) })()
                    }
                  />
                </td>
                <td>
                  <EditableCell value={row.entry.description ?? ''} onSave={(value) => save(row.name, { description: value })()} />
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr><td colSpan={10} className="cp-empty">No nodes match.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
