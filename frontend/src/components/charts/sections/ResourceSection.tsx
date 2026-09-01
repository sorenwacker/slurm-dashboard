import React from 'react';
import ChartCaption from '../ChartCaption';
import type { AggregatedChartsResponse, ChartData, ClusterUtilization } from '../../../types';
import type { ChartColors } from '../../../hooks/useDarkMode';
import type { ProcessedNodeChart } from '../../../utils/nodeChart';
import { MEMORY_COVERAGE_THRESHOLD } from '../../../hooks/useProcessedNodeData';
import StackedAreaChart from '../StackedAreaChart';
import PieChart from '../PieChart';
import HistogramChart from '../HistogramChart';
import GaugeChart from '../GaugeChart';
import TimelineChart from '../TimelineChart';
import { COLORS } from '../chartHelpers';

export interface ResourceSectionConfig {
  title: string;            // section heading, e.g. "CPU"
  color: string;            // the resource's hue
  unit: string;             // "CPU Hours" | "GPU Hours" | "GB-Hours"
  overTimeKey: 'cpu_usage_over_time' | 'gpu_usage_over_time' | 'memory_usage_over_time';
  byDimKey: 'cpu_hours_by_account' | 'gpu_hours_by_account' | 'memory_hours_by_account';
  perJobKey: 'cpus_per_job' | 'gpus_per_job' | 'memory_per_job';
  efficiencyKey?: 'cpu_efficiency_over_time' | 'memory_efficiency_over_time';
  gaugeKey: 'cpu' | 'gpu' | 'memory';
  totalLabel: (data: AggregatedChartsResponse) => string;
  overTimeCaption: string;
  byDimCaption: string;
  perJobTitle: string;
  perJobXTitle: string;
  perJobCaption: string;
  nodeTitle: string;
  nodeCaption: string;
  efficiencyTitle?: string;
  efficiencyCaption?: string;
  gaugeTitle: string;
}

interface ResourceSectionProps {
  config: ResourceSectionConfig;
  data: AggregatedChartsResponse;
  colorMap: Map<string, string> | null;
  colorBy: string;
  periodType: string;
  chartColors: ChartColors;
  nodeChart: ProcessedNodeChart | null;
  utilization: ClusterUtilization;
}

const hasData = (chart?: ChartData): boolean =>
  !!chart && ((chart.type === 'pie' && (chart.labels?.length ?? 0) > 0) || (chart.x?.length ?? 0) > 0);

