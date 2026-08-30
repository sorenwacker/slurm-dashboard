import React from 'react';
import Plot from './Plot';
import type { ChartData } from '../../types';
import { adjustColorForDarkMode } from './chartHelpers';
import type { ChartColors } from '../../hooks/useDarkMode';

interface StackedPercentageChartProps {
  data: ChartData;
  title: string;
  chartColors: ChartColors;
  isDark: boolean;
}

const StackedPercentageChart: React.FC<StackedPercentageChartProps> = ({
  data,
  title,
  chartColors,
  isDark,
}) => {
  if (!data.x || data.x.length === 0) return null;

  return (
    <div className="card">
      <h3>
        {title}{' '}
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>
          (stacked percentages)
        </span>
      </h3>
      <div className="chart-container">
        <Plot
          data={data.series?.map((series: any) => ({
            x: data.x,
            y: series.data,
            name: series.name,
            type: 'bar',
            marker: { color: adjustColorForDarkMode(series.color, isDark) },
            hovertemplate: `<b>${series.name}</b><br>%{y:.1f}%<br>Period: %{x}<extra></extra>`,
          })) || []}
          layout={{
            autosize: true,
            margin: { l: 80, r: 20, t: 20, b: 60 },
            xaxis: {
              title: { text: 'Period', font: { size: 14, color: chartColors.textColor }, standoff: 10 },
              showgrid: true,
              gridcolor: chartColors.gridColor,
              zeroline: false,
              tickfont: { color: chartColors.textColor },
            },
            yaxis: {
              title: { text: 'Percentage (%)', font: { size: 14, color: chartColors.textColor }, standoff: 10 },
              showgrid: true,
              gridcolor: chartColors.gridColor,
              zeroline: false,
              tickformat: ',',
              range: [0, 100],
              tickfont: { color: chartColors.textColor },
            },
            barmode: 'stack',
            showlegend: true,
            legend: {
              orientation: 'h',
              y: -0.2,
              x: 0.5,
              xanchor: 'center',
              yanchor: 'top',
              font: { size: 10, color: chartColors.textColor },
            },
            plot_bgcolor: 'rgba(0, 0, 0, 0)',
            paper_bgcolor: 'rgba(0, 0, 0, 0)',
            hovermode: 'x unified',
            hoverlabel: {
              bgcolor: chartColors.hoverBgColor,
              bordercolor: chartColors.hoverBorderColor,
              font: { color: chartColors.hoverTextColor },
            },
          }}
          useResizeHandler={true}
          style={{ width: '100%', height: '400px' }}
          config={{ responsive: true }}
        />
      </div>
    </div>
  );
};

export default StackedPercentageChart;
