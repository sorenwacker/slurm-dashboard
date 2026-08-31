import React from 'react';
import ChartCaption from '../ChartCaption';
import type { AggregatedChartsResponse } from '../../../types';
import type { ChartColors } from '../../../hooks/useDarkMode';
import StackedAreaChart from '../StackedAreaChart';
import PieChart from '../PieChart';
import HistogramChart from '../HistogramChart';
import GaugeChart from '../GaugeChart';
import { COLORS } from '../chartHelpers';

import { MEMORY_COVERAGE_THRESHOLD, type ProcessedNodeData } from '../../../hooks/useProcessedNodeData';
import type { ClusterUtilization } from '../../../types';

const MEMORY_COLOR = '#2E8B57';

interface UsageSectionProps {
  data: AggregatedChartsResponse;
  colorMap: Map<string, string> | null;
  colorBy: string;
  periodType: string;
  chartColors: ChartColors;
  processedNodeData: ProcessedNodeData;
  clusterUtilization: ClusterUtilization;
  hideUnusedNodes: boolean;
  setHideUnusedNodes: (value: boolean) => void;
  sortByUsage: boolean;
  setSortByUsage: (value: boolean) => void;
  normalizeNodeUsage: boolean;
  setNormalizeNodeUsage: (value: boolean) => void;
}

