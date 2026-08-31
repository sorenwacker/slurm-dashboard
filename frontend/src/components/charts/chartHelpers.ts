import type { ChartData } from '../../types';

// Base color palette for reference (used for pie charts and fallbacks)
/** One colour per meaning across the dashboard; memory owns green, duration owns teal. */
export const SECTION_COLORS = {
  users: '#64748B',
  jobs: '#6F42C1',
  cpu: '#04A5D5',
  gpu: '#EC7300',
  memory: '#2E8B57',
  waiting: '#DC3545',
  duration: '#0F766E',
} as const;

export const COLORS = [
  '#04A5D5', '#EC7300', '#28a745', '#6f42c1', '#dc3545',
  '#17a2b8', '#ffc107', '#e83e8c', '#6c757d', '#fd7e14'
];

// Generate a distinct color using HSL color space
// This creates unlimited unique colors with good visual distinction
export const generateColorFromIndex = (index: number): string => {
  // Use golden angle approximation for better color distribution
  const goldenAngle = 137.508;
  const hue = (index * goldenAngle) % 360;

  // Vary saturation and lightness to create more distinct colors
  // This helps when there are many categories
  const saturationVariations = [75, 65, 85, 55];
  const lightnessVariations = [50, 60, 40, 55];

  const satIndex = Math.floor(index / 30) % saturationVariations.length;
  const lightIndex = Math.floor(index / 15) % lightnessVariations.length;

  const saturation = saturationVariations[satIndex];
  const lightness = lightnessVariations[lightIndex];

  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
};

// Helper function to create a consistent color mapping based on all unique labels
export const createGlobalColorMap = (allLabels: string[]): Map<string, string> => {
  const uniqueLabels = Array.from(new Set(allLabels)).sort();
  const colorMap = new Map<string, string>();

  uniqueLabels.forEach((label, index) => {
    // For first 10 labels, use the predefined colors for better consistency with existing charts
    // For labels beyond 10, use generated colors
    if (index < COLORS.length) {
      colorMap.set(label, COLORS[index]);
    } else {
      colorMap.set(label, generateColorFromIndex(index));
    }
  });
  return colorMap;
};

// Helper function to get color for a label
export const getColorForLabel = (label: string, colorMap: Map<string, string> | null, defaultColor: string): string => {
  if (colorMap && colorMap.has(label)) {
    return colorMap.get(label)!;
  }
  // If no color map (no "color by" selected), use the default color for all series
  return defaultColor;
};

// Helper function to create consistent median/mean annotations for histogram charts
export const createMedianMeanAnnotation = (
  median: number | undefined,
  average: number | undefined,
  color: string,
  decimalPlaces: number = 0,
  unit: string = '',
  chartColors?: ChartColorOptions
): Record<string, unknown>[] => {
  if (median === undefined || average === undefined) {
    return [];
  }

  const bgColor = chartColors?.legendBgColor || 'rgba(255,255,255,0.9)';
  const textColor = chartColors?.textColor || color;

  return [{
    x: 0.5,
    y: 1.05,
    xref: 'paper',
    yref: 'paper',
    text: `Median: ${median.toFixed(decimalPlaces)}${unit} | Mean: ${average.toFixed(decimalPlaces)}${unit}`,
    showarrow: false,
    font: {
      size: 12,
      color: textColor,
    },
    bgcolor: bgColor,
    bordercolor: chartColors?.legendBorderColor || color,
    borderwidth: 1,
    borderpad: 4,
  }];
};

