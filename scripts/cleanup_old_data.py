#!/usr/bin/env python3
"""Clean up old parquet files to reduce memory usage.

This script removes parquet files older than a specified number of months.
Useful for reducing memory footprint of the dashboard.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_files(data_dir: Path, keep_months: int = 6, dry_run: bool = True) -> None:
    """Remove parquet files older than keep_months.

    Args:
        data_dir: Path to data directory
        keep_months: Number of months to keep (default: 6)
        dry_run: If True, only print what would be deleted
    """
    cutoff_date = datetime.now() - timedelta(days=keep_months * 30)

    total_size = 0
    total_files = 0

    for hostname_dir in data_dir.iterdir():
        if not hostname_dir.is_dir():
            continue

        weekly_data_dir = hostname_dir / "data"
        if not weekly_data_dir.exists():
            continue

        print(f"\nChecking {hostname_dir.name}...")

        for parquet_file in weekly_data_dir.glob("*.parquet"):
            # Get file modification time
            mtime = datetime.fromtimestamp(parquet_file.stat().st_mtime)

            if mtime < cutoff_date:
                file_size = parquet_file.stat().st_size
                total_size += file_size
                total_files += 1

                if dry_run:
                    print(
                        f"  Would delete: {parquet_file.name} ({file_size / 1024 / 1024:.2f} MB) "
                        f"- modified {mtime.strftime('%Y-%m-%d')}"
                    )
                else:
                    print(f"  Deleting: {parquet_file.name} ({file_size / 1024 / 1024:.2f} MB)")
                    parquet_file.unlink()

    print(f"\n{'Would delete' if dry_run else 'Deleted'} {total_files} files, {total_size / 1024 / 1024:.2f} MB total")
    print(f"Keeping files from the last {keep_months} months (since {cutoff_date.strftime('%Y-%m-%d')})")


def main():
    parser = argparse.ArgumentParser(description="Clean up old parquet data files")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("/opt/slurm-usage-history/data"),
        help="Path to data directory (default: /opt/slurm-usage-history/data)",
    )
    parser.add_argument(
        "--keep-months",
        type=int,
        default=6,
        help="Number of months to keep (default: 6)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually delete files (default is dry-run mode)",
    )

    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Error: Data directory does not exist: {args.data_dir}")
        return 1

    print(f"Data directory: {args.data_dir}")
    print(f"Keep months: {args.keep_months}")
    print(f"Mode: {'DELETE' if args.no_dry_run else 'DRY-RUN (no files will be deleted)'}")
    print("=" * 60)

    cleanup_old_files(args.data_dir, args.keep_months, dry_run=not args.no_dry_run)

    if not args.no_dry_run:
        print("\nThis was a dry-run. Use --no-dry-run to actually delete files.")

    return 0


if __name__ == "__main__":
    exit(main())
