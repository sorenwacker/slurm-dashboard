# Changelog

All notable changes to SLURM Dashboard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Dashboard filter values (dates, partitions, accounts, users, QOS, states) and the hostname were interpolated into DuckDB SQL; an unauthenticated request could read or write server files through `read_text` and `COPY`. Values are now bound parameters and the hostname must be a known cluster
- The admin JWT signing key defaulted to a fixed string in code, so anyone could mint a superadmin token for a deployment that did not set `ADMIN_SECRET_KEY` (the Docker quick start and `.env.example` did not). There is no default anymore: an unset or placeholder key is replaced by a random key at startup with a logged warning, and a token is accepted only when its subject is a configured admin
- Agent uploads used the client-supplied filename as a path, so a cluster key could write `.parquet` files outside its own cluster directory. The filename must be a single path component and the content must be valid parquet
- `POST /api/data/ingest` used the body `hostname` as a directory without checking it against the API key's cluster, so any cluster key could write another cluster's data or files outside `DATA_PATH`. The target directory is now the key's cluster; a different hostname is rejected with `403`

### Fixed
- Admin pages and the report view referenced seven CSS custom properties (`--white`, `--border-radius`, `--box-shadow`, `--border-color`, `--bg-color`, `--text-color`, `--card-bg`) that were never declared, so cards had no background or shadow, corners were square, and button labels inherited the page text color. They now use the declared design tokens; a test fails on any undeclared `var(--name)`
- Memory efficiency is weighted by job runtime; unweighted per-job ratios were dominated by sub-6-minute jobs (72% of DAIC jobs) and sat far below the actual occupancy
- Node utilization: jobs overlapping the window are counted for the overlapping hours only, multi-node jobs are split across their nodes instead of counted once per node, gauges are capacity-weighted over all configured nodes, and nodes without synced capacity are no longer normalized against default values (see docs/user-guide/utilization.md)
- Dashboard date filters are kept inside the cluster's data range: the initial start date is the first data point when the cluster has less than six weeks of data, and typed dates outside the range snap to the nearest bound
- Ingest endpoint crashed with 500 on jobs that never started (null Start) while deriving the week column; it now stores them with empty timing columns and logs the traceback on failure
- Exporter sent the literal string `None` as `Start`/`End` for jobs that never started, which made the dashboard reject the whole batch with 422

### Changed
- Dashboard summary cards carry one accent color per metric instead of a left border and a gradient top bar, and the wide-screen grid no longer leaves an empty fifth slot when memory data is absent; the footer's API documentation link and the loading screen no longer point at localhost
- Report preview and its sidebar controls use stylesheet classes instead of inline styles; the report page is one `.report-page` block that stays light in dark mode, fits narrow screens, and uses the shared metric colors for every chart. The unused `ReportGenerator` and `ReportOverview` components are removed
- Admin pages share one layout (header, navigation, theme toggle, logout) and one token-based stylesheet, so they follow the dashboard's fonts and colors and support dark mode; the four page-specific stylesheets with hardcoded Bootstrap colors are removed. Reload and demo results are shown as page messages instead of browser alert dialogs
- mypy is a configured gate (pre-commit hook and CI lint job) at mypy's default strictness; the 36 pre-existing errors are fixed. --strict reports 342 errors and remains tracked work
- Waiting-time bins match the job-duration grid (11 bins from < 30s to > 7d) in both the histogram and the stacked timeline, so waits of jobs that start near-immediately are separated from real queueing
- Dashboard grouped by resource: each of CPU, GPU, and Memory has one section with usage over time, distribution, per-node chart with its gauge, per-job histogram, and efficiency; node-chart options moved to the sidebar; Nodes per Job joined the Jobs group
- Lint is enforced: ruff and vulture run as pre-commit hooks and as a failing CI job; the repository is at zero findings with accepted rules documented in pyproject.toml; the dead Plotly-Dash app and legacy weekly-usage agent are removed
- API keys are stored hashed; the full key is shown once at creation, rotation, or deploy-key exchange, and the admin UI shows only its prefix afterwards. Existing plaintext keys are hashed on first use.
- `CLUSTER_CONFIG_PATH` setting moves the writable cluster configuration out of the git checkout; `backend/config/clusters.yaml` is no longer tracked (`clusters.example.yaml` documents the structure)
- Admin: one cluster page per cluster (`/admin/clusters/<name>`) with Overview, Nodes, Partitions, Accounts, and YAML tabs replaces the Cluster Details and Configuration pages; labels are edited in place per entry; the Auto-Generate action is removed
- `requires-python` bounded to `<3.13` because the pinned `pyarrow`/`numpy` have no wheels for 3.13; install commands pass `--python 3.12` and the conda instructions are replaced by uv and venv

