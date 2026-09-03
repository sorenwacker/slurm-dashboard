import React from 'react';
import type { MetadataResponse } from '../types';

interface ReportControlsProps {
  metadata: MetadataResponse | undefined;
  reportHostname: string;
  setReportHostname: (value: string) => void;
  reportType: 'monthly' | 'quarterly' | 'annual';
  setReportType: (value: 'monthly' | 'quarterly' | 'annual') => void;
  selectedYear: number;
  setSelectedYear: (value: number) => void;
  selectedMonth: number;
  setSelectedMonth: (value: number) => void;
  selectedQuarter: number;
  setSelectedQuarter: (value: number) => void;
  downloadFormat: 'pdf' | 'csv' | 'json';
  setDownloadFormat: (value: 'pdf' | 'csv' | 'json') => void;
  onDownload: () => void;
  availableYears: number[];
}

const ReportControls: React.FC<ReportControlsProps> = ({
  metadata,
  reportHostname,
  setReportHostname,
  reportType,
  setReportType,
  selectedYear,
  setSelectedYear,
  selectedMonth,
  setSelectedMonth,
  selectedQuarter,
  setSelectedQuarter,
  downloadFormat,
  setDownloadFormat,
  onDownload,
  availableYears,
}) => {
  const months = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  return (
    <>
      <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Report Generator</h3>

      {/* Cluster Selector */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label htmlFor="report-cluster" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
          Select Cluster
        </label>
        <select
          id="report-cluster"
          value={reportHostname}
          onChange={(e) => setReportHostname(e.target.value)}
          style={{
            padding: '0.5rem',
            borderRadius: '4px',
            border: '1px solid var(--border)',
            fontSize: '1rem',
            width: '100%',
            background: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
          }}
        >
          <option value="">Select cluster...</option>
          {metadata?.hostnames.map((hostname) => (
            <option key={hostname} value={hostname}>
              {hostname}
            </option>
          ))}
        </select>
      </div>

      {/* Report Configuration - only shown when cluster is selected */}
      {reportHostname && (
        <>
          <hr style={{ margin: '1.5rem 0', border: 'none', borderTop: '1px solid var(--border)' }} />

          {/* Report Type */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: 'var(--text-primary)' }}>
              Report Type
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as typeof reportType)}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="monthly">Monthly Report</option>
              <option value="quarterly">Quarterly Report</option>
              <option value="annual">Annual Report</option>
            </select>
          </div>

          {/* Year */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: 'var(--text-primary)' }}>
              Year
            </label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(parseInt(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
              }}
            >
              {availableYears.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>

          {/* Month (only for monthly reports) */}
          {reportType === 'monthly' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: 'var(--text-primary)' }}>
                Month
              </label>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                }}
              >
                {months.map((month) => (
                  <option key={month.value} value={month.value}>
                    {month.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Quarter (only for quarterly reports) */}
          {reportType === 'quarterly' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: 'var(--text-primary)' }}>
                Quarter
              </label>
              <select
                value={selectedQuarter}
                onChange={(e) => setSelectedQuarter(parseInt(e.target.value))}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                }}
              >
                <option value={1}>Q1 (Jan - Mar)</option>
                <option value={2}>Q2 (Apr - Jun)</option>
                <option value={3}>Q3 (Jul - Sep)</option>
                <option value={4}>Q4 (Oct - Dec)</option>
              </select>
            </div>
          )}

          {/* Download Format */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: 'var(--text-primary)' }}>
              Download Format
            </label>
            <select
              value={downloadFormat}
              onChange={(e) => setDownloadFormat(e.target.value as typeof downloadFormat)}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="pdf">PDF</option>
            </select>
          </div>

          {/* Download Button */}
          <button
            onClick={onDownload}
            className="no-print"
            style={{
              padding: '0.75rem 1.5rem',
              background: '#04A5D5',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '1rem',
              width: '100%',
            }}
          >
            Download Report
          </button>
        </>
      )}

      {!reportHostname && (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem', margin: '1rem 0 0 0' }}>
          Please select a cluster to generate reports
        </p>
      )}
    </>
  );
};

export default ReportControls;
