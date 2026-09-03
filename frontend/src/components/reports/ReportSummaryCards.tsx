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

const ReportSummaryCards: React.FC<ReportSummaryCardsProps> = ({ reportData, reportType }) => {
  const renderComparisonIndicator = (changePercent: number, periodLabel: string) => {
    if (changePercent === 0) {
      return (
        <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '0.25rem' }}>
          0.0% → vs previous {periodLabel}
        </div>
      );
    }

    const isPositive = changePercent > 0;
    const color = isPositive ? '#22c55e' : '#ef4444';
    const arrow = isPositive ? '↑' : '↓';
    const sign = isPositive ? '+' : '';

    return (
      <div style={{ fontSize: '0.7rem', color: color, marginTop: '0.25rem', fontWeight: 600 }}>
        {sign}{changePercent.toFixed(1)}% {arrow} vs previous {periodLabel}
      </div>
    );
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '1rem',
      marginBottom: '2rem',
    }}>
      {/* Total Active Users */}
      <div style={{
        background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
        padding: '1rem',
        borderRadius: '6px',
        border: '1px solid #e0e0e0',
      }}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
          Total Active Users
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.users }}>
          {formatCompact(reportData.summary.total_users)}
        </div>
        <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
          Unique users in period
        </div>
        {reportData.comparison && renderComparisonIndicator(
          reportData.comparison.users_change_percent,
          getPeriodLabel(reportType)
        )}
      </div>

      {/* Total Jobs */}
      <div style={{
        background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
        padding: '1rem',
        borderRadius: '6px',
        border: '1px solid #e0e0e0',
      }}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
          Total Jobs
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.total_jobs }}>
          {formatCompact(reportData.summary.total_jobs)}
        </div>
        <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
          {formatNumber(reportData.summary.total_jobs)} jobs submitted
        </div>
        {reportData.comparison && renderComparisonIndicator(
          reportData.comparison.jobs_change_percent,
          getPeriodLabel(reportType)
        )}
      </div>

      {/* Total CPU Hours */}
      <div style={{
        background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
        padding: '1rem',
        borderRadius: '6px',
        border: '1px solid #e0e0e0',
      }}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
          Total CPU Hours
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.cpu_hours }}>
          {formatCompact(reportData.summary.total_cpu_hours)}
        </div>
        <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
          {formatNumber(reportData.summary.total_cpu_hours)} hours
        </div>
        {reportData.comparison && renderComparisonIndicator(
          reportData.comparison.cpu_hours_change_percent,
          getPeriodLabel(reportType)
        )}
      </div>

      {/* Total GPU Hours */}
      <div style={{
        background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
        padding: '1rem',
        borderRadius: '6px',
        border: '1px solid #e0e0e0',
      }}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
          Total GPU Hours
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.gpu_hours }}>
          {formatCompact(reportData.summary.total_gpu_hours)}
        </div>
        <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
          {formatNumber(reportData.summary.total_gpu_hours)} hours
        </div>
        {reportData.comparison && renderComparisonIndicator(
          reportData.comparison.gpu_hours_change_percent,
          getPeriodLabel(reportType)
        )}
      </div>

      {/* Job Success Rate */}
      {reportData.summary.success_rate !== undefined && (
        <div style={{
          background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
          padding: '1rem',
          borderRadius: '6px',
          border: '1px solid #e0e0e0',
        }}>
          <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
            Job Success Rate
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.total_jobs }}>
            {reportData.summary.success_rate.toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
            {formatNumber(reportData.summary.completed_jobs || 0)} completed, {formatNumber(reportData.summary.failed_jobs || 0)} failed
          </div>
        </div>
      )}

      {/* Avg Job Duration */}
      {reportData.summary.avg_job_duration_hours !== undefined && reportData.summary.avg_job_duration_hours > 0 && (
        <div style={{
          background: 'var(--report-card-bg)',
          padding: '1.5rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
        }}>
          <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#000' }}>
            Avg Job Duration: <span style={{ color: COLORS.duration }}>{formatHours(reportData.summary.avg_job_duration_hours)}h</span> - Median: {formatHours(reportData.summary.median_job_duration_hours || 0)}h
          </div>
        </div>
      )}

      {/* Avg Waiting Time */}
      {reportData.summary.avg_waiting_time_hours !== undefined && reportData.summary.avg_waiting_time_hours > 0 && (
        <div style={{
          background: 'var(--report-card-bg)',
          padding: '1.5rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
        }}>
          <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#000' }}>
            Avg Waiting Time: <span style={{ color: COLORS.waiting }}>{formatHours(reportData.summary.avg_waiting_time_hours)}h</span> - Median: {formatHours(reportData.summary.median_waiting_time_hours || 0)}h
          </div>
        </div>
      )}

      {/* Average Jobs per Day */}
      {reportData.timeline && reportData.timeline.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
          padding: '1rem',
          borderRadius: '6px',
          border: '1px solid #e0e0e0',
        }}>
          <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
            Avg Jobs/Day
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.total_jobs }}>
            {formatCompact(reportData.summary.total_jobs / reportData.timeline.length)}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
            Over {reportData.timeline.length} days
          </div>
        </div>
      )}

      {/* Peak Jobs in a Day */}
      {reportData.timeline && reportData.timeline.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
          padding: '1rem',
          borderRadius: '6px',
          border: '1px solid #e0e0e0',
        }}>
          <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
            Peak Jobs/Day
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.total_jobs }}>
            {formatCompact(Math.max(...reportData.timeline.map(d => d.jobs)))}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
            {reportData.timeline.find(d => d.jobs === Math.max(...reportData.timeline.map(d => d.jobs)))?.date}
          </div>
        </div>
      )}

      {/* Avg CPU Hours per Day */}
      {reportData.timeline && reportData.timeline.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
          padding: '1rem',
          borderRadius: '6px',
          border: '1px solid #e0e0e0',
        }}>
          <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
            Avg CPU-Hours/Day
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.cpu_hours }}>
            {formatCompact(reportData.summary.total_cpu_hours / reportData.timeline.length)}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
            max {formatCompact(Math.max(...reportData.timeline.map(d => d.cpu_hours)))} h/day
          </div>
        </div>
      )}

      {/* Avg GPU Hours per Day */}
      {reportData.timeline && reportData.timeline.length > 0 && reportData.summary.total_gpu_hours > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
          padding: '1rem',
          borderRadius: '6px',
          border: '1px solid #e0e0e0',
        }}>
          <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem', fontWeight: 600 }}>
            Avg GPU-Hours/Day
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.gpu_hours }}>
            {formatCompact(reportData.summary.total_gpu_hours / reportData.timeline.length)}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
            max {formatCompact(Math.max(...reportData.timeline.map(d => d.gpu_hours)))} h/day
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportSummaryCards;
