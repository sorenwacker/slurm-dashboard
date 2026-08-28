# Configuration Guide

This document explains the two-level configuration structure used by the SLURM Usage History Dashboard.

## Overview

The dashboard uses two separate configuration files:

1. **Dashboard-wide Configuration** (`.env`) - Global settings for the entire dashboard
2. **Cluster-specific Configuration** (`config/clusters.yaml`) - Settings for each individual cluster

---

## 1. Dashboard-wide Configuration (.env)

Located at: `/opt/slurm-usage-history/.env` (on server) or `backend/.env` (development)

### Authentication Settings

#### Admin Access (Password-based)
```bash
# Fallback admin account (username:bcrypt_hash format)
ADMIN_USERS=admin:$2b$12$tCIgrmuyRCjOPJdAyds0kehbikagSkZqTKkavZTl9teDfT9aNps2.

# Secret key for JWT tokens (generate with: python -c "import secrets; print(secrets.token_urlsafe(64))")
ADMIN_SECRET_KEY=your-random-secret-key-here
```

**Current Admin Credentials:**
- Username: `admin`
- Password: `KUhN7Ty6Fb7tigTE7c5mfEYoLba00dp1vSNVmKwgLqg`

#### SAML-based Access
```bash
# Admin emails - users with these emails get admin access after SAML login
ADMIN_EMAILS=user1@example.com,user2@example.com

# Superadmin emails - users with these emails get superadmin panel access
SUPERADMIN_EMAILS=admin@example.com
```

**Permissions:**
- **Admin** (via SAML): Can manage clusters, view all data, generate reports
- **Superadmin** (via SAML): Full access including cluster creation/deletion, API key rotation
- **Password-based admin**: Fallback access when SAML is unavailable

### Other Dashboard Settings

```bash
# API Keys for agent data uploads (comma-separated)
# Note: These are legacy - prefer using per-cluster API keys from database
API_KEYS=legacy-key-1,legacy-key-2

# Data storage path
DATA_PATH=/data/slurm-usage-history

# CORS origins (comma-separated)
CORS_ORIGINS=https://dashboard.daic.tudelft.nl,https://dashboard2.example.com

# Auto-refresh interval (seconds)
AUTO_REFRESH_INTERVAL=600

# SAML session secret key
SECRET_KEY=your-saml-secret-key

# DuckDB configuration directory
DUCKDB_HOME=/opt/slurm-usage-history/.duckdb
```

---

## 2. Cluster-specific Configuration (config/clusters.yaml)

Located at: `/opt/slurm-usage-history/config/clusters.yaml`

Each cluster can have its own configuration with node labels, hardware specs, account mappings, and partition information.

### Structure

```yaml
clusters:
  CLUSTER_NAME:  # Must match cluster name in database (case-sensitive)
    display_name: "Human-readable Cluster Name"
    description: "Description of the cluster"

    metadata:
      location: "Physical location"
      owner: "Organization/Department"
      contact: "contact@example.com"
      url: "https://cluster-docs.example.com"

    # Node configuration
    node_labels:
      canonical_node_name:
        synonyms: ["alias1", "alias2", "Alias3"]  # Case variations and aliases
        type: "gpu|cpu|login|storage"
        description: "Node description"
        hardware:
          cpu:
            model: "Intel Xeon Gold 6248R"
            cores: 48
            threads: 96
          ram:
            total_gb: 384
            type: "DDR4"
          gpus:
            - model: "NVIDIA A100"
              count: 4
              memory_gb: 40
              nvlink: true
              nvlink_topology: "4x NVLink"

    # Account/project mappings
    account_labels:
      account_id:
        display_name: "Full Department Name"
        short_name: "DEPT"
        faculty: "Faculty Name"
        department: "Department Name"

    # Partition/queue information
    partition_labels:
      partition_name:
        display_name: "Partition Display Name"
        description: "Partition description"

settings:
  # Global settings for all clusters
  default_node_type: "cpu"
  case_sensitive: false
  auto_generate_labels: true  # Auto-discover nodes from data
```

### Example Configuration

