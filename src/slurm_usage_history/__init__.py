"""
slurm-usage-history: Dashboard for to display the usage history of a Slurm scheduler.
"""

from __future__ import annotations

import json
import sys
from importlib.metadata import Distribution, version


def _is_editable() -> bool:
    try:
        dist = Distribution.from_name("slurm-dashboard")
    except Exception:
        # Fallback to old name for backward compatibility
        try:
            dist = Distribution.from_name("slurm-usage-history")
        except Exception:
            return False

    if sys.version_info >= (3, 13):
        if dist.origin is None:
            return False
        editable = dist.origin.dir_info.editable
    else:
        direct_url = dist.read_text("direct_url.json")
        if direct_url is None:
            return False

        editable = json.loads(direct_url).get("dir_info", {}).get("editable", False)

    if not isinstance(editable, bool):
        return False

    return editable


if _is_editable():
    # Development way of getting the version, it is dynamically updated on each call
    try:
        # setuptools_scm is not included in the runtime virtual environment
        # importing it raises an ImportError,
        # it also fails in the gitlab CI with a UserWarning error
        from setuptools_scm import get_version

        # This will fail with LookupError if Git is not installed
        __version__ = get_version(root="../..", relative_to=__file__)
    except (ImportError, LookupError, UserWarning):
        try:
            __version__ = version(__name__)
        except Exception:
            __version__ = "0.0.0-dev"
else:
    # Get the version as specified by the wheel
    try:
        __version__ = version(__name__)
    except Exception:
        # When using mounted src directory without installed package
        __version__ = "0.0.0-dev"

__all__ = ("__version__",)
