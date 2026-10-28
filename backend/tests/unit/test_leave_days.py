from datetime import date

import pytest

from app.leave_days import count_leave_days


# 預期值抄自 docs/06-test-plan.md TC-02（人工核算）。
@pytest.mark.req("TC-02", "AC-01.2、FR-05")
@pytest.mark.parametrize(
    ("start", "end", "period", "expected"),
    [
        (date(2026, 11, 2), date(2026, 11, 2), "full", 1),
        (date(2026, 11, 2), date(2026, 11, 8), "full", 5),
        (date(2026, 11, 6), date(2026, 11, 9), "full", 2),
        (date(2026, 11, 7), date(2026, 11, 8), "full", 0),
        (date(2026, 11, 6), date(2026, 11, 6), "am", 0.5),
        (date(2026, 11, 7), date(2026, 11, 7), "pm", 0),
    ],
)
def test_count_leave_days_counts_weekdays_only(start, end, period, expected):
    assert count_leave_days(start, end, period) == expected
