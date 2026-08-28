"""Cluster agent CLI for data collection and submission to dashboard."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import requests
import yaml

from slurm_usage_history.scripts.node_inventory import collect_node_inventory


def setup_command(args):
    """Setup agent using deploy key."""
    api_url = args.api_url.rstrip('/')
    deploy_key = args.deploy_key

    print(f"Exchanging deploy key with {api_url}...")

    try:
        # Exchange deploy key for API key
        response = requests.post(
            f"{api_url}/api/agent/exchange-deploy-key",
            data={"deploy_key": deploy_key},
            timeout=30
        )

        if response.status_code != 200:
            print(f"ERROR: Failed to exchange deploy key: {response.text}", file=sys.stderr)
            sys.exit(1)

        result = response.json()
        api_key = result.get("api_key")
        cluster_name = result.get("cluster_name")

        if not api_key:
            print("ERROR: No API key returned from server", file=sys.stderr)
            sys.exit(1)

        print(f"Successfully authenticated as cluster: {cluster_name}")

        # Create configuration
        config = {
            "api_url": api_url,
            "api_key": api_key,
            "cluster_name": cluster_name,
            "local_data_path": args.local_data_path or "",
            "timeout": 120,
            "collection_window_days": 14,
        }

        config_path = Path(args.output)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        config_path.chmod(0o600)

        print(f"\nConfiguration created at: {config_path}")
        print(f"Cluster: {cluster_name}")
        print(f"API URL: {api_url}")
        print("\nSetup complete! You can now run:")
        print(f"  slurm-dashboard run --config {config_path}")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to connect to dashboard: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def create_config_command(args):
    """Create configuration file."""
    config = {
        "api_url": args.api_url,
        "api_key": args.api_key,
        "cluster_name": args.cluster_name or "",
        "local_data_path": args.local_data_path or "",
        "timeout": 120,
        "collection_window_days": 14,
    }

    config_path = Path(args.output)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    config_path.chmod(0o600)
    print(f"Configuration created at: {config_path}")
    print(f"API URL: {config['api_url']}")
    print(f"Cluster: {config['cluster_name'] or '(auto-detect)'}")
    if config['local_data_path']:
        print(f"Local data path: {config['local_data_path']}")


def sync_config(config_path, dry_run):
    """Read node hardware from scontrol and upload it to the dashboard.

    Args:
        config_path: Path to the agent config.json
        dry_run: Print the inventory instead of uploading it

    Returns:
        Server response with ``added``/``updated`` counts, or None for a dry run

    Raises:
        RuntimeError: If scontrol fails or the server rejects the upload
    """
    with open(config_path) as f:
        config = json.load(f)

    inventory = collect_node_inventory()
    document = yaml.dump(inventory, default_flow_style=False, sort_keys=False)

    if dry_run:
        print(document)
        return None

    response = requests.post(
        f"{config['api_url'].rstrip('/')}/api/agent/upload-config",
        headers={"X-API-Key": config["api_key"]},
        files={"file": ("inventory.yaml", document, "application/x-yaml")},
        timeout=config.get("timeout", 120),
    )
    if response.status_code != 201:
        message = f"Hardware sync rejected ({response.status_code}): {response.text}"
        raise RuntimeError(message)
    return response.json()


def sync_config_command(args):
    """CLI entry for sync-config."""
    try:
        result = sync_config(Path(args.config), args.dry_run)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    if result is not None:
        print(f"Hardware synced: {result.get('added', 0)} nodes added, {result.get('updated', 0)} updated")


def run_command(args):
    """Run the cluster agent exporter."""
    if args.sync_config:
        try:
            result = sync_config(Path(args.config), args.dry_run)
            if result is not None:
                print(f"Hardware synced: {result.get('added', 0)} nodes added, {result.get('updated', 0)} updated")
        except RuntimeError as e:
            print(f"WARNING: hardware sync failed, continuing with job collection: {e}", file=sys.stderr)

    # Get the exporter script path
    script_path = Path(__file__).parent / "exporter.py"

    if not script_path.exists():
        print(f"ERROR: Exporter script not found at {script_path}", file=sys.stderr)
        print("Please reinstall the package with: pip install slurm-dashboard[agent]", file=sys.stderr)
        sys.exit(1)

    # Build command arguments
    cmd = [sys.executable, str(script_path)]

    if args.config:
        cmd.extend(["--config", args.config])
    if args.cluster_name:
        cmd.extend(["--cluster-name", args.cluster_name])
    if args.start_date:
        cmd.extend(["--start-date", args.start_date])
    if args.end_date:
        cmd.extend(["--end-date", args.end_date])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.verbose:
        cmd.append("--verbose")

    # Run the exporter
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def build_parser():
    """Build the argument parser for the agent CLI."""
    parser = argparse.ArgumentParser(
        prog="slurm-dashboard",
        description="SLURM Usage History Dashboard - Cluster Agent",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup command (recommended for first-time setup)
    setup_parser = subparsers.add_parser(
        "setup",
        help="Setup agent using deploy key (recommended for first-time setup)",
    )
    setup_parser.add_argument(
        "--api-url",
        required=True,
        help="Dashboard API URL (e.g., https://dashboard.daic.tudelft.nl)",
    )
    setup_parser.add_argument(
        "--deploy-key",
        required=True,
        help="One-time deployment key from dashboard admin",
    )
    setup_parser.add_argument(
        "--local-data-path",
        help="Local path to save extracted data as backup (optional)",
    )
    setup_parser.add_argument(
        "-o", "--output",
        default="config.json",
        help="Output configuration file path (default: config.json)",
    )
    setup_parser.set_defaults(func=setup_command)

    # create-config command
    config_parser = subparsers.add_parser(
        "create-config",
        help="Create agent configuration file",
    )
    config_parser.add_argument(
        "--api-url",
        required=True,
        help="Dashboard API URL (e.g., https://dashboard.example.com)",
    )
    config_parser.add_argument(
        "--api-key",
        required=True,
        help="API key for authentication",
    )
    config_parser.add_argument(
        "--cluster-name",
        help="Cluster name (auto-detected if not provided)",
    )
    config_parser.add_argument(
        "--local-data-path",
        help="Local path to save extracted data as backup (optional)",
    )
    config_parser.add_argument(
        "-o", "--output",
        default="config.json",
        help="Output configuration file path (default: config.json)",
    )
    config_parser.set_defaults(func=create_config_command)

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run the cluster agent to collect and submit data",
    )
    run_parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )
    run_parser.add_argument(
        "--cluster-name",
        help="Override cluster name from config",
    )
    run_parser.add_argument(
        "--start-date",
        help="Start date for data collection (YYYY-MM-DD)",
    )
    run_parser.add_argument(
        "--end-date",
        help="End date for data collection (YYYY-MM-DD)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and format but don't submit to API",
    )
    run_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )
    run_parser.add_argument(
        "--sync-config",
        action="store_true",
        help="Upload node hardware from scontrol before collecting jobs",
    )
    run_parser.set_defaults(func=run_command)

    # sync-config command
    sync_parser = subparsers.add_parser(
        "sync-config",
        help="Upload node hardware (CPU cores, memory, GPUs, partitions) from scontrol to the dashboard",
    )
    sync_parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the node inventory without uploading",
    )
    sync_parser.set_defaults(func=sync_config_command)

    return parser


def main():
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
