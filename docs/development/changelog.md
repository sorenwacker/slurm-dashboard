# Changelog

All notable changes to SLURM Dashboard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Ingest endpoint crashed with 500 on jobs that never started (null Start) while deriving the week column; it now stores them with empty timing columns and logs the traceback on failure
- Exporter sent the literal string `None` as `Start`/`End` for jobs that never started, which made the dashboard reject the whole batch with 422

### Changed
- `requires-python` bounded to `<3.13` because the pinned `pyarrow`/`numpy` have no wheels for 3.13; install commands pass `--python 3.12` and the conda instructions are replaced by uv and venv

### Added
- `slurm-dashboard sync-config` and `run --sync-config`: agent reads node CPU, memory, GPU, and partition data from `scontrol` and the dashboard merges it into `clusters.yaml`
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
