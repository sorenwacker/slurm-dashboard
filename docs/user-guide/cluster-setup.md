# Cluster Setup Guide

Quick guide for installing and configuring the SLURM data collection agent on your cluster.

## Prerequisites

- SLURM cluster with `sacct` access
- Python 3.10-3.12 (installed by uv if the system Python does not match)
- Git (for GitLab installation)
- Network access to dashboard API

## Installation on Cluster

### Using uv (Recommended)

`uv tool install` creates an isolated environment for the agent and puts `slurm-dashboard` on your PATH (`~/.local/bin`). uv downloads its own Python build, so the system Python version does not matter. `--python 3.12` is required: the agent pins `pyarrow<15` and `numpy<2` for old-GCC compatibility, and those have no wheels for Python 3.13 or later.

```bash
# Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the agent
uv tool install --python 3.12 'slurm-dashboard[agent] @ git+https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git'

# Verify installation
slurm-dashboard --help
```

To update later: `uv tool upgrade slurm-dashboard`.

### Alternative: Using venv

Requires a system `python3` between 3.10 and 3.12.

```bash
python3 --version
python3 -m venv ~/slurm-dash-venv
source ~/slurm-dash-venv/bin/activate

# Install the agent
pip install "git+https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git#egg=slurm-dashboard[agent]"

# Verify installation
slurm-dashboard --help
```

### From PyPI (When Published)

```bash
pip install slurm-dashboard[agent]
slurm-dashboard --help
```

### Important Notes

- **Python version**: 3.10-3.12. On Python 3.13+ the install fails while building `pyarrow`; use the uv route or a venv with an older Python.
- **PATH setup**: If `slurm-dashboard` command is not found, add `~/.local/bin` to PATH:
  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  ```
- **Old systems**: the pinned `pandas`, `numpy`, and `pyarrow` versions ship wheels that run on GCC 4.8-era systems, so no compiler is needed

## Setup Data Collection

The new agent uses API-based submission - no shared filesystem required.

### 1. One-Command Setup (Recommended)

The easiest way to set up the agent is using a deploy key from your dashboard administrator.

**Steps:**

1. Ask your dashboard administrator to generate a deploy key for your cluster
2. Copy the installation command from the admin panel (it includes everything you need)
3. Run it on your cluster:

The admin panel shows the command in two variants; use whichever tool is available on the cluster.

With uv:

```bash
uv tool install --python 3.12 'slurm-dashboard[agent] @ git+https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git' && \
slurm-dashboard setup \
  --api-url https://dashboard.daic.tudelft.nl \
  --deploy-key deploy_xxxxxxxxxxxx
```

With pip (inside an activated venv):

```bash
pip install 'git+https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git#egg=slurm-dashboard[agent]' && \
slurm-dashboard setup \
  --api-url https://dashboard.daic.tudelft.nl \
  --deploy-key deploy_xxxxxxxxxxxx
```

This will:
- Exchange the one-time deploy key for a permanent API key
- Create a `config.json` file with your credentials
- Set up the cluster name automatically

The deploy key:
- Expires after 7 days
- Can only be used once
- Is automatically invalidated after setup

### 2. Manual Setup (Alternative)

If you prefer manual setup or already have an API key:

```bash
# Create config with your credentials
slurm-dashboard create-config \
  --api-url https://dashboard.daic.tudelft.nl \
  --api-key YOUR_API_KEY_HERE \
  --cluster-name DAIC \
  --local-data-path /data/slurm-usage/DAIC \
  -o config.json
```

This creates a `config.json` file with mode `0600` (readable only by you) containing:
```json
{
  "api_url": "https://dashboard.daic.tudelft.nl",
  "api_key": "YOUR_API_KEY_HERE",
  "cluster_name": "DAIC",
  "local_data_path": "/data/slurm-usage/DAIC",
  "timeout": 30,
  "collection_window_days": 14
}
```

### 3. Test with Dry Run

```bash
# Test data extraction without submitting
slurm-dashboard run --config config.json --dry-run --verbose
```

You should see:
- Number of jobs extracted
- Total CPU-hours and GPU-hours
- Sample job record, including `ReqMemMB` and `MaxRSSMB` (see [Memory Usage](memory-usage.md))

### 4. Run for Real

```bash
# Submit data to dashboard
slurm-dashboard run --config config.json
```

Check the dashboard to verify data appears.

### 5. Sync Cluster Configuration

The dashboard needs each node's schedulable CPU count, memory, and GPU count to normalize utilization, and uses partition and account labels in filters and charts. `sync-config` reads all of this from SLURM and pushes it to the dashboard, so nothing has to be typed by hand and nothing is guessed from names:

```bash
# Show what would be sent
slurm-dashboard sync-config --config config.json --dry-run

