"""Chart generation functions for PDF reports using matplotlib."""

from datetime import datetime
from io import BytesIO
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import AutoDateLocator, DateFormatter
from reportlab.platypus import Image

# Use non-interactive backend for server-side generation
matplotlib.use("Agg")


def create_timeline_chart(timeline_data: list[dict[str, Any]], title: str, y_label: str, metric_key: str) -> Image:
    """Create a timeline chart image for PDF inclusion.

    Args:
        timeline_data: List of timeline data points with 'date' and metric keys
        title: Chart title
        y_label: Y-axis label
        metric_key: Key to extract metric values (e.g., 'cpu_hours', 'jobs')

    Returns:
        ReportLab Image object
    """
    if not timeline_data:
        return None

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)

    # Convert date strings to datetime objects
    dates = [
        datetime.fromisoformat(item["date"]) if isinstance(item["date"], str) else item["date"]
        for item in timeline_data
    ]
    values = [item[metric_key] for item in timeline_data]

    ax.plot(dates, values, color="#3498db", linewidth=2, marker="o", markersize=3)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.grid(True, alpha=0.3, linestyle="--")

    # Format x-axis dates with matplotlib's date handling
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax.tick_params(axis="x", labelsize=8, rotation=45)
    ax.tick_params(axis="y", labelsize=8)

    plt.tight_layout()

    # Save to buffer with high quality
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)

    # Convert to ReportLab Image
    img = Image(buf, width=500, height=250)
    return img


def create_bar_chart(
    data: list[dict[str, Any]], title: str, x_key: str, y_key: str, y_label: str, top_n: int = 10
) -> Image:
    """Create a horizontal bar chart for PDF inclusion.

    Args:
        data: List of data points with x_key and y_key
        title: Chart title
        x_key: Key for category labels (e.g., 'account', 'partition')
        y_key: Key for values (e.g., 'cpu_hours', 'jobs')
        y_label: Y-axis label
        top_n: Number of top items to display

    Returns:
        ReportLab Image object
    """
    if not data:
        return None

    # Take top N items
    data_sorted = sorted(data, key=lambda x: x[y_key], reverse=True)[:top_n]

    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)

    labels = [str(item[x_key])[:20] for item in data_sorted]  # Truncate long labels
    values = [item[y_key] for item in data_sorted]

    # Create horizontal bar chart
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color="#04A5D5", alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel(y_label, fontsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, alpha=0.3, axis="x", linestyle="--")

    # Invert y-axis so highest value is on top
    ax.invert_yaxis()

    plt.tight_layout()

    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)

    # Convert to ReportLab Image
    img = Image(buf, width=500, height=300)
    return img


def create_pie_chart(data: list[dict[str, Any]], title: str, label_key: str, value_key: str, top_n: int = 8) -> Image:
    """Create a pie chart for PDF inclusion.

    Args:
        data: List of data points with label_key and value_key
        title: Chart title
        label_key: Key for labels (e.g., 'partition', 'state')
        value_key: Key for values (e.g., 'jobs', 'gpu_hours')
        top_n: Number of top slices to show (others grouped as "Other")

    Returns:
        ReportLab Image object
    """
    if not data:
        return None

    # Sort and take top N
    data_sorted = sorted(data, key=lambda x: x[value_key], reverse=True)

    labels = []
    values = []

    for i, item in enumerate(data_sorted):
        if i < top_n - 1:
            labels.append(str(item[label_key])[:15])
            values.append(item[value_key])
        elif i == top_n - 1:
            # Group remaining as "Other"
            other_sum = sum(item[value_key] for item in data_sorted[i:])
            labels.append("Other")
            values.append(other_sum)
            break

    fig, ax = plt.subplots(figsize=(5, 5), dpi=100)

    # Use frontend partition colors for consistency, but generate more if needed
    base_colors = ["#6f42c1", "#28a745", "#fd7e14", "#dc3545", "#17a2b8", "#ffc107", "#6c757d", "#343a40"]
    if len(labels) <= len(base_colors):
        colors = base_colors[: len(labels)]
    else:
        # For more partitions than base colors, use a colormap to generate distinct colors
        colors = plt.cm.tab20(np.linspace(0, 1, len(labels)))

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90, textprops={"fontsize": 8}
    )

    # Make percentage text bold
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")
        autotext.set_fontsize(7)

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)

    plt.tight_layout()

    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)

    # Convert to ReportLab Image
    img = Image(buf, width=400, height=300)
    return img


