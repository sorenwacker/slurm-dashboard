import React from 'react';
import Plot from './Plot';
import type { TrendData } from '../../types';

import { getColorForLabel, getCommonLayout, getCommonConfig, type ChartColorOptions } from './chartHelpers';

interface TimelineChartProps {
  data: Omit<TrendData, 'stats'> & Partial<Pick<TrendData, 'stats'>>;
  xTitle: string;
  yTitle: string;
  colorMap: Map<string, string> | null;
  defaultColor?: string;
  statistic?: string;
  chartColors?: ChartColorOptions;
}

const TimelineChart: React.FC<TimelineChartProps> = ({
  data,
  xTitle,
  yTitle,
  colorMap,
  defaultColor = '#0F766E',
  statistic = 'median',
  chartColors,
}) => {
  if (!data || !data.x || data.x.length === 0) {
    return null;
  }

  const generateTraces = () => {
    // Multi-line mode when grouped (series data present)
    if (data.series && data.series.length > 0) {
      return data.series.map((series) => ({
        x: data.x,
        y: series.data,
        type: 'scatter',
        mode: 'lines+markers',
        marker: { color: getColorForLabel(series.name, colorMap, defaultColor), size: 8 },
        line: { color: getColorForLabel(series.name, colorMap, defaultColor), width: 3 },
        name: series.name,
      }));
    }

    if (!data.stats) return [];

    // Single line mode with only P25-P75 range
    return [
      // P75 upper bound
      {
        x: data.x,
        y: data.stats.p75,
        type: 'scatter',
        mode: 'lines',
        line: { width: 0 },
        showlegend: false,
        hoverinfo: 'skip',
      },
      // P25-P75 shaded range (using preferred color with transparency)
      {
        x: data.x,
        y: data.stats.p25,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: `${defaultColor}30`, // Add transparency to the default color (hex alpha)
        line: { width: 0 },
        name: 'P25-P75 Range',
        showlegend: true,
        hoverinfo: 'skip',
      },
      // Selected statistic line
      {
        x: data.x,
        y: data.stats[statistic as keyof typeof data.stats],
        type: 'scatter',
        mode: 'lines+markers',
        marker: { color: defaultColor, size: 6 },
        line: { color: defaultColor, width: 2 },
        name: statistic.toUpperCase(),
      },
    ];
  };

  const baseLayout = getCommonLayout(xTitle, yTitle, false, chartColors);

  return (
    <div className="chart-container">
      <Plot
        data={generateTraces()}
        layout={{
          ...baseLayout,
          showlegend: true,
          legend: {
            x: 0.02,
            y: 0.98,
            xanchor: 'left',
            yanchor: 'top',
            bgcolor: chartColors?.legendBgColor || 'rgba(255, 255, 255, 0.8)',
            bordercolor: chartColors?.legendBorderColor || '#ddd',
            borderwidth: 1,
            font: { size: 10, color: chartColors?.textColor || '#333' },
          },
        }}
        useResizeHandler={true}
        style={{ width: '100%', height: '400px' }}
        config={getCommonConfig()}
      />
    </div>
  );
};

export default TimelineChart;
