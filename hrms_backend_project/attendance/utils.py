"""Small, dependency-free helper functions used across the attendance module."""
import calendar
from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone


def get_setting(key, default=None):
    return settings.ATTENDANCE_SETTINGS.get(key, default)


def to_decimal_hours(value) -> Decimal:
    """Round any numeric value to 2-decimal-place Decimal hours."""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def timedelta_to_hours(td) -> Decimal:
    """Convert a timedelta into Decimal hours (can be negative)."""
    seconds = td.total_seconds()
    return to_decimal_hours(seconds / 3600)


def parse_shift_time(value: str) -> time:
    """'09:30' -> time(9, 30)"""
    hour, minute = value.split(':')
    return time(int(hour), int(minute))


def shift_start_datetime(for_date):
    shift_start = parse_shift_time(get_setting('SHIFT_START_TIME', '09:30'))
    naive = datetime.combine(for_date, shift_start)
    return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


def shift_end_datetime(for_date):
    shift_end = parse_shift_time(get_setting('SHIFT_END_TIME', '18:30'))
    naive = datetime.combine(for_date, shift_end)
    return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def month_bounds(year: int, month: int):
    """Return (first_day, last_day) date objects for the given month/year."""
    from datetime import date

    first_day = date(year, month, 1)
    last_day = date(year, month, days_in_month(year, month))
    return first_day, last_day


def percentage(numerator, denominator, decimals=2):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, decimals)


def is_weekend(day) -> bool:
    """Saturday/Sunday are treated as the standard weekend."""
    return day.weekday() in (5, 6)
