"""Time helpers.

Two concerns live here.

**Storage vs. reading.** PostgreSQL returns timezone-aware datetimes for
``TIMESTAMP WITH TIME ZONE``; SQLite has no timezone type and hands back naive
values. Everything this application writes is UTC, so a naive value read back
from the database is UTC and is labelled as such here. Normalising at the
boundary keeps comparisons working identically on both backends.

**The cooperative's day.** A cooperative in Coimbatore closes its books at
local midnight, not at midnight UTC. "Completed today" and the weekly demand
buckets are therefore measured against the cooperative's own timezone, which
is configurable rather than hardcoded.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone, tzinfo
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings

logger = logging.getLogger(__name__)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@lru_cache
def cooperative_tz() -> tzinfo:
    """The cooperative's operating timezone, falling back to UTC loudly."""
    name = settings.cooperative_timezone
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        logger.warning(
            "Unknown COOPERATIVE_TIMEZONE %r; falling back to UTC. Install the "
            "'tzdata' package or set a valid IANA timezone name.",
            name,
        )
        return timezone.utc


def to_local(value: datetime | None) -> datetime | None:
    """A UTC instant expressed in the cooperative's local time."""
    normalised = ensure_utc(value)
    return normalised.astimezone(cooperative_tz()) if normalised else None


def local_today(now: datetime | None = None) -> date:
    """Today's date as the cooperative would write it."""
    return (to_local(now or utcnow()) or utcnow()).date()


def local_day_start(now: datetime | None = None) -> datetime:
    """Midnight at the start of the cooperative's current day, in UTC."""
    local = to_local(now or utcnow())
    assert local is not None
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc)


def local_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """The UTC instants bounding the cooperative's current day."""
    start = local_day_start(now)
    return start, start + timedelta(days=1)