### Added
- CPU efficiency: agent reports consumed core-time (`TotalCPU`); dashboard shows CPU efficiency over time and efficiency by account for CPU and memory
- `slurm-dashboard sync-config` and `run --sync-config`: agent reads cluster metadata, node hardware and features, partitions, and accounts from `scontrol` and `sacctmgr`; the dashboard merges them into `clusters.yaml` without generating descriptions or guessing node types from names
- Agent install command shown with uv (`uv tool install`) as well as pip in the admin panel and docs
- Memory usage charts: agent collects requested memory and peak RSS per job; dashboard shows memory-hours over time, memory efficiency, memory per job, and per-node memory utilization

## [0.5.0] - 2025-11-20

Deploy Key System & Security Enhancements

### Added
- Deploy key system for secure one-time agent setup with 7-day expiration
- One-command agent setup: `slurm-dashboard setup --api-url URL --deploy-key KEY`
- IP address tracking for deploy key usage with proxy support (X-Forwarded-For, X-Real-IP)
- Dedicated cluster details page at `/admin/clusters/{id}` for key management
- Deploy key status display (Valid/Used/Expired) in admin panel
- Custom SLURM icon with #09a4d6 background color
- Admin user management stored in database instead of .env file

### Changed
- Default data collection period increased from 7 to 14 days
- Sensitive API keys and deploy keys moved from cluster list to dedicated details page
- Agent installation command updated to use GitLab repository
- Improved key rotation workflow with better UI/UX

### Security
- Deploy keys expire after 7 days and can only be used once
- Deploy key exchange tracked with timestamp and IP address
- API keys no longer visible in main cluster list view
- Config files created with 0600 permissions (user-readable only)

### Fixed
- Missing timedelta import in cluster database module
- Agent installation command now uses correct GitLab repository URL
- Package name corrected from slurm-usage-history to slurm-dashboard

## [0.4.2] - 2025-11-XX

### Added
- Docker development environment improvements
- Cluster filtering enhancements

## [0.4.1] - 2025-11-XX

### Added
- Various bug fixes and improvements

## [0.4.0] - 2025-11-XX

### Added
- Admin panel with cluster management
- Multi-cluster support with API key authentication
- Demo cluster generation with synthetic data
- User management interface

## [0.3.0-rc1] - 2024-11-10

Release Candidate for v0.3.0 - ready for testing and feedback.

### Added
- Modern **DuckDB-powered backend** for 95% memory reduction (13GB → 1.1GB)
- **React + TypeScript frontend** with Vite build system
- **FastAPI backend** replacing legacy Flask/Dash
- **Integrated frontend distribution** - pre-built frontend included in Python package
- **Single-command deployment** - `pip install slurm-dashboard[web]` includes everything
- **Dynamic filter population** - filters now only show values from selected date range
- **Column name normalization** for consistent data processing across parquet files
- **Timing column support** - waiting times and job duration charts now working
- **Shared datastore singleton** for efficient memory management across workers
- **Modern pyproject.toml** with optional extras: `[agent]`, `[web]`, `[all]`
- **Comprehensive documentation** - INSTALL.md, QUICKSTART.md guides
- **New CLI commands**: `slurm-dashboard-agent`, `slurm-dashboard`, `slurm-dashboard-wait-times`
- **Simplified backend startup** - `slurm-dashboard` command with sensible defaults
- **Query caching** for 5-minute cache of chart data
- **SAML 2.0 authentication** for enterprise SSO
- **PDF report generation** with customizable templates
- **Ansible playbooks** for automated deployment
- **Environment-based configuration** via .env files
- **Proper logging** throughout the codebase

### Changed
- **Package renamed** from `slurm-usage-history` to `slurm-dashboard`
- **Installation method** now supports pip extras: `pip install slurm-dashboard[web]`
- **Query performance** improved ~15x for yearly data queries
- **Startup time** reduced from 45s to 30s (33% faster)
- **Code quality** - replaced all `print()` with proper `logging` calls
- **Line length** standardized to 120 characters (from 200)
- **Python requirement** bumped to 3.10+ for modern type hints

### Removed
- Debug print statements from production code
- Unnecessary verbose logging
- Legacy pandas-only datastore (kept as fallback)

