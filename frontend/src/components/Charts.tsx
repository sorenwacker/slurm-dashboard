import React, { useMemo } from 'react';
import type { AggregatedChartsResponse } from '../types';
import { createGlobalColorMap } from './charts/chartHelpers';
import useDarkMode from '../hooks/useDarkMode';
import { useTimingStats } from '../hooks/useTimingStats';
import { useProcessedNodeData, useClusterUtilization } from '../hooks/useProcessedNodeData';
import {
  UsersJobsSection,
  UsageSection,
  TimingSection,
  ResourcesSection,
} from './charts/sections';

interface ChartsProps {
  data: AggregatedChartsResponse | undefined;
  hideUnusedNodes: boolean;
  setHideUnusedNodes: (value: boolean) => void;
  sortByUsage: boolean;
  setSortByUsage: (value: boolean) => void;
  normalizeNodeUsage: boolean;
  setNormalizeNodeUsage: (value: boolean) => void;
  colorBy: string;
  periodType: string;
}

const Charts: React.FC<ChartsProps> = ({
  data,
  hideUnusedNodes,
  setHideUnusedNodes,
  sortByUsage,
  setSortByUsage,
  normalizeNodeUsage,
  setNormalizeNodeUsage,
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

    const extractSeriesNames = (chartData: any) => {
      if (chartData?.series) {
        chartData.series.forEach((series: any) => allLabels.push(String(series.name)));
      }
    };

    // Extract from all chart data that has series
    // NOTE: Timing section charts are excluded from color mapping
    extractSeriesNames(data.active_users_over_time);
    extractSeriesNames(data.jobs_over_time);
    extractSeriesNames(data.cpu_usage_over_time);
    extractSeriesNames(data.gpu_usage_over_time);
    extractSeriesNames(data.cpu_hours_by_account);
    extractSeriesNames(data.gpu_hours_by_account);
    extractSeriesNames(data.node_cpu_usage);
    extractSeriesNames(data.node_gpu_usage);

    return allLabels.length > 0 ? createGlobalColorMap(allLabels) : null;
  }, [data, colorBy]);

  if (!data) {
    return (
      <div className="card">
        <p style={{ textAlign: 'center', color: '#666', padding: '2rem' }}>
          No data available. Select a cluster and date range to view charts.
        </p>
      </div>
    );
  }

  return (
    <div>
      <UsersJobsSection
        data={data}
        colorMap={colorMap}
        colorBy={colorBy}
        periodType={periodType}
        chartColors={chartColors}
      />

      <UsageSection
        data={data}
        colorMap={colorMap}
        colorBy={colorBy}
        periodType={periodType}
        chartColors={chartColors}
        processedNodeData={processedNodeData}
        clusterUtilization={clusterUtilization}
        hideUnusedNodes={hideUnusedNodes}
        setHideUnusedNodes={setHideUnusedNodes}
        sortByUsage={sortByUsage}
        setSortByUsage={setSortByUsage}
        normalizeNodeUsage={normalizeNodeUsage}
        setNormalizeNodeUsage={setNormalizeNodeUsage}
      />

      <TimingSection
        data={data}
        colorMap={colorMap}
        colorBy={colorBy}
        chartColors={chartColors}
        isDark={isDark}
        timingStats={timingStats}
      />

      <ResourcesSection
        data={data}
        colorMap={colorMap}
        chartColors={chartColors}
      />
    </div>
  );
};

export default Charts;
