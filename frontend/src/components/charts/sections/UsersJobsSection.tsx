import React from 'react';
import ChartCaption from '../ChartCaption';
import type { AggregatedChartsResponse } from '../../../types';
import type { ChartColors } from '../../../hooks/useDarkMode';
import StackedAreaChart from '../StackedAreaChart';
import PieChart from '../PieChart';
import HistogramChart from '../HistogramChart';
import { COLORS, SECTION_COLORS } from '../chartHelpers';

interface UsersJobsSectionProps {
  data: AggregatedChartsResponse;
  colorMap: Map<string, string> | null;
  colorBy: string;
  periodType: string;
  chartColors: ChartColors;
}

const UsersJobsSection: React.FC<UsersJobsSectionProps> = ({
  data,
  colorMap,
  colorBy,
  periodType,
  chartColors,
}) => {
  return (
    <section className="section-combined">
      <div className="users-jobs-container">
        {/* Users Section */}
        <div className="subsection">
          <h2 className="subsection-header">Users</h2>
          <div className="chart-row-2col">
            {data.active_users_over_time && data.active_users_over_time.x.length > 0 && (
              <div className="card">
                <h3>Active Users</h3>
                <StackedAreaChart
                  data={data.active_users_over_time}
                  xTitle="Period"
                  yTitle="Number of Users"
                  defaultColor={SECTION_COLORS.users}
                  colorMap={colorMap}
                  defaultName="Active Users"
                  chartType="area"
                  periodType={periodType}
                  chartColors={chartColors}
                />
                <ChartCaption text="Distinct users with at least one job starting in the period." />
              </div>
            )}
            {data.user_activity_frequency && (
              (data.user_activity_frequency.type === 'pie' && (data.user_activity_frequency.labels?.length ?? 0) > 0) ||
              (data.user_activity_frequency.x && data.user_activity_frequency.x.length > 0)
            ) && (
              <div className="card">
                <h3>
                  {data.user_activity_frequency.type === 'pie'
                    ? (colorBy === 'User' ? 'Most Active Users' : `User Activity by ${colorBy}`)
                    : 'User Activity Frequency'}
                  <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                    {' '}({data.user_activity_frequency.total_users} users over {data.user_activity_frequency.total_periods} {data.user_activity_frequency.period_label})
                  </span>
                </h3>
                {data.user_activity_frequency.type === 'pie' ? (
                  <PieChart
                    data={{
                      labels: data.user_activity_frequency.labels || [],
                      values: data.user_activity_frequency.values || [],
                    }}
                    valueLabel={colorBy === 'User'
                      ? `Active ${data.user_activity_frequency.period_label || 'periods'}`
                      : `User-${data.user_activity_frequency.period_label || 'periods'}`}
                    colors={colorMap ? (data.user_activity_frequency.labels || []).map((label, idx) =>
                      colorMap.get(label) || COLORS[idx % COLORS.length]
                    ) : undefined}
                    chartColors={chartColors}
                  />
                ) : (
                  <HistogramChart
                    data={data.user_activity_frequency}
                    xTitle={`Active ${data.user_activity_frequency.period_label || 'periods'}`}
                    yTitle="Number of Users"
                    defaultColor={SECTION_COLORS.users}
                    colorMap={null}
                    isHistogram={true}
                    showMedianMean={true}
                    unit={` ${data.user_activity_frequency.period_label || 'periods'}`}
                    decimalPlaces={1}
                    chartColors={chartColors}
                  />
                )}
                <ChartCaption text="How many periods each user was active in: users on the x-axis grouped by number of active periods." />
              </div>
            )}
          </div>
        </div>

        {/* Jobs Section */}
        <div className="subsection">
          <h2 className="subsection-header">Jobs</h2>
          <div className="chart-row-3col">
            {data.jobs_over_time && data.jobs_over_time.x.length > 0 && (
              <div className="card">
                <h3>Number of Submitted Jobs</h3>
                <StackedAreaChart
                  data={data.jobs_over_time}
                  xTitle="Period"
                  yTitle="Number of Submitted Jobs"
                  defaultColor="#6f42c1"
                  colorMap={colorMap}
                  defaultName="Jobs"
                  chartType="area"
                  periodType={periodType}
                  chartColors={chartColors}
                />
                <ChartCaption text="Jobs submitted per period, stacked by the selected colour dimension." />
              </div>
            )}
            {data.jobs_distribution && (
              (data.jobs_distribution.type === 'pie' && (data.jobs_distribution.labels?.length ?? 0) > 0) ||
              (data.jobs_distribution.x && data.jobs_distribution.x.length > 0)
            ) && (
              <div className="card">
                <h3>
                  {data.jobs_distribution.type === 'pie'
                    ? `Jobs by ${colorBy}`
                    : 'Jobs Distribution'}
                  <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                    {' '}({data.summary.total_jobs.toLocaleString()} jobs)
                  </span>
                </h3>
                {data.jobs_distribution.type === 'pie' ? (
                  <PieChart
                    data={{
                      labels: data.jobs_distribution.labels || [],
                      values: data.jobs_distribution.values || [],
                    }}
                    valueLabel="Jobs"
                    colors={colorMap ? (data.jobs_distribution.labels || []).map((label, idx) =>
                      colorMap.get(label) || COLORS[idx % COLORS.length]
                    ) : undefined}
                    chartColors={chartColors}
                  />
                ) : (
                  <HistogramChart
                    data={data.jobs_distribution}
                    xTitle="Jobs per Period"
                    yTitle="Count"
                    defaultColor="#6f42c1"
                    colorMap={null}
                    isHistogram={true}
                    showMedianMean={true}
                    unit=""
                    decimalPlaces={0}
                    chartColors={chartColors}
                  />
                )}
                <ChartCaption text="Jobs per user, or per colour dimension when one is selected." />
              </div>
            )}
            {data.nodes_per_job && data.nodes_per_job.x.length > 0 && (
              <div className="card">
                <h3>
                  Nodes per Job{' '}
                  <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>(all jobs)</span>
                </h3>
                <HistogramChart
                  data={data.nodes_per_job}
                  xTitle="Number of Nodes"
                  yTitle="Number of Jobs"
                  defaultColor={SECTION_COLORS.nodes}
                  colorMap={colorMap}
                  isHistogram={true}
                  chartColors={chartColors}
                />
                <ChartCaption text="Number of jobs per number of allocated nodes." />
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default UsersJobsSection;
