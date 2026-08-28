import React from 'react';
import Plot from 'react-plotly.js';
import type { ChartColorOptions } from './chartHelpers';

interface GaugeChartProps {
  value: number;  // 0-100 percentage
  title: string;
  color: string;  // resource color, same as the matching charts
  chartColors?: ChartColorOptions;
}

/** Flat single-color arc matching the area and bar charts; no bands, border or needle. */
const GaugeChart: React.FC<GaugeChartProps> = ({ value, title, color, chartColors }) => {
  const textColor = chartColors?.textColor || '#333';
  const isDark = textColor === '#ffffff' || textColor === '#fff';
  const track = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.06)';

  return (
    <div>
      <h3 style={{ textAlign: 'center' }}>{title}</h3>
      <div style={{ width: '100%', height: '170px' }}>
        <Plot
          data={[
            {
              type: 'indicator',
              mode: 'gauge+number',
              value,
              number: { suffix: '%', font: { size: 32, color: textColor }, valueformat: '.1f' },
              gauge: {
                shape: 'angular',
                axis: {
                  range: [0, 100],
                  tickvals: [0, 100],
                  ticktext: ['0%', '100%'],
                  tickfont: { color: textColor, size: 12 },
                  tickwidth: 0,
                  ticklen: 4,
                  tickcolor: 'rgba(0,0,0,0)',
                },
                bar: { color, thickness: 0.35 },
                bgcolor: track,
                borderwidth: 0,
              },
            },
          ]}
          layout={{
            autosize: true,
            margin: { l: 24, r: 24, t: 10, b: 0 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: { color: textColor },
          }}
          useResizeHandler={true}
          style={{ width: '100%', height: '100%' }}
          config={{ responsive: true, displayModeBar: false }}
        />
      </div>
    </div>
  );
};

export default GaugeChart;
