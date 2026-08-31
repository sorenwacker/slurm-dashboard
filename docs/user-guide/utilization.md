# Utilization

The "Usage by Node" charts and the gauges compare **allocated** resource-hours with the capacity of the nodes over the selected date range - they measure how much of the cluster was handed out to jobs, not how busy the hardware was. SLURM accounting records allocations; the only measured quantity available is peak memory per job (`MaxRSS`), which feeds the memory efficiency chart. The dashboard labels these values "allocation" for this reason. This page states exactly how the numbers are computed so they can be checked.

## Inputs

- The date range `[start, end]` selected in the filters; `end` is inclusive, so the window length is `hours = (end - start + 1 day)` in hours.
- Jobs that **overlap** the window: every job with `Start < end + 1 day` and `End > start` (or still running). This is a separate selection from the other charts, which use jobs *submitted* in the window; a job submitted before the window but running inside it counts towards node utilization, and a job submitted inside the window only counts for the part that ran inside it.
- Per job: allocated CPUs, GPUs, requested memory, elapsed time, and the list of nodes it ran on.
- Per node: capacity from `clusters.yaml` as written by `slurm-dashboard sync-config` (`hardware.cpu.cores`, `hardware.gpus[].count`, `hardware.ram.total_gb`).

## Per-node resource-hours

For each job and each node in its node list:

```
overlap_hours   = hours of [Start, End] that fall inside the window
share           = 1 / number of nodes in the job's node list
cpu_hours(node) += allocated_cpus * overlap_hours * share
gpu_hours(node) += allocated_gpus * overlap_hours * share
mem_gb_hours(node) += requested_memory_gb * overlap_hours * share
```

The equal split across nodes is an approximation: SLURM accounting records allocations per job, not per node. For single-node jobs, which are the large majority, it is exact.

Without the "Normalize" toggle the charts show these sums per node.

## Per-node utilization

With "Normalize" enabled, each node's value is divided by its capacity over the window:

```
utilization(node) = resource_hours(node) / (capacity(node) * hours)
```

`capacity(node)` is the value from `clusters.yaml`. A node whose capacity for that resource is not known (no synced hardware, or 0 GPUs / 0 GB) is not normalized: it is left out of the normalized chart and counted in the "capacity unknown" note under it. Capacity is never substituted with a default or a value guessed from the node name.

Utilization is capped at 100 % per node; values above 100 % indicate that the configuration understates the node's capacity or that the node list attribution is off for multi-node jobs.

## Cluster gauges

The gauges show capacity-weighted utilization over **all configured nodes** with known capacity, regardless of the hide/sort options of the node charts:

```
cluster_utilization = sum over nodes of resource_hours(node) / sum over nodes of (capacity(node) * hours)
```

An idle node with known capacity lowers the gauge; an unknown-capacity node does not appear in either sum. Nodes of type `login` and `storage` are excluded. A configured node that the last `sync-config` run did not report and that ran nothing in the range is treated as decommissioned and excluded - on clusters that never ran `sync-config`, only nodes with usage in the range count as capacity.

When requested memory is known for fewer than 90 % of the jobs in the range, the memory gauge carries a warning stating the coverage; it then describes only the jobs with memory data. This happens for data collected before the agent reported memory fields.

## Where to look when a number is surprising

- Node missing from the normalized chart: it has no synced capacity for that resource. Run `sync-config` or set the hardware on the cluster page's YAML tab.
- Utilization above 100 %: check the node's `hardware` block against `scontrol show node <name>`, and check whether multi-node jobs list more nodes than they actually used.
- Gauge lower than the node charts suggest: idle configured nodes count in the denominator; the node charts hide unused nodes by default.

## Efficiency

Efficiency compares what jobs consumed with what they allocated; it does not affect the allocation charts and gauges above.

- CPU efficiency of a period = `sum(CPUUsedHours) / sum(CPUHours)` over jobs reporting both. `CPUUsedHours` is sacct's `TotalCPU` (consumed core-time), a measured value.
- Memory efficiency of a period = `sum(MaxRSS * elapsed) / sum(ReqMem * elapsed)`, weighted by job runtime so short jobs do not dominate. It uses peak usage and is therefore an upper bound; see [Memory Usage](memory-usage.md).
- With a colour dimension selected in the sidebar, both efficiency charts show one line per group (the groups with the most allocated resource); without one, a single cluster-wide line. Group names appear only when the dimension is selected, like in every other chart.
- GPU efficiency cannot be computed from SLURM accounting.

Jobs collected before the agent reported `CPUUsedHours` are excluded from CPU efficiency; a period with no such jobs is omitted.
