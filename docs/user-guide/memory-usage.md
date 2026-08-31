# Memory Usage

The dashboard shows how much memory jobs request, how much they use, and how much of each node's memory is allocated over time. Together these answer whether memory, rather than CPU or GPU, is the limiting resource on a cluster.

## Data Source

SLURM's accounting database does not store memory samples. Two per-job values are available from `sacct` and are collected by the agent:

| Field | Source | Meaning |
|-------|--------|---------|
| `ReqMemMB` | `mem=` entry of `AllocTRES` (fallback: `ReqMem`) | Memory allocated to the job, in MB |
| `MaxRSSMB` | `MaxRSS`, maximum over the job's steps | Peak resident set size reached by any step, in MB |

`MaxRSS` is reported per job step (`123.batch`, `123.0`), not on the job line. The agent takes the maximum over all steps of a job and stores it on the job record, then drops the step rows as before. Both fields are null when SLURM does not report them, and job records collected before this feature have no memory columns; the dashboard treats missing values as unknown and excludes them from memory charts, never as zero.

`ReqMem` values with a per-CPU suffix (`4000Mc`) are multiplied by the allocated CPU count; per-node values (`64Gn`) by the allocated node count.

## Derived Values

- `MemGBHours = ReqMemMB / 1024 * ElapsedHours` - memory-hours allocated, analogous to CPU-hours. This is the quantity charted over time and per node.
- Memory efficiency of a period = `sum(MaxRSSMB * ElapsedHours) / sum(ReqMemMB * ElapsedHours)` over the jobs in that period that have both values - weighted by runtime, on the same GB-hours basis as the usage charts. A persistently low value means users request far more memory than they use.
- Node memory utilization follows the same rule as CPU and GPU utilization, with `ram.total_gb` as the capacity; see [Utilization](utilization.md). Nodes without a synced memory size are shown with absolute memory-hours only.

## Charts

The Usage section gains a Memory subsection next to CPU and GPU:

- **Memory Usage** - allocated memory-hours (GB-hours) per period, stacked by the selected colour dimension.
- **Memory Usage by Account / Distribution** - same split as the CPU and GPU charts.
- **Memory per Job** (in the Allocated Resources section) - histogram of requested memory per job in GB.
- **Memory Efficiency** (in the Efficiency subsection) - percentage of requested memory actually used, per period; peak-based, so an upper bound. See [Utilization](utilization.md#efficiency).

Usage by Node gains a Memory row alongside CPU and GPU. With "Normalize" enabled it shows the percentage of each node's memory that was allocated over the selected range, and the cluster-wide utilization gauges gain a Memory gauge. A node at high memory utilization with low CPU utilization is memory-bound: its cores sit idle because its memory is fully allocated.

The summary cards show total allocated memory-hours next to CPU-hours and GPU-hours.

## Limitations

- Values are per job, not sampled over the job's lifetime. `MaxRSS` is a peak; the average use of a job is not known.
- Node utilization is derived from allocations, not from measured node memory. A job that requests 64 GB and uses 4 GB still counts as 64 GB allocated on the node, which is the correct quantity for "could another job have been scheduled here".
- Jobs on old SLURM versions without `AllocTRES` fall back to `ReqMem`; if neither is present the job has no memory data.
- PDF reports do not include memory charts.
