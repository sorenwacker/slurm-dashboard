"""Report generation endpoints for monthly and annual usage reports."""
import json
from typing import Any, Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..core.saml_auth import get_current_user_saml
from ..services.reports import (
    format_report_as_csv,
    format_report_as_pdf,
    generate_report_data,
    get_month_date_range,
    get_quarter_date_range,
    get_year_date_range,
)
from .dashboard import get_datastore

router = APIRouter()


@router.get("/generate")
async def generate_report(
    hostname: str = Query(..., description="Cluster hostname"),
    format: Literal["json", "csv", "pdf"] = Query("json", description="Report format"),
    type: Literal["monthly", "quarterly", "annual"] = Query("monthly", description="Report type"),
    year: int = Query(..., description="Year for the report"),
    month: int | None = Query(None, description="Month for monthly report (1-12)"),
    quarter: int | None = Query(None, description="Quarter for quarterly report (1-4)"),
    current_user: dict = Depends(get_current_user_saml),
) -> Response:
    """
    Generate usage report for a specific period.

    - **hostname**: Cluster hostname
    - **format**: Output format (json, csv, pdf)
    - **type**: Report type (monthly, quarterly, or annual)
    - **year**: Year for the report
    - **month**: Month for monthly report (1-12)
    - **quarter**: Quarter for quarterly report (1-4)
    """
    try:
        # Validate inputs
        datastore = get_datastore()
        if hostname not in datastore.get_hostnames():
            raise HTTPException(status_code=404, detail=f"Cluster {hostname} not found")

        # Check if period is complete (not current/future period)
        from datetime import datetime
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_quarter = (current_month - 1) // 3 + 1

        if type == "monthly":
            if month is None:
                raise HTTPException(status_code=400, detail="Month is required for monthly reports")
            if not 1 <= month <= 12:
                raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
            # Prevent reports for current or future months
            if year > current_year or (year == current_year and month >= current_month):
                raise HTTPException(status_code=400, detail=f"Cannot generate report for incomplete or future period: {year}-{month:02d}")
            start_date, end_date = get_month_date_range(year, month)
            report_type = f"Monthly Report - {year}-{month:02d}"
            filename_suffix = f"{year}_{month:02d}"
        elif type == "quarterly":
            if quarter is None:
                raise HTTPException(status_code=400, detail="Quarter is required for quarterly reports")
            if not 1 <= quarter <= 4:
                raise HTTPException(status_code=400, detail="Quarter must be between 1 and 4")
            # Prevent reports for current or future quarters
            if year > current_year or (year == current_year and quarter >= current_quarter):
                raise HTTPException(status_code=400, detail=f"Cannot generate report for incomplete or future period: {year} Q{quarter}")
            start_date, end_date = get_quarter_date_range(year, quarter)
            report_type = f"Quarterly Report - {year} Q{quarter}"
            filename_suffix = f"{year}_Q{quarter}"
        else:
            # Prevent reports for current or future years
            if year >= current_year:
                raise HTTPException(status_code=400, detail=f"Cannot generate report for incomplete or future period: {year}")
            start_date, end_date = get_year_date_range(year)
            report_type = f"Annual Report - {year}"
            filename_suffix = f"{year}"

        # Generate report data
        report_data = generate_report_data(hostname, start_date, end_date, report_type)

        # Return in requested format
        if format == "json":
            return Response(
                content=json.dumps(report_data, indent=2),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{hostname}_{filename_suffix}.json"
                },
            )
        if format == "csv":
            csv_content = format_report_as_csv(report_data)
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{hostname}_{filename_suffix}.csv"
                },
            )
        if format == "pdf":
            pdf_content = format_report_as_pdf(report_data)
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{hostname}_{filename_suffix}.pdf"
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {e!s}")


