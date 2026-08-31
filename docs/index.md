# SLURM Dashboard

Web dashboard for SLURM cluster usage analytics powered by DuckDB.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

![SLURM Dashboard Screenshot](images/SLURM-Dashboard.png)

## Features

- **DuckDB-powered analytics** - 92% memory reduction (13GB → 1.1GB), 15x faster queries
- **React + FastAPI** - Modern async backend with interactive charts
- **SAML 2.0 authentication** - Enterprise SSO with role-based access
- **Multi-cluster support** - Aggregate data from multiple SLURM clusters
- **PDF reports** - Generate and share usage insights
- **Parquet storage** - Efficient compression and query speed

## Quick Start

### Installation

```bash
pip install slurm-dashboard[all]
```

### Collect Data

On the SLURM cluster:
```bash
# One-time setup with a deploy key from the admin panel
slurm-dashboard setup --api-url https://your-dashboard.example.com --deploy-key deploy_xxx

# Collect and upload job data (last 7 days by default)
slurm-dashboard run --config config.json
```

### Start Dashboard

```bash
export DATA_PATH=/data/slurm-usage
slurm-dashboard
# → http://localhost:8100
```

For production deployment with Gunicorn, SAML authentication, and systemd services, see [Installation Guide](getting-started/installation.md).

## Architecture

```
SLURM Cluster → Agent → Parquet files → Dashboard Server
                                         ├─ DuckDB
                                         ├─ FastAPI
                                         └─ React Frontend
```

## Documentation

- [Quick Start](getting-started/quickstart.md)
- [Installation](getting-started/installation.md)
- [Cluster Setup](user-guide/cluster-setup.md)
- [Configuration](user-guide/configuration.md)
- [API Docs](http://localhost:8100/docs) (when running)

## Development

```bash
git clone https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git
cd slurm-usage-history
uv pip install -e ".[all,dev]"
./build_frontend.sh
uv run pytest
```

See [Local Development](development/local-development.md) for Docker setup with SAML.

## License & Contact

GPL-3.0-or-later | [Issues](https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history/-/issues) | s.wacker@tudelft.nl | TU Delft REIT

## Citation

```bibtex
@software{slurm_dashboard,
  author = {Wacker, Sören},
  title = {SLURM Dashboard},
  year = {2024},
  url = {https://github.com/sorenwacker/slurm-dashboard}
}
```
