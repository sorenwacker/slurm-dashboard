import React, { useMemo } from 'react';
import type { AggregatedChartsResponse } from '../types';
import { createGlobalColorMap } from './charts/chartHelpers';
import { RESOURCE_SECTIONS } from './charts/resourceConfigs';
import useDarkMode from '../hooks/useDarkMode';
import { useTimingStats } from '../hooks/useTimingStats';
import { useProcessedNodeData, useClusterUtilization } from '../hooks/useProcessedNodeData';
import { UsersJobsSection, ResourceSection, TimingSection } from './charts/sections';

interface ChartsProps {
  data: AggregatedChartsResponse | undefined;
  hideUnusedNodes: boolean;
  sortByUsage: boolean;
  normalizeNodeUsage: boolean;
  colorBy: string;
  periodType: string;
}

const Charts: React.FC<ChartsProps> = ({
  data,
  hideUnusedNodes,
  sortByUsage,
  normalizeNodeUsage,
  colorBy,
  periodType,
}) => {
  const { chartColors, isDark } = useDarkMode();
  const timingStats = useTimingStats(data);
  const processedNodeData = useProcessedNodeData(data, hideUnusedNodes, sortByUsage, normalizeNodeUsage);
  const clusterUtilization = useClusterUtilization(data, normalizeNodeUsage);

  // Create color map for consistent colors across charts
  const colorMap = useMemo(() => {
    if (!data || !colorBy) {
      return null;
    }

    const allLabels: string[] = [];

    const extractSeriesNames = (chartData: { series?: { name: string | number }[] } | undefined) => {
      chartData?.series?.forEach((series) => allLabels.push(String(series.name)));
    };

    // NOTE: Timing section charts are excluded from color mapping
    extractSeriesNames(data.active_users_over_time);
    extractSeriesNames(data.jobs_over_time);
    extractSeriesNames(data.cpu_usage_over_time);
    extractSeriesNames(data.gpu_usage_over_time);
    extractSeriesNames(data.memory_usage_over_time);
    extractSeriesNames(data.cpu_hours_by_account);
    extractSeriesNames(data.gpu_hours_by_account);
    extractSeriesNames(data.memory_hours_by_account);
    extractSeriesNames(data.node_cpu_usage);
    extractSeriesNames(data.node_gpu_usage);
    extractSeriesNames(data.node_memory_usage);

    return allLabels.length > 0 ? createGlobalColorMap(allLabels) : null;
  }, [data, colorBy]);

  if (!data) {
    return (
      <div className="card">
        <p className="card-empty">
          No data available. Select a cluster and date range to view charts.
        </p>
      </div>
    );
  }

  const nodeCharts = {
    cpu: processedNodeData.cpu,
    gpu: processedNodeData.gpu,
    memory: processedNodeData.memory,
  };

  return (
    <div>
      <UsersJobsSection
        data={data}
        colorMap={colorMap}
        colorBy={colorBy}
        periodType={periodType}
        chartColors={chartColors}
      />

      {RESOURCE_SECTIONS.map((config) => (
        <ResourceSection
          key={config.title}
          config={config}
          data={data}
          colorMap={colorMap}
          colorBy={colorBy}
          periodType={periodType}
          chartColors={chartColors}
          nodeChart={nodeCharts[config.gaugeKey]}
          utilization={clusterUtilization}
        />
      ))}

      <TimingSection
        data={data}
        colorMap={colorMap}
        colorBy={colorBy}
        chartColors={chartColors}
        isDark={isDark}
        timingStats={timingStats}
      />
    </div>
  );
};

export default Charts;