### Fixed
- **500 errors** on charts endpoint caused by separate datastore instances
- **Empty graphs** when selecting periods without filter value data
- **Column name mismatches** between parquet files (CPU-hours vs CPUHours)
- **Timing data not appearing** in charts (WaitingTime [h] vs WaitingTimeHours)
- **DuckDB extension conflicts** between gunicorn workers
- **Account formatter** method name error
- **Week normalization** for StartYearWeek timestamps
- **Test suite compatibility** with pandas FutureWarnings and chart format validation
- **Chart generation tests** now properly validate pie, bar, stacked, and trends formats

### Performance
- **Memory**: 13GB → 1.1GB (92% reduction)
- **Query time**: 8-12s → 0.3-0.8s for yearly data (~15x faster)
- **Scalability**: Now supports TB+ datasets without OOM errors
- **Thread safety**: Per-process DuckDB connections
- **Auto-refresh**: Efficient file change detection

### Security
- Added SAML 2.0 authentication support
- Environment-based secrets management
- Read-only filesystem protection
- HTTPS/TLS support in deployment guides
- CORS configuration

## [0.2.0] - 2024-11-XX (Previous React Migration)

### Added
- React frontend with TypeScript
- FastAPI backend
- Interactive Plotly.js charts
- Advanced filtering and aggregations

### Changed
- Migrated from Dash to React
- API restructured to RESTful design

## [0.1.0] - 2024-XX-XX (Initial Dash Version)

### Added
- Initial Dash-based dashboard
- Pandas datastore implementation
- SLURM data collection scripts
- Basic visualization capabilities

---

## Migration Guide

### From v0.1.0 (Dash) to v0.3.0 (DuckDB)

**Installation:**
```bash
# Old
pip install slurm-usage-history

# New
pip install slurm-dashboard[web]
```

**CLI Commands:**
```bash
# Old
slushi-dashboard

# New
slurm-dashboard  # Or use uvicorn directly
```

**Configuration:**
```bash
# Old
export SLURM_DATA=/data

# New
export DATA_PATH=/data/slurm-usage
```

**Data Collection:**
```bash
# Old
slushi-get-weekly-usage

# New
slurm-dashboard-agent --output /data/slurm-usage/$(hostname)
```

**Memory Requirements:**
- Old: ~13GB RAM for 2M jobs
- New: ~1.1GB RAM for same dataset

### Breaking Changes

1. **Package name**: `slurm-usage-history` → `slurm-dashboard`
2. **CLI commands**: All commands renamed with `slurm-` prefix
3. **Environment variables**: `SLURM_DATA` → `DATA_PATH`
4. **Python version**: Now requires Python 3.10+

### Backward Compatibility

The DuckDB datastore is fully backward compatible with existing parquet files. No data migration needed - just update the package and restart!

---

## Roadmap

### v0.4.0 (Q1 2025)
- [ ] Multi-cluster aggregated view
- [ ] User quota tracking
- [ ] Email notifications for quota limits
- [ ] Historical trend forecasting

### v0.5.0 (Q2 2025)
- [ ] Cost/chargeback reporting
- [ ] GPU utilization deep-dive
- [ ] Node efficiency metrics
- [ ] Custom dashboard widgets

### v1.0.0 (Q3 2025)
- [ ] Production-ready stable release
- [ ] Full RBAC implementation
- [ ] Multi-tenancy support
- [ ] Comprehensive test coverage (>80%)

---

## Deprecation Notices

### Deprecated in v0.3.0

- **Legacy Dash dashboard** (`slurm-dashboard-legacy` command) will be removed in v1.0.0
- **Pandas-only datastore** will be removed when DuckDB is fully stable (v1.0.0)
- **Old CLI command names**:
  - `slushi-*` commands deprecated, use new `slurm-dashboard-*` commands
  - `slurm-agent` deprecated, use `slurm-dashboard-agent`
  - `slurm-backend` deprecated, use `slurm-dashboard`
  - `slurm-waiting-times` deprecated, use `slurm-dashboard-wait-times`
  - Old names will be removed in v1.0.0

---

## Contributors

- Sören Wacker (@sdrwacker) - Lead Developer
- Claude Code (Anthropic) - Code refactoring and documentation assistance
- REIT Team - Testing and feedback
- DAIC Users - Feature requests and bug reports

---

## Links

- [GitLab Repository](https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history)
- [Issue Tracker](https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history/-/issues)
- [Documentation](../index.md)
- [Installation Guide](../getting-started/installation.md)
- [Quick Start](../getting-started/quickstart.md)
