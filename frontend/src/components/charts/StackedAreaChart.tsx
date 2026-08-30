import React from 'react';
import Plot from './Plot';
import type { ChartData } from '../../types';
import { generateChartTraces, getCommonLayout, getCommonConfig, type ChartColorOptions } from './chartHelpers';

interface StackedAreaChartProps {
  data: ChartData;
  xTitle: string;
  yTitle: string;
  defaultColor: string;
  colorMap: Map<string, string> | null;
  defaultName?: string;
  chartType?: 'area' | 'bar';
  barMode?: 'stack' | 'group';
  periodType?: string;
  chartColors?: ChartColorOptions;
}

const StackedAreaChart: React.FC<StackedAreaChartProps> = ({
  data,
  xTitle,
  yTitle,
  defaultColor,
  colorMap,
  defaultName = '',
  chartType = 'area',
  barMode = 'stack',
  periodType,
  chartColors,
}) => {
  if (!data || !data.x || data.x.length === 0) {
    return null;
  }

  const showLegend = data.series && data.series.length > 1;

  const layout: any = {
    ...getCommonLayout(xTitle, yTitle, showLegend, chartColors),
  };

  // Add day of week to daily x-axis labels
  if (periodType === 'day') {
    layout.xaxis.tickformat = '%a %b %-d';  // e.g., "Mon Jan 1"
  }

  // Add barmode for bar charts and use 'closest' hover mode to prevent tooltip cutoff
  if (chartType === 'bar') {
    layout.barmode = barMode;
    layout.hovermode = 'closest';  // Prevents tooltip from being cut off at chart edges
  }

  return (
    <div className="chart-container">
      <Plot
        data={generateChartTraces(data, chartType, defaultColor, colorMap, defaultName)}
        layout={layout}
        useResizeHandler={true}
        style={{ width: '100%', height: '400px' }}
        config={getCommonConfig()}
      />
    </div>
  );
};

export default StackedAreaChart;
