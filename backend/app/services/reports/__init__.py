"""Report services package for SLURM usage reporting."""

from .comparison_metrics import (
    calculate_comparison_metrics,
    calculate_previous_period_dates,
)
from .report_formatters import (
    convert_numpy_to_native,
    format_hours_readable,
    format_report_as_csv,
    format_report_as_pdf,
)
from .report_generator import generate_report_data
from .report_helpers import (
    calculate_duration_stats,
    calculate_waiting_time_stats,
    get_month_date_range,
    get_quarter_date_range,
    get_year_date_range,
)

__all__ = [
    "calculate_comparison_metrics",
    "calculate_duration_stats",
    "calculate_previous_period_dates",
    "calculate_waiting_time_stats",
    "convert_numpy_to_native",
    "format_hours_readable",
    "format_report_as_csv",
    "format_report_as_pdf",
    "generate_report_data",
    "get_month_date_range",
    "get_quarter_date_range",
    "get_year_date_range",
]
