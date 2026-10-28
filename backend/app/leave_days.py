from datetime import date, timedelta


def _is_workday(day: date) -> bool:
    return day.weekday() < 5


def count_leave_days(start: date, end: date, period: str) -> float:
    if start > end:
        raise ValueError("start must not be after end")
    if period in ("am", "pm"):
        if start != end:
            raise ValueError("half-day leave must be a single day")
        return 0.5 if _is_workday(start) else 0
    span = (end - start).days + 1
    return sum(1 for offset in range(span) if _is_workday(start + timedelta(days=offset)))