// Simplified: Generate Plotly traces from chart data
// Handles both single-series (y array) and multi-series (series array) automatically
export const generateChartTraces = (
  chartData: ChartData,
  chartType: 'area' | 'bar',
  defaultColor: string,
  colorMap: Map<string, string> | null,
  defaultName: string = ''
): Record<string, unknown>[] => {
  if (!chartData || !chartData.x || chartData.x.length === 0) {
    return [];
  }

  // Multi-series data (grouped by color_by)
  if (chartData.series && chartData.series.length > 0) {
    // If no color map (color by "None"), aggregate all series into one
    if (!colorMap) {
      // Sum up all series data for each x value
      const aggregatedData = chartData.x.map((_, index) =>
        chartData.series!.reduce((sum, series) => sum + (series.data[index] || 0), 0)
      );

      if (chartType === 'area') {
        return [{
          x: chartData.x,
          y: aggregatedData,
          type: 'scatter',
          mode: 'lines',
          fill: 'tozeroy',
          marker: { color: defaultColor },
          line: { color: defaultColor },
          showlegend: false,
          hovertemplate: 'Period: %{x}<br>Value: %{y:,.0f}<extra></extra>',
        }];
      } else {
        // Build custom data with hardware config if available
        let customdata: string[] | undefined = undefined;
        let hovertemplate = '%{x}<br>Value: %{y:,.1f}';

        if (chartData.hardware_config) {
          customdata = chartData.x.map(node => {
            const hw = chartData.hardware_config![String(node)];
            if (hw) {
              return `<br>Configured: ${hw.cpu_cores} cores, ${hw.gpu_count} GPUs`;
            }
            return '';
          });
          hovertemplate = '%{x}<br>Value: %{y:,.1f}%{customdata}<extra></extra>';
        } else {
          hovertemplate = '%{x}<br>Value: %{y:,.0f}<extra></extra>';
        }

        return [{
          x: chartData.x,
          y: aggregatedData,
          type: 'bar',
          marker: { color: defaultColor },
          showlegend: false,
          customdata: customdata,
          hovertemplate: hovertemplate,
        }];
      }
    }

    // With color map, show all series with their respective colors
    if (chartType === 'area') {
      // Stacked area chart
      return chartData.series.map((series, index) => {
        const color = getColorForLabel(String(series.name), colorMap, defaultColor);
        return {
          x: chartData.x,
          y: series.data,
          type: 'scatter',
          mode: 'lines',
          fill: index === 0 ? 'tozeroy' : 'tonexty',
          stackgroup: 'one',
          name: String(series.name),
          marker: { color: color },
          hovertemplate: '<b>%{fullData.name}</b><br>Period: %{x}<br>Value: %{y:,.0f}<extra></extra>',
        };
      });
    } else {
      // Stacked bar chart
      return chartData.series.map((series) => {
        // Build custom data with hardware config if available
        let customdata: string[] | undefined = undefined;
        let hovertemplate = '<b>%{fullData.name}</b><br>%{x}<br>Value: %{y:,.1f}';

        if (chartData.hardware_config) {
          customdata = chartData.x.map(node => {
            const hw = chartData.hardware_config![String(node)];
            if (hw) {
              return `<br>Configured: ${hw.cpu_cores} cores, ${hw.gpu_count} GPUs`;
            }
            return '';
          });
          hovertemplate = '<b>%{fullData.name}</b><br>%{x}<br>Value: %{y:,.1f}%{customdata}<extra></extra>';
        } else {
          hovertemplate = '<b>%{fullData.name}</b><br>%{x}<br>Value: %{y:,.0f}<extra></extra>';
        }

        return {
          x: chartData.x,
          y: series.data,
          type: 'bar',
          name: String(series.name),
          marker: { color: getColorForLabel(String(series.name), colorMap, defaultColor) },
          customdata: customdata,
          hovertemplate: hovertemplate,
        };
      });
    }
  }

  // Single-series data (no grouping)
  if (chartData.y) {
    if (chartType === 'area') {
      // Simple area chart
      return [{
        x: chartData.x,
        y: chartData.y,
        type: 'scatter',
        mode: 'lines+markers',
        fill: 'tozeroy',
        line: { color: defaultColor, width: 2 },
        marker: { color: defaultColor, size: 8 },
        name: defaultName,
        hovertemplate: '<b>%{fullData.name}</b><br>Period: %{x}<br>Value: %{y:,.0f}<extra></extra>',
      }];
    } else {
      // Simple bar chart - color each bar based on category if we have a colorMap
      // If no colorMap, use the default color for all bars (consistent single color)
      let colors: string | string[];

      if (colorMap) {
        // Color each bar based on category from colorMap or generated color
        colors = chartData.x.map((category, idx) => {
          const categoryStr = String(category);
          if (colorMap.has(categoryStr)) {
            return colorMap.get(categoryStr)!;
          }
          return generateColorFromIndex(idx);
        });
      } else {
        // No colorMap: use single default color for all bars
        colors = defaultColor;
      }

      // Build custom hover text with hardware config if available
      let hovertemplate = '<b>%{x}</b><br>Value: %{y:,.1f}';
      let customdata: string[] | undefined = undefined;

      if (chartData.hardware_config) {
        customdata = chartData.x.map(node => {
          const hw = chartData.hardware_config![String(node)];
          if (hw) {
            return `<br>Configured: ${hw.cpu_cores} cores, ${hw.gpu_count} GPUs`;
          }
          return '';
        });
        hovertemplate = '<b>%{x}</b><br>Value: %{y:,.1f}%{customdata}<extra></extra>';
      } else {
        hovertemplate = '<b>%{x}</b><br>Value: %{y:,.0f}<extra></extra>';
      }

      return [{
        x: chartData.x,
        y: chartData.y,
        type: 'bar',
        marker: { color: colors },
        name: defaultName,
        customdata: customdata,
        hovertemplate: hovertemplate,
      }];
    }
  }

  return [];
};

