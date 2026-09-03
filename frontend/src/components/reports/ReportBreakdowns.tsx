import React from 'react';
import Plot from '../charts/Plot';
import { COLORS, PARTITION_COLORS } from '../../theme/colors';
import { formatNumber } from './reportHelpers';

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

const ReportBreakdowns: React.FC<ReportBreakdownsProps> = ({
  byAccount,
  byPartition,
  byState,
  totalJobs,
  totalGpuHours
}) => {
  return (
    <>
      {/* Charts Section */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {/* CPU Hours by Account */}
        {byAccount.length > 0 && (
          <div className="page-break-avoid" style={{
            background: 'var(--report-card-bg)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--report-border)',
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
              Top 10 Accounts by CPU Usage
            </h3>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
              This chart shows the top 10 accounts ranked by total CPU hours consumed during the reporting period.
              CPU hours represent the computational resources used for job execution.
            </p>
            <Plot
              data={[{
                x: byAccount.slice(0, 10).map(a => a.cpu_hours),
                y: byAccount.slice(0, 10).map(a => a.account),
                type: 'bar',
                orientation: 'h',
                marker: { color: COLORS.cpu_hours },
                hovertemplate: '<b>%{y}</b><br>CPU Hours: %{x:,.2f}<extra></extra>',
              }]}
              layout={{
                height: 300,
                margin: { l: 120, r: 20, t: 10, b: 50 },
                xaxis: {
                  title: { text: 'CPU Hours', font: { size: 11 } },
                  gridcolor: '#e0e0e0',
                  tickfont: { size: 10 }
                },
                yaxis: {
                  autorange: 'reversed',
                  gridcolor: '#e0e0e0',
                  tickfont: { size: 10 }
                },
                plot_bgcolor: '#fafafa',
                paper_bgcolor: 'white',
                font: { color: '#000', family: 'Arial, sans-serif' },
              }}
              config={{ displayModeBar: false, staticPlot: true }}
              style={{ width: '100%' }}
            />
          </div>
        )}

        {/* GPU Hours by Account */}
        {byAccount.length > 0 && totalGpuHours > 0 && (
          <div className="page-break-avoid" style={{
            background: 'var(--report-card-bg)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--report-border)',
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
              Top 10 Accounts by GPU Usage
            </h3>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
              This chart displays the top 10 accounts by GPU hours utilized. GPU hours measure accelerated computing resources
              used for machine learning, scientific simulations, and other GPU-intensive workloads.
            </p>
            <Plot
              data={[{
                x: [...byAccount].sort((a, b) => b.gpu_hours - a.gpu_hours).slice(0, 10).map(a => a.gpu_hours),
                y: [...byAccount].sort((a, b) => b.gpu_hours - a.gpu_hours).slice(0, 10).map(a => a.account),
                type: 'bar',
                orientation: 'h',
                marker: { color: COLORS.gpu_hours },
                hovertemplate: '<b>%{y}</b><br>GPU Hours: %{x:,.2f}<extra></extra>',
              }]}
              layout={{
                height: 300,
                margin: { l: 120, r: 20, t: 10, b: 50 },
                xaxis: {
                  title: { text: 'GPU Hours', font: { size: 11 } },
                  gridcolor: '#e0e0e0',
                  tickfont: { size: 10 }
                },
                yaxis: {
                  autorange: 'reversed',
                  gridcolor: '#e0e0e0',
                  tickfont: { size: 10 }
                },
                plot_bgcolor: '#fafafa',
                paper_bgcolor: 'white',
                font: { color: '#000', family: 'Arial, sans-serif' },
              }}
              config={{ displayModeBar: false, staticPlot: true }}
              style={{ width: '100%' }}
            />
          </div>
        )}

        {/* Complete Account Usage Table - moved here to group with account charts */}
        {byAccount.length > 0 && (
          <div className="page-break-avoid" style={{
            background: 'var(--report-card-bg)',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid var(--report-border)',
            marginTop: '1.5rem',
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
              Account Resource Usage
            </h3>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
              Comprehensive breakdown of all account usage during the reporting period, showing job counts, CPU/GPU hours consumed, and active users per account.
            </p>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: '#000' }}>Account</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Jobs</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>CPU Hours</th>
                  {totalGpuHours > 0 && (
                    <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>GPU Hours</th>
                  )}
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Users</th>
                </tr>
              </thead>
              <tbody>
                {byAccount.map((account) => (
                  <tr key={account.account} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '0.5rem', fontWeight: 500 }}>{account.account}</td>
                    <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatNumber(account.jobs)}</td>
                    <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatNumber(Math.round(account.cpu_hours))}</td>
                    {totalGpuHours > 0 && (
                      <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatNumber(Math.round(account.gpu_hours))}</td>
                    )}
                    <td style={{ textAlign: 'right', padding: '0.5rem' }}>{account.users}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Jobs by State */}
        {byState.length > 0 && (
          <div className="page-break-avoid" style={{
            background: 'var(--report-card-bg)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--report-border)',
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
              Job Completion Status
            </h3>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
              Breakdown of jobs by their final execution state. Common states include COMPLETED (successful), FAILED (errors),
              CANCELLED (user-terminated), and TIMEOUT (exceeded time limit).
            </p>
            <Plot
              data={[{
                x: byState.map(s => s.state),
                y: byState.map(s => s.jobs),
                type: 'bar',
                marker: { color: COLORS.total_jobs },
                hovertemplate: '<b>%{x}</b><br>Jobs: %{y:,.0f}<extra></extra>',
              }]}
              layout={{
                height: 250,
                margin: { l: 60, r: 20, t: 10, b: 70 },
                xaxis: {
                  title: { text: 'Job State', font: { size: 11 } },
                  gridcolor: '#e0e0e0',
                  tickfont: { size: 10 },
                  tickangle: -45
                },
                yaxis: {
                  title: { text: 'Number of Jobs', font: { size: 11 } },
                  gridcolor: '#e0e0e0',
                  tickfont: { size: 10 }
                },
                plot_bgcolor: '#fafafa',
                paper_bgcolor: 'white',
                font: { color: '#000', family: 'Arial, sans-serif' },
              }}
              config={{ displayModeBar: false, staticPlot: true }}
              style={{ width: '100%' }}
            />
          </div>
        )}
      </div>

      {/* Jobs by Partition (Pie Chart) - moved here to group with partition table */}
      {byPartition.length > 0 && (
        <div className="page-break-avoid" style={{
          background: 'var(--report-card-bg)',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
            Job Distribution by Partition
          </h3>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
            Distribution of jobs across different cluster partitions. Partitions represent different hardware configurations
            or resource pools optimized for specific workload types.
          </p>
          <Plot
            data={[{
              labels: byPartition.map(p => p.partition),
              values: byPartition.map(p => p.jobs),
              type: 'pie',
              marker: {
                colors: PARTITION_COLORS,
              },
              textinfo: 'label+percent',
              textfont: { size: 10 },
              hovertemplate: '<b>%{label}</b><br>Jobs: %{value:,.0f} (%{percent})<extra></extra>',
            }]}
            layout={{
              height: 280,
              margin: { l: 10, r: 10, t: 10, b: 10 },
              plot_bgcolor: 'white',
              paper_bgcolor: 'white',
              font: { color: '#000', family: 'Arial, sans-serif', size: 10 },
              showlegend: false,
            }}
            config={{ displayModeBar: false, staticPlot: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* Partition Resource Usage - moved here to follow partition chart */}
      {byPartition && byPartition.length > 0 && (
        <div className="page-break-avoid" style={{
          background: 'var(--report-card-bg)',
          padding: '1.5rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
          marginBottom: '2rem',
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
            Partition Resource Usage
          </h3>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
            Comprehensive breakdown of job distribution and resource consumption across different cluster partitions, including user engagement per partition.
          </p>
          <div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: '#000' }}>Partition</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Jobs</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>% of Total</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>CPU Hours</th>
                  {totalGpuHours > 0 && (
                    <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>GPU Hours</th>
                  )}
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Users</th>
                </tr>
              </thead>
              <tbody>
                {byPartition.map((partition) => (
                  <tr key={partition.partition} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '0.5rem', fontWeight: 500 }}>{partition.partition}</td>
                    <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatNumber(partition.jobs)}</td>
                    <td style={{ textAlign: 'right', padding: '0.5rem' }}>
                      {((partition.jobs / totalJobs) * 100).toFixed(1)}%
                    </td>
                    <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatNumber(Math.round(partition.cpu_hours))}</td>
                    {totalGpuHours > 0 && (
                      <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatNumber(Math.round(partition.gpu_hours))}</td>
                    )}
                    <td style={{ textAlign: 'right', padding: '0.5rem' }}>{partition.users}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
};

export default ReportBreakdowns;
