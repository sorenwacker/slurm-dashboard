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

const ReportPreview: React.FC<ReportPreviewProps> = ({
  reportData,
  isLoading,
  error,
  reportType,
}) => {
  return (
    <>
      {/* Print-friendly A4 CSS */}
      <style>{`
        @media print {
          @page {
            size: A4;
            margin: 20mm;
          }
          body {
            print-color-adjust: exact;
            -webkit-print-color-adjust: exact;
          }
          .no-print {
            display: none !important;
          }
          .page-break {
            page-break-before: always;
            break-before: page;
          }
          .page-break-avoid {
            page-break-inside: avoid;
            break-inside: avoid;
          }
        }
      `}</style>

      {/* Report Preview */}
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          <div className="loading-spinner"></div>
          <p>Loading report preview...</p>
        </div>
      )}

      {error && (
        <div style={{
          background: '#fee',
          border: '1px solid #fcc',
          padding: '1rem',
          borderRadius: '4px',
          color: '#c00',
        }}>
          <strong>Unable to generate report</strong>
          <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
            {(() => {
              // Extract user-friendly error message from API response
              const axiosError = error as { response?: { data?: { detail?: string } }; message?: string };
              if (axiosError?.response?.data?.detail) {
                return axiosError.response.data.detail;
              }
              if (axiosError?.message?.includes('400')) {
                return 'Please select a valid cluster and time period for the report.';
              }
              return 'Please check your selections and try again.';
            })()}
          </p>
        </div>
      )}

      {reportData && (
        <div style={{
          maxWidth: '210mm',
          margin: '0 auto',
          background: 'white',
          padding: '20mm',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderRadius: '4px',
        }}>
          {/* Report Header */}
          <div style={{
            background: 'var(--card-bg)',
            padding: '1.5rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            border: '1px solid var(--border-color)',
          }}>
            <h2 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000000' }}>
              {reportData.report_type}
            </h2>
            <p style={{ margin: 0, color: '#000000' }}>
              Cluster: <strong>{reportData.hostname}</strong> |
              Period: <strong>{reportData.period.start_date}</strong> to <strong>{reportData.period.end_date}</strong>
            </p>
          </div>

          {/* 1. EXECUTIVE SUMMARY */}
          <h3 style={{ marginTop: '2rem', marginBottom: '1rem', color: '#000', borderBottom: '2px solid #e0e0e0', paddingBottom: '0.5rem' }}>
            Executive Summary
          </h3>
          <ReportSummaryCards reportData={reportData} reportType={reportType} />

          {/* 2. TRENDS OVER TIME */}
          <h3 style={{ marginTop: '3rem', marginBottom: '1rem', color: '#000', borderBottom: '2px solid #e0e0e0', paddingBottom: '0.5rem' }}>
            Trends Over Time
          </h3>
          <ReportTimelines
            timeline={reportData.timeline}
            previousTimeline={reportData.comparison?.previous_timeline}
            totalGpuHours={reportData.summary.total_gpu_hours}
            reportType={reportType}
          />

          {/* 3. RESOURCE ALLOCATION & USAGE */}
          <h3 style={{ marginTop: '3rem', marginBottom: '1rem', color: '#000', borderBottom: '2px solid #e0e0e0', paddingBottom: '0.5rem' }}>
            Resource Allocation & Usage
          </h3>
          <ReportBreakdowns
            byAccount={reportData.by_account}
            byPartition={reportData.by_partition}
            byState={reportData.by_state}
            totalJobs={reportData.summary.total_jobs}
            totalGpuHours={reportData.summary.total_gpu_hours}
          />

          {/* 4. PERFORMANCE METRICS */}
          <h3 style={{ marginTop: '3rem', marginBottom: '1rem', color: '#000', borderBottom: '2px solid #e0e0e0', paddingBottom: '0.5rem' }}>
            Performance Metrics
          </h3>
          <ReportDistributions
            jobDurationStats={reportData.job_duration_stats}
            waitingTimeStats={reportData.waiting_time_stats}
            timeline={reportData.timeline}
            totalGpuHours={reportData.summary.total_gpu_hours}
          />

        </div>
      )}
    </>
  );
};

export default ReportPreview;
