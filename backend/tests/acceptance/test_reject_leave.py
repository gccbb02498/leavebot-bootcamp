import sqlite3

import pytest

from app import db


def error_pairs(response):
    return [(error["field"], error["code"]) for error in response.json()["errors"]]


@pytest.mark.req("TC-05", "AC-02.1、FR-02、NFR-01")
def test_missing_end_date_is_rejected_without_saving(client, baseline, count_rows):
    payload = dict(baseline)
    del payload["end_date"]
    before = count_rows()

    response = client.post("/api/leave-requests", json=payload)

    assert response.status_code == 422
    assert error_pairs(response) == [("end_date", "missing")]
    assert count_rows() == before


@pytest.mark.req("TC-05", "AC-02.1、FR-02、NFR-01")
def test_blank_employee_id_is_missing(client, baseline, count_rows):
    before = count_rows()

    response = client.post("/api/leave-requests", json={**baseline, "employee_id": ""})

    assert response.status_code == 422
    assert error_pairs(response) == [("employee_id", "missing")]
    assert count_rows() == before


@pytest.mark.req("TC-05", "AC-02.1、FR-01、FR-02、NFR-01")
def test_unknown_employee_is_rejected(client, baseline, count_rows):
    before = count_rows()

    response = client.post("/api/leave-requests", json={**baseline, "employee_id": "E999"})

    assert response.status_code == 422
    assert error_pairs(response) == [("employee_id", "employee_not_found")]
    assert count_rows() == before


@pytest.mark.req("TC-05", "AC-02.1、FR-03、S-02、NFR-01")
def test_all_field_errors_are_returned_together(client, baseline, count_rows):
    payload = {**baseline, "period": "night"}
    del payload["leave_type"]
    before = count_rows()

    response = client.post("/api/leave-requests", json=payload)

    assert response.status_code == 422
    assert sorted(error_pairs(response)) == [("leave_type", "missing"), ("period", "invalid_choice")]
    assert count_rows() == before


@pytest.mark.req("TC-05", "AC-02.1、FR-08、NFR-01")
def test_storage_failure_returns_500_without_saving(client, baseline, count_rows, monkeypatch):
    def failing_insert(conn, data):
        raise sqlite3.Error("disk I/O error")

    monkeypatch.setattr(db, "insert_leave_request", failing_insert)
    before = count_rows()

    response = client.post("/api/leave-requests", json=baseline)

    assert response.status_code == 500
    assert error_pairs(response) == [(None, "storage_error")]
    assert count_rows() == before


@pytest.mark.req("TC-06", "AC-02.1、FR-04、NFR-01")
def test_end_before_start_is_rejected(client, baseline, count_rows):
    before = count_rows()

    response = client.post(
        "/api/leave-requests", json={**baseline, "start_date": "2026-11-04", "end_date": "2026-11-02"}
    )

    assert response.status_code == 422
    assert error_pairs(response) == [("end_date", "end_before_start")]
    assert count_rows() == before


@pytest.mark.req("TC-06", "AC-02.1、FR-05、NFR-01")
def test_half_day_spanning_days_is_rejected(client, baseline, count_rows):
    before = count_rows()

    response = client.post(
        "/api/leave-requests",
        json={**baseline, "start_date": "2026-11-02", "end_date": "2026-11-03", "period": "am"},
    )

    assert response.status_code == 422
    assert error_pairs(response) == [("period", "half_day_multi_day")]
    assert count_rows() == before


@pytest.mark.req("TC-06", "AC-02.1、FR-05、NFR-01")
def test_range_without_workdays_is_rejected(client, baseline, count_rows):
    before = count_rows()

    response = client.post(
        "/api/leave-requests", json={**baseline, "start_date": "2026-11-07", "end_date": "2026-11-08"}
    )

    assert response.status_code == 422
    assert error_pairs(response) == [(None, "no_workdays")]
    assert count_rows() == before


@pytest.mark.req("TC-06", "AC-02.1、FR-04、NFR-01")
def test_nonexistent_date_is_rejected(client, baseline, count_rows):
    before = count_rows()

    response = client.post("/api/leave-requests", json={**baseline, "start_date": "2026-02-30"})

    assert response.status_code == 422
    assert error_pairs(response) == [("start_date", "invalid_date")]
    assert count_rows() == before
