import React from 'react';
import Plot from './Plot';
import { getColorForLabel, getCommonLayout, getCommonConfig, type ChartColorOptions } from './chartHelpers';

export interface ScatterSeries {
  name: string;
  x: number[];
  y: number[];
}

interface ScatterChartProps {
  series: ScatterSeries[];
  xTitle: string;
  yTitle: string;
  defaultColor: string;
  colorMap: Map<string, string> | null;
  chartColors?: ChartColorOptions;
}

/** Log-log scatter of per-job value pairs; one trace per colour group. */
const ScatterChart: React.FC<ScatterChartProps> = ({ series, xTitle, yTitle, defaultColor, colorMap, chartColors }) => {
  if (!series.length) return null;

  const traces = series.map((s) => ({
    x: s.x,
    y: s.y,
    type: 'scatter',
    mode: 'markers',
    marker: {
      color: series.length > 1 ? getColorForLabel(s.name, colorMap, defaultColor) : defaultColor,
      size: 4,
      opacity: 0.35,
    },
    name: s.name,
    hovertemplate: `${xTitle}: %{x:.2f}h<br>${yTitle}: %{y:.2f}h<extra>%{fullData.name}</extra>`,
  }));

  const layout: Record<string, unknown> = {
    ...getCommonLayout(xTitle, yTitle, series.length > 1, chartColors),
  };
  layout.xaxis = { ...(layout.xaxis as object), type: 'log' };
  layout.yaxis = { ...(layout.yaxis as object), type: 'log' };
  layout.hovermode = 'closest';

  return (
    <div className="chart-container">
      <Plot
        data={traces}
        layout={layout}
        useResizeHandler={true}
        style={{ width: '100%', height: '400px' }}
        config={getCommonConfig()}
      />
    </div>
  );
};

export default ScatterChart;
