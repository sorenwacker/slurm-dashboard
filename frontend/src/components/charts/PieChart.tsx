import React from 'react';
import Plot from './Plot';
import type { PieChartData } from '../../types';
import { COLORS, getCommonConfig, type ChartColorOptions } from './chartHelpers';

interface PieChartProps {
  data: PieChartData;
  colors?: string[];
  valueLabel?: string;  // Custom label for values (e.g., "Days active", "Jobs")
  chartColors?: ChartColorOptions;
}

const PieChart: React.FC<PieChartProps> = ({
  data,
  colors = COLORS,
  valueLabel = 'Jobs',
  chartColors,
}) => {
  if (!data || !data.labels || !data.values || data.labels.length === 0) {
    return null;
  }

  return (
    <div className="chart-container">
      <Plot
        data={[
          {
            labels: data.labels,
            values: data.values,
            type: 'pie',
            marker: { colors: colors },
            textposition: 'inside',
            textinfo: 'label+percent',
            hovertemplate: `<b>%{label}</b><br>${valueLabel}: %{value:,.0f}<br>Percentage: %{percent}<extra></extra>`,
          },
        ]}
        layout={{
          autosize: true,
          margin: { l: 20, r: 20, t: 20, b: 20 },
          showlegend: true,
          legend: {
            x: 1.05,
            y: 0.5,
            xanchor: 'left',
            yanchor: 'middle',
            font: { size: 10, color: chartColors?.textColor || '#333' },
          },
          plot_bgcolor: 'rgba(0, 0, 0, 0)',
          paper_bgcolor: 'rgba(0, 0, 0, 0)',
        }}
        useResizeHandler={true}
        style={{ width: '100%', height: '400px' }}
        config={getCommonConfig()}
      />
    </div>
  );
};

export default PieChart;
