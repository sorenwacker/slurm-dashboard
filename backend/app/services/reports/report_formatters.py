"""CSV and PDF formatting functions for reports."""

import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .pdf_charts import (
    create_bar_chart,
    create_comparison_timeline,
)


def convert_numpy_to_native(obj: Any) -> Any:
    """Convert NumPy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {key: convert_numpy_to_native(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy_to_native(item) for item in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def format_report_as_csv(report_data: dict[str, Any]) -> str:
    """Format report data as CSV."""
    output = StringIO()

    # Write header
    output.write("# SLURM Usage Report\n")
    output.write(f"# Report Type: {report_data['report_type']}\n")
    output.write(f"# Cluster: {report_data['hostname']}\n")
    output.write(f"# Period: {report_data['period']['start_date']} to {report_data['period']['end_date']}\n")
    output.write(f"# Generated: {report_data['generated_at']}\n")
    output.write("\n")

    # Summary section
    output.write("# SUMMARY\n")
    summary = report_data["summary"]
    output.write(f"Total Jobs,{summary['total_jobs']}\n")
    output.write(f"Total CPU Hours,{summary['total_cpu_hours']:.2f}\n")
    output.write(f"Total GPU Hours,{summary['total_gpu_hours']:.2f}\n")
    output.write(f"Total Users,{summary['total_users']}\n")
    output.write("\n")

    # By Account section
    if report_data["by_account"]:
        output.write("# USAGE BY ACCOUNT\n")
        writer = csv.DictWriter(output, fieldnames=["account", "jobs", "cpu_hours", "gpu_hours", "users"])
        writer.writeheader()
        for row in report_data["by_account"]:
            writer.writerow(row)
        output.write("\n")

    # By User section intentionally omitted to protect user privacy
    # Individual user data is not included in reports

    # By Partition section
    if report_data["by_partition"]:
        output.write("# USAGE BY PARTITION\n")
        writer = csv.DictWriter(output, fieldnames=["partition", "jobs", "cpu_hours", "gpu_hours", "users"])
        writer.writeheader()
        for row in report_data["by_partition"]:
            writer.writerow(row)
        output.write("\n")

    # By State section
    if report_data["by_state"]:
        output.write("# JOBS BY STATE\n")
        writer = csv.DictWriter(output, fieldnames=["state", "jobs"])
        writer.writeheader()
        for row in report_data["by_state"]:
            writer.writerow(row)

    return output.getvalue()


def format_hours_readable(hours: float) -> str:
    """Format hours into a readable string (e.g., '1,234.5 hours' or '51.4 days')."""
    if hours < 24:
        return f"{hours:,.1f} hours"
    if hours < 168:  # Less than a week
        return f"{hours / 24:,.1f} days"
    return f"{hours / 168:,.1f} weeks"


def format_report_as_pdf(report_data: dict[str, Any]) -> bytes:
    """Format report data as a professional A4 PDF with executive-level metrics."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
        alignment=1,  # Center
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#34495e"),
        spaceAfter=10,
        spaceBefore=12,
    )
    subheading_style = ParagraphStyle(
        "CustomSubheading",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#000000"),
        spaceAfter=6,
        spaceBefore=8,
    )
    description_style = ParagraphStyle(
        "Description",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#666666"),
        spaceAfter=6,
        leading=13,
    )
    normal_style = styles["Normal"]

    # Build story
    story = []

    # Title
    story.append(Paragraph("<b>SLURM Usage Report</b>", title_style))
    story.append(Paragraph(f"{report_data['report_type']}", heading_style))
    story.append(Spacer(1, 0.2 * inch))

    # Report metadata
    meta_data = [
        ["Cluster:", report_data["hostname"]],
        ["Period:", f"{report_data['period']['start_date']} to {report_data['period']['end_date']}"],
        ["Generated:", datetime.fromisoformat(report_data["generated_at"]).strftime("%Y-%m-%d %H:%M")],
    ]
    meta_table = Table(meta_data, colWidths=[1.5 * inch, 4 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#7f8c8d")),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.3 * inch))

    # Executive Summary
    story.append(Paragraph("<b>Executive Summary</b>", heading_style))
    summary = report_data["summary"]

    summary_data = [
        ["Metric", "Value"],
        ["Total Jobs Submitted", f"{summary['total_jobs']:,}"],
        ["Completed Jobs", f"{summary.get('completed_jobs', 0):,}"],
        ["Failed Jobs", f"{summary.get('failed_jobs', 0):,}"],
        ["Success Rate", f"{summary.get('success_rate', 0):.1f}%"],
        ["Active Users", f"{summary['total_users']:,}"],
        ["Total CPU Hours", format_hours_readable(summary["total_cpu_hours"])],
        ["Total GPU Hours", format_hours_readable(summary["total_gpu_hours"])],
        ["Avg Job Duration", format_hours_readable(summary.get("avg_job_duration_hours", 0))],
        ["Median Job Duration", format_hours_readable(summary.get("median_job_duration_hours", 0))],
        ["Avg Waiting Time", format_hours_readable(summary.get("avg_waiting_time_hours", 0))],
        ["Median Waiting Time", format_hours_readable(summary.get("median_waiting_time_hours", 0))],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 2.5 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    # Trends Over Time Section (must come BEFORE Resource Allocation & Usage to match interactive report)
    story.append(PageBreak())
    story.append(Paragraph("<b>Trends Over Time</b>", heading_style))
    story.append(Spacer(1, 0.2 * inch))

    # Active Users Over Time
    if report_data.get("timeline"):
        story.append(Paragraph("<b>Active Users Over Time</b>", subheading_style))
        story.append(
            Paragraph(
                "This chart displays the number of unique active users each day, showing user engagement trends and comparing them to the previous period.",
                description_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        users_chart = create_comparison_timeline(
            report_data["timeline"],
            report_data["comparison"].get("previous_timeline") if report_data.get("comparison") else None,
            "Active Users Over Time",
            "Active Users",
            "users",
            color="#10b981",  # Green
        )
        if users_chart:
            story.append(users_chart)
            story.append(Spacer(1, 0.3 * inch))

    # Jobs Over Time
    if report_data.get("timeline"):
        story.append(Paragraph("<b>Submitted Jobs Over Time</b>", subheading_style))
        story.append(
            Paragraph(
                "This chart shows the number of jobs submitted daily, tracking job submission patterns and comparing them to the previous period.",
                description_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        jobs_chart = create_comparison_timeline(
            report_data["timeline"],
            report_data["comparison"].get("previous_timeline") if report_data.get("comparison") else None,
            "Submitted Jobs Over Time",
            "Number of Submitted Jobs",
            "jobs",
            color="#8b5cf6",  # Purple
        )
        if jobs_chart:
            story.append(jobs_chart)
            story.append(Spacer(1, 0.3 * inch))

    # Daily CPU Consumption
    if report_data.get("timeline"):
        story.append(Paragraph("<b>CPU Consumption Over Time</b>", subheading_style))
        story.append(
            Paragraph(
                "This chart displays CPU hours consumed per day, showing CPU resource utilization trends and helping identify high-demand periods.",
                description_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        cpu_chart = create_comparison_timeline(
            report_data["timeline"],
            report_data["comparison"].get("previous_timeline") if report_data.get("comparison") else None,
            "Daily CPU Consumption",
            "CPU Hours",
            "cpu_hours",
            color="#04A5D5",  # Blue
        )
        if cpu_chart:
            story.append(cpu_chart)
            story.append(Spacer(1, 0.3 * inch))

    # Daily GPU Consumption
    if report_data.get("timeline") and report_data["summary"]["total_gpu_hours"] > 0:
        story.append(Paragraph("<b>GPU Consumption Over Time</b>", subheading_style))
        story.append(
            Paragraph(
                "This chart displays GPU hours consumed per day, showing GPU resource utilization trends and helping identify high-demand periods.",
                description_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        gpu_chart = create_comparison_timeline(
            report_data["timeline"],
            report_data["comparison"].get("previous_timeline") if report_data.get("comparison") else None,
            "Daily GPU Consumption",
            "GPU Hours",
            "gpu_hours",
            color="#EC7300",  # Orange
        )
        if gpu_chart:
            story.append(gpu_chart)
            story.append(Spacer(1, 0.3 * inch))

    # Resource Allocation & Usage Section
    story.append(PageBreak())
    story.append(Paragraph("<b>Resource Allocation & Usage</b>", heading_style))
    story.append(
        Paragraph(
            "This section provides a comprehensive breakdown of how computational resources were allocated and consumed across different accounts, partitions, and job states during the reporting period. Understanding resource distribution helps identify usage patterns, top consumers, and potential optimization opportunities.",
            description_style,
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    # Usage by Account (Top 10)
    if report_data["by_account"]:
        story.append(Paragraph("<b>Top 10 Accounts by CPU Hours</b>", heading_style))
        story.append(
            Paragraph(
                "The following analysis ranks accounts by their total CPU hour consumption, showing which research groups or projects consumed the most computational resources. CPU hours represent the primary measure of computational work performed on the cluster.",
                description_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        # Bar chart for CPU Hours by Account
        cpu_account_chart = create_bar_chart(
            report_data["by_account"], "Top 10 Accounts by CPU Hours", "account", "cpu_hours", "CPU Hours", top_n=10
        )
        if cpu_account_chart:
            story.append(cpu_account_chart)
            story.append(Spacer(1, 0.2 * inch))

        # Bar chart for GPU Hours by Account (if GPU usage exists)
        total_gpu = sum(acc["gpu_hours"] for acc in report_data["by_account"])
        if total_gpu > 0:
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("<b>Top 10 Accounts by GPU Hours</b>", heading_style))
            story.append(
                Paragraph(
                    "GPU hours measure accelerated computing resources used for machine learning, scientific simulations, and other GPU-intensive workloads. This analysis shows which accounts utilized the most GPU resources during the reporting period.",
                    description_style,
                )
            )
            story.append(Spacer(1, 0.1 * inch))

            gpu_account_chart = create_bar_chart(
                report_data["by_account"], "Top 10 Accounts by GPU Hours", "account", "gpu_hours", "GPU Hours", top_n=10
            )
            if gpu_account_chart:
                story.append(gpu_account_chart)
                story.append(Spacer(1, 0.2 * inch))

        # Table with detailed metrics
        account_data = [["Account", "Jobs", "CPU Hours", "GPU Hours", "Users"]]
        for acc in report_data["by_account"][:10]:
            account_data.append(
                [
                    str(acc["account"]),
                    f"{acc['jobs']:,}",
                    f"{acc['cpu_hours']:,.0f}",
                    f"{acc['gpu_hours']:,.0f}",
                    str(acc.get("users", "-")),
                ]
            )

        account_table = Table(account_data, colWidths=[2 * inch, 1 * inch, 1.5 * inch, 1.5 * inch, 0.75 * inch])
        account_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#9b59b6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                ]
            )
        )
        story.append(account_table)
        story.append(Spacer(1, 0.3 * inch))

    # Usage by Partition - Start on new page for better visual separation
    if report_data["by_partition"]:
        story.append(PageBreak())
        story.append(Paragraph("<b>Usage by Partition</b>", heading_style))
        story.append(
            Paragraph(
                "Partitions represent different hardware configurations or resource pools on the cluster, each optimized for specific workload types. This analysis shows how jobs were distributed across different partitions and the resources consumed in each, helping identify partition utilization patterns and potential capacity constraints.",
                description_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        # Bar chart for Jobs by Partition
        partition_bar = create_bar_chart(
            report_data["by_partition"],
            "Job Distribution by Partition",
            "partition",
            "jobs",
            "Number of Jobs",
            top_n=10,
        )
        if partition_bar:
            story.append(partition_bar)
            story.append(Spacer(1, 0.2 * inch))

        # Table with detailed metrics
        partition_data = [["Partition", "Jobs", "CPU Hours", "GPU Hours"]]
        for part in report_data["by_partition"]:
            partition_data.append(
                [
                    str(part["partition"]),
                    f"{part['jobs']:,}",
                    f"{part['cpu_hours']:,.0f}",
                    f"{part['gpu_hours']:,.0f}",
                ]
            )

        partition_table = Table(partition_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch, 1.5 * inch])
        partition_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f39c12")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                ]
            )
        )
        story.append(partition_table)
        story.append(Spacer(1, 0.3 * inch))

    # Page break before job states
    story.append(PageBreak())

    # Job States
    if report_data["by_state"]:
        story.append(Paragraph("<b>Jobs by State</b>", heading_style))
        story.append(
            Paragraph(
                "Job states indicate the final execution status of submitted jobs, providing insight into job success rates and failure patterns. Common states include COMPLETED (successful execution), FAILED (errors during execution), CANCELLED (user-terminated), TIMEOUT (exceeded time limit), and others. Understanding state distribution helps identify system reliability and potential user workflow issues.",
                description_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        # Bar chart for Jobs by State
        state_bar = create_bar_chart(
            report_data["by_state"], "Job Distribution by State", "state", "jobs", "Number of Jobs", top_n=10
        )
        if state_bar:
            story.append(state_bar)
            story.append(Spacer(1, 0.2 * inch))

        # Table with detailed metrics
        state_data = [["State", "Number of Jobs", "Percentage"]]
        total = sum(s["jobs"] for s in report_data["by_state"])
        for state in report_data["by_state"]:
            pct = (state["jobs"] / total * 100) if total > 0 else 0
            state_data.append(
                [
                    str(state["state"]),
                    f"{state['jobs']:,}",
                    f"{pct:.1f}%",
                ]
            )

        state_table = Table(state_data, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
        state_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1abc9c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                ]
            )
        )
        story.append(state_table)

    # Build PDF
    doc.build(story)

    return buffer.getvalue()
