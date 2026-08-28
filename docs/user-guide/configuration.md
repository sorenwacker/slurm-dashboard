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

1. **Admin > Clusters > Add Cluster**: enter the cluster name; the API key is generated and a `clusters.yaml` entry is created with the name, description, contact, and location. The YAML entry is written before the cluster record, so a cluster is never created without its configuration; if `clusters.yaml` is not writable by the service user, creation fails and nothing is created.
2. **Install the agent** on the cluster with the deploy-key command shown on the cluster page and run `slurm-dashboard sync-config`. This fills in nodes, hardware, partitions, accounts, and the SLURM version from SLURM itself (see [Cluster Sync](#cluster-sync)).
3. **Add labels** on the cluster page: node synonyms and descriptions, partition and account display names. These are the only hand-maintained values.

### Admin Cluster Page

Every cluster has one page, `/admin/clusters/<name>`, reached from the cluster list. The page has five tabs.

**Overview**

- Identity: display name, description, location, owner, contact, URL. Editable in place; the description, contact, and location are also stored on the cluster record.
- SLURM: version and cluster name as reported by the agent.
- Sync status: time of the last `sync-config`, number of nodes with SLURM hardware, number of nodes known only from job data, number of partitions and accounts. If the cluster was never synced, the page shows the command to run.
- Data status: first and last job date, jobs submitted through the API, time of the last submission.
- Credentials: the API key (with rotate) and the one-time deploy key with the install command.

**Nodes**

One row per node: name, type, CPUs, memory, GPUs, partitions, features, source, synonyms, description. Source is `SLURM` when the node has synced hardware and `job data` when it was only discovered from uploaded jobs; nodes in the configuration that SLURM no longer reports are marked. Search, filter by type and partition, and a toggle to show only nodes not reported by SLURM. Synonyms, description, and type are editable in place; hardware, partitions, and features are read-only because they come from SLURM. Type can be set to `login` or `storage` for nodes that must not count as compute capacity.

**Partitions**

Name (with a marker for the SLURM default partition), nodes, CPUs, maximum wall time, state, display name, description. Display name and description are editable in place.

**Accounts**

Account, SLURM description, organization, display name, short name, faculty, department. The label fields are editable in place.

**YAML**

The raw cluster entry for edits the tabs do not cover, and an export button. Saving validates the YAML and reloads the configuration.

There is no automatic label generation: the page never invents descriptions, display names, or node types. Values come from SLURM through the agent or are typed by an administrator.

Per-entry edits use `PATCH /api/admin/clusters/by-name/<name>/nodes/<node>`, `/partitions/<partition>`, `/accounts/<account>`, and `/identity`; each accepts only the label fields listed above and returns the updated entry. `GET /api/admin/clusters/by-name/<name>/status` returns the sync and data status.

### Cluster Without Configuration

When a cluster record exists without a `clusters.yaml` entry (for example after a failed creation), the cluster page reports it and offers to create a default entry; it never shows another cluster's configuration in its place.

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

With `auto_generate_labels: true`, the dashboard adds every node name found in uploaded job data to the configuration (after checking canonical names and synonyms), with `type` set to `default_node_type` and no hardware. Such nodes show `Source: job data` on the cluster page until a `sync-config` run replaces the default type with the one derived from the reported GPU count.

### Cluster Sync

The agent command `slurm-dashboard sync-config` reads the cluster from SLURM (`scontrol show config`, `scontrol show node`, `scontrol show partition`, `sacctmgr show account`) and uploads it to `POST /api/agent/upload-config`. The dashboard merges it into `clusters.yaml`:

- nodes: `hardware.cpu.cores` (schedulable CPUs), `sockets`, `cores_per_socket`, `threads_per_core`, `hardware.ram.total_gb`, `hardware.gpus[]` (`model`, `count`), `partitions`, `features` are overwritten; `type` is set to `gpu` or `cpu` from the GPU count unless it is `login`, `storage`, or another hand-set type; `synonyms` and `description` are kept
- partitions: `slurm.nodes`, `slurm.total_cpus`, `slurm.total_nodes`, `slurm.max_time`, `slurm.default`, `slurm.state` are overwritten; `display_name` and `description` are kept
- accounts: `slurm.description` and `slurm.organization` are overwritten; `display_name`, `short_name`, `faculty`, `department` are kept
- cluster: `metadata.slurm_version`, `metadata.slurm_cluster_name`, and `metadata.last_hardware_sync` (UTC ISO 8601) are set
- entries no longer reported by SLURM are kept

The sync never generates descriptions or display names. The configuration is reloaded after each sync. See the [Cluster Setup Guide](cluster-setup.md#5-sync-cluster-configuration) for the agent side.

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