```yaml
clusters:
  DAIC:
    display_name: "DAIC Cluster"
    description: "TU Delft AI Cluster"

    metadata:
      location: "TU Delft"
      owner: "REIT"
      contact: "reit@tudelft.nl"

    node_labels:
      # GPU nodes
      gpu05:
        synonyms: ["gpu5", "Gpu05", "GPU05", "gpu-05"]
        type: "gpu"
        description: "GPU Node 05"
        hardware:
          cpu:
            model: "Intel Xeon Gold 6248R"
            cores: 48
            threads: 96
          ram:
            total_gb: 384
            type: "DDR4"
          gpus:
            - model: "NVIDIA A100"
              count: 4
              memory_gb: 40
              nvlink: true
              nvlink_topology: "4x NVLink"

      # CPU nodes
      compute01:
        synonyms: ["compute1", "Compute01", "comp01"]
        type: "cpu"
        description: "Compute Node 01"
        hardware:
          cpu:
            model: "Intel Xeon Silver 4214R"
            cores: 24
            threads: 48
          ram:
            total_gb: 192
            type: "DDR4"

    account_labels:
      ewi-insy-prb:
        display_name: "INSY - Pattern Recognition & Bioinformatics"
        short_name: "PRB"
        faculty: "EWI"
        department: "INSY"

    partition_labels:
      gpu:
        display_name: "GPU Partition"
        description: "GPU-enabled compute nodes"
      compute:
        display_name: "Compute Partition"
        description: "General purpose compute nodes"

settings:
  default_node_type: "cpu"
  case_sensitive: false
  auto_generate_labels: true
```

---

## Configuration Workflow

### Adding Admin/Superadmin Users

#### Method 1: Via Admin Panel (Recommended)

1. **Login to admin panel:**
   - Visit https://dashboard.daic.tudelft.nl/admin/login
   - Login with admin credentials

2. **Navigate to Users page:**
   - Click "Users" in the navigation menu
   - Or visit https://dashboard.daic.tudelft.nl/admin/users

3. **Add email addresses:**
   - Enter email addresses in the appropriate sections (Admin or Superadmin)
   - Click "Add" to add each email
   - Click "Save Changes" to apply

4. **Restart backend:**
   ```bash
   sudo systemctl restart slurm-usage-backend
   ```

#### Method 2: Via .env File (Alternative)

1. **Via SAML:**
   ```bash
   # Edit .env file
   ADMIN_EMAILS=user1@tudelft.nl,user2@tudelft.nl
   SUPERADMIN_EMAILS=admin@tudelft.nl

   # Restart backend
   sudo systemctl restart slurm-usage-backend
   ```

2. **Via Password (Fallback):**
   ```bash
   # Generate secure password
   python -c "import secrets; print(secrets.token_urlsafe(32))"

   # Generate bcrypt hash
   python -c "import bcrypt; pw = b'YOUR_PASSWORD'; print(bcrypt.hashpw(pw, bcrypt.gensalt()).decode())"

   # Add to .env
   ADMIN_USERS=username:$2b$12$...hash...

   # Restart backend
   sudo systemctl restart slurm-usage-backend
   ```

### Configuring a New Cluster

1. **Create cluster in admin panel:**
   - Login at https://dashboard.daic.tudelft.nl/admin/login
   - Click "Add Cluster"
   - Enter cluster name (e.g., "DAIC"), description, contact email, and location
   - Save and copy the generated API key
   - **A default YAML configuration is automatically created** with the provided metadata. The YAML entry is written before the cluster record, so a cluster is never created without its configuration. If `clusters.yaml` is not writable by the service user, creation fails with an error and nothing is created.

2. **Customize cluster details in YAML (optional):**
   ```bash
   # Edit config/clusters.yaml to add node hardware specs, aliases, etc.
   nano /opt/slurm-usage-history/config/clusters.yaml

   # Add node_labels, account_labels, partition_labels (see example above)
   ```

3. **Reload configuration:**
   - Visit https://dashboard.daic.tudelft.nl/admin/config
   - Click "Reload" to apply changes
   - Or use API: `POST /api/admin/config/reload`

