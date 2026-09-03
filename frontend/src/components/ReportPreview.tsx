import React from 'react';
import ReportSummaryCards from './reports/ReportSummaryCards';
import ReportTimelines from './reports/ReportTimelines';
import ReportDistributions from './reports/ReportDistributions';
import ReportBreakdowns from './reports/ReportBreakdowns';

export interface ReportData {
  report_type: string;
  hostname: string;
  period: {
    start_date: string;
    end_date: string;
  };
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
    previous_period_start: string;
    previous_period_end: string;
    jobs_change_percent: number;
    cpu_hours_change_percent: number;
    gpu_hours_change_percent: number;
    users_change_percent: number;
    previous_timeline: Array<{
      date: string;
      jobs: number;
      cpu_hours: number;
      gpu_hours: number;
      users: number;
    }>;
  } | null;
  job_duration_stats?: {
    mean: number;
    median: number;
    p25: number;
    p75: number;
    p90: number;
    min: number;
    max: number;
  };
  waiting_time_stats?: {
    mean: number;
    median: number;
    p25: number;
    p75: number;
    p90: number;
    min: number;
    max: number;
  };
  by_account: Array<{
    account: string;
    jobs: number;
    cpu_hours: number;
    gpu_hours: number;
    users: number;
  }>;
  by_user: Array<{
    user: string;
    jobs: number;
    cpu_hours: number;
    gpu_hours: number;
  }>;
  by_partition: Array<{
    partition: string;
    jobs: number;
    cpu_hours: number;
    gpu_hours: number;
    users: number;
  }>;
  by_state: Array<{
    state: string;
    jobs: number;
  }>;
  timeline: Array<{
    date: string;
    jobs: number;
    cpu_hours: number;
    gpu_hours: number;
    users: number;
  }>;
  generated_at: string;
}

interface ReportPreviewProps {
  reportData: ReportData | undefined;
  isLoading: boolean;
  error: Error | null;
  reportType: 'monthly' | 'quarterly' | 'annual';
}

/** Message shown for a failed report request, taken from the API detail when present. */
function errorMessage(error: Error): string {
  const axiosError = error as { response?: { data?: { detail?: string } }; message?: string };
  if (axiosError?.response?.data?.detail) return axiosError.response.data.detail;
  if (axiosError?.message?.includes('400')) return 'Select a valid cluster and time period for the report.';
  return 'Check your selections and try again.';
}

const ReportPreview: React.FC<ReportPreviewProps> = ({ reportData, isLoading, error, reportType }) => (
  <>
    {isLoading && (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading report preview...</p>
      </div>
    )}

    {error && (
      <div className="error">
        <strong>Unable to generate report.</strong> {errorMessage(error)}
      </div>
    )}

    {reportData && (
      <article className="report-page">
        <header className="report-header">
          <h2>{reportData.report_type}</h2>
          <p>
            Cluster: <strong>{reportData.hostname}</strong> | Period: <strong>{reportData.period.start_date}</strong> to{' '}
            <strong>{reportData.period.end_date}</strong>
          </p>
        </header>

        <h3 className="report-section-title">Executive Summary</h3>
        <ReportSummaryCards reportData={reportData} reportType={reportType} />

        <h3 className="report-section-title">Trends Over Time</h3>
        <ReportTimelines
          timeline={reportData.timeline}
          previousTimeline={reportData.comparison?.previous_timeline}
          totalGpuHours={reportData.summary.total_gpu_hours}
          reportType={reportType}
        />

        <h3 className="report-section-title">Resource Allocation and Usage</h3>
        <ReportBreakdowns
          byAccount={reportData.by_account}
          byPartition={reportData.by_partition}
          byState={reportData.by_state}
          totalJobs={reportData.summary.total_jobs}
          totalGpuHours={reportData.summary.total_gpu_hours}
        />

        <h3 className="report-section-title">Performance Metrics</h3>
        <ReportDistributions
          jobDurationStats={reportData.job_duration_stats}
          waitingTimeStats={reportData.waiting_time_stats}
          timeline={reportData.timeline}
          totalGpuHours={reportData.summary.total_gpu_hours}
        />
      </article>
    )}
  </>
);

export default ReportPreview;
