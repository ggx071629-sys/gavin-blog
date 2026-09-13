from __future__ import annotations

from datetime import date, datetime, timedelta

from ..time_utils import as_utc
from .constants import BEIJING_TZ, MIDNIGHT_OVERLAP_MINUTES


def beijing_now(now: datetime) -> datetime:
    return as_utc(now).astimezone(BEIJING_TZ)


def beijing_date(now: datetime) -> date:
    return beijing_now(now).date()


def beijing_midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=BEIJING_TZ)


def next_beijing_midnight(now: datetime) -> datetime:
    current = beijing_date(now)
    return beijing_midnight(current + timedelta(days=1)).astimezone(now.tzinfo or BEIJING_TZ)


def seconds_until(target: datetime, now: datetime) -> int:
    delta = (target - as_utc(now)).total_seconds()
    return max(0, int(delta + 0.999))


def in_midnight_overlap(now: datetime) -> bool:
    local = beijing_now(now)
    return local.hour == 0 and local.minute < MIDNIGHT_OVERLAP_MINUTES