**Note:** With `auto_generate_labels: true` (default), the dashboard will automatically discover nodes from uploaded data and add them to the configuration. Hardware specifications are filled in by the agent's `sync-config` command (see [Hardware Sync](#hardware-sync)); descriptions and synonyms are edited by hand.

### Cluster Without Configuration

The configuration page is opened per cluster (`/admin/config?cluster=NAME`). When the named cluster has no entry in `clusters.yaml`, the page reports "No configuration for cluster NAME" and offers to create a default entry; it never shows another cluster's configuration in its place.

### Adding Node Aliases

If SLURM reports nodes with different names (e.g., "gpu5", "GPU05", "gpu-05"), add them as synonyms:

```yaml
node_labels:
  gpu05:  # Canonical name
    synonyms: ["gpu5", "Gpu05", "GPU05", "gpu-05"]
    type: "gpu"
```

The dashboard will aggregate all data from these aliases under the canonical name "gpu05".

### Auto-discovery

With `auto_generate_labels: true`, the dashboard automatically:
1. Discovers new nodes from uploaded data
2. Adds them to the cluster configuration with default values
3. Checks if node exists as canonical name OR synonym before adding

You can then edit the auto-generated entries to add better descriptions.

### Hardware Sync

The agent command `slurm-dashboard sync-config` reads node hardware from SLURM (`scontrol show node`) and uploads it to `POST /api/agent/upload-config`. The dashboard merges it into `clusters.yaml` per node:

- `hardware.cpu.cores`, `hardware.ram.total_gb`, and `hardware.gpus[]` (`model`, `count`) are overwritten with the reported values
- `synonyms` and `description` are kept
- `type` is set to `gpu` or `cpu` according to the reported GPU count; `login`, `storage`, and other types are kept
- `partitions` lists the SLURM partitions the node belongs to
- nodes not yet in the configuration are added; nodes no longer reported by SLURM are kept

The merge records `metadata.last_hardware_sync` (UTC ISO 8601 timestamp) on the cluster, shown on the admin configuration page. The configuration is reloaded after each sync; no manual reload is required. See the [Cluster Setup Guide](cluster-setup.md#5-sync-node-hardware) for the agent side.

---

## Security Best Practices

1. **Use strong passwords:**
   ```bash
   # Generate with:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Prefer SAML authentication** for user access (no password storage needed)

3. **Keep admin passwords for emergency access** only

4. **Rotate API keys periodically** via admin panel

5. **Use HTTPS** for all dashboard access (already configured)

6. **Restrict .env file permissions:**
   ```bash
   chmod 600 /opt/slurm-usage-history/.env
   chown slurmusage:slurmusage /opt/slurm-usage-history/.env
   ```

---

## Access Levels

| User Type | How to Configure | Access Level |
|-----------|-----------------|--------------|
| **Regular User** | Anyone with SAML login | View dashboard, generate personal reports |
| **Admin** | Add email to `ADMIN_EMAILS` | Manage clusters, view all data, admin panel |
| **Superadmin** | Add email to `SUPERADMIN_EMAILS` | Full access: create/delete clusters, rotate keys |
| **Password Admin** | Add to `ADMIN_USERS` | Fallback access when SAML unavailable |

---

## Troubleshooting

### SAML users not getting admin access
- Check `ADMIN_EMAILS` and `SUPERADMIN_EMAILS` in `.env`
- Email must match exactly (case-sensitive)
- Restart backend after changes: `sudo systemctl restart slurm-usage-backend`

### Password login not working
- Verify bcrypt hash in `ADMIN_USERS`
- Check `ADMIN_SECRET_KEY` is set
- Test hash generation:
  ```bash
  python -c "import bcrypt; print(bcrypt.checkpw(b'your-password', b'$2b$12$...'))"
  ```

### Configuration not updating
- Click "Reload" in admin config panel
- Or restart backend: `sudo systemctl restart slurm-usage-backend`
- Check file permissions: `ls -l /opt/slurm-usage-history/config/clusters.yaml`

### Node aliases not working
- Check YAML syntax (use 2 spaces, not tabs)
- Ensure `case_sensitive: false` in settings
- Reload configuration after changes
