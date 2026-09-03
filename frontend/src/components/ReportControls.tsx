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

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const QUARTERS = ['Q1 (Jan - Mar)', 'Q2 (Apr - Jun)', 'Q3 (Jul - Sep)', 'Q4 (Oct - Dec)'];

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
}) => (
  <div className="filters-stack">
    <h4>Report Generator</h4>

    <div className="filter-group">
      <label htmlFor="report-cluster">Cluster</label>
      <select id="report-cluster" value={reportHostname} onChange={(e) => setReportHostname(e.target.value)}>
        <option value="">Select cluster...</option>
        {metadata?.hostnames.map((hostname) => (
          <option key={hostname} value={hostname}>
            {hostname}
          </option>
        ))}
      </select>
    </div>

    {reportHostname ? (
      <>
        <hr />

        <div className="filter-group">
          <label htmlFor="report-type">Report Type</label>
          <select
            id="report-type"
            value={reportType}
            onChange={(e) => setReportType(e.target.value as typeof reportType)}
          >
            <option value="monthly">Monthly Report</option>
            <option value="quarterly">Quarterly Report</option>
            <option value="annual">Annual Report</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="report-year">Year</label>
          <select id="report-year" value={selectedYear} onChange={(e) => setSelectedYear(parseInt(e.target.value))}>
            {availableYears.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        {reportType === 'monthly' && (
          <div className="filter-group">
            <label htmlFor="report-month">Month</label>
            <select id="report-month" value={selectedMonth} onChange={(e) => setSelectedMonth(parseInt(e.target.value))}>
              {MONTHS.map((label, index) => (
                <option key={label} value={index + 1}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        )}

        {reportType === 'quarterly' && (
          <div className="filter-group">
            <label htmlFor="report-quarter">Quarter</label>
            <select
              id="report-quarter"
              value={selectedQuarter}
              onChange={(e) => setSelectedQuarter(parseInt(e.target.value))}
            >
              {QUARTERS.map((label, index) => (
                <option key={label} value={index + 1}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="filter-group">
          <label htmlFor="report-format">Download Format</label>
          <select
            id="report-format"
            value={downloadFormat}
            onChange={(e) => setDownloadFormat(e.target.value as typeof downloadFormat)}
          >
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="pdf">PDF</option>
          </select>
        </div>

        <button type="button" className="button no-print" onClick={onDownload}>
          Download Report
        </button>
      </>
    ) : (
      <p className="filter-empty">Select a cluster to generate reports</p>
    )}
  </div>
);

export default ReportControls;
