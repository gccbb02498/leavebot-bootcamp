import re
from dataclasses import dataclass
from datetime import date

from app.leave_days import count_leave_days


@dataclass(frozen=True)
class FieldError:
    field: str | None
    code: str
    message: str


@dataclass(frozen=True)
class LeaveInput:
    employee_id: str
    leave_type: str
    start_date: date
    end_date: date
    period: str
    reason: str | None
    days: float


INVALID_BODY = FieldError(None, "invalid_body", "請求格式錯誤")

REQUIRED_FIELDS = ("employee_id", "leave_type", "start_date", "end_date", "period")

FIELD_LABELS = {
    "employee_id": "員工",
    "leave_type": "假別",
    "start_date": "開始日期",
    "end_date": "結束日期",
    "period": "時段",
}

CHOICES = {
    "leave_type": ("annual", "personal", "sick"),
    "period": ("full", "am", "pm"),
}

ALLOWED_FIELDS = (*REQUIRED_FIELDS, "reason")
REASON_MAX_LENGTH = 200
DATE_RULE_FIELDS = {"start_date", "end_date", "period"}
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _parse_date(value: str) -> date | None:
    if not DATE_PATTERN.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _normalize_reason(value: str | None) -> str | None:
    # 存去掉前後空白後的值；只有空白時存 NULL（S-04）。
    if value is None:
        return None
    return value.strip() or None


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate_leave_request(
    payload: object, employee_ids: set[str]
) -> tuple[LeaveInput | None, list[FieldError]]:
    if not isinstance(payload, dict):
        # 階段 0：本文不是 JSON 物件時不再做其他檢查。
        return None, [INVALID_BODY]

    errors: list[FieldError] = []

    # 階段 1：逐欄檢查，全部收集完再回傳。
    for field in payload:
        if field not in ALLOWED_FIELDS:
            errors.append(FieldError(field, "unknown_field", f"不接受欄位 {field}"))

    # 只有通過必填與型別檢查的欄位，才進入後續的欄位規則。
    values: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if _is_blank(value):
            errors.append(FieldError(field, "missing", f"請填寫{FIELD_LABELS[field]}"))
        elif not isinstance(value, str):
            errors.append(FieldError(field, "invalid_type", "欄位格式錯誤"))
        else:
            values[field] = value

    employee_id = values.get("employee_id")
    if employee_id is not None and employee_id not in employee_ids:
        errors.append(FieldError("employee_id", "employee_not_found", "查無此員工"))

    for field, choices in CHOICES.items():
        value = values.get(field)
        if value is not None and value not in choices:
            errors.append(FieldError(field, "invalid_choice", f"{FIELD_LABELS[field]}不正確"))

    reason = payload.get("reason")
    if reason is not None and not isinstance(reason, str):
        errors.append(FieldError("reason", "invalid_type", "欄位格式錯誤"))
    elif reason is not None and len(reason.strip()) > REASON_MAX_LENGTH:
        errors.append(FieldError("reason", "reason_too_long", f"理由最多 {REASON_MAX_LENGTH} 字"))

    dates: dict[str, date] = {}
    for field in ("start_date", "end_date"):
        value = values.get(field)
        if value is None:
            continue
        parsed = _parse_date(value)
        if parsed is None:
            errors.append(FieldError(field, "invalid_date", "日期格式不正確"))
        else:
            dates[field] = parsed

    # 階段 2：日期欄位與時段都合法才檢查，遇到第一個錯誤就停止。
    errored_fields = {error.field for error in errors}
    if not errored_fields & DATE_RULE_FIELDS:
        start = dates["start_date"]
        end = dates["end_date"]
        period = values["period"]
        days, date_error = _check_date_rules(start, end, period)
        if date_error is not None:
            errors.append(date_error)

    if errors:
        return None, errors

    data = LeaveInput(
        employee_id=employee_id,
        leave_type=values["leave_type"],
        start_date=start,
        end_date=end,
        period=period,
        reason=_normalize_reason(reason),
        days=days,
    )
    return data, []


def _check_date_rules(start: date, end: date, period: str) -> tuple[float, FieldError | None]:
    if end < start:
        return 0, FieldError("end_date", "end_before_start", "結束日期不可早於開始日期")
    if period in ("am", "pm") and start != end:
        return 0, FieldError("period", "half_day_multi_day", "半天假只能選同一天")
    days = count_leave_days(start, end, period)
    if days == 0:
        return 0, FieldError(None, "no_workdays", "所選期間沒有工作日")
    return days, None
