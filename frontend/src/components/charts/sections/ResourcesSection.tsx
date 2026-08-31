import React from 'react';
import ChartCaption from '../ChartCaption';
import type { AggregatedChartsResponse } from '../../../types';
import type { ChartColors } from '../../../hooks/useDarkMode';
import HistogramChart from '../HistogramChart';

interface ResourcesSectionProps {
  data: AggregatedChartsResponse;
  colorMap: Map<string, string> | null;
  chartColors: ChartColors;
}

const ResourcesSection: React.FC<ResourcesSectionProps> = ({
  data,
  colorMap,
  chartColors,
}) => {
  const hasResources =
    (data.memory_per_job && data.memory_per_job.x.length > 0) ||
    (data.cpus_per_job && data.cpus_per_job.x.length > 0) ||
    (data.gpus_per_job && data.gpus_per_job.x.length > 0) ||
    (data.nodes_per_job && data.nodes_per_job.x.length > 0);

  if (!hasResources) return null;

  return (
    <section className="section">
      <h2 className="section-title">Allocated Resources</h2>
      <div className="chart-row-4col">
        {data.cpus_per_job && data.cpus_per_job.x.length > 0 && (
          <div className="card">
            <h3>
              CPUs per Job{' '}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                (all jobs)
              </span>
            </h3>
            <HistogramChart
              data={data.cpus_per_job}
              xTitle="Number of CPUs"
              yTitle="Number of Jobs"
              defaultColor="#04A5D5"
              colorMap={colorMap}
              isHistogram={true}
              chartColors={chartColors}
            />
            <ChartCaption text="Number of jobs per allocated CPU count." />
          </div>
        )}
        {data.gpus_per_job && data.gpus_per_job.x.length > 0 && (
          <div className="card">
            <h3>
              GPUs per Job{' '}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                (GPU jobs only)
              </span>
            </h3>
            <HistogramChart
              data={data.gpus_per_job}
              xTitle="Number of GPUs"
              yTitle="Number of Jobs"
              defaultColor="#EC7300"
              colorMap={colorMap}
              isHistogram={true}
              chartColors={chartColors}
            />
            <ChartCaption text="Number of jobs per allocated GPU count; jobs without GPUs are not shown." />
          </div>
        )}
        {data.memory_per_job && data.memory_per_job.x.length > 0 && (
          <div className="card">
            <h3>
              Memory per Job{' '}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                (all jobs)
              </span>
            </h3>
            <HistogramChart
              data={data.memory_per_job}
              xTitle="Requested Memory (GB)"
              yTitle="Number of Jobs"
              defaultColor="#2E8B57"
              colorMap={colorMap}
              isHistogram={true}
              chartColors={chartColors}
            />
            <ChartCaption text="Number of jobs per requested memory size in GB (20 most common sizes)." />
          </div>
        )}
        {data.nodes_per_job && data.nodes_per_job.x.length > 0 && (
          <div className="card">
            <h3>
              Nodes per Job{' '}
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: 'normal' }}>
                (all jobs)
              </span>
            </h3>
            <HistogramChart
              data={data.nodes_per_job}
              xTitle="Number of Nodes"
              yTitle="Number of Jobs"
              defaultColor="#17a2b8"
              colorMap={colorMap}
              isHistogram={true}
              chartColors={chartColors}
            />
            <ChartCaption text="Number of jobs per number of allocated nodes." />
          </div>
        )}
      </div>
    </section>
  );
};

export default ResourcesSection;
