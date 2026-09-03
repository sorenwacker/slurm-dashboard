import React from 'react';
import Plot from '../charts/Plot';
import { COLORS } from '../../theme/colors';
import { alignPreviousPeriodDates, REPORT_AXIS, REPORT_LAYOUT, REPORT_PREVIOUS_LINE } from './reportHelpers';

interface TimelineData {
  date: string;
  jobs: number;
  cpu_hours: number;
  gpu_hours: number;
  users: number;
}

interface ReportTimelinesProps {
  timeline: TimelineData[];
  previousTimeline?: TimelineData[];
  totalGpuHours: number;
  reportType: 'monthly' | 'quarterly' | 'annual';
}

type Metric = keyof Omit<TimelineData, 'date'>;

interface TimelineCardProps {
  title: string;
  description: string;
  metric: Metric;
  label: string;
  color: string;
  timeline: TimelineData[];
  previousTimeline?: TimelineData[];
  integer?: boolean;
}

/** One line chart of a metric over the period, with the previous period dashed behind it. */
const TimelineCard: React.FC<TimelineCardProps> = ({
  title,
  description,
  metric,
  label,
  color,
  timeline,
  previousTimeline,
  integer,
}) => {
  const format = integer ? '%{y}' : '%{y:,.0f}';
  return (
    <div className="report-card page-break-avoid">
      <h3>{title}</h3>
      <p className="report-description">{description}</p>
      <Plot
        data={[
          ...(previousTimeline
            ? [
                {
                  x: alignPreviousPeriodDates(timeline, previousTimeline).map((d) => d.date),
                  y: previousTimeline.map((d) => d[metric]),
                  type: 'scatter' as const,
                  mode: 'lines' as const,
                  name: 'Previous Period',
                  line: REPORT_PREVIOUS_LINE,
                  opacity: 0.5,
                  hovertemplate: `<b>%{x}</b><br>Previous ${label}: ${format}<extra></extra>`,
                },
              ]
            : []),
          {
            x: timeline.map((d) => d.date),
            y: timeline.map((d) => d[metric]),
            type: 'scatter',
            mode: 'lines',
            name: 'Current Period',
            line: { color, width: 3 },
            hovertemplate: `<b>%{x}</b><br>${label}: ${format}<extra></extra>`,
          },
        ]}
        layout={{
          ...REPORT_LAYOUT,
          height: 250,
          margin: { l: 60, r: 20, t: 10, b: 50 },
          xaxis: { ...REPORT_AXIS, title: { text: 'Date', font: { size: 11 } }, tickfont: { size: 9 }, tickangle: -45 },
          yaxis: { ...REPORT_AXIS, title: { text: label, font: { size: 11 } } },
          showlegend: Boolean(previousTimeline),
          legend: { orientation: 'h', y: -0.25, x: 0.5, xanchor: 'center', font: { size: 10 } },
        }}
        config={{ displayModeBar: false, staticPlot: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
};

const TIME_UNIT: Record<ReportTimelinesProps['reportType'], string> = {
  monthly: 'Daily',
  quarterly: 'Weekly',
  annual: 'Monthly',
};

const ReportTimelines: React.FC<ReportTimelinesProps> = ({ timeline, previousTimeline, totalGpuHours, reportType }) => {
  if (!timeline || timeline.length === 0) {
    return null;
  }

  const timeUnit = TIME_UNIT[reportType];
  const shared = { timeline, previousTimeline };

  return (
    <div className="report-cards">
      <TimelineCard
        {...shared}
        title="Active Users Over Time"
        description="Number of unique active users per period, compared with the previous period."
        metric="users"
        label="Active Users"
        color={COLORS.users}
        integer
      />
      <TimelineCard
        {...shared}
        title="Submitted Jobs Over Time"
        description="Number of jobs submitted per period, compared with the previous period."
        metric="jobs"
        label="Jobs"
        color={COLORS.total_jobs}
        integer
      />
      <TimelineCard
        {...shared}
        title={`${timeUnit} CPU Consumption`}
        description={`CPU hours consumed per ${timeUnit.toLowerCase()} period, showing high-demand periods.`}
        metric="cpu_hours"
        label="CPU Hours"
        color={COLORS.cpu_hours}
      />
      {totalGpuHours > 0 && (
        <TimelineCard
          {...shared}
          title={`${timeUnit} GPU Consumption`}
          description={`GPU hours consumed per ${timeUnit.toLowerCase()} period, showing high-demand periods.`}
          metric="gpu_hours"
          label="GPU Hours"
          color={COLORS.gpu_hours}
        />
      )}
    </div>
  );
};

export default ReportTimelines;
