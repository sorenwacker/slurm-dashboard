import React from 'react';
import Plot from '../charts/Plot';
import { COLORS } from '../../theme/colors';
import { alignPreviousPeriodDates } from './reportHelpers';

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

const ReportTimelines: React.FC<ReportTimelinesProps> = ({
  timeline,
  previousTimeline,
  totalGpuHours,
  reportType
}) => {
  if (!timeline || timeline.length === 0) {
    return null;
  }

  // Determine the time unit label based on report type
  const getTimeUnit = () => {
    switch (reportType) {
      case 'monthly':
        return 'Daily';
      case 'quarterly':
        return 'Weekly';
      case 'annual':
        return 'Monthly';
      default:
        return 'Daily';
    }
  };

  const timeUnit = getTimeUnit();

  return (
    <div style={{ marginTop: '3rem' }}>
      {/* Daily Active Users Timeline */}
      <div className="page-break-avoid" style={{
        background: 'var(--report-card-bg)',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid var(--report-border)',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
          Active Users Over Time
        </h3>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
          This chart displays the number of unique active users each day, showing user engagement trends and comparing them to the previous period.
        </p>
        <Plot
          data={[
            // Previous period trace (draw first so it appears behind)
            ...(previousTimeline ? [{
              x: alignPreviousPeriodDates(timeline, previousTimeline).map(d => d.date),
              y: previousTimeline.map(d => d.users),
              type: 'scatter' as const,
              mode: 'lines' as const,
              name: 'Previous Period',
              line: { color: '#999', width: 2, dash: 'dash' },
              opacity: 0.5,
              hovertemplate: '<b>%{x}</b><br>Previous Users: %{y}<extra></extra>',
            }] : []),
            // Current period trace (draw second so it appears on top)
            {
              x: timeline.map(d => d.date),
              y: timeline.map(d => d.users),
              type: 'scatter',
              mode: 'lines',
              name: 'Current Period',
              line: { color: '#10b981', width: 3 },
              hovertemplate: '<b>%{x}</b><br>Active Users: %{y}<extra></extra>',
            },
          ]}
          layout={{
            height: 250,
            margin: { l: 60, r: 20, t: 10, b: 50 },
            xaxis: {
              title: { text: 'Date', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 9 },
              tickangle: -45,
            },
            yaxis: {
              title: { text: 'Active Users', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 10 },
            },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            font: { color: '#000', family: 'Arial, sans-serif' },
            showlegend: previousTimeline ? true : false,
            legend: {
              orientation: 'h',
              y: -0.25,
              x: 0.5,
              xanchor: 'center',
              font: { size: 10 },
            },
          }}
          config={{ displayModeBar: false, staticPlot: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Daily Jobs Timeline */}
      <div className="page-break-avoid" style={{
        background: 'var(--report-card-bg)',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid var(--report-border)',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
          Submitted Jobs Over Time
        </h3>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
          This chart shows the number of jobs submitted daily, tracking job submission patterns and comparing them to the previous period.
        </p>
        <Plot
          data={[
            // Previous period trace (draw first so it appears behind)
            ...(previousTimeline ? [{
              x: alignPreviousPeriodDates(timeline, previousTimeline).map(d => d.date),
              y: previousTimeline.map(d => d.jobs),
              type: 'scatter' as const,
              mode: 'lines' as const,
              name: 'Previous Period',
              line: { color: '#999', width: 2, dash: 'dash' },
              opacity: 0.5,
              hovertemplate: '<b>%{x}</b><br>Previous Jobs: %{y}<extra></extra>',
            }] : []),
            // Current period trace (draw second so it appears on top)
            {
              x: timeline.map(d => d.date),
              y: timeline.map(d => d.jobs),
              type: 'scatter',
              mode: 'lines',
              name: 'Current Period',
              line: { color: '#8b5cf6', width: 3 },
              hovertemplate: '<b>%{x}</b><br>Jobs: %{y}<extra></extra>',
            },
          ]}
          layout={{
            height: 250,
            margin: { l: 60, r: 20, t: 10, b: 50 },
            xaxis: {
              title: { text: 'Date', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 9 },
              tickangle: -45,
            },
            yaxis: {
              title: { text: 'Number of Submitted Jobs', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 10 },
            },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            font: { color: '#000', family: 'Arial, sans-serif' },
            showlegend: previousTimeline ? true : false,
            legend: {
              orientation: 'h',
              y: -0.25,
              x: 0.5,
              xanchor: 'center',
              font: { size: 10 },
            },
          }}
          config={{ displayModeBar: false, staticPlot: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* CPU Consumption Timeline */}
      <div className="page-break-avoid" style={{
        background: 'var(--report-card-bg)',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid var(--report-border)',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
          {timeUnit} CPU Consumption
        </h3>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
          This chart displays CPU hours consumed per {timeUnit.toLowerCase()} period, showing CPU resource utilization trends and helping identify high-demand periods.
        </p>
        <Plot
          data={[
            // Previous period trace (draw first so it appears behind)
            ...(previousTimeline ? [{
              x: alignPreviousPeriodDates(timeline, previousTimeline).map(d => d.date),
              y: previousTimeline.map(d => d.cpu_hours),
              type: 'scatter' as const,
              mode: 'lines' as const,
              name: 'Previous Period',
              line: { color: '#999', width: 2, dash: 'dash' },
              opacity: 0.5,
              hovertemplate: '<b>%{x}</b><br>Previous CPU Hours: %{y:,.0f}<extra></extra>',
            }] : []),
            // Current period trace (draw second so it appears on top)
            {
              x: timeline.map(d => d.date),
              y: timeline.map(d => d.cpu_hours),
              type: 'scatter',
              mode: 'lines',
              name: 'Current Period',
              line: { color: COLORS.cpu_hours, width: 3 },
              hovertemplate: '<b>%{x}</b><br>CPU Hours: %{y:,.0f}<extra></extra>',
            },
          ]}
          layout={{
            height: 250,
            margin: { l: 60, r: 20, t: 10, b: 50 },
            xaxis: {
              title: { text: 'Date', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 9 },
              tickangle: -45,
            },
            yaxis: {
              title: { text: 'CPU Hours', font: { size: 11 } },
              gridcolor: '#e0e0e0',
              tickfont: { size: 10 },
            },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            font: { color: '#000', family: 'Arial, sans-serif' },
            showlegend: previousTimeline ? true : false,
            legend: {
              orientation: 'h',
              y: -0.25,
              x: 0.5,
              xanchor: 'center',
              font: { size: 10 },
            },
          }}
          config={{ displayModeBar: false, staticPlot: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* GPU Consumption Timeline */}
      {totalGpuHours > 0 && (
        <div className="page-break-avoid" style={{
          background: 'var(--report-card-bg)',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid var(--report-border)',
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#000', fontSize: '1.1rem' }}>
            {timeUnit} GPU Consumption
          </h3>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
            This chart displays GPU hours consumed per {timeUnit.toLowerCase()} period, showing GPU resource utilization trends and helping identify high-demand periods.
          </p>
          <Plot
            data={[
              // Previous period trace (draw first so it appears behind)
              ...(previousTimeline ? [{
                x: alignPreviousPeriodDates(timeline, previousTimeline).map(d => d.date),
                y: previousTimeline.map(d => d.gpu_hours),
                type: 'scatter' as const,
                mode: 'lines' as const,
                name: 'Previous Period',
                line: { color: '#999', width: 2, dash: 'dash' },
                opacity: 0.5,
                hovertemplate: '<b>%{x}</b><br>Previous GPU Hours: %{y:,.0f}<extra></extra>',
              }] : []),
              // Current period trace (draw second so it appears on top)
              {
                x: timeline.map(d => d.date),
                y: timeline.map(d => d.gpu_hours),
                type: 'scatter',
                mode: 'lines',
                name: 'Current Period',
                line: { color: COLORS.gpu_hours, width: 3 },
                hovertemplate: '<b>%{x}</b><br>GPU Hours: %{y:,.0f}<extra></extra>',
              },
            ]}
            layout={{
              height: 250,
              margin: { l: 60, r: 20, t: 10, b: 50 },
              xaxis: {
                title: { text: 'Date', font: { size: 11 } },
                gridcolor: '#e0e0e0',
                tickfont: { size: 9 },
                tickangle: -45,
              },
              yaxis: {
                title: { text: 'GPU Hours', font: { size: 11 } },
                gridcolor: '#e0e0e0',
                tickfont: { size: 10 },
              },
              plot_bgcolor: '#fafafa',
              paper_bgcolor: 'white',
              font: { color: '#000', family: 'Arial, sans-serif' },
              showlegend: previousTimeline ? true : false,
              legend: {
                orientation: 'h',
                y: -0.25,
                x: 0.5,
                xanchor: 'center',
                font: { size: 10 },
              },
            }}
            config={{ displayModeBar: false, staticPlot: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}
    </div>
  );
};

export default ReportTimelines;
