import functools
import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, TypeVar

import pandas as pd

T = TypeVar("T")  # For generic function typing


def timeit(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to measure execution time of a function."""

    @functools.wraps(func)
    def wrapper_timeit(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time
        print(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds")
        return result

    return wrapper_timeit


def natural_sort_key(s: str | Any | None) -> list[int | str] | Any:
    """
    Natural sorting function that handles numeric parts in strings properly.
    For example: "cpu2" will come before "cpu11" with natural sorting.

    Args:
        s: String to convert to a natural sort key

    Returns:
        A list that can be used as a sort key with proper numeric ordering
    """
    # If the input is not a string (e.g., None or already numeric), return it
    if not isinstance(s, str):
        return s

    # Split the string into text and numeric parts
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def get_time_column(date_str1: str, date_str2: str) -> str:
    """
    Calculate the timespan in days between two dates provided in ISO format strings.

    Args:
        date_str1: The first date in ISO format (YYYY-MM-DD).
        date_str2: The second date in ISO format (YYYY-MM-DD).

    Returns:
        The column name to use based on the timespan between dates.
    """
    # Parse the input strings into datetime objects
    date1 = datetime.strptime(date_str1, "%Y-%m-%d")
    date2 = datetime.strptime(date_str2, "%Y-%m-%d")

    # Calculate the difference in days
    timespan = abs((date2 - date1).days)

    if timespan < 66:
        return "SubmitDay"
    if timespan < (365 * 1.5):
        return "SubmitYearWeek"
    return "SubmitYearMonth"


def week_to_date(year_week_str: str) -> datetime:
    """
    Convert a year-week string to a datetime object.

    Args:
        year_week_str: String in format 'YYYY-WW' where YYYY is year and WW is week number

    Returns:
        First day (Monday) of the specified week
    """
    # Parse the year and week from the input string
    year, week = map(int, year_week_str.split("-"))

    # Define the first day of the year
    first_day_of_year = datetime(year, 1, 1)

    # Find the start of the first week (Monday)
    first_week_start = first_day_of_year - timedelta(days=first_day_of_year.weekday())

    # Calculate the start date of the given week
    return first_week_start + timedelta(weeks=week - 1)


def month_to_date(year_month_str: str) -> datetime:
    """
    Convert a year-month string to a datetime object.

    Args:
        year_month_str: String in format 'YYYY-MM' where YYYY is year and MM is month

    Returns:
        First day of the specified month
    """
    # Parse the year and month from the input string
    year, month = map(int, year_month_str.split("-"))

    # Construct the first day of the given month
    return datetime(year, month, 1)


def print_column_info_in_markdown(df: pd.DataFrame) -> None:
    """
    Prints the column data types and an example value for each
    column in markdown format.

    Args:
        df: The dataframe to inspect.
    """
    # Create a list to store the column data type and example value
    column_info: list[list[Any]] = []

    for column in df.columns:
        dtype = df[column].dtype
        example_value = df[column].iloc[0]  # Get the first value as example
        column_info.append([column, str(dtype), example_value])

    # Create a DataFrame from the list to display in markdown format
    column_info_df = pd.DataFrame(column_info, columns=["Column", "Data Type", "Example Value"])

    # Print the markdown representation of the dataframe
    print(column_info_df.to_markdown(index=False))


def categorize_time(hours: float | int) -> str:
    """
    Categorize time in hours into predefined categories.

    Args:
        hours: Time in hours to categorize.

    Returns:
        The category corresponding to the given time.
    """
    if hours < (5 / 3600):
        return "<5s"
    if hours < (1 / 60):
        return "<1min"
    if hours < (5 / 60):
        return "<5min"
    if hours < (30 / 60):
        return "<30min"
    if hours < 1:
        return "<1h"
    if hours < 5:
        return "<5h"
    if hours < 10:
        return "<10h"
    if hours < 24:
        return "<24h"
    # > 24 hours
    return ">=24h"


def categorize_time_series(hours_series: pd.Series) -> pd.Series:
    """
    Categorize a Pandas Series of time in hours into predefined categories.

    Args:
        hours_series: A Pandas Series with time in hours.

    Returns:
        A Pandas Series of categorical type with the corresponding categories.
    """
    categories = [
        "<5s",
        "<1min",
        "<15min",
        "<30min",
        "<1h",
        "<5h",
        "<10h",
        "<24h",
        ">=24h",
    ]
    bins = [0, 5 / 3600, 1 / 60, 15 / 60, 30 / 60, 1, 5, 10, 24, float("inf")]

    # Use pd.cut to bin and categorize
    categorized_series = pd.cut(hours_series, bins=bins, labels=categories, right=False, ordered=True)

    return categorized_series.astype("category")


def unpack_nodelist_string(nodelist_str: str | None) -> list[str]:
    """
    Unpacks a GPU string into a list of individual components.
    Handles ranges (e.g., gpu[08-09,11,14]) and single items (e.g., gpu16).
    Also handles malformed strings like "gpu[30" or "14-15]" by cleaning them.

    Args:
        nodelist_str: String containing node list information

    Returns:
        List of individual node names
    """
    if not nodelist_str or nodelist_str == "None assigned":
        return []

    # Clean up obviously malformed strings first
    # If it starts with just digits and brackets, it's incomplete - skip it
    if re.match(r"^[\d\[\]\-,]+$", nodelist_str.strip()):
        return []

    # Initialize a list to collect unpacked values
    unpacked_list: list[str] = []

    # Match patterns for ranges and list items
    range_pattern = re.compile(r"(\d+)-(\d+)")
    list_pattern = re.compile(r"(\w+)\[(.*?)\]")
    # Pattern for incomplete bracket notation like "gpu[30" without closing bracket
    incomplete_pattern = re.compile(r"(\w+)\[(\d+)$")

    # Check for incomplete bracket notation (e.g., "gpu[30")
    incomplete_match = incomplete_pattern.search(nodelist_str)
    if incomplete_match:
        base, num_str = incomplete_match.groups()
        # Detect padding from the number
        padding = len(num_str) if num_str and num_str[0] == "0" and len(num_str) > 1 else 0
        num = int(num_str)
        if padding:
            unpacked_list.append(f"{base}{num:0{padding}d}")
        else:
            unpacked_list.append(f"{base}{num}")
        return unpacked_list

    # Check for list patterns (e.g., gpu[08-09,11,14])
    list_match = list_pattern.search(nodelist_str)
    if list_match:
        base, range_str = list_match.groups()
        ranges = range_str.split(",")
        for r in ranges:
            if "-" in r:
                start_str, end_str = r.split("-")
                # Detect padding from the first number in the range
                padding = len(start_str) if start_str and start_str[0] == "0" and len(start_str) > 1 else 0
                start, end = int(start_str), int(end_str)
                for num in range(start, end + 1):
                    if padding:
                        unpacked_list.append(f"{base}{num:0{padding}d}")
                    else:
                        unpacked_list.append(f"{base}{num}")
            else:
                # Single items - detect padding
                try:
                    padding = len(r) if r and r[0] == "0" and len(r) > 1 else 0
                    num = int(r)
                    if padding:
                        unpacked_list.append(f"{base}{num:0{padding}d}")
                    else:
                        unpacked_list.append(f"{base}{num}")
                except ValueError:
                    # If it's not a number, append as is
                    unpacked_list.append(f"{base}{r}")
    else:
        # If no list pattern, check if there are single items or other cases
        parts = nodelist_str.split(",")
        for part in parts:
            # Check for ranges in single items (e.g., gpu[01-03])
            range_match = range_pattern.search(part)
            if range_match and "[" in part:
                base, _ = part.split("[")
                start_str, end_str = range_match.groups()
                # Detect padding from the first number
                padding = len(start_str) if start_str and start_str[0] == "0" and len(start_str) > 1 else 0
                start, end = int(start_str), int(end_str)
                for num in range(start, end + 1):
                    if padding:
                        unpacked_list.append(f"{base}{num:0{padding}d}")
                    else:
                        unpacked_list.append(f"{base}{num}")
            else:
                # Handle regular items (just strip brackets if any)
                clean_part = part.strip().rstrip("]").lstrip("[")
                if clean_part:
                    unpacked_list.append(clean_part)

    # Ensure no invalid items like trailing ']'
    return [item.strip("]") for item in unpacked_list]
