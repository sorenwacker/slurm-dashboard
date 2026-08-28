import React from 'react';
import ChartCaption from '../ChartCaption';
import type { AggregatedChartsResponse } from '../../../types';
import type { ChartColors } from '../../../hooks/useDarkMode';
import type { TimingStats } from '../../../hooks/useTimingStats';
import { formatHours } from '../../../hooks/useTimingStats';
import TimelineChart from '../TimelineChart';
import PieChart from '../PieChart';
import HistogramChart from '../HistogramChart';
import StackedPercentageChart from '../StackedPercentageChart';
import { COLORS } from '../chartHelpers';

interface TimingSectionProps {
  data: AggregatedChartsResponse;
  colorMap: Map<string, string> | null;
  colorBy: string;
  chartColors: ChartColors;
  isDark: boolean;
  timingStats: TimingStats | null;
}

const TimingSection: React.FC<TimingSectionProps> = ({
  data,
  colorMap,
  colorBy,
  chartColors,
  isDark,
  timingStats,
}) => {
  return (
    <section className="section">
      <h2 className="section-title">Timing</h2>

      {/* TREND CHARTS */}
      <div className="timing-trends-row">
        {/* Waiting Time Trends */}
        <div className="timing-subsection">
          <div className="timing-subsection-header">
            <h3>Waiting Times</h3>
            <div className="timing-stats-row">
              <div className="timing-stat">
                <span className="timing-stat-label">Median</span>
                <span className="timing-stat-value">{formatHours(timingStats?.waitMedian ?? null)}</span>
              </div>
              <div className="timing-stat">
                <span className="timing-stat-label">P95</span>
                <span className="timing-stat-value timing-stat-warning">{formatHours(timingStats?.waitP95 ?? null)}</span>
              </div>
              <div className="timing-stat">
                <span className="timing-stat-label">Max</span>
                <span className="timing-stat-value timing-stat-danger">{formatHours(timingStats?.waitMax ?? null)}</span>
              </div>
            </div>
          </div>
          {data.waiting_times_trends && data.waiting_times_trends.x.length > 0 && (
            <div className="card">
              <h3>Waiting Time Trends</h3>
              <TimelineChart
                data={data.waiting_times_trends}
                xTitle="Period"
                yTitle="Waiting Time (hours)"
                colorMap={colorMap}
                defaultColor="#dc3545"
                statistic="median"
                chartColors={chartColors}
              />
              <ChartCaption text="Time from submission to start per period: median, mean and percentiles." />
            </div>
          )}
        </div>

        {/* Job Duration Trends */}
        <div className="timing-subsection">
          <div className="timing-subsection-header">
            <h3>Job Duration</h3>
            <div className="timing-stats-row">
              <div className="timing-stat">
                <span className="timing-stat-label">Median</span>
                <span className="timing-stat-value">{formatHours(timingStats?.durationMedian ?? null)}</span>
              </div>
              <div className="timing-stat">
                <span className="timing-stat-label">P95</span>
                <span className="timing-stat-value">{formatHours(timingStats?.durationP95 ?? null)}</span>
              </div>
              <div className="timing-stat">
                <span className="timing-stat-label">Max</span>
                <span className="timing-stat-value">{formatHours(timingStats?.durationMax ?? null)}</span>
              </div>
            </div>
          </div>
          {data.job_duration_trends && data.job_duration_trends.x.length > 0 && (
            <div className="card">
              <h3>Job Duration Trends</h3>
              <TimelineChart
                data={data.job_duration_trends}
                xTitle="Period"
                yTitle="Job Duration (hours)"
                colorMap={colorMap}
                defaultColor="#28a745"
                statistic="median"
                chartColors={chartColors}
              />
              <ChartCaption text="Elapsed time per job per period: median, mean and percentiles." />
            </div>
          )}
        </div>
      </div>

      {/* STACKED DISTRIBUTION CHARTS */}
      <div className="chart-row-equal">
        {data.waiting_times_stacked && data.waiting_times_stacked.x && data.waiting_times_stacked.x.length > 0 && (
          <StackedPercentageChart
            data={data.waiting_times_stacked}
            title="Waiting Time Distribution Over Time"
            chartColors={chartColors}
            isDark={isDark}
          />
        )}
        {data.job_duration_stacked && data.job_duration_stacked.x && data.job_duration_stacked.x.length > 0 && (
          <StackedPercentageChart
            data={data.job_duration_stacked}
            title="Job Duration Distribution Over Time"
            chartColors={chartColors}
            isDark={isDark}
          />
        )}
      </div>

      {/* HISTOGRAM CHARTS */}
      <div className="chart-row-equal">
        {data.waiting_times_hist && (
          (data.waiting_times_hist.type === 'pie' && (data.waiting_times_hist.labels?.length ?? 0) > 0) ||
          (data.waiting_times_hist.x && data.waiting_times_hist.x.length > 0)
        ) && (
          <div className="card">
            <h3>
              {data.waiting_times_hist.type === 'pie'
                ? `Total Waiting Time by ${colorBy}`
                : 'Job Waiting Times Distribution'}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}> (all jobs)</span>
            </h3>
            {data.waiting_times_hist.type === 'pie' ? (
              <PieChart
                data={{
                  labels: data.waiting_times_hist.labels || [],
                  values: data.waiting_times_hist.values || [],
                }}
                valueLabel="Hours waiting"
                colors={colorMap ? (data.waiting_times_hist.labels || []).map((label, idx) =>
                  colorMap.get(label) || COLORS[idx % COLORS.length]
                ) : undefined}
                chartColors={chartColors}
              />
            ) : (
              <HistogramChart
                data={data.waiting_times_hist}
                xTitle="Waiting Time (hours)"
                yTitle="Percentage of Jobs (%)"
                defaultColor="#dc3545"
                colorMap={null}
                isHistogram={false}
                showMedianMean={true}
                unit="h"
                decimalPlaces={1}
                chartColors={chartColors}
              />
            )}
            <ChartCaption text="Waiting time split by the colour dimension; without one, the distribution of waiting times across jobs." />
          </div>
        )}
        {data.job_duration_hist && (
          (data.job_duration_hist.type === 'pie' && (data.job_duration_hist.labels?.length ?? 0) > 0) ||
          (data.job_duration_hist.x && data.job_duration_hist.x.length > 0)
        ) && (
          <div className="card">
            <h3>
              {data.job_duration_hist.type === 'pie'
                ? `Total Job Duration by ${colorBy}`
                : 'Job Duration Distribution'}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}> (all jobs)</span>
            </h3>
            {data.job_duration_hist.type === 'pie' ? (
              <PieChart
                data={{
                  labels: data.job_duration_hist.labels || [],
                  values: data.job_duration_hist.values || [],
                }}
                valueLabel="Hours runtime"
                colors={colorMap ? (data.job_duration_hist.labels || []).map((label, idx) =>
                  colorMap.get(label) || COLORS[idx % COLORS.length]
                ) : undefined}
                chartColors={chartColors}
              />
            ) : (
              <HistogramChart
                data={data.job_duration_hist}
                xTitle="Job Duration (hours)"
                yTitle="Percentage of Jobs (%)"
                defaultColor="#28a745"
                colorMap={null}
                isHistogram={false}
                showMedianMean={true}
                unit="h"
                decimalPlaces={1}
                chartColors={chartColors}
              />
            )}
            <ChartCaption text="Job duration split by the colour dimension; without one, the distribution of durations across jobs." />
          </div>
        )}
      </div>
    </section>
  );
};

export default TimingSection;
