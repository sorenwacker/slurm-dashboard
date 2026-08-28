# SLURM Dashboard

Web dashboard for SLURM cluster usage analytics powered by DuckDB.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

**[Documentation](https://sdrwacker.pages.ewi.tudelft.nl/slurm-usage-history)** | **[GitHub](https://github.com/tudelft-reit/slurm-dashboard)**

![SLURM Dashboard Screenshot](docs/images/SLURM-Dashboard.png)

## Quick Start with Docker (Demo)

Try the dashboard with synthetic demo data in 3 steps:

```bash
# 1. Start the dashboard
docker-compose up -d

# 2. Open http://localhost:3100/admin/clusters
#    Login: admin / admin (default credentials)

# 3. Click "Create Demo" button to generate 2 years of synthetic data
```

The demo cluster includes 110k jobs, seasonal patterns, simulated outages, and realistic job distributions.

## Production Setup

### 1. Install

```bash
pip install slurm-dashboard[all]
```

### 2. Collect Data (on SLURM cluster)

```bash
# Collect job data from SLURM and save to shared storage
slurm-dashboard-agent --output /shared/slurm-data/$(hostname)
```

This extracts job data from SLURM using `sacct` and saves it as Parquet files.

### 3. Start Dashboard (on dashboard server)

```bash
# Point to the data directory and start the web server
export DATA_PATH=/shared/slurm-data
slurm-dashboard
```

Access at **http://localhost:8100**

See [documentation](https://sdrwacker.pages.ewi.tudelft.nl/slurm-usage-history) for production deployment with SAML, systemd, and multi-cluster setup.

## Admin Panel

Access the admin panel at **http://localhost:8100/admin/login** to:

- **Manage Clusters**: Add, activate/deactivate, and configure multiple SLURM clusters
- **Deploy Keys**: Generate one-time setup keys for secure agent deployment
- **Generate Demo Data**: Create synthetic cluster data for testing with realistic patterns
- **Auto-generate Configs**: Automatically detect nodes, accounts, and partitions from data
- **User Management**: Control access and view user activity
- **API Key Rotation**: Manage and rotate authentication keys for data submission agents

Default admin credentials can be configured via environment variables or SAML.

### Cluster Agent Setup

For cluster administrators, the recommended setup process uses deploy keys:

1. Admin creates cluster in dashboard and generates a deploy key
2. Copy the one-command setup from the admin panel
3. Run on your cluster - it installs the agent and exchanges the deploy key for a permanent API key

```bash
# with uv
uv tool install --python 3.12 'slurm-dashboard[agent] @ git+https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git' && \
slurm-dashboard setup --api-url https://your-dashboard.example.com --deploy-key deploy_xxx

# or with pip
pip install 'git+https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history.git#egg=slurm-dashboard[agent]' && \
slurm-dashboard setup --api-url https://your-dashboard.example.com --deploy-key deploy_xxx
```

Deploy keys are single-use, expire after 7 days, and provide IP tracking for security.

## Development

### Setup

```bash
git clone https://github.com/tudelft-reit/slurm-dashboard.git
cd slurm-dashboard
uv pip install -e ".[all,dev]"
./build_frontend.sh
uv run pytest
```

### Generate Test Data

Create synthetic cluster data for local development:

```bash
# Generate test data for a cluster (creates data/TestCluster/weekly-data/*.parquet)
python scripts/generate_test_cluster_data.py --cluster TestCluster

# Customize date range and job volume
python scripts/generate_test_cluster_data.py \
  --cluster MyCluster \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --jobs-per-day 100
```

### Run Development Environment

Use Docker Compose for local development with hot-reload:

```bash
# Build and start containers
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

Access the dashboard:
- **Frontend UI**: http://localhost:3100
- **Backend API**: http://localhost:8100
- **API Docs**: http://localhost:8100/docs

Stop containers:
```bash
docker-compose down
```

## License & Contact

GPL-3.0-or-later | [Issues](https://github.com/tudelft-reit/slurm-dashboard/issues) | s.wacker@tudelft.nl | TU Delft REIT
