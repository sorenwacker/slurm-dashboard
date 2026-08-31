# Installation Guide - SLURM Dashboard

Modern web dashboard for SLURM cluster usage analytics with DuckDB-powered data processing.

## Quick Start

### From PyPI (Recommended)

```bash
# Install core package
pip install slurm-dashboard

# With data collection agent
pip install slurm-dashboard[agent]

# With web dashboard
pip install slurm-dashboard[web]

# Everything
pip install slurm-dashboard[all]
```

### From GitLab (Development/Pre-release)

Install directly from the GitLab repository:

**With pip:**
```bash
# Latest from main branch - core only
pip install git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git

# With agent extra
pip install "slurm-dashboard[agent] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"

# With web extra
pip install "slurm-dashboard[web] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"

# Everything
pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"

# Specific tag/version
pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git@v0.3.0"

# Specific commit
pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git@382c032"
```

**With uv (faster):**
```bash
# Everything from latest
uv pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git"

# Specific version
uv pip install "slurm-dashboard[all] @ git+https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git@v0.3.0"
```

**Note:** GitLab installation requires git to be installed and GitLab access configured.

## Installation Scenarios

### 1. Cluster Agent (Data Collection)

Install on SLURM head node or compute node with `sacct` access:

```bash
pip install slurm-dashboard[agent]
```

**Usage:**
```bash
# One-time setup with a deploy key from the admin panel
slurm-dashboard setup --api-url https://your-dashboard.example.com --deploy-key deploy_xxx

# Collect and upload job data (last 7 days by default)
slurm-dashboard run --config config.json
```

**Automated Collection (cron):**
```bash
# Add to crontab: daily at 2 AM, keeping the cluster configuration synced
0 2 * * * $HOME/.local/bin/slurm-dashboard run --config $HOME/config.json --sync-config >> $HOME/agent.log 2>&1
```

See the [Cluster Setup Guide](../user-guide/cluster-setup.md) for the full setup.

### 2. Web Dashboard

Install on dashboard server:

```bash
pip install slurm-dashboard[web]
```

**Requirements:**
- Python 3.10+
- Access to data directory (e.g., NFS mount)
- For production: systemd, optional nginx/apache for reverse proxy

**Quick Test:**
```bash
# Set data path
export DATA_PATH=/data/slurm-usage

# Start backend with integrated frontend
slurm-dashboard
```

The `[web]` extra includes the pre-built React frontend served directly by FastAPI.

**Production Deployment:**