const UsageSection: React.FC<UsageSectionProps> = ({
  data,
  colorMap,
  colorBy,
  periodType,
  chartColors,
  processedNodeData,
  clusterUtilization,
  hideUnusedNodes,
  setHideUnusedNodes,
  sortByUsage,
  setSortByUsage,
  normalizeNodeUsage,
  setNormalizeNodeUsage,
}) => {
  return (
    <section className="section-combined">
      <div className="users-jobs-container">
        {/* CPU Usage Section */}
        <div className="subsection">
          <h2 className="subsection-header">CPU Usage</h2>
          <div className="chart-row-2col">
            {data.cpu_usage_over_time && data.cpu_usage_over_time.x.length > 0 && (
              <div className="card">
                <h3>CPU Usage</h3>
                <StackedAreaChart
                  data={data.cpu_usage_over_time}
                  xTitle="Period"
                  yTitle="CPU Hours"
                  defaultColor="#04A5D5"
                  colorMap={colorMap}
                  defaultName="CPU Hours"
                  chartType="area"
                  periodType={periodType}
                  chartColors={chartColors}
                />
                <ChartCaption text="CPU-hours (allocated CPUs times elapsed time) of jobs starting in the period." />
              </div>
            )}
            {data.cpu_hours_by_account && (
              (data.cpu_hours_by_account.type === 'pie' && (data.cpu_hours_by_account.labels?.length ?? 0) > 0) ||
              (data.cpu_hours_by_account.x && data.cpu_hours_by_account.x.length > 0)
            ) && (
              <div className="card">
                <h3>
                  {data.cpu_hours_by_account.type === 'pie'
                    ? `CPU Usage by ${colorBy}`
                    : 'CPU Usage Distribution'}
                  <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                    {' '}({Math.round(data.summary.total_cpu_hours).toLocaleString()} hours)
                  </span>
                </h3>
                {data.cpu_hours_by_account.type === 'pie' ? (
                  <PieChart
                    data={{
                      labels: data.cpu_hours_by_account.labels || [],
                      values: data.cpu_hours_by_account.values || [],
                    }}
                    valueLabel="CPU Hours"
                    colors={colorMap ? (data.cpu_hours_by_account.labels || []).map((label, idx) =>
                      colorMap.get(label) || COLORS[idx % COLORS.length]
                    ) : undefined}
                    chartColors={chartColors}
                  />
                ) : (
                  <HistogramChart
                    data={data.cpu_hours_by_account}
                    xTitle="CPU Hours per Period"
                    yTitle="Number of Periods"
                    defaultColor="#04A5D5"
                    colorMap={null}
                    isHistogram={true}
                    showMedianMean={true}
                    unit="h"
                    decimalPlaces={0}
                    chartColors={chartColors}
                  />
                )}
                <ChartCaption text="CPU-hours split by the colour dimension; without one, the distribution of CPU-hours per period." />
              </div>
            )}
          </div>
        </div>

        {/* GPU Usage Section */}
        <div className="subsection">
          <h2 className="subsection-header">GPU Usage</h2>
          <div className="chart-row-2col">
            {data.gpu_usage_over_time && data.gpu_usage_over_time.x.length > 0 && (
              <div className="card">
                <h3>GPU Usage</h3>
                <StackedAreaChart
                  data={data.gpu_usage_over_time}
                  xTitle="Period"
                  yTitle="GPU Hours"
                  defaultColor="#EC7300"
                  colorMap={colorMap}
                  defaultName="GPU Hours"
                  chartType="area"
                  periodType={periodType}
                  chartColors={chartColors}
                />
                <ChartCaption text="GPU-hours (allocated GPUs times elapsed time) of jobs starting in the period." />
              </div>
            )}
            {data.gpu_hours_by_account && (
              (data.gpu_hours_by_account.type === 'pie' && (data.gpu_hours_by_account.labels?.length ?? 0) > 0) ||
              (data.gpu_hours_by_account.x && data.gpu_hours_by_account.x.length > 0)
            ) && (
              <div className="card">
                <h3>
                  {data.gpu_hours_by_account.type === 'pie'
                    ? `GPU Usage by ${colorBy}`
                    : 'GPU Usage Distribution'}
                  <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                    {' '}({Math.round(data.summary.total_gpu_hours).toLocaleString()} hours)
                  </span>
                </h3>
                {data.gpu_hours_by_account.type === 'pie' ? (
                  <PieChart
                    data={{
                      labels: data.gpu_hours_by_account.labels || [],
                      values: data.gpu_hours_by_account.values || [],
                    }}
                    valueLabel="GPU Hours"
                    colors={colorMap ? (data.gpu_hours_by_account.labels || []).map((label, idx) =>
                      colorMap.get(label) || COLORS[idx % COLORS.length]
                    ) : undefined}
                    chartColors={chartColors}
                  />
                ) : (
                  <HistogramChart
                    data={data.gpu_hours_by_account}
                    xTitle="GPU Hours per Period"
                    yTitle="Number of Periods"
                    defaultColor="#EC7300"
                    colorMap={null}
                    isHistogram={true}
                    showMedianMean={true}
                    unit="h"
                    decimalPlaces={0}
                    chartColors={chartColors}
                  />
                )}
                <ChartCaption text="GPU-hours split by the colour dimension; without one, the distribution of GPU-hours per period." />
              </div>
            )}
          </div>
        </div>

        {/* Memory Usage Section */}
        {data.memory_usage_over_time && data.memory_usage_over_time.x.length > 0 && (
          <div className="subsection">
            <h2 className="subsection-header">Memory Usage</h2>
            <div className="chart-row-2col">
              <div className="card">
                <h3>Memory Usage</h3>
                <StackedAreaChart
                  data={data.memory_usage_over_time}
                  xTitle="Period"
                  yTitle="GB-Hours"
                  defaultColor={MEMORY_COLOR}
                  colorMap={colorMap}
                  defaultName="Memory GB-Hours"
                  chartType="area"
                  periodType={periodType}
                  chartColors={chartColors}
                />
                <ChartCaption text="Memory-hours (requested memory in GB times elapsed time) of jobs starting in the period; jobs without memory data are excluded." />
              </div>
              {data.memory_hours_by_account && (
                (data.memory_hours_by_account.type === 'pie' && (data.memory_hours_by_account.labels?.length ?? 0) > 0) ||
                (data.memory_hours_by_account.x && data.memory_hours_by_account.x.length > 0)
              ) && (
                <div className="card">
                  <h3>
                    {data.memory_hours_by_account.type === 'pie'
                      ? `Memory Usage by ${colorBy}`
                      : 'Memory Usage Distribution'}
                    <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                      {' '}({Math.round(data.summary.total_memory_gb_hours).toLocaleString()} GB-hours)
                    </span>
                  </h3>
                  {data.memory_hours_by_account.type === 'pie' ? (
                    <PieChart
                      data={{
                        labels: data.memory_hours_by_account.labels || [],
                        values: data.memory_hours_by_account.values || [],
                      }}
                      valueLabel="GB-Hours"
                      colors={colorMap ? (data.memory_hours_by_account.labels || []).map((label, idx) =>
                        colorMap.get(label) || COLORS[idx % COLORS.length]
                      ) : undefined}
                      chartColors={chartColors}
                    />
                  ) : (
                    <HistogramChart
                      data={data.memory_hours_by_account}
                      xTitle="GB-Hours per Period"
                      yTitle="Number of Periods"
                      defaultColor={MEMORY_COLOR}
                      colorMap={null}
                      isHistogram={true}
                      showMedianMean={true}
                      unit="GBh"
                      decimalPlaces={0}
                      chartColors={chartColors}
                    />
                  )}
                  <ChartCaption text="Memory-hours split by the colour dimension; without one, the distribution of memory-hours per period." />
                </div>
              )}
              {data.memory_efficiency_over_time && data.memory_efficiency_over_time.x.length > 0 && (
                <div className="card">
                  <h3>
                    Memory Efficiency
                    <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                      {' '}(peak used / requested)
                    </span>
                  </h3>
                  <StackedAreaChart
                    data={data.memory_efficiency_over_time}
                    xTitle="Period"
                    yTitle="Used (%)"
                    defaultColor={MEMORY_COLOR}
                    colorMap={null}
                    defaultName="Memory used (%)"
                    chartType="area"
                    periodType={periodType}
                    chartColors={chartColors}
                  />
                  <ChartCaption text="Sum of peak memory used divided by sum of requested memory, per period, over jobs reporting both." />
                </div>
              )}
              {data.memory_per_job && data.memory_per_job.x.length > 0 && (
                <div className="card">
                  <h3>Memory per Job</h3>
                  <HistogramChart
                    data={data.memory_per_job}
                    xTitle="Requested Memory (GB)"
                    yTitle="Number of Jobs"
                    defaultColor={MEMORY_COLOR}
                    colorMap={null}
                    chartColors={chartColors}
                  />
                  <ChartCaption text="Number of jobs per requested memory size in GB (20 most common sizes)." />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Node Usage Section */}
      {(processedNodeData.cpu?.x.length || processedNodeData.gpu?.x.length || processedNodeData.memory?.x.length) && (
        <div className="node-usage-section">
          <div className="node-usage-header">
            <h3 className="section-title">Usage by Node</h3>
            <div className="node-usage-controls">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={hideUnusedNodes}
                  onChange={(e) => setHideUnusedNodes(e.target.checked)}
                />
                <span>Hide unused</span>
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={sortByUsage}
                  onChange={(e) => setSortByUsage(e.target.checked)}
                />
                <span>Sort by usage</span>
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={normalizeNodeUsage}
                  onChange={(e) => setNormalizeNodeUsage(e.target.checked)}
                />
                <span>Normalize %</span>
              </label>
            </div>
          </div>

          {/* Utilization gauges */}
          {(clusterUtilization.cpu !== null || clusterUtilization.gpu !== null || clusterUtilization.memory !== null) && (
            <>
            <p style={{ fontSize: '0.85rem', color: '#666', margin: '0 0 0.5rem' }}>
              Capacity-weighted over nodes with known capacity that SLURM reports or that ran jobs in the selected range.
            </p>
            <div className="gauge-grid" style={{ marginBottom: 'var(--space-lg)' }}>
              {clusterUtilization.cpu !== null && (
                <div className="card gauge-card">
                  <GaugeChart
                    value={Math.round(clusterUtilization.cpu * 10) / 10}
                    title="CPU allocation"
                    color="#04A5D5"
                    chartColors={chartColors}
                  />
                </div>
              )}
              {clusterUtilization.gpu !== null && (
                <div className="card gauge-card">
                  <GaugeChart
                    value={Math.round(clusterUtilization.gpu * 10) / 10}
                    title="GPU allocation"
                    color="#EC7300"
                    chartColors={chartColors}
                  />
                </div>
              )}
              {clusterUtilization.memory !== null && (
                <div className="card gauge-card">
                  <GaugeChart
                    value={Math.round(clusterUtilization.memory * 10) / 10}
                    title="Memory allocation"
                    color={MEMORY_COLOR}
                    chartColors={chartColors}
                  />
                  {clusterUtilization.memory_coverage < MEMORY_COVERAGE_THRESHOLD && (
                    <ChartCaption
                      text=""
                      warning={`Requested memory is known for only ${Math.round(clusterUtilization.memory_coverage * 100)}% of jobs in this range; the gauge covers those jobs.`}
                    />
                  )}
                </div>
              )}
            </div>
            </>
          )}

          <div className="users-jobs-container">
            {/* CPU Node Usage */}
            {processedNodeData.cpu && processedNodeData.cpu.x.length > 0 && (
              <div className="subsection">
                <h2 className="subsection-header">CPU Usage by Node</h2>
                <div className="card">
                  <h3>
                    CPU Usage by Node{' '}
                    {processedNodeData.cpu.normalized && (
                      <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                        (% of capacity)
                      </span>
                    )}
                  </h3>
                  <StackedAreaChart
                    data={processedNodeData.cpu}
                    xTitle="Node"
                    yTitle={processedNodeData.cpu.normalized ? "Allocation (%)" : "CPU Hours"}
                    defaultColor="#04A5D5"
                    colorMap={colorMap}
                    chartType="bar"
                    barMode="stack"
                    chartColors={chartColors}
                  />
                  {processedNodeData.cpu.unknownCapacity.length > 0 && (
                    <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.5rem' }}>
                      {processedNodeData.cpu.unknownCapacity.length} nodes without known capacity are not shown: {processedNodeData.cpu.unknownCapacity.join(', ')}
                    </p>
                  )}
                  <ChartCaption text="CPU-hours per node from jobs overlapping the range, split equally over a job's nodes. Normalized: percentage of the node's known capacity over the range." />
                </div>
              </div>
            )}

            {/* GPU Node Usage */}
            {processedNodeData.gpu && processedNodeData.gpu.x.length > 0 && (
              <div className="subsection">
                <h2 className="subsection-header">GPU Usage by Node</h2>
                <div className="card">
                  <h3>
                    GPU Usage by Node{' '}
                    {processedNodeData.gpu.normalized && (
                      <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                        (% of capacity)
                      </span>
                    )}
                  </h3>
                  <StackedAreaChart
                    data={processedNodeData.gpu}
                    xTitle="Node"
                    yTitle={processedNodeData.gpu.normalized ? "Allocation (%)" : "GPU Hours"}
                    defaultColor="#EC7300"
                    colorMap={colorMap}
                    chartType="bar"
                    barMode="stack"
                    chartColors={chartColors}
                  />
                  {processedNodeData.gpu.unknownCapacity.length > 0 && (
                    <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.5rem' }}>
                      {processedNodeData.gpu.unknownCapacity.length} nodes without known capacity are not shown: {processedNodeData.gpu.unknownCapacity.join(', ')}
                    </p>
                  )}
                  <ChartCaption text="GPU-hours per node from jobs overlapping the range, split equally over a job's nodes. Normalized: percentage of the node's known GPU count over the range." />
                </div>
              </div>
            )}
            {/* Memory Node Usage */}
            {processedNodeData.memory && processedNodeData.memory.x.length > 0 && (
              <div className="subsection">
                <h2 className="subsection-header">Memory Usage by Node</h2>
                <div className="card">
                  <h3>
                    Memory Allocated by Node{' '}
                    {processedNodeData.memory.normalized && (
                      <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                        (% of node memory)
                      </span>
                    )}
                  </h3>
                  <StackedAreaChart
                    data={processedNodeData.memory}
                    xTitle="Node"
                    yTitle={processedNodeData.memory.normalized ? "Allocation (%)" : "GB-Hours"}
                    defaultColor={MEMORY_COLOR}
                    colorMap={colorMap}
                    chartType="bar"
                    barMode="stack"
                    chartColors={chartColors}
                  />
                  {processedNodeData.memory.unknownCapacity.length > 0 && (
                    <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.5rem' }}>
                      {processedNodeData.memory.unknownCapacity.length} nodes without known capacity are not shown: {processedNodeData.memory.unknownCapacity.join(', ')}
                    </p>
                  )}
                  <ChartCaption text="Requested memory-hours per node from jobs overlapping the range, split equally over a job's nodes. Normalized: percentage of the node's known memory over the range." />
                </div>
              </div>
            )}

          </div>
        </div>
      )}
    </section>
  );
};

export default UsageSection;