const ResourceSection: React.FC<ResourceSectionProps> = ({
  config,
  data,
  colorMap,
  colorBy,
  periodType,
  chartColors,
  nodeChart,
  utilization,
}) => {
  const overTime = data[config.overTimeKey];
  const byDim = data[config.byDimKey];
  const perJob = data[config.perJobKey];
  const efficiency = config.efficiencyKey ? data[config.efficiencyKey] : undefined;
  const gaugeValue = utilization[config.gaugeKey];
  const showGauge = gaugeValue !== null && nodeChart?.normalized;

  if (!hasData(overTime) && !hasData(perJob) && !(nodeChart && nodeChart.x.length > 0)) return null;

  return (
    <section className="section">
      <h2 className="section-title">{config.title}</h2>

      <div className="resource-top-row">
        {hasData(overTime) && (
          <div className="card">
            <h3>{config.title} Usage</h3>
            <StackedAreaChart
              data={overTime}
              xTitle="Period"
              yTitle={config.unit}
              defaultColor={config.color}
              colorMap={colorMap}
              defaultName={config.unit}
              chartType="area"
              periodType={periodType}
              chartColors={chartColors}
            />
            <ChartCaption text={config.overTimeCaption} />
          </div>
        )}
        {hasData(byDim) && (
          <div className="card">
            <h3>
              {byDim.type === 'pie' ? `${config.title} Usage by ${colorBy}` : `${config.title} Usage Distribution`}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}> ({config.totalLabel(data)})</span>
            </h3>
            {byDim.type === 'pie' ? (
              <PieChart
                data={{ labels: byDim.labels || [], values: byDim.values || [] }}
                valueLabel={config.unit}
                colors={colorMap ? (byDim.labels || []).map((label, idx) => colorMap.get(label) || COLORS[idx % COLORS.length]) : undefined}
                chartColors={chartColors}
              />
            ) : (
              <HistogramChart
                data={byDim}
                xTitle={`${config.unit} per Period`}
                yTitle="Number of Periods"
                defaultColor={config.color}
                colorMap={null}
                isHistogram={true}
                showMedianMean={true}
                unit=""
                decimalPlaces={0}
                chartColors={chartColors}
              />
            )}
            <ChartCaption text={config.byDimCaption} />
          </div>
        )}
        {hasData(perJob) && (
          <div className="card">
            <h3>{config.perJobTitle}</h3>
            <HistogramChart
              data={perJob}
              xTitle={config.perJobXTitle}
              yTitle="Number of Jobs"
              defaultColor={config.color}
              colorMap={colorMap}
              isHistogram={true}
              chartColors={chartColors}
            />
            <ChartCaption text={config.perJobCaption} />
          </div>
        )}
      </div>

      {nodeChart && nodeChart.x.length > 0 && (
        <div className={showGauge ? 'node-row-with-gauge' : undefined} style={{ marginTop: 'var(--space-md)' }}>
          {showGauge && (
            <div className="card gauge-card">
              <GaugeChart
                value={Math.round((gaugeValue as number) * 10) / 10}
                title={config.gaugeTitle}
                color={config.color}
                chartColors={chartColors}
              />
              <ChartCaption
                text="Capacity-weighted over nodes with known capacity that SLURM reports or that ran jobs in the range."
                warning={
                  config.gaugeKey === 'memory' && utilization.memory_coverage < MEMORY_COVERAGE_THRESHOLD
                    ? `Requested memory is known for only ${Math.round(utilization.memory_coverage * 100)}% of jobs in this range.`
                    : undefined
                }
              />
            </div>
          )}
          <div className="card">
            <h3>
              {config.nodeTitle}{' '}
              {nodeChart.normalized && (
                <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>(% of capacity)</span>
              )}
            </h3>
            <StackedAreaChart
              data={nodeChart}
              xTitle="Node"
              yTitle={nodeChart.normalized ? 'Allocation (%)' : config.unit}
              defaultColor={config.color}
              colorMap={colorMap}
              chartType="bar"
              barMode="stack"
              chartColors={chartColors}
            />
            <ChartCaption text={config.nodeCaption} />
            {nodeChart.unknownCapacity.length > 0 && (
              <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.5rem' }}>
                {nodeChart.unknownCapacity.length} nodes without known capacity are not shown: {nodeChart.unknownCapacity.join(', ')}
              </p>
            )}
          </div>
        </div>
      )}

      {efficiency && (efficiency.series?.length ?? 0) > 0 && config.efficiencyTitle && (
        <div className="efficiency-row" style={{ marginTop: 'var(--space-md)' }}>
          <div className="card">
            <h3>
              {config.efficiencyTitle}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}> (used / allocated)</span>
            </h3>
            {(efficiency.series?.length ?? 0) > 1 ? (
              <TimelineChart
                data={{ x: efficiency.x, series: efficiency.series }}
                xTitle="Period"
                yTitle="Used (%)"
                colorMap={colorMap}
                defaultColor={config.color}
                chartColors={chartColors}
              />
            ) : (
              <StackedAreaChart
                data={{ x: efficiency.x, y: efficiency.series![0].data as number[] }}
                xTitle="Period"
                yTitle="Used (%)"
                defaultColor={config.color}
                colorMap={null}
                defaultName={efficiency.series![0].name}
                chartType="area"
                periodType={periodType}
                chartColors={chartColors}
              />
            )}
            <ChartCaption text={config.efficiencyCaption ?? ''} />
          </div>
        </div>
      )}
    </section>
  );
};

export default ResourceSection;
