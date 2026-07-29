"""
Social Pulse API — Shared Utilities Package
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-naive for DB storage)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