def create_comparison_timeline(
    timeline_data: list[dict[str, Any]],
    previous_timeline: list[dict[str, Any]] | None,
    title: str,
    y_label: str,
    metric_key: str,
    color: str = "#04A5D5",
) -> Image:
    """Create a timeline chart with current and previous period comparison.

    Args:
        timeline_data: Current period timeline data
        previous_timeline: Previous period timeline data for comparison
        title: Chart title
        y_label: Y-axis label
        metric_key: Key to extract metric values
        color: Line color for current period (hex format)

    Returns:
        ReportLab Image object
    """
    if not timeline_data:
        return None

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)

    # Plot current period - convert date strings to datetime objects
    dates = [
        datetime.fromisoformat(item["date"]) if isinstance(item["date"], str) else item["date"]
        for item in timeline_data
    ]
    values = [item[metric_key] for item in timeline_data]
    ax.plot(dates, values, color=color, linewidth=2, marker="o", markersize=3, label="Current Period")

    # Plot previous period if available - align dates with current period
    if previous_timeline:
        # Align previous period data to use current period dates for overlay
        aligned_length = min(len(timeline_data), len(previous_timeline))
        aligned_dates = dates[:aligned_length]
        prev_values = [previous_timeline[i][metric_key] for i in range(aligned_length)]
        ax.plot(
            aligned_dates,
            prev_values,
            color="#999999",
            linewidth=1.5,
            linestyle="--",
            marker="s",
            markersize=2,
            alpha=0.7,
            label="Previous Period",
        )

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.grid(True, alpha=0.3, linestyle="--")

    # Only show legend if there's a previous period
    if previous_timeline:
        ax.legend(fontsize=8, loc="best")

    # Format x-axis dates with matplotlib's date handling
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax.tick_params(axis="x", labelsize=8, rotation=45)
    ax.tick_params(axis="y", labelsize=8)

    plt.tight_layout()

    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)

    # Convert to ReportLab Image
    img = Image(buf, width=500, height=250)
    return img


def create_cumulative_chart(
    timeline_data: list[dict[str, Any]], title: str, y_label: str, metric_key: str, color: str = "#636EFA"
) -> Image:
    """Create a cumulative area chart.

    Args:
        timeline_data: List of timeline data points
        title: Chart title
        y_label: Y-axis label
        metric_key: Key to extract metric values
        color: Line color (hex)

    Returns:
        ReportLab Image object
    """
    if not timeline_data:
        return None

    # Sort by date and calculate cumulative values
    sorted_data = sorted(timeline_data, key=lambda x: x["date"])

    # Convert date strings to datetime objects
    dates = [
        datetime.fromisoformat(item["date"]) if isinstance(item["date"], str) else item["date"] for item in sorted_data
    ]
    values = [item[metric_key] for item in sorted_data]

    # Calculate cumulative sum
    cumulative = np.cumsum(values)

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)

    # Plot area chart
    ax.fill_between(dates, 0, cumulative, color=color, alpha=0.3)
    ax.plot(dates, cumulative, color=color, linewidth=2)

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.grid(True, alpha=0.3, linestyle="--")

    # Format x-axis dates with matplotlib's date handling
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax.tick_params(axis="x", labelsize=8, rotation=45)
    ax.tick_params(axis="y", labelsize=8)

    plt.tight_layout()

    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)

    # Convert to ReportLab Image
    img = Image(buf, width=500, height=250)
    return img


def create_stacked_bar_chart(
    data: list[dict[str, Any]],
    title: str,
    x_key: str,
    y_keys: list[tuple[str, str]],  # List of (key, label) tuples
    y_label: str,
    top_n: int = 10,
) -> Image:
    """Create a stacked horizontal bar chart.

    Args:
        data: List of data points
        title: Chart title
        x_key: Key for category labels
        y_keys: List of (key, label) tuples for stacking
        y_label: Y-axis label
        top_n: Number of top items to display

    Returns:
        ReportLab Image object
    """
    if not data:
        return None

    # Take top N items based on sum of all y_keys
    data_sorted = sorted(data, key=lambda x: sum(x.get(k[0], 0) for k in y_keys), reverse=True)[:top_n]

    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)

    labels = [str(item[x_key])[:20] for item in data_sorted]
    y_pos = np.arange(len(labels))

    # Colors for stacking
    colors = ["#636EFA", "#EF553B"]

    left = np.zeros(len(labels))
    for idx, (key, label) in enumerate(y_keys):
        values = [item.get(key, 0) for item in data_sorted]
        ax.barh(y_pos, values, left=left, label=label, color=colors[idx % len(colors)], alpha=0.8)
        left += values

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel(y_label, fontsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, alpha=0.3, axis="x", linestyle="--")
    ax.legend(fontsize=8, loc="best")

    # Invert y-axis so highest value is on top
    ax.invert_yaxis()

    plt.tight_layout()

    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)

    # Convert to ReportLab Image
    img = Image(buf, width=500, height=300)
    return img
