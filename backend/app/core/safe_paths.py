"""Checks that keep request-supplied names inside the directory they belong to."""

from pathlib import Path

from fastapi import HTTPException, status


def single_path_component(value: str | None, what: str) -> str:
    """Return ``value`` if it is one plain path component, else raise ``400``.

    Rejects empty values, separators, ``.``/``..``, and names starting with a dot,
    so the value can only ever name a direct child of the intended directory.
    """
    if (
        not value
        or value in (".", "..")
        or value.startswith(".")
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or Path(value).name != value
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {what}: {value!r}")
    return value


def path_within(base: Path, *parts: str) -> Path:
    """``base`` joined with ``parts``, guaranteed to resolve inside ``base``."""
    base_resolved = base.resolve()
    target = base_resolved.joinpath(*parts).resolve()
    if base_resolved not in target.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path escapes the data directory")
    return target