# Push the cluster configuration to the dashboard
slurm-dashboard sync-config --config config.json
```

What is collected:

| Source | Written to `clusters.yaml` |
|--------|----------------------------|
| `scontrol show config` | `metadata.slurm_version`, `metadata.slurm_cluster_name` |
| `scontrol show node` | per node: `hardware.cpu.cores` (`CPUTot`, the CPUs SLURM schedules), `hardware.cpu.sockets`, `cores_per_socket`, `threads_per_core`, `hardware.ram.total_gb` (`RealMemory`), `hardware.gpus[]` (from `Gres`), `partitions`, `features` (`AvailableFeatures`) |
| `scontrol show partition` | per partition: `slurm.nodes`, `slurm.total_cpus`, `slurm.total_nodes`, `slurm.max_time`, `slurm.default`, `slurm.state` |
| `sacctmgr show account` | per account: `slurm.description`, `slurm.organization` |

Merge rules on the dashboard:

- Everything under `hardware`, `partitions`, `features`, and `slurm` is overwritten with the reported values on every sync.
- Node `type` is set to `gpu` or `cpu` from the reported GPU count; `login`, `storage`, and other hand-set types are kept.
- `synonyms`, `description`, `display_name`, and any other hand-edited field are never touched. The sync does not invent descriptions or display names; a field SLURM has no value for stays absent.
- Nodes, partitions, or accounts that exist in the configuration but are no longer reported by SLURM are kept, so historical data keeps its labels.

`sacctmgr` requires accounting access; if it is unavailable the accounts section is skipped and reported in the output, and the rest of the sync proceeds.

To keep the configuration current, add `--sync-config` to the `run` command in the cron job. The sync is executed before the job data collection; a failed sync is logged and does not block the collection.

### 6. Automated Collection with Cron

```bash
# Edit crontab
crontab -e

# Add daily collection at 2 AM (uv tool install puts slurm-dashboard in ~/.local/bin)
0 2 * * * $HOME/.local/bin/slurm-dashboard run --config ~/config.json --sync-config >> ~/agent.log 2>&1
```

**For a venv install:**
```bash
0 2 * * * source ~/slurm-dash-venv/bin/activate && slurm-dashboard run --config ~/config.json --sync-config >> ~/agent.log 2>&1
```

### 7. Verify Cron Job

```bash
# Check crontab
crontab -l

# Watch the log file
tail -f ~/agent.log
```

**Advantages of this approach:**
- No NFS required
- HTTPS encryption
- API key authentication
- Works across networks/firewalls
- Simple configuration file
- Optional local data backup

### Error Handling and Recovery

**If API submission fails:**

The agent extracts data from SLURM's accounting database (sacct), which retains historical data. If submission fails:

1. Error is logged to `~/agent.log` (or wherever your cron logs)
2. Next cron run will retry the same period (default: last 7 days)
3. No data is lost - SLURM keeps accounting data persistently
4. Overlapping submissions are handled - dashboard deduplicates jobs by JobID

**Checking for failures:**

```bash
# Check recent log entries
tail -20 ~/agent.log

# Look for errors
grep -i error ~/agent.log

# Check if agent is running
ps aux | grep slurm-dashboard
```

**Manual recovery after outage:**

If the dashboard was down for an extended period, you can backfill data:

```bash
# Collect specific date range
slurm-dashboard run \
  --config config.json \
  --start-date 2025-01-01 \
  --end-date 2025-01-31
```

**Future enhancement:**

Local data backup (via `local_data_path` config option) will save extracted data locally before submission, providing an additional safety layer. This feature is planned for a future release.

---

## Advanced Configuration

### Collect Specific Date Range

```bash
# Collect specific period
slurm-dashboard run \
  --config config.json \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

### Override Cluster Name

```bash
# Override cluster name from config
slurm-dashboard run \
  --config config.json \
  --cluster-name MyCluster
```

### Custom SLURM Path

If SLURM commands are not in your PATH:

```bash
# Add SLURM to PATH before running
export PATH=/usr/local/slurm/bin:$PATH
slurm-dashboard run --config config.json
```

## Troubleshooting

### "sacct: command not found"

Ensure SLURM client tools are installed and in PATH:

```bash
# Find sacct
which sacct

# If not in PATH, add it
export PATH=/path/to/slurm/bin:$PATH
```

### Permission Denied on Output Directory

```bash
# Check permissions
ls -ld /data/slurm-usage

# Fix permissions (adjust as needed)
chmod 755 /data/slurm-usage
```

### No Data in Parquet Files

```bash
# Check if sacct returns data
sacct --starttime $(date -d '7 days ago' +%Y-%m-%d) --format=JobID,Start,End,State

# If no output, check SLURM accounting configuration
sacctmgr show configuration
```

### Install Fails Building pyarrow (Python 3.13+)

The agent pins `pyarrow<15` and `numpy<2`, which have no wheels for Python 3.13 or later, so pip or uv tries to compile them and fails. Install with a supported interpreter:

```bash
uv tool uninstall slurm-dashboard
uv tool install --python 3.12 'slurm-dashboard[agent] @ git+https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git'
```

### Git Not Found During Install

uv and pip call `git` for `git+https://` sources. If the node has no `git`, install from the repository archive instead:

```bash
uv tool install --python 3.12 'slurm-dashboard[agent] @ https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history/-/archive/main/slurm-usage-history-main.tar.gz'
```

### Command Not Found

If `slurm-dashboard` is not found after installation:

```bash
# Add ~/.local/bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Make permanent
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Or use full path
~/.local/bin/slurm-dashboard --help
```

### GitLab Access Issues

If you can't access GitLab from the cluster, ask your administrator to:

1. Build the wheel file on a machine with GitLab access
2. Copy it to the cluster
3. Install with: `pip install slurm_dashboard-*.whl[agent]`

## Security Considerations

1. **Read-only SLURM access**: Agent only reads from SLURM accounting database
2. **Config file permissions**: config.json is created with mode 0600 (user-readable only)
3. **API authentication**: All uploads use HTTPS with API key authentication
4. **No data leakage**: Agent only uploads job metadata (no job outputs or user data)

## Next Steps

After setting up data collection:

1. Set up the dashboard server - see [INSTALL.md](../getting-started/installation.md)
2. Configure automated reports - see documentation
3. Set up SAML authentication (optional) - see [INSTALL.md](../getting-started/installation.md#saml-authentication-optional)

## Support

- Issues: https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history/-/issues
- Documentation: See README.md and QUICKSTART.md
