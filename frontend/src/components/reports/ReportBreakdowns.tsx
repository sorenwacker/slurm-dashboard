import React from 'react';
import Plot from '../charts/Plot';
import { COLORS, PARTITION_COLORS } from '../../theme/colors';
import { formatNumber, REPORT_AXIS, REPORT_LAYOUT } from './reportHelpers';

interface AccountData {
  account: string;
  jobs: number;
  cpu_hours: number;
  gpu_hours: number;
  users: number;
}

interface PartitionData {
  partition: string;
  jobs: number;
  cpu_hours: number;
  gpu_hours: number;
  users: number;
}

interface StateData {
  state: string;
  jobs: number;
}

interface ReportBreakdownsProps {
  byAccount: AccountData[];
  byPartition: PartitionData[];
  byState: StateData[];
  totalJobs: number;
  totalGpuHours: number;
}

interface TopAccountsCardProps {
  title: string;
  description: string;
  accounts: AccountData[];
  metric: 'cpu_hours' | 'gpu_hours';
  label: string;
  color: string;
}

/** Horizontal bar chart of the ten largest accounts by one metric. */
const TopAccountsCard: React.FC<TopAccountsCardProps> = ({ title, description, accounts, metric, label, color }) => {
  const top = [...accounts].sort((a, b) => b[metric] - a[metric]).slice(0, 10);
  return (
    <div className="report-card page-break-avoid">
      <h3>{title}</h3>
      <p className="report-description">{description}</p>
      <Plot
        data={[
          {
            x: top.map((a) => a[metric]),
            y: top.map((a) => a.account),
            type: 'bar',
            orientation: 'h',
            marker: { color },
            hovertemplate: `<b>%{y}</b><br>${label}: %{x:,.2f}<extra></extra>`,
          },
        ]}
        layout={{
          ...REPORT_LAYOUT,
          height: 300,
          margin: { l: 120, r: 20, t: 10, b: 50 },
          xaxis: { ...REPORT_AXIS, title: { text: label, font: { size: 11 } } },
          yaxis: { ...REPORT_AXIS, autorange: 'reversed' },
        }}
        config={{ displayModeBar: false, staticPlot: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
};

const ReportBreakdowns: React.FC<ReportBreakdownsProps> = ({
  byAccount,
  byPartition,
  byState,
  totalJobs,
  totalGpuHours,
}) => {
  const hasGpu = totalGpuHours > 0;

  return (
    <div className="report-cards">
      {byAccount.length > 0 && (
        <TopAccountsCard
          title="Top 10 Accounts by CPU Usage"
          description="Accounts ranked by total CPU hours consumed during the reporting period."
          accounts={byAccount}
          metric="cpu_hours"
          label="CPU Hours"
          color={COLORS.cpu_hours}
        />
      )}

      {byAccount.length > 0 && hasGpu && (
        <TopAccountsCard
          title="Top 10 Accounts by GPU Usage"
          description="Accounts ranked by total GPU hours consumed during the reporting period."
          accounts={byAccount}
          metric="gpu_hours"
          label="GPU Hours"
          color={COLORS.gpu_hours}
        />
      )}

      {byAccount.length > 0 && (
        <div className="report-card page-break-avoid">
          <h3>Account Resource Usage</h3>
          <p className="report-description">
            Job counts, CPU and GPU hours consumed, and active users per account during the reporting period.
          </p>
          <table className="report-table">
            <thead>
              <tr>
                <th>Account</th>
                <th className="num">Jobs</th>
                <th className="num">CPU Hours</th>
                {hasGpu && <th className="num">GPU Hours</th>}
                <th className="num">Users</th>
              </tr>
            </thead>
            <tbody>
              {byAccount.map((account) => (
                <tr key={account.account}>
                  <td>{account.account}</td>
                  <td className="num">{formatNumber(account.jobs)}</td>
                  <td className="num">{formatNumber(Math.round(account.cpu_hours))}</td>
                  {hasGpu && <td className="num">{formatNumber(Math.round(account.gpu_hours))}</td>}
                  <td className="num">{account.users}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {byState.length > 0 && (
        <div className="report-card page-break-avoid">
          <h3>Job Completion Status</h3>
          <p className="report-description">
            Jobs by final state: COMPLETED (successful), FAILED (errors), CANCELLED (user-terminated), and TIMEOUT
            (exceeded time limit).
          </p>
          <Plot
            data={[
              {
                x: byState.map((s) => s.state),
                y: byState.map((s) => s.jobs),
                type: 'bar',
                marker: { color: COLORS.total_jobs },
                hovertemplate: '<b>%{x}</b><br>Jobs: %{y:,.0f}<extra></extra>',
              },
            ]}
            layout={{
              ...REPORT_LAYOUT,
              height: 250,
              margin: { l: 60, r: 20, t: 10, b: 70 },
              xaxis: { ...REPORT_AXIS, title: { text: 'Job State', font: { size: 11 } }, tickangle: -45 },
              yaxis: { ...REPORT_AXIS, title: { text: 'Number of Jobs', font: { size: 11 } } },
            }}
            config={{ displayModeBar: false, staticPlot: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {byPartition.length > 0 && (
        <div className="report-card page-break-avoid">
          <h3>Job Distribution by Partition</h3>
          <p className="report-description">
            Share of jobs per cluster partition. Partitions are hardware configurations or resource pools for specific
            workload types.
          </p>
          <Plot
            data={[
              {
                labels: byPartition.map((p) => p.partition),
                values: byPartition.map((p) => p.jobs),
                type: 'pie',
                marker: { colors: PARTITION_COLORS },
                textinfo: 'label+percent',
                textfont: { size: 10 },
                hovertemplate: '<b>%{label}</b><br>Jobs: %{value:,.0f} (%{percent})<extra></extra>',
              },
            ]}
            layout={{
              ...REPORT_LAYOUT,
              height: 280,
              margin: { l: 10, r: 10, t: 10, b: 10 },
              showlegend: false,
            }}
            config={{ displayModeBar: false, staticPlot: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {byPartition.length > 0 && (
        <div className="report-card page-break-avoid">
          <h3>Partition Resource Usage</h3>
          <p className="report-description">
            Job distribution, resource consumption, and active users per partition.
          </p>
          <table className="report-table">
            <thead>
              <tr>
                <th>Partition</th>
                <th className="num">Jobs</th>
                <th className="num">% of Total</th>
                <th className="num">CPU Hours</th>
                {hasGpu && <th className="num">GPU Hours</th>}
                <th className="num">Users</th>
              </tr>
            </thead>
            <tbody>
              {byPartition.map((partition) => (
                <tr key={partition.partition}>
                  <td>{partition.partition}</td>
                  <td className="num">{formatNumber(partition.jobs)}</td>
                  <td className="num">{((partition.jobs / totalJobs) * 100).toFixed(1)}%</td>
                  <td className="num">{formatNumber(Math.round(partition.cpu_hours))}</td>
                  {hasGpu && <td className="num">{formatNumber(Math.round(partition.gpu_hours))}</td>}
                  <td className="num">{partition.users}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ReportBreakdowns;
