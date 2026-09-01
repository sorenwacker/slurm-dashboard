"""Shared bin edges, labels, and color ramps for distribution charts."""

# =============================================================================
# Constants for bin configurations
# =============================================================================

# Time column mappings
TIME_COLUMN_MAP = {
    "day": "StartDay",
    "week": "StartYearWeek",
    "month": "StartYearMonth",
    "year": "StartYear",
}

# Histogram bin edges for time-based distributions (in hours)


# Durations get finer bins at the short end: most jobs run for minutes, and a
# single "< 1h" bin would hide them all
TIME_HISTOGRAM_BIN_EDGES = [0, 30 / 3600, 5 / 60, 10 / 60, 0.5, 1, 4, 12, 24, 72, 168, float("inf")]
TIME_HISTOGRAM_BIN_LABELS = [
    "< 30s",
    "30s - 5min",
    "5 - 10min",
    "10 - 30min",
    "30min - 1h",
    "1h - 4h",
    "4h - 12h",
    "12h - 24h",
    "1d - 3d",
    "3d - 7d",
    "> 7d",
]

# Job duration stacked chart bins (teal gradient, same edges as the histogram)
DURATION_BINS = [
    ("< 30s", 0, 30 / 3600),
    ("30s-5min", 30 / 3600, 5 / 60),
    ("5-10min", 5 / 60, 10 / 60),
    ("10-30min", 10 / 60, 0.5),
    ("30min-1h", 0.5, 1),
    ("1h-4h", 1, 4),
    ("4h-12h", 4, 12),
    ("12h-24h", 12, 24),
    ("1d-3d", 24, 72),
    ("3d-7d", 72, 168),
    ("> 7d", 168, float("inf")),
]
DURATION_COLORS = [
    "#e7f9f7",  # Very light teal
    "#d0f1ed",
    "#b4e6e0",
    "#95d9d1",
    "#73cabf",
    "#52b9ac",
    "#37a598",
    "#249082",
    "#177c6f",
    "#10695e",
    "#0a564d",  # Dark teal
]

# Waiting time stacked chart bins (red gradient, same edges as the histogram)
WAITING_TIME_BINS = [
    ("< 30s", 0, 30 / 3600),
    ("30s-5min", 30 / 3600, 5 / 60),
    ("5-10min", 5 / 60, 10 / 60),
    ("10-30min", 10 / 60, 0.5),
    ("30min-1h", 0.5, 1),
    ("1h-4h", 1, 4),
    ("4h-12h", 4, 12),
    ("12h-24h", 12, 24),
    ("1d-3d", 24, 72),
    ("3d-7d", 72, 168),
    ("> 7d", 168, float("inf")),
]
WAITING_TIME_COLORS = [
    "#fdeaea",  # Very light red
    "#fbd2d2",
    "#f7b6b6",
    "#f29797",
    "#ec7575",
    "#e45454",
    "#d93a3a",
    "#c92626",
    "#b31818",
    "#990f0f",
    "#7d0808",  # Dark red
]
