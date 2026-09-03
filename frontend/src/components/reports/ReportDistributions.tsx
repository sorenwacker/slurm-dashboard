import React from 'react';
import Plot from '../charts/Plot';
import { COLORS } from '../../theme/colors';
import { formatHours, REPORT_AXIS, REPORT_LAYOUT, withAlpha } from './reportHelpers';

interface DurationStats {
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
  jobDurationStats?: DurationStats;
  waitingTimeStats?: DurationStats;
  timeline: TimelineData[];
  totalGpuHours: number;
}

interface CumulativeCardProps {
  title: string;
  description: string;
  timeline: TimelineData[];
  metric: 'cpu_hours' | 'gpu_hours';
  label: string;
  color: string;
}

/** Running total of a metric over the period as a filled line. */
const CumulativeCard: React.FC<CumulativeCardProps> = ({ title, description, timeline, metric, label, color }) => {
  const sorted = [...timeline].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  let total = 0;
  const cumulative = sorted.map((d) => (total += d[metric]));
  return (
    <div className="report-card page-break-avoid">
      <h3>{title}</h3>
      <p className="report-description">{description}</p>
      <Plot
        data={[
          {
            x: sorted.map((d) => d.date),
            y: cumulative,
            type: 'scatter',
            mode: 'lines',
            name: label,
            line: { color, width: 2 },
            fill: 'tozeroy',
            fillcolor: withAlpha(color, 0.2),
            hovertemplate: `<b>%{x}</b><br>Cumulative ${label}: %{y:,.2f}h<extra></extra>`,
          },
        ]}
        layout={{
          ...REPORT_LAYOUT,
          height: 280,
          margin: { l: 80, r: 20, t: 10, b: 50 },
          xaxis: { ...REPORT_AXIS, title: { text: 'Date', font: { size: 11 } }, tickfont: { size: 9 }, tickangle: -45 },
          yaxis: { ...REPORT_AXIS, title: { text: `Cumulative ${label}`, font: { size: 11 } } },
          showlegend: false,
        }}
        config={{ displayModeBar: false, staticPlot: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
};

interface StatsTableCardProps {
  title: string;
  description: string;
  stats: DurationStats;
  rows: { key: keyof DurationStats; label: string }[];
}

/** Percentile table of a duration distribution in hours and days. */
const StatsTableCard: React.FC<StatsTableCardProps> = ({ title, description, stats, rows }) => (
  <div className="report-card page-break-avoid">
    <h3>{title}</h3>
    <p className="report-description">{description}</p>
    <table className="report-table">
      <thead>
        <tr>
          <th>Metric</th>
          <th className="num">Hours</th>
          <th className="num">Days</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ key, label }) => (
          <tr key={key}>
            <td>{label}</td>
            <td className="num">{formatHours(stats[key])}</td>
            <td className="num">{(stats[key] / 24).toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const DURATION_ROWS: StatsTableCardProps['rows'] = [
  { key: 'mean', label: 'Mean (Average)' },
  { key: 'median', label: 'Median (50th percentile)' },
  { key: 'p25', label: '25th Percentile' },
  { key: 'p75', label: '75th Percentile' },
  { key: 'p90', label: '90th Percentile' },
  { key: 'min', label: 'Minimum' },
  { key: 'max', label: 'Maximum' },
];

const WAITING_ROWS: StatsTableCardProps['rows'] = [
  { key: 'mean', label: 'Mean (Average)' },
  { key: 'median', label: 'Median (50th percentile)' },
  { key: 'p90', label: '90th Percentile' },
  { key: 'max', label: 'Maximum' },
];

const ReportDistributions: React.FC<ReportDistributionsProps> = ({
  jobDurationStats,
  waitingTimeStats,
  timeline,
  totalGpuHours,
}) => {
  if (!timeline || timeline.length === 0) {
    return null;
  }

  return (
    <div className="report-cards">
      <CumulativeCard
        title="Cumulative CPU-Hours Consumption"
        description="Running total of CPU hours consumed over the reporting period."
        timeline={timeline}
        metric="cpu_hours"
        label="CPU-Hours"
        color={COLORS.cpu_hours}
      />
      {totalGpuHours > 0 && (
        <CumulativeCard
          title="Cumulative GPU-Hours Consumption"
          description="Running total of GPU hours consumed over the reporting period."
          timeline={timeline}
          metric="gpu_hours"
          label="GPU-Hours"
          color={COLORS.gpu_hours}
        />
      )}
      {jobDurationStats && jobDurationStats.mean > 0 && (
        <StatsTableCard
          title="Job Duration Statistics"
          description="Distribution of job execution times."
          stats={jobDurationStats}
          rows={DURATION_ROWS}
        />
      )}
      {waitingTimeStats && waitingTimeStats.mean > 0 && (
        <StatsTableCard
          title="Queue Waiting Time Statistics"
          description="Time jobs spent waiting in the queue before execution started."
          stats={waitingTimeStats}
          rows={WAITING_ROWS}
        />
      )}
    </div>
  );
};

export default ReportDistributions;
