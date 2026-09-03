import React from 'react';
import Plot from '../charts/Plot';
import { COLORS } from '../../theme/colors';
import { formatHours } from './reportHelpers';

interface JobDurationStats {
  mean: number;
  median: number;
  p25: number;
  p75: number;
  p90: number;
  min: number;
  max: number;
}

interface WaitingTimeStats {
  mean: number;
  median: number;
  p25: number;
  p75: number;
  p90: number;
  min: number;
  max: number;
}

interface TimelineData {
  date: string;
  jobs: number;
  cpu_hours: number;
  gpu_hours: number;
  users: number;
}

interface ReportDistributionsProps {
  jobDurationStats?: JobDurationStats;
  waitingTimeStats?: WaitingTimeStats;
  timeline: TimelineData[];
  totalGpuHours: number;
}

const ReportDistributions: React.FC<ReportDistributionsProps> = ({
  jobDurationStats,
  waitingTimeStats,
  timeline,
  totalGpuHours
}) => {
  if (!timeline || timeline.length === 0) {
    return null;
  }

  return (
    <>
      {/* Cumulative CPU Hours */}
      <div className="page-break-avoid" style={{
        background: 'var(--report-card-bg)',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid var(--report-border)',
        marginTop: '2rem',
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
          Cumulative CPU-Hours Consumption
        </h3>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
          Cumulative view of total CPU hours consumed over the reporting period, showing overall compute resource accumulation.
        </p>
        <Plot
          data={(() => {
            const sortedTimeline = [...timeline].sort((a, b) =>
              new Date(a.date).getTime() - new Date(b.date).getTime()
            );

            let cumulativeCPU = 0;
            const cumulativeCPUData: number[] = [];

            sortedTimeline.forEach(d => {
              cumulativeCPU += d.cpu_hours;
              cumulativeCPUData.push(cumulativeCPU);
            });

            return [
              {
                x: sortedTimeline.map(d => d.date),
                y: cumulativeCPUData,
                type: 'scatter' as const,
                mode: 'lines' as const,
                name: 'CPU Hours',
                line: { color: COLORS.cpu_hours, width: 2 },
                fill: 'tozeroy',
                fillcolor: 'rgba(99, 110, 250, 0.2)',
                hovertemplate: '<b>%{x}</b><br>Cumulative CPU: %{y:,.2f}h<extra></extra>',
              }
            ];
          })()}
          layout={{
            height: 280,
            margin: { l: 80, r: 20, t: 10, b: 50 },
            xaxis: {
              title: { text: 'Date', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 9 },
              tickangle: -45,
            },
            yaxis: {
              title: { text: 'Cumulative CPU-Hours', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 10 },
            },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            font: { color: '#000', family: 'Arial, sans-serif' },
            showlegend: false,
          }}
          config={{ displayModeBar: false, staticPlot: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Cumulative GPU Hours */}
      {totalGpuHours > 0 && (
        <div className="page-break-avoid" style={{
          background: 'var(--report-card-bg)',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
          marginTop: '2rem',
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
            Cumulative GPU-Hours Consumption
          </h3>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
            Cumulative view of total GPU hours consumed over the reporting period, showing overall accelerator resource accumulation.
          </p>
          <Plot
            data={(() => {
              const sortedTimeline = [...timeline].sort((a, b) =>
                new Date(a.date).getTime() - new Date(b.date).getTime()
              );

              let cumulativeGPU = 0;
              const cumulativeGPUData: number[] = [];

              sortedTimeline.forEach(d => {
                cumulativeGPU += d.gpu_hours;
                cumulativeGPUData.push(cumulativeGPU);
              });

              return [
                {
                  x: sortedTimeline.map(d => d.date),
                  y: cumulativeGPUData,
                  type: 'scatter' as const,
                  mode: 'lines' as const,
                  name: 'GPU Hours',
                  line: { color: COLORS.gpu_hours, width: 2 },
                  fill: 'tozeroy',
                  fillcolor: 'rgba(239, 85, 59, 0.2)',
                  hovertemplate: '<b>%{x}</b><br>Cumulative GPU: %{y:,.2f}h<extra></extra>',
                }
              ];
            })()}
            layout={{
              height: 280,
              margin: { l: 80, r: 20, t: 10, b: 50 },
              xaxis: {
                title: { text: 'Date', font: { size: 11 } },
                gridcolor: '#e0e0e0',
                tickfont: { size: 9 },
                tickangle: -45,
              },
              yaxis: {
                title: { text: 'Cumulative GPU-Hours', font: { size: 11 } },
                gridcolor: '#e0e0e0',
                tickfont: { size: 10 },
              },
              plot_bgcolor: '#fafafa',
              paper_bgcolor: 'white',
              font: { color: '#000', family: 'Arial, sans-serif' },
              showlegend: false,
            }}
            config={{ displayModeBar: false, staticPlot: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* Job Performance Statistics */}
      {jobDurationStats && jobDurationStats.mean > 0 && (
        <div className="page-break-avoid" style={{
          background: 'var(--report-card-bg)',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
          marginTop: '2rem',
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
            Job Duration Statistics
          </h3>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
            Statistical distribution of job execution times, showing how long jobs typically run.
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: '#000' }}>Metric</th>
                <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Hours</th>
                <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Days</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>Mean (Average)</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(jobDurationStats.mean)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(jobDurationStats.mean / 24).toFixed(2)}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>Median (50th percentile)</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(jobDurationStats.median)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(jobDurationStats.median / 24).toFixed(2)}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>25th Percentile</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(jobDurationStats.p25)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(jobDurationStats.p25 / 24).toFixed(2)}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>75th Percentile</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(jobDurationStats.p75)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(jobDurationStats.p75 / 24).toFixed(2)}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>90th Percentile</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(jobDurationStats.p90)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(jobDurationStats.p90 / 24).toFixed(2)}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>Minimum</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(jobDurationStats.min)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(jobDurationStats.min / 24).toFixed(2)}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.5rem' }}>Maximum</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(jobDurationStats.max)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(jobDurationStats.max / 24).toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Waiting Time Statistics */}
      {waitingTimeStats && waitingTimeStats.mean > 0 && (
        <div className="page-break-avoid" style={{
          background: 'var(--report-card-bg)',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
          marginTop: '2rem',
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
            Queue Waiting Time Statistics
          </h3>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
            Time jobs spent waiting in the queue before execution started.
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: '#000' }}>Metric</th>
                <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Hours</th>
                <th style={{ textAlign: 'right', padding: '0.5rem', color: '#000' }}>Days</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>Mean (Average)</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(waitingTimeStats.mean)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(waitingTimeStats.mean / 24).toFixed(2)}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>Median (50th percentile)</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(waitingTimeStats.median)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(waitingTimeStats.median / 24).toFixed(2)}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '0.5rem' }}>90th Percentile</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(waitingTimeStats.p90)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(waitingTimeStats.p90 / 24).toFixed(2)}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.5rem' }}>Maximum</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{formatHours(waitingTimeStats.max)}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem' }}>{(waitingTimeStats.max / 24).toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </>
  );
};

export default ReportDistributions;
