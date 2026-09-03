import React from 'react';
import type { AggregatedChartsResponse } from '../types';
import { formatNumber, formatCompact } from '../utils/format';

interface StatsCardsProps {
  data: AggregatedChartsResponse | undefined;
}

const StatsCards: React.FC<StatsCardsProps> = ({ data }) => {
  if (!data || !data.summary) {
    return null;
  }

  const { summary } = data;

  return (
    <div className="stats-grid">
      <div className="stat-card stat-users">
        <h4>Total Active Users</h4>
        <div className="stat-value">{formatNumber(summary.total_users)}</div>
        <div className="stat-label">Unique users in period</div>
      </div>

      <div className="stat-card stat-jobs">
        <h4>Total Jobs</h4>
        <div className="stat-value">{formatCompact(summary.total_jobs)}</div>
        <div className="stat-label">{formatNumber(summary.total_jobs)} jobs submitted</div>
      </div>

      <div className="stat-card stat-cpu">
        <h4>Total CPU Hours</h4>
        <div className="stat-value">{formatCompact(summary.total_cpu_hours)}</div>
        <div className="stat-label">{formatNumber(Math.round(summary.total_cpu_hours))} hours</div>
      </div>

      <div className="stat-card stat-gpu">
        <h4>Total GPU Hours</h4>
        <div className="stat-value">{formatCompact(summary.total_gpu_hours)}</div>
        <div className="stat-label">{formatNumber(Math.round(summary.total_gpu_hours))} hours</div>
      </div>

      {summary.total_memory_gb_hours > 0 && (
        <div className="stat-card stat-memory">
          <h4>Total Memory GB-Hours</h4>
          <div className="stat-value">{formatCompact(summary.total_memory_gb_hours)}</div>
          <div className="stat-label">{formatNumber(Math.round(summary.total_memory_gb_hours))} GB-hours allocated</div>
        </div>
      )}
    </div>
  );
};

export default StatsCards;
