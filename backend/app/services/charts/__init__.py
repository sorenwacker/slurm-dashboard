"""Chart generation services for aggregated chart data."""
from .timeline_generators import (
    generate_cpu_usage_over_time,
    generate_gpu_usage_over_time,
    generate_jobs_over_time,
    generate_active_users_over_time,
    generate_waiting_times_over_time,
    generate_job_duration_over_time,
)
from .distribution_generators import (
    generate_jobs_by_account,
    generate_jobs_by_partition,
    generate_jobs_by_state,
    generate_waiting_times_hist,
    generate_job_duration_hist,
    generate_active_users_distribution,
    generate_jobs_distribution,
    generate_job_duration_stacked,
    generate_waiting_times_stacked,
    generate_waiting_times_trends,
    generate_job_duration_trends,
    generate_cpus_per_job,
    generate_gpus_per_job,
    generate_nodes_per_job,
    generate_cpu_hours_by_account,
    generate_gpu_hours_by_account,
    generate_by_dimension,
    generate_user_activity_frequency,
)
from .node_generators import (
    generate_node_usage,
)
from .chart_helpers import (
    format_account_name,
    format_accounts_in_df,
)

__all__ = [
    # Timeline generators
    "generate_cpu_usage_over_time",
    "generate_gpu_usage_over_time",
    "generate_jobs_over_time",
    "generate_active_users_over_time",
    "generate_waiting_times_over_time",
    "generate_job_duration_over_time",
    # Distribution generators
    "generate_jobs_by_account",
    "generate_jobs_by_partition",
    "generate_jobs_by_state",
    "generate_waiting_times_hist",
    "generate_job_duration_hist",
    "generate_active_users_distribution",
    "generate_jobs_distribution",
    "generate_job_duration_stacked",
    "generate_waiting_times_stacked",
    "generate_waiting_times_trends",
    "generate_job_duration_trends",
    "generate_cpus_per_job",
    "generate_gpus_per_job",
    "generate_nodes_per_job",
    "generate_cpu_hours_by_account",
    "generate_gpu_hours_by_account",
    "generate_by_dimension",
    "generate_user_activity_frequency",
    # Node generators
    "generate_node_usage",
    # Helpers
    "format_account_name",
    "format_accounts_in_df",
]
from .memory_generators import (
    generate_memory_efficiency_over_time,
    generate_memory_per_job,
    generate_memory_usage_over_time,
    total_memory_gb_hours,
)
