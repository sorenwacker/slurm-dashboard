# Quick Start Guide

Get SLURM Dashboard up and running in 5 minutes.

## TL;DR

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install from GitLab
pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"

# Collect data (on cluster; deploy key comes from the admin panel)
slurm-dashboard setup --api-url http://localhost:8100 --deploy-key deploy_xxx
slurm-dashboard run --config config.json

# Start dashboard (on server) - frontend included
export DATA_PATH=/data/slurm-usage
slurm-dashboard
```

Open browser to `http://localhost:8100`

Frontend is included with `[web]` extra - no separate build needed.

**Note:** Once published to PyPI, you can use `pip install slurm-dashboard[all]` instead.

## Step-by-Step

### 1. Install Package

Create a virtual environment and install the package:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install package (choose based on needs)
```

**From PyPI (when published):**
```bash
# For web dashboard (recommended)
pip install slurm-dashboard[web]

# Everything (includes agent + web)
pip install slurm-dashboard[all]

# For cluster agent only
pip install slurm-dashboard[agent]
```

**From GitLab (before PyPI release or for development):**
```bash
# With pip - everything (agent + web)
pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"

# With uv (faster)
uv pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"

# For cluster agent only
pip install "slurm-dashboard[agent] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"
```

**Note:** Remember to activate the virtual environment before running commands:
```bash
source .venv/bin/activate
```

### 2. Collect SLURM Data

On your SLURM cluster head node:

```bash
# One-time setup with a deploy key from the admin panel
slurm-dashboard setup --api-url https://your-dashboard.example.com --deploy-key deploy_xxx

# Collect and upload job data (last 7 days by default)
slurm-dashboard run --config config.json
```

**Automate with cron:**

```bash
# Edit crontab
crontab -e

# Add daily collection at 2 AM, keeping the cluster configuration synced
0 2 * * * $HOME/.local/bin/slurm-dashboard run --config $HOME/config.json --sync-config >> $HOME/agent.log 2>&1
```

See the [Cluster Setup Guide](../user-guide/cluster-setup.md) for details.

### 3. Configure Environment

Create a `.env` file with your configuration:

```bash
# Create .env file
cat > .env << 'EOF'
# Required: Path to SLURM data
DATA_PATH=/data/slurm-usage

# Optional: API configuration
API_PREFIX=/api
AUTO_REFRESH_INTERVAL=600

# Optional: CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:8100

# Optional: SAML authentication
ENABLE_SAML=false

# Optional: Logging
LOG_LEVEL=INFO
EOF
```

Or copy from example:
```bash
cp .env.example .env
# Edit with your values
nano .env
```

### 4. Start Backend

```bash
# Start backend with integrated frontend
slurm-dashboard

# Or with auto-reload for development
slurm-dashboard --reload
```

Backend is now running at `http://localhost:8100`

Test API: `curl http://localhost:8100/api/dashboard/health`

### 5. Access Dashboard

Open browser to:
- Dashboard: `http://localhost:8100`
- Backend API docs: `http://localhost:8100/docs`

The frontend is pre-built and served directly by FastAPI.

### 6. Frontend Development (Optional)

Only needed if you want to modify the frontend:

```bash
cd frontend

# Install dependencies
npm install

# Start development server with hot reload
npm run dev
```

Development server runs at `http://localhost:5173` with hot module replacement.

## Production Deployment

### Option 1: Automated (Ansible)

```bash
cd ansible
ansible-playbook -i inventory.yml playbook.yml
```

### Option 2: Manual

See [INSTALL.md](../getting-started/installation.md) for detailed production setup.

## Common Commands

### Data Collection

```bash
# Collect last 7 days
slurm-dashboard run --config config.json

# Collect specific date range
slurm-dashboard run --config config.json --start-date 2024-01-01 --end-date 2024-12-31

# Analyze waiting times
slurm-dashboard-wait-times --input /data/slurm-usage/CLUSTER
```

### Backend Management

```bash
# Development
slurm-dashboard --reload

# Production (with Gunicorn)
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8100

# Check logs
tail -f /var/log/slurm-dashboard-backend.log
```

### Frontend Management

```bash
# Development
npm run dev

# Build for production
VITE_API_URL=https://dashboard.example.com npm run build

# Preview production build
npm run preview
```

## Environment Variables

Create `.env` file in project root:

```bash
# Required
DATA_PATH=/data/slurm-usage

# Optional
API_PREFIX=/api
AUTO_REFRESH_INTERVAL=600
CORS_ORIGINS=http://localhost:5173,https://dashboard.example.com

# SAML (optional)
ENABLE_SAML=false
SAML_SETTINGS_PATH=/etc/slurm-dashboard/saml.json
```

## Troubleshooting

### No data showing in dashboard

1. Check data path:
   ```bash
   ls -la $DATA_PATH
   ```

2. Verify parquet files exist:
   ```bash
   find $DATA_PATH -name "*.parquet"
   ```

3. Check backend logs:
   ```bash
   # Development
   Check terminal output

   # Production
   journalctl -u slurm-dashboard-backend -n 50
   ```

### Backend won't start

1. Check DuckDB installation:
   ```bash
   python -c "import duckdb; print('OK')"
   ```

2. Verify data path is accessible:
   ```bash
   python -c "from pathlib import Path; print(Path('$DATA_PATH').exists())"
   ```

3. Check port availability:
   ```bash
   lsof -i :8100
   ```

### Frontend build fails

1. Check Node.js version:
   ```bash
   node --version  # Should be 20+
   ```

2. Clear cache:
   ```bash
   rm -rf node_modules dist
   npm install
   ```

### Charts show empty data

1. Check date range matches available data:
   ```bash
   # List available date ranges
   find $DATA_PATH -name "*.parquet" | head
   ```

2. Clear browser cache and hard refresh (Ctrl+Shift+R)

3. Check browser console for errors (F12)

## Next Steps

- Read [INSTALL.md](../getting-started/installation.md) for production deployment
- Configure [SAML authentication](../getting-started/installation.md#saml-authentication-optional)
- Set up [automated backups](../getting-started/installation.md#data-backup)
- Explore [API documentation](http://localhost:8100/docs)

## Getting Help

- Open an [issue](https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history/-/issues)
- Contact: s.wacker@tudelft.nl
