#!/usr/bin/env python3
"""
Synthetic Cluster Data Generator for Testing

This script generates realistic synthetic SLURM job data for testing the
Slurm Usage History Dashboard. It mimics the structure and patterns found
in real DAIC cluster data.

Usage:
    python3 generate_test_cluster_data.py --cluster TestCluster --start-date 2024-01-01 --end-date 2024-12-31 --jobs-per-day 100
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


class SyntheticClusterDataGenerator:
    """Generates synthetic SLURM cluster job data with realistic patterns."""

    def __init__(self, cluster_name="TestCluster", seed=42, num_users=None, simple_partitions=False):
        """
        Initialize the generator with cluster configuration.

        Args:
            cluster_name: Name of the synthetic cluster
            seed: Random seed for reproducibility
            num_users: Override number of users (default: 70 users)
            simple_partitions: If True, use simplified partition structure (general, cpu, gpu)
        """
        self.cluster_name = cluster_name
        random.seed(seed)
        np.random.seed(seed)

        # Define realistic cluster configuration with configurable users
        if num_users:
            # Custom user count - distribute among types
            power_count = max(5, num_users // 10)
            occasional_count = max(10, num_users // 5)
            regular_count = num_users - power_count - occasional_count

            power_users = [f"poweruser{i:02d}" for i in range(1, power_count + 1)]
            regular_users = [f"user{i:03d}" for i in range(1, regular_count + 1)]
            occasional_users = [f"student{i:02d}" for i in range(1, occasional_count + 1)]
        else:
            # Default: 70 users total
            power_users = [f"poweruser{i:02d}" for i in range(1, 11)]  # 10 heavy users
            regular_users = [f"user{i:03d}" for i in range(1, 41)]  # 40 regular users
            occasional_users = [f"student{i:02d}" for i in range(1, 21)]  # 20 light users

        self.users = power_users + regular_users + occasional_users

        # User activity weights (how likely each user type is to submit jobs)
        self.user_weights = {}
        for user in power_users:
            self.user_weights[user] = 8.0  # Power users 8x more active
        for user in regular_users:
            self.user_weights[user] = 1.0  # Baseline
        for user in occasional_users:
            self.user_weights[user] = 0.2  # Occasional users 5x less active

        # 30 diverse accounts across departments and research groups
        self.accounts = [
            # Computer Science
            "cs-ml-lab", "cs-vision-lab", "cs-nlp-group", "cs-systems", "cs-graphics", "cs-robotics",
            # Electrical Engineering
            "ee-signal-proc", "ee-controls", "ee-comms", "ee-power", "ee-circuits",
            # Physics
            "physics-hep", "physics-astro", "physics-cmp", "physics-quantum",
            # Biology
            "bio-genomics", "bio-proteomics", "bio-imaging", "bio-neuro", "bio-ecology",
            # Chemistry
            "chem-compbio", "chem-materials", "chem-synthesis", "chem-catalysis",
            # Mathematics & Statistics
            "math-optimization", "math-statistics", "math-modeling",
            # Medical & Health
            "med-imaging", "med-bioinformatics",
            # Materials Science
            "matsci-nano", "matsci-polymers"
        ]

        # Account usage patterns - some accounts more active than others
        self.account_weights = {
            "cs-ml-lab": 5.0, "cs-vision-lab": 4.0, "bio-genomics": 3.5,
            "physics-hep": 3.0, "chem-compbio": 2.5,
        }
        # Default weight for accounts not specified
        for acc in self.accounts:
            if acc not in self.account_weights:
                self.account_weights[acc] = 1.0

        # Partition configuration - simple or complex
        if simple_partitions:
            # Simple 3-partition structure for demos
            self.partitions = ["general", "cpu", "gpu"]
            self.partition_weights = {
                "general": 3.0,
                "cpu": 2.5,
                "gpu": 2.0
            }
        else:
            # More diverse partitions with realistic usage patterns
            self.partitions = [
                "gpu", "gpu-a100", "gpu-v100",  # GPU variants
                "cpu", "cpu-highmem",  # CPU variants
                "bigmem",  # Memory-intensive
                "interactive",  # Quick interactive jobs
                "short", "medium", "long"  # Duration-based
            ]

            # Partition selection weights (some more popular)
            self.partition_weights = {
                "gpu": 3.0, "gpu-a100": 2.0, "gpu-v100": 1.5,
                "cpu": 4.0, "cpu-highmem": 1.0,
                "bigmem": 1.0,
                "interactive": 2.0,
                "short": 3.0, "medium": 2.0, "long": 1.0
            }

        # More varied QoS types
        self.qos_types = [
            "short", "medium", "long", "verylong",
            "interactive", "debug",
            "normal", "high-priority", "low-priority"
        ]

        # QoS selection weights
        self.qos_weights = {
            "short": 3.0, "medium": 2.5, "normal": 2.0,
            "long": 1.5, "interactive": 1.0,
            "debug": 0.5, "verylong": 0.3,
            "high-priority": 0.2, "low-priority": 1.0
        }

        self.states = [
            "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED",  # 50% completed
            "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED",
            "CANCELLED", "CANCELLED", "CANCELLED",  # 30% cancelled
            "CANCELLED", "CANCELLED", "CANCELLED",
            "TIMEOUT", "TIMEOUT",  # 20% timeout
            "FAILED", "OUT_OF_MEMORY"  # 10% failed/OOM
        ]

        # Node lists for different partitions
        if simple_partitions:
            # Simple demo cluster: 30 nodes (15 GPU, 15 CPU)
            self.node_lists = {
                "general": [f"node{i:02d}" for i in range(1, 11)],  # 10 general nodes
                "cpu": [f"cpu{i:02d}" for i in range(1, 16)],       # 15 CPU nodes
                "gpu": [f"gpu{i:02d}" for i in range(1, 16)]        # 15 GPU nodes
            }  # Total: 30 unique nodes (10+15+15, general can overlap with others)
        else:
            # Complex cluster with ~46 nodes
            self.node_lists = {
                "gpu": [f"gpu{i:02d}" for i in range(1, 5)],           # 4 GPU nodes
                "gpu-a100": [f"a100-{i:02d}" for i in range(1, 3)],    # 2 A100 nodes
                "gpu-v100": [f"v100-{i:02d}" for i in range(1, 4)],    # 3 V100 nodes
                "cpu": [f"cpu{i:03d}" for i in range(1, 17)],          # 16 CPU nodes
                "cpu-highmem": [f"highmem{i:02d}" for i in range(1, 4)], # 3 high-mem nodes
                "bigmem": [f"bigmem{i:02d}" for i in range(1, 3)],     # 2 bigmem nodes
                "interactive": [f"int{i:02d}" for i in range(1, 4)],   # 3 interactive nodes
                "short": [f"short{i:02d}" for i in range(1, 5)],       # 4 short nodes
                "medium": [f"med{i:02d}" for i in range(1, 4)],        # 3 medium nodes
                "long": [f"long{i:02d}" for i in range(1, 3)]          # 2 long nodes
            }  # Total: 46 nodes

        # Track user lifecycles - when users joined the cluster
        self.user_join_dates = {}
        self.user_leave_dates = {}

    def generate_job_submit_times(self, start_date, end_date, jobs_per_day, seasonal_pattern=True, outages=None):
        """
        Generate realistic job submission times with daily, weekly, and seasonal patterns.

        Args:
            start_date: Start date for data generation
            end_date: End date for data generation
            jobs_per_day: Average number of jobs per day
            seasonal_pattern: If True, add more activity in spring and fall
            outages: List of (start_date, end_date) tuples for outage periods

        Returns:
            List of submission timestamps
        """
        submit_times = []
        current_date = start_date
        outages = outages or []

        while current_date <= end_date:
            # Check if we're in an outage period
            in_outage = any(outage_start <= current_date.date() <= outage_end
                          for outage_start, outage_end in outages)

            if in_outage:
                # During outages, much reduced activity
                daily_multiplier = 0.1
            else:
                # Weekly pattern: fewer jobs on weekends
                is_weekend = current_date.weekday() >= 5
                daily_multiplier = 0.3 if is_weekend else 1.0

                # Seasonal pattern: more activity in spring (Mar-May) and fall (Sep-Nov)
                if seasonal_pattern:
                    month = current_date.month
                    if month in [3, 4, 5, 9, 10, 11]:  # Spring and fall
                        daily_multiplier *= 1.5
                    elif month in [12, 1, 6, 7, 8]:  # Winter break and summer
                        daily_multiplier *= 0.7

            # Daily pattern: more jobs during work hours
            num_jobs = int(np.random.poisson(jobs_per_day * daily_multiplier))

            for _ in range(num_jobs):
                # Generate time during the day with bias toward work hours
                hour = int(np.random.beta(2, 2) * 24)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)

                submit_time = current_date.replace(
                    hour=hour, minute=minute, second=second
                )
                submit_times.append(submit_time)

            current_date += timedelta(days=1)

        return sorted(submit_times)

    def get_active_users(self, current_date):
        """Get list of users active at given date based on lifecycle."""
        active_users = []
        for user in self.users:
            # Check if user has joined yet
            if user in self.user_join_dates and current_date < self.user_join_dates[user]:
                continue
            # Check if user has left
            if user in self.user_leave_dates and current_date > self.user_leave_dates[user]:
                continue
            active_users.append(user)
        return active_users if active_users else self.users

    def generate_job_record(self, submit_time, outages=None):
        """
        Generate a single realistic job record with weighted selections.

        Args:
            submit_time: Job submission timestamp
            outages: List of (start_date, end_date) tuples for outage periods

        Returns:
            Dictionary containing job data
        """
        outages = outages or []

        # Get active users at this time
        active_users = self.get_active_users(submit_time.date())
        user_list = active_users
        user_weight_list = [self.user_weights.get(u, 1.0) for u in user_list]

        # Select job characteristics with weights
        user = random.choices(user_list, weights=user_weight_list, k=1)[0]

        account_list = self.accounts
        account_weight_list = [self.account_weights.get(a, 1.0) for a in account_list]
        account = random.choices(account_list, weights=account_weight_list, k=1)[0]

        partition_list = self.partitions
        partition_weight_list = [self.partition_weights.get(p, 1.0) for p in partition_list]
        partition = random.choices(partition_list, weights=partition_weight_list, k=1)[0]

        qos_list = self.qos_types
        qos_weight_list = [self.qos_weights.get(q, 1.0) for q in qos_list]
        qos = random.choices(qos_list, weights=qos_weight_list, k=1)[0]

        state = random.choice(self.states)

        # Determine GPU usage and node assignment based on partition
        # cpu partition: always CPU nodes, never GPUs
        # gpu partition: always GPU nodes, always has GPUs
        # general partition: can be either, 30% chance of GPU
        if partition == "cpu":
            has_gpu = False
            gpus = 0
            cpus = random.choices([1, 2, 4, 8, 16, 32], weights=[20, 30, 25, 15, 7, 3])[0]
            available_nodes = self.node_lists["cpu"]
        elif partition == "gpu":
            has_gpu = True
            gpus = random.choices([1, 2, 4, 8], weights=[50, 30, 15, 5])[0]
            cpus = gpus * random.choice([4, 8, 16])
            available_nodes = self.node_lists["gpu"]
        elif partition == "general":
            # General partition can use either CPU or GPU nodes
            has_gpu = random.random() < 0.3
            if has_gpu:
                gpus = random.choices([1, 2, 4], weights=[60, 30, 10])[0]
                cpus = gpus * random.choice([4, 8, 12])
                available_nodes = self.node_lists["gpu"]
            else:
                gpus = 0
                cpus = random.choices([1, 2, 4, 8, 16], weights=[25, 30, 25, 15, 5])[0]
                available_nodes = self.node_lists["cpu"]
        else:
            # For complex partition setups (non-simple)
            is_gpu_partition = partition in ["gpu", "gpu-a100", "gpu-v100"]
            has_gpu = is_gpu_partition or (partition in ["short", "medium"] and random.random() < 0.05)

            if has_gpu:
                gpus = random.choices([1, 2, 4, 8], weights=[50, 30, 15, 5])[0]
                cpus = gpus * random.choice([4, 8, 16])
            else:
                gpus = 0
                cpus = random.choices([1, 2, 4, 8, 16, 32, 64],
                                    weights=[20, 30, 25, 15, 5, 3, 2])[0]

            available_nodes = self.node_lists[partition]

        nodes = max(1, cpus // 32) if cpus > 32 else 1

        # Generate node list (without brackets - just node names)
        if nodes == 1:
            node_list = random.choice(available_nodes)
        else:
            selected_nodes = random.sample(available_nodes, min(nodes, len(available_nodes)))
            node_list = ",".join(selected_nodes)

        # Check if we're in or near an outage period
        in_outage = any(outage_start <= submit_time.date() <= outage_end
                       for outage_start, outage_end in outages)

        # Generate waiting time (much longer during outages)
        if in_outage:
            # During outages, waiting times are 5-20x longer
            waiting_hours = np.random.exponential(10.0) * random.uniform(1.5, 3.0)
        elif partition == "interactive":
            waiting_hours = np.random.exponential(0.1)
        else:
            waiting_hours = np.random.exponential(2.0)

        # Generate elapsed time based on QoS and state
        if qos == "short":
            elapsed_hours = np.random.exponential(0.5)
        elif qos == "medium":
            elapsed_hours = np.random.exponential(4.0)
        elif qos == "long":
            elapsed_hours = np.random.exponential(24.0)
        elif qos == "interactive":
            elapsed_hours = np.random.exponential(0.25)
        else:
            elapsed_hours = np.random.exponential(12.0)

        # Adjust for job state
        if state == "TIMEOUT":
            # Timeout jobs hit the time limit
            elapsed_hours = min(elapsed_hours * 1.5, 168)  # Cap at 1 week
        elif state in ["CANCELLED", "FAILED"]:
            # These jobs typically don't run to completion
            elapsed_hours *= random.uniform(0.1, 0.8)
        elif state == "OUT_OF_MEMORY":
            elapsed_hours *= random.uniform(0.3, 0.9)

        # Calculate timestamps
        start_time = submit_time + timedelta(hours=waiting_hours)
        end_time = start_time + timedelta(hours=elapsed_hours)

        # Calculate derived time fields
        submit_day = submit_time.replace(hour=0, minute=0, second=0, microsecond=0)
        submit_weekday = submit_time.strftime("%A")
        submit_year_week = (submit_time - timedelta(days=submit_time.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        submit_year_month = submit_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        start_day = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        start_weekday = start_time.strftime("%A")
        start_year_week = (start_time - timedelta(days=start_time.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        start_year_month = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Calculate CPU and GPU hours
        cpu_hours = cpus * elapsed_hours
        gpu_hours = gpus * elapsed_hours

        # Generate resource usage statistics (realistic patterns)
        if state == "COMPLETED":
            # Completed jobs have reasonable CPU efficiency
            cpu_efficiency = random.uniform(0.6, 0.95)
            ave_cpu = f"{int(cpu_efficiency * 100)}%"
            total_cpu_days = int((cpu_hours * cpu_efficiency) / 24)
            total_cpu_hours = int((cpu_hours * cpu_efficiency) % 24)
            total_cpu = f"{total_cpu_days}-{total_cpu_hours:02d}:00:00"

            # Memory and I/O stats
            max_rss = f"{random.randint(1000, 50000)}K"
            ave_disk_read = f"{random.randint(100, 10000)}M"
            ave_disk_write = f"{random.randint(50, 5000)}M"
        else:
            # Failed jobs have incomplete stats
            ave_cpu = "0%" if random.random() < 0.5 else f"{random.randint(1, 50)}%"
            total_cpu = "00:00:00" if random.random() < 0.3 else "00-01:30:00"
            max_rss = "0K" if random.random() < 0.4 else f"{random.randint(100, 10000)}K"
            ave_disk_read = "0M" if random.random() < 0.4 else f"{random.randint(10, 1000)}M"
            ave_disk_write = "0M" if random.random() < 0.4 else f"{random.randint(5, 500)}M"

        # Requested memory per job (GB) and peak usage as a fraction of it;
        # OUT_OF_MEMORY jobs reach their limit, most jobs use far less.
        req_mem_gb = random.choice([4, 8, 16, 32, 64, 128]) * max(1, cpus // 4)
        if state == "OUT_OF_MEMORY":
            used_fraction = random.uniform(0.95, 1.0)
        else:
            used_fraction = random.betavariate(2, 5)
        req_mem_mb = float(req_mem_gb * 1024)
        max_rss_mb = round(req_mem_mb * used_fraction, 1)
        cpu_used_hours = round(cpu_hours * (cpu_efficiency if state == "COMPLETED" else random.uniform(0.0, 0.5)), 2)

        return {
            "User": user,
            "QOS": qos,
            "Account": account,
            "Partition": partition,
            "Submit": submit_time,
            "Start": start_time,
            "End": end_time,
            "SubmitDay": submit_day,
            "SubmitWeekDay": submit_weekday,
            "SubmitYearWeek": submit_year_week,
            "SubmitYearMonth": submit_year_month,
            "StartDay": start_day,
            "StartWeekDay": start_weekday,
            "StartYearWeek": start_year_week,
            "StartYearMonth": start_year_month,
            "State": state,
            "WaitingTime [h]": waiting_hours,
            "Elapsed [h]": elapsed_hours,
            "Nodes": nodes,
            "NodeList": node_list,
            "CPUs": cpus,
            "GPUs": gpus,
            "CPU-hours": cpu_hours,
            "GPU-hours": gpu_hours,
            "AveCPU": ave_cpu,
            "TotalCPU": total_cpu,
            "AveDiskRead": ave_disk_read,
            "AveDiskWrite": ave_disk_write,
            "MaxRSS": max_rss,
            "ReqMemMB": req_mem_mb,
            "MaxRSSMB": max_rss_mb,
            "CPUUsedHours": cpu_used_hours,
            "Cluster": self.cluster_name
        }

    def initialize_user_lifecycles(self, start_date, end_date):
        """Initialize when users join and potentially leave the cluster."""
        total_days = (end_date - start_date).days

        # 90% of users start from beginning (increased from 70%)
        initial_users = random.sample(self.users, int(len(self.users) * 0.9))

        # Remaining users join at various points
        new_users = [u for u in self.users if u not in initial_users]
        for user in new_users:
            # New users more likely to join earlier
            days_offset = int(np.random.beta(2, 5) * total_days)
            self.user_join_dates[user] = (start_date + timedelta(days=days_offset)).date()

        # Reduced turnover (5-8% instead of 10-15%)
        leaving_users = random.sample(self.users, int(len(self.users) * random.uniform(0.05, 0.08)))
        for user in leaving_users:
            # Users more likely to leave later in the period
            days_offset = int(np.random.beta(5, 2) * total_days * 0.9)  # Leave in last 90%
            leave_date = (start_date + timedelta(days=days_offset)).date()
            # Make sure they don't leave before they join
            if user in self.user_join_dates:
                leave_date = max(leave_date, self.user_join_dates[user] + timedelta(days=30))
            self.user_leave_dates[user] = leave_date

    def generate_dataset(self, start_date, end_date, jobs_per_day, seasonal_pattern=True, outages=None):
        """
        Generate complete synthetic dataset with user lifecycles.

        Args:
            start_date: Start date for data generation
            end_date: End date for data generation
            jobs_per_day: Average number of jobs per day
            seasonal_pattern: If True, add more activity in spring and fall
            outages: List of (start_date, end_date) tuples for outage periods

        Returns:
            DataFrame containing synthetic job data
        """
        outages = outages or []

        print("Initializing user lifecycles...")
        self.initialize_user_lifecycles(start_date, end_date)

        print(f"Generating job submission times from {start_date} to {end_date}...")
        submit_times = self.generate_job_submit_times(start_date, end_date, jobs_per_day,
                                                      seasonal_pattern=seasonal_pattern,
                                                      outages=outages)

        print(f"Generating {len(submit_times)} job records...")
        jobs = []
        for i, submit_time in enumerate(submit_times):
            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1}/{len(submit_times)} jobs...")
            jobs.append(self.generate_job_record(submit_time, outages=outages))

        df = pd.DataFrame(jobs)
        print(f"Generated {len(df)} total jobs")
        return df

    def save_weekly_data(self, df, output_dir):
        """
        Save data organized by week (matching DAIC structure).

        Args:
            df: DataFrame containing job data
            output_dir: Directory to save weekly parquet files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Group by year and week
        df["_year"] = df["SubmitYearWeek"].dt.year
        df["_week"] = df["SubmitYearWeek"].dt.isocalendar().week

        weeks = df.groupby(["_year", "_week"])

        print(f"\nSaving {len(weeks)} weekly files to {output_path}...")
        for (year, week), week_df in weeks:
            # Remove temporary grouping columns
            week_df = week_df.drop(columns=["_year", "_week"])

            filename = f"week_{year}_W{week:02d}.parquet"
            filepath = output_path / filename
            week_df.to_parquet(filepath, index=False)
            print(f"  Saved {filename} ({len(week_df)} jobs)")

        print(f"\nSuccessfully saved {len(weeks)} weekly parquet files")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic SLURM cluster job data for testing"
    )
    parser.add_argument(
        "--cluster",
        type=str,
        default="TestCluster",
        help="Name of the synthetic cluster (default: TestCluster)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date for data generation (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date for data generation (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--jobs-per-day",
        type=int,
        default=100,
        help="Average number of jobs per day (default: 100)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: ./data/{cluster}/data)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        print("Please use YYYY-MM-DD format")
        return 1

    if start_date >= end_date:
        print("Error: start-date must be before end-date")
        return 1

    # Set output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        script_dir = Path(__file__).parent.parent
        output_dir = script_dir / "data" / args.cluster / "weekly-data"

    # Generate data
    print("=== Synthetic Cluster Data Generator ===")
    print(f"Cluster: {args.cluster}")
    print(f"Date range: {args.start_date} to {args.end_date}")
    print(f"Jobs per day (avg): {args.jobs_per_day}")
    print(f"Output directory: {output_dir}")
    print(f"Random seed: {args.seed}")
    print()

    generator = SyntheticClusterDataGenerator(
        cluster_name=args.cluster,
        seed=args.seed
    )

    df = generator.generate_dataset(start_date, end_date, args.jobs_per_day)

    # Display summary statistics
    print("\n=== Dataset Summary ===")
    print(f"Total jobs: {len(df)}")
    print(f"Date range: {df['Submit'].min()} to {df['Submit'].max()}")
    print("\nJob states:")
    print(df["State"].value_counts().to_string())
    print("\nPartitions:")
    print(df["Partition"].value_counts().to_string())
    print("\nQoS:")
    print(df["QOS"].value_counts().to_string())
    print(f"\nTotal CPU-hours: {df['CPU-hours'].sum():,.2f}")
    print(f"Total GPU-hours: {df['GPU-hours'].sum():,.2f}")

    # Save data
    generator.save_weekly_data(df, output_dir)

    print("\n=== Generation Complete ===")
    print(f"Data saved to: {output_dir}")
    print("\nTo use this data, update backend configuration:")
    print(f"  CLUSTER_{args.cluster.upper()}_DATA_PATH={output_dir}")

    return 0


if __name__ == "__main__":
    exit(main())
