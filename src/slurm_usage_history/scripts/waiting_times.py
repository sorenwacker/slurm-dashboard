import argparse
import csv
import os
import subprocess
import time
from datetime import datetime, timedelta


class SlurmJobMonitor:
    def __init__(self, csv_file="waiting_jobs.csv", interval=10):
        self.csv_file = csv_file
        self.interval = interval
        self.pending_jobs = {}  # Stores job IDs and their submission times
        self.mock_jobs = {}  # Mock job data for testing

        # If the file does not exist, create it and write the header
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["JobID", "TaskIndex", "Username", "WaitingTime [s]"])

    def fetch_pending_jobs(self):
        try:
            # Execute the squeue command to get pending jobs with additional details
            result = subprocess.run(
                ["squeue", "--states=PD", "--noheader", "--format=%i %V %u"],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )

            # Parse the output and populate the pending jobs dictionary
            new_pending_jobs = {}
            for line in result.stdout.strip().split("\n"):
                job_id_full, submit_time, username = line.split(maxsplit=2)

                # Handle job arrays
                if "_" in job_id_full:
                    job_id, task_index = job_id_full.split("_")
                else:
                    job_id, task_index = job_id_full, ""

                new_pending_jobs[job_id_full] = {
                    "job_id": job_id,
                    "task_index": task_index,
                    "submit_time": datetime.strptime(submit_time, "%Y-%m-%dT%H:%M:%S"),
                    "username": username,
                }

            # Combine real pending jobs with mock jobs for testing
            new_pending_jobs.update(self.mock_jobs)
            return new_pending_jobs

        except subprocess.CalledProcessError as e:
            print(f"Error executing squeue command: {e}")
            return {}

    def update_job_status(self):
        current_jobs = self.fetch_pending_jobs()
        completed_jobs = []
        new_jobs = []

        # Determine new jobs and completed jobs
        current_job_ids = set(current_jobs.keys())
        previous_job_ids = set(self.pending_jobs.keys())

        new_jobs = current_job_ids - previous_job_ids
        completed_jobs = previous_job_ids - current_job_ids

        # Log waiting times for completed jobs
        for job_id_full in completed_jobs:
            job_info = self.pending_jobs[job_id_full]
            submission_time = job_info["submit_time"]
            waiting_time = datetime.now() - submission_time
            self.log_waiting_time(
                job_info["job_id"],
                job_info["task_index"],
                job_info["username"],
                waiting_time,
            )

        # Update pending jobs list
        self.pending_jobs = current_jobs

        # Print job status
        self.print_job_status(len(current_jobs), len(new_jobs), len(completed_jobs))

    def log_waiting_time(self, job_id, task_index, username, waiting_time):
        waiting_time_seconds = int(waiting_time.total_seconds())
        with open(self.csv_file, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([job_id, task_index, username, waiting_time_seconds])

        print(f"JobID {job_id} | Task: {task_index} | {username} | Waiting: {{waiting_time_seconds}} seconds")

    def print_job_status(self, total_waiting, new_jobs, started_jobs):
        print(
            f"{datetime.now()}: Currently waiting: {total_waiting} "
            f"| New jobs: {new_jobs} | Jobs started: {started_jobs}"
        )

    def start_monitoring(self):
        print(f"Monitoring pending SLURM jobs every {self.interval} seconds. Logging to {self.csv_file}...")
        try:
            while True:
                self.update_job_status()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")

    def add_mock_job(self, job_id, task_index, username, wait_time_minutes):
        submission_time = datetime.now() - timedelta(minutes=wait_time_minutes)
        mock_job_id_full = f"{job_id}_{task_index}" if task_index else job_id
        self.mock_jobs[mock_job_id_full] = {
            "job_id": job_id,
            "task_index": task_index,
            "submit_time": submission_time,
            "username": username,
        }
        print(f"Added mock job: {mock_job_id_full} with waiting time: {wait_time_minutes} minutes.")


def main():
    parser = argparse.ArgumentParser(description="Monitor SLURM jobs and log waiting times.")
    parser.add_argument(
        "--csv-file",
        type=str,
        default="slurm-waiting-times.csv",
        help="Path to the CSV file where the waiting time data will be logged.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Time interval in seconds between checks for pending jobs.",
    )

    args = parser.parse_args()

    monitor = SlurmJobMonitor(csv_file=args.csv_file, interval=args.interval)

    monitor.start_monitoring()


if __name__ == "__main__":
    main()
