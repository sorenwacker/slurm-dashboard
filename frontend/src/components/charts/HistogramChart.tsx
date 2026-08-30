import React from 'react';
import Plot from './Plot';
import type { ChartData } from '../../types';
import {
  generateChartTraces,
  getColorForLabel,
  getCommonLayout,
  getCommonConfig,
  createMedianMeanAnnotation,
  type ChartColorOptions,
} from './chartHelpers';

interface HistogramChartProps {
  data: ChartData;
  xTitle: string;
  yTitle: string;
  defaultColor: string;
  colorMap: Map<string, string> | null;
  isHistogram?: boolean;
  showMedianMean?: boolean;
  unit?: string;
  decimalPlaces?: number;
  tickAngle?: number;
  barMode?: 'stack' | 'group' | 'overlay';
  chartColors?: ChartColorOptions;
}

const HistogramChart: React.FC<HistogramChartProps> = ({
  data,
  xTitle,
  yTitle,
  defaultColor,
  colorMap,
  isHistogram = false,
  showMedianMean = false,
  unit = '',
  decimalPlaces = 0,
  tickAngle,
  barMode = 'overlay',
  chartColors,
}) => {
  if (!data || !data.x || data.x.length === 0) {
    return null;
  }

  const generateTraces = () => {
    // For histogram mode with series (grouped bar charts)
    if (isHistogram && data.series && data.series.length > 0) {
      return data.series.map((series: any, _idx: number) => ({
        x: data.x,
        y: series.data,
        type: 'bar',
        marker: { color: getColorForLabel(series.name, colorMap, defaultColor) },
        name: series.name,
        hovertemplate: '<b>%{x}</b><br>Jobs: %{y:.1f}%<extra></extra>',
      }));
    }

    // For histogram mode without series (single histogram)
    if (isHistogram) {
      return [
        {
          x: data.x,
          y: data.y,
          type: 'bar',
          marker: { color: defaultColor },
          name: xTitle,
          hovertemplate: `<b>${xTitle}</b><br>Range: %{x}<br>Count: %{y:,.0f}<extra></extra>`,
        },
      ];
    }

    // For regular bar charts, use the trace generator
    return generateChartTraces(data, 'bar', defaultColor, colorMap);
  };

  const layout: any = {
    ...getCommonLayout(xTitle, yTitle, data.series && data.series.length > 1, chartColors),
  };

  // For histogram mode with string bin labels, force categorical x-axis to align labels with bars
  // Only apply for data with string x values (bin labels like "1-10", "11-20")
  // Don't apply for numeric x values (like CPUs per job: 1, 2, 4, 8...)
  if (isHistogram && data.x.length > 0 && typeof data.x[0] === 'string') {
    layout.xaxis = {
      ...layout.xaxis,
      type: 'category',
    };
  }

  // Add tick angle if specified
  if (tickAngle !== undefined) {
    layout.xaxis = {
      ...layout.xaxis,
      tickangle: tickAngle,
    };
  }

  // Add bar mode if specified
  if (barMode !== 'overlay') {
    layout.barmode = barMode;
  }

  // Add median/mean annotation if requested
  if (showMedianMean) {
    layout.annotations = createMedianMeanAnnotation(
      data.median,
      data.average || data.mean,
      defaultColor,
      decimalPlaces,
      unit,
      chartColors
    );
  }

  return (
    <div className="chart-container">
      <Plot
        data={generateTraces()}
        layout={layout}
        useResizeHandler={true}
        style={{ width: '100%', height: '400px' }}
        config={getCommonConfig()}
      />
    </div>
  );
};

export default HistogramChart;
