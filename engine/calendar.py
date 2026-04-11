from datetime import date, timedelta
from typing import Tuple


def cycle_dates(cycle_start: date) -> Tuple[date, date]:
    """Return (start, end) for a cycle beginning on the 15th of a month."""
    if cycle_start.day != 15:
        raise ValueError("Cycle must start on the 15th of a month")
    month = cycle_start.month
    year = cycle_start.year
    if month == 12:
        end = date(year + 1, 1, 14)
    else:
        end = date(year, month + 1, 14)
    return cycle_start, end


def count_working_days(start: date, end: date) -> int:
    """Count Monday–Friday days in [start, end] inclusive."""
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count