// Chart color options for dark/light mode support
export interface ChartColorOptions {
  gridColor?: string;
  textColor?: string;
  hoverBgColor?: string;
  hoverBorderColor?: string;
  hoverTextColor?: string;
  legendBgColor?: string;
  legendBorderColor?: string;
}

// Helper function to invert color brightness for dark mode
// In light mode: better values = brighter (toward white)
// In dark mode: better values = darker (toward black), darkest colors stay unchanged
export const adjustColorForDarkMode = (color: string, isDark: boolean): string => {
  if (!isDark) return color;

  // Parse hex color
  let hex = color.replace('#', '');
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }

  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  // Calculate brightness (0-255)
  const brightness = (r + g + b) / 3;

  // Dark/saturated colors (brightness < 95) stay unchanged
  // This keeps #cc0000 (red, ~68) and #28a745 (green, ~92) intact
  if (brightness < 95) {
    return color;
  }

  // For colors above threshold: darken based on brightness
  // brightness 255 -> factor ~0.03 (nearly black)
  // brightness 95 -> factor ~1.0 (unchanged)
  const normalizedBrightness = (brightness - 95) / (255 - 95); // 0 to 1
  const factor = Math.pow(1 - normalizedBrightness, 2);

  const newR = Math.round(r * factor);
  const newG = Math.round(g * factor);
  const newB = Math.round(b * factor);

  const toHex = (n: number) => n.toString(16).padStart(2, '0');
  return `#${toHex(newR)}${toHex(newG)}${toHex(newB)}`;
};

// Default light mode colors
const defaultColors: ChartColorOptions = {
  gridColor: 'rgba(128, 128, 128, 0.1)',
  textColor: '#333',
  hoverBgColor: 'white',
  hoverBorderColor: '#ddd',
  hoverTextColor: 'black',
  legendBgColor: 'rgba(255, 255, 255, 0.9)',
  legendBorderColor: '#ddd',
};

// Common layout settings for better chart consistency
export const getCommonLayout = (
  xTitle: string,
  yTitle: string,
  showLegend: boolean = false,
  colors: ChartColorOptions = {}
) => {
  const c = { ...defaultColors, ...colors };

  return {
    autosize: true,
    margin: { l: 80, r: showLegend ? 220 : 20, t: 20, b: 80 },
    xaxis: {
      title: {
        text: xTitle,
        font: { size: 14, color: c.textColor },
        standoff: 10,
      },
      showgrid: true,
      gridcolor: c.gridColor,
      zeroline: false,
      automargin: true,
      tickfont: { color: c.textColor },
    },
    yaxis: {
      title: {
        text: yTitle,
        font: { size: 14, color: c.textColor },
        standoff: 10,
      },
      showgrid: true,
      gridcolor: c.gridColor,
      zeroline: false,
      tickformat: ',',
      automargin: true,
      tickfont: { color: c.textColor },
    },
    hovermode: 'x unified',
    hoverlabel: {
      bgcolor: c.hoverBgColor,
      bordercolor: c.hoverBorderColor,
      font: { color: c.hoverTextColor, size: 12 },
      namelength: -1,
    },
    showlegend: showLegend,
    legend: {
      x: 1.01,
      y: 1,
      xanchor: 'left',
      yanchor: 'top',
      bgcolor: c.legendBgColor,
      bordercolor: c.legendBorderColor,
      borderwidth: 1,
      font: { size: 10, color: c.textColor },
    },
    plot_bgcolor: 'rgba(0, 0, 0, 0)',
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
  };
};

// Common config for all charts
export const getCommonConfig = () => ({
  responsive: true,
  displayModeBar: 'hover',  // Show toolbar only on hover
  displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  toImageButtonOptions: {
    format: 'png',
    filename: 'slurm_chart',
    height: 800,
    width: 1200,
    scale: 2,
  },
});
