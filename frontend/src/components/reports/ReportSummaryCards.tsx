import React from 'react';
import { COLORS } from '../../theme/colors';
import { formatNumber, formatCompact, formatHours, getPeriodLabel } from './reportHelpers';

interface ReportData {
  report_type: string;
  summary: {
    total_jobs: number;
    total_cpu_hours: number;
    total_gpu_hours: number;
    total_users: number;
    avg_job_duration_hours?: number;
    median_job_duration_hours?: number;
    avg_waiting_time_hours?: number;
    median_waiting_time_hours?: number;
    completed_jobs?: number;
    failed_jobs?: number;
    success_rate?: number;
  };
  comparison?: {
    jobs_change_percent: number;
    cpu_hours_change_percent: number;
    gpu_hours_change_percent: number;
    users_change_percent: number;
  } | null;
  timeline: Array<{
    date: string;
    jobs: number;
    cpu_hours: number;
    gpu_hours: number;
    users: number;
  }>;
}

interface ReportSummaryCardsProps {
  reportData: ReportData;
  reportType: 'monthly' | 'quarterly' | 'annual';
}

interface StatProps {
  label: string;
  value: string;
  color: string;
  note?: string;
  change?: number;
  periodLabel?: string;
}

/** One summary figure: label, colored value, an optional note, and an optional change against the previous period. */
const Stat: React.FC<StatProps> = ({ label, value, color, note, change, periodLabel }) => {
  let delta: React.ReactNode = null;
  if (change !== undefined && periodLabel) {
    const direction = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
    const arrow = change > 0 ? '↑' : change < 0 ? '↓' : '→';
    const sign = change > 0 ? '+' : '';
    delta = (
      <div className={`report-stat-delta ${direction}`}>
        {sign}{change.toFixed(1)}% {arrow} vs previous {periodLabel}
      </div>
    );
  }
  return (
    <div className="report-stat">
      <div className="report-stat-label">{label}</div>
      <div className="report-stat-value" style={{ color }}>{value}</div>
      {note && <div className="report-stat-note">{note}</div>}
      {delta}
    </div>
  );
};

const ReportSummaryCards: React.FC<ReportSummaryCardsProps> = ({ reportData, reportType }) => {
  const { summary, comparison, timeline } = reportData;
  const periodLabel = getPeriodLabel(reportType);
  const days = timeline?.length ?? 0;
  const maxJobs = days > 0 ? Math.max(...timeline.map((d) => d.jobs)) : 0;
  const peakDay = days > 0 ? timeline.find((d) => d.jobs === maxJobs)?.date : undefined;

  return (
    <div className="report-stats">
      <Stat
        label="Total Active Users"
        value={formatCompact(summary.total_users)}
        color={COLORS.users}
        note="Unique users in period"
        change={comparison?.users_change_percent}
        periodLabel={periodLabel}
      />
      <Stat
        label="Total Jobs"
        value={formatCompact(summary.total_jobs)}
        color={COLORS.total_jobs}
        note={`${formatNumber(summary.total_jobs)} jobs submitted`}
        change={comparison?.jobs_change_percent}
        periodLabel={periodLabel}
      />
      <Stat
        label="Total CPU Hours"
        value={formatCompact(summary.total_cpu_hours)}
        color={COLORS.cpu_hours}
        note={`${formatNumber(summary.total_cpu_hours)} hours`}
        change={comparison?.cpu_hours_change_percent}
        periodLabel={periodLabel}
      />
      <Stat
        label="Total GPU Hours"
        value={formatCompact(summary.total_gpu_hours)}
        color={COLORS.gpu_hours}
        note={`${formatNumber(summary.total_gpu_hours)} hours`}
        change={comparison?.gpu_hours_change_percent}
        periodLabel={periodLabel}
      />

      {summary.success_rate !== undefined && (
        <Stat
          label="Job Success Rate"
          value={`${summary.success_rate.toFixed(1)}%`}
          color={COLORS.total_jobs}
          note={`${formatNumber(summary.completed_jobs || 0)} completed, ${formatNumber(summary.failed_jobs || 0)} failed`}
        />
      )}

      {summary.avg_job_duration_hours !== undefined && summary.avg_job_duration_hours > 0 && (
        <Stat
          label="Avg Job Duration"
          value={`${formatHours(summary.avg_job_duration_hours)} h`}
          color={COLORS.duration}
          note={`median ${formatHours(summary.median_job_duration_hours || 0)} h`}
        />
      )}

      {summary.avg_waiting_time_hours !== undefined && summary.avg_waiting_time_hours > 0 && (
        <Stat
          label="Avg Waiting Time"
          value={`${formatHours(summary.avg_waiting_time_hours)} h`}
          color={COLORS.waiting}
          note={`median ${formatHours(summary.median_waiting_time_hours || 0)} h`}
        />
      )}

      {days > 0 && (
        <>
          <Stat
            label="Avg Jobs/Day"
            value={formatCompact(summary.total_jobs / days)}
            color={COLORS.total_jobs}
            note={`Over ${days} days`}
          />
          <Stat label="Peak Jobs/Day" value={formatCompact(maxJobs)} color={COLORS.total_jobs} note={peakDay} />
          <Stat
            label="Avg CPU-Hours/Day"
            value={formatCompact(summary.total_cpu_hours / days)}
            color={COLORS.cpu_hours}
            note={`max ${formatCompact(Math.max(...timeline.map((d) => d.cpu_hours)))} h/day`}
          />
          {summary.total_gpu_hours > 0 && (
            <Stat
              label="Avg GPU-Hours/Day"
              value={formatCompact(summary.total_gpu_hours / days)}
              color={COLORS.gpu_hours}
              note={`max ${formatCompact(Math.max(...timeline.map((d) => d.gpu_hours)))} h/day`}
            />
          )}
        </>
      )}
    </div>
  );
};

export default ReportSummaryCards;