See [deployment guide](#production-deployment) below.

### 3. Development Environment

```bash
# Clone repository
git clone https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history.git
cd slurm-usage-history

# Install with uv (recommended)
uv pip install -e ".[all,dev]"

# Or with pip
pip install -e ".[all,dev]"
```

## Production Deployment

### Using Ansible (Recommended)

We provide Ansible playbooks for automated deployment:

```bash
cd ansible
ansible-playbook -i inventory.yml playbook.yml
```

See [https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history-ansible](https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history-ansible) for configuration options.

### Manual Deployment

#### 1. Backend Setup

```bash
# Create user
sudo useradd -r -s /bin/bash -d /opt/slurm-dashboard slurmusage

# Install package
sudo -u slurmusage pip install slurm-dashboard[web]

# Create environment file
sudo tee /opt/slurm-dashboard/.env << EOF
DATA_PATH=/data/slurm-usage
API_PREFIX=/api
AUTO_REFRESH_INTERVAL=600
ENABLE_SAML=false
EOF

# Create systemd service
sudo tee /etc/systemd/system/slurm-dashboard-backend.service << EOF
[Unit]
Description=SLURM Dashboard Backend API
After=network.target

[Service]
Type=simple
User=slurmusage
Group=slurmusage
WorkingDirectory=/opt/slurm-dashboard
Environment="PATH=/opt/slurm-dashboard/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/opt/slurm-dashboard/.env
ExecStart=/opt/slurm-dashboard/.venv/bin/gunicorn \\
    backend.app.main:app \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 127.0.0.1:8100 \\
    --timeout 120
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable slurm-dashboard-backend
sudo systemctl start slurm-dashboard-backend
```

#### 2. Nginx Reverse Proxy (Optional)

For HTTPS/TLS termination:

```bash
sudo tee /etc/nginx/sites-available/slurm-dashboard << 'EOF'
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    # Proxy all requests to FastAPI (serves both frontend and API)
    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/slurm-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

FastAPI serves both the frontend and API endpoints.

#### 3. SAML Authentication (Optional)

```bash
# Install python3-saml
pip install python3-saml

# Create SAML settings
sudo mkdir -p /opt/slurm-dashboard/saml
sudo tee /opt/slurm-dashboard/saml/settings.json << EOF
{
  "strict": true,
  "debug": false,
  "sp": {
    "entityId": "https://your-domain.com/saml/metadata",
    "assertionConsumerService": {
      "url": "https://your-domain.com/saml/acs",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    },
    "singleLogoutService": {
      "url": "https://your-domain.com/saml/sls",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
  },
  "idp": {
    "entityId": "https://your-idp.com/saml/metadata",
    "singleSignOnService": {
      "url": "https://your-idp.com/saml/sso",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "x509cert": "YOUR_IDP_CERTIFICATE"
  }
}
EOF

# Update .env
echo "ENABLE_SAML=true" | sudo tee -a /opt/slurm-dashboard/.env
echo "SAML_SETTINGS_PATH=/opt/slurm-dashboard/saml/settings.json" | sudo tee -a /opt/slurm-dashboard/.env

# Restart backend
sudo systemctl restart slurm-dashboard-backend
```

## Data Directory Structure

The dashboard expects data in this format:

```
/data/slurm-usage/
├── CLUSTER1/
│   └── weekly-data/
│       ├── 2024-W01.parquet
│       ├── 2024-W02.parquet
│       └── ...
├── CLUSTER2/
│   └── weekly-data/
│       └── ...
```

Written by the dashboard when agents upload data through the API.

## Configuration

### Environment Variables

Backend configuration via `.env` file:

```bash
# Required
DATA_PATH=/data/slurm-usage

# Optional
API_PREFIX=/api
AUTO_REFRESH_INTERVAL=600  # seconds

# SAML (optional)
ENABLE_SAML=false
SAML_SETTINGS_PATH=/path/to/saml/settings.json

# CORS (optional)
CORS_ORIGINS=https://your-domain.com,https://other-domain.com
```

### Frontend Configuration

Set API URL at build time:

```bash
VITE_API_URL=https://your-domain.com npm run build
```

## Troubleshooting

### Backend won't start
```bash
# Check logs
sudo journalctl -u slurm-dashboard-backend -n 100 --no-pager

# Check data path
ls -la $DATA_PATH

# Test DuckDB
python3 -c "import duckdb; print('DuckDB OK')"
```

### High memory usage
- Ensure using DuckDB backend (not legacy Pandas)
- Reduce workers: `--workers 2`
- Check data size: `du -sh $DATA_PATH`

### Frontend build fails
```bash
# Check Node.js version
node --version  # Should be 20+

# Clear cache and rebuild
rm -rf node_modules dist
npm install
npm run build
```

### Charts show no data
- Check date range matches data availability
- Verify filter values exist in the period
- Check browser console for API errors
- Test backend directly: `curl http://localhost:8100/api/dashboard/metadata`

## Upgrading

```bash
# Backup data (optional)
cp -r /data/slurm-usage /data/slurm-usage.backup

# Upgrade package
pip install --upgrade slurm-dashboard[web]

# Rebuild frontend (if using web extra)
cd frontend
npm install
VITE_API_URL=https://your-domain.com npm run build

# Restart services
sudo systemctl restart slurm-dashboard-backend
sudo systemctl reload nginx
```

## Performance Tuning

### DuckDB Configuration

For large datasets (>100GB), tune DuckDB settings:

```python
# In backend config
DUCKDB_MEMORY_LIMIT=8GB
DUCKDB_THREADS=4
```

### Gunicorn Workers

Adjust based on CPU cores:

```bash
# Rule of thumb: (2 x cores) + 1
--workers 9  # for 4-core machine
```

### Nginx Caching

Add caching for static assets:

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Security Considerations

1. **SAML Authentication**: Recommended for production
2. **HTTPS**: Required for SAML and security
3. **File Permissions**: Restrict data directory access
4. **Firewall**: Only expose port 443 (HTTPS)
5. **Updates**: Regularly update dependencies

## Support

- Issues: https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history/-/issues
- Documentation: https://gitlab.ewi.tudelft.nl/sdrwacker/slurm-usage-history
