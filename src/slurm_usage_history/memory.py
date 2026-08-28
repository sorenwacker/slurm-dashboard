"""Memory value parsing shared by the cluster agent and the dashboard."""

import math
import re

import pandas as pd

_UNIT_TO_MB = {"K": 1 / 1024, "M": 1.0, "G": 1024.0, "T": 1024.0 * 1024.0}
_MEMORY_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMGT])?B?\s*$", re.IGNORECASE)


def parse_memory_to_mb(value) -> float | None:
    """Convert a SLURM memory string such as ``16G``, ``4000M`` or ``512K`` to MB.

    A bare number is taken as MB. Returns None for empty or unparseable input.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    match = _MEMORY_RE.match(str(value))
    if not match:
        return None
    number, unit = match.groups()
    return float(number) * _UNIT_TO_MB[(unit or "M").upper()]


def parse_reqmem_to_mb(value, cpus: int, nodes: int) -> float | None:
    """Convert a sacct ``ReqMem`` value to the job's total requested memory in MB.

    ``ReqMem`` may carry a ``c`` (per allocated CPU) or ``n`` (per allocated node) suffix.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    multiplier = 1
    if text[-1] in "cC":
        multiplier = max(int(cpus or 0), 1)
        text = text[:-1]
    elif text[-1] in "nN":
        multiplier = max(int(nodes or 0), 1)
        text = text[:-1]
    per_unit = parse_memory_to_mb(text)
    return None if per_unit is None else per_unit * multiplier


def add_memory_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Derive ``MaxRSSMB`` from legacy ``MaxRSS`` strings and ``MemGBHours`` from ``ReqMemMB``.

    Missing values stay NaN so charts can exclude jobs with unknown memory.
    """
    if "MaxRSS" in df.columns:
        df = df.copy()
        parsed = df["MaxRSS"].map(parse_memory_to_mb).astype(float)
        if "MaxRSSMB" in df.columns:
            df["MaxRSSMB"] = pd.to_numeric(df["MaxRSSMB"], errors="coerce").fillna(parsed)
        else:
            df["MaxRSSMB"] = parsed
    if "MemGBHours" not in df.columns and "ReqMemMB" in df.columns and "ElapsedHours" in df.columns:
        df = df.copy()
        req_mem_gb = pd.to_numeric(df["ReqMemMB"], errors="coerce") / 1024.0
        df["MemGBHours"] = req_mem_gb * pd.to_numeric(df["ElapsedHours"], errors="coerce")
    return df