@router.get("/preview")
async def preview_report(
    hostname: str = Query(..., description="Cluster hostname"),
    type: Literal["monthly", "quarterly", "annual"] = Query("monthly", description="Report type"),
    year: int = Query(..., description="Year for the report"),
    month: int | None = Query(None, description="Month for monthly report (1-12)"),
    quarter: int | None = Query(None, description="Quarter for quarterly report (1-4)"),
    current_user: dict = Depends(get_current_user_saml),
) -> dict[str, Any]:
    """
    Preview report data for inline display (without downloading).

    Returns JSON data with summary statistics and breakdowns for visualization.

    - **hostname**: Cluster hostname
    - **type**: Report type (monthly, quarterly, or annual)
    - **year**: Year for the report
    - **month**: Month for monthly report (1-12)
    - **quarter**: Quarter for quarterly report (1-4)
    """
    try:
        # Validate inputs
        datastore = get_datastore()
        if hostname not in datastore.get_hostnames():
            raise HTTPException(status_code=404, detail=f"Cluster {hostname} not found")

        # Check if period is complete (not current/future period)
        from datetime import datetime
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_quarter = (current_month - 1) // 3 + 1

        if type == "monthly":
            if month is None:
                raise HTTPException(status_code=400, detail="Month is required for monthly reports")
            if not 1 <= month <= 12:
                raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
            # Prevent reports for current or future months
            if year > current_year or (year == current_year and month >= current_month):
                raise HTTPException(status_code=400, detail=f"Cannot generate report for incomplete or future period: {year}-{month:02d}")
            start_date, end_date = get_month_date_range(year, month)
            report_type = f"Monthly Report - {year}-{month:02d}"
        elif type == "quarterly":
            if quarter is None:
                raise HTTPException(status_code=400, detail="Quarter is required for quarterly reports")
            if not 1 <= quarter <= 4:
                raise HTTPException(status_code=400, detail="Quarter must be between 1 and 4")
            # Prevent reports for current or future quarters
            if year > current_year or (year == current_year and quarter >= current_quarter):
                raise HTTPException(status_code=400, detail=f"Cannot generate report for incomplete or future period: {year} Q{quarter}")
            start_date, end_date = get_quarter_date_range(year, quarter)
            report_type = f"Quarterly Report - {year} Q{quarter}"
        else:
            # Prevent reports for current or future years
            if year >= current_year:
                raise HTTPException(status_code=400, detail=f"Cannot generate report for incomplete or future period: {year}")
            start_date, end_date = get_year_date_range(year)
            report_type = f"Annual Report - {year}"

        # Generate report data
        report_data = generate_report_data(hostname, start_date, end_date, report_type)

        return report_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report preview: {e!s}")


@router.get("/available-periods/{hostname}")
async def get_available_periods(hostname: str, current_user: dict = Depends(get_current_user_saml)) -> dict[str, Any]:
    """
    Get available reporting periods for a cluster.

    Returns the min/max dates and a list of available months and years.
    """
    try:
        datastore = get_datastore()
        if hostname not in datastore.get_hostnames():
            raise HTTPException(status_code=404, detail=f"Cluster {hostname} not found")

        min_date, max_date = datastore.get_min_max_dates(hostname)

        if not min_date or not max_date:
            return {
                "hostname": hostname,
                "min_date": None,
                "max_date": None,
                "available_years": [],
                "available_months": {},
            }

        # Parse dates
        min_dt = pd.Timestamp(min_date)
        max_dt = pd.Timestamp(max_date)

        # Generate list of available years
        available_years = list(range(min_dt.year, max_dt.year + 1))

        # Generate available months for each year
        available_months = {}
        for year in available_years:
            if year == min_dt.year and year == max_dt.year:
                # Same year
                months = list(range(min_dt.month, max_dt.month + 1))
            elif year == min_dt.year:
                # First year
                months = list(range(min_dt.month, 13))
            elif year == max_dt.year:
                # Last year
                months = list(range(1, max_dt.month + 1))
            else:
                # Full year
                months = list(range(1, 13))
            available_months[year] = months

        return {
            "hostname": hostname,
            "min_date": min_date,
            "max_date": max_date,
            "available_years": available_years,
            "available_months": available_months,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching available periods: {e!s}")
