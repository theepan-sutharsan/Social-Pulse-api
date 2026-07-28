"""
Social Pulse API — Shared Utilities
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
