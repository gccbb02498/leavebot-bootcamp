from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def submit(client, baseline, employee_id, day):
    payload = {**baseline, "employee_id": employee_id, "start_date": day, "end_date": day}
    response = client.post("/api/leave-requests", json=payload)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def three_requests(client, baseline):
    first = submit(client, baseline, "E001", "2026-11-02")
    second = submit(client, baseline, "E001", "2026-11-03")
    third = submit(client, baseline, "E002", "2026-11-04")
    return first, second, third


@pytest.mark.req("TC-09", "AC-03.1、FR-09、S-04")
def test_list_shows_only_own_requests_newest_first(client, three_requests):
    first, second, _ = three_requests

    response = client.get("/api/employees/E001/leave-requests")

    assert response.status_code == 200
    assert response.json() == [second, first]


@pytest.mark.req("TC-09", "AC-03.1、FR-09")
def test_other_employee_sees_only_their_request(client, three_requests):
    _, _, third = three_requests

    response = client.get("/api/employees/E002/leave-requests")

    assert response.status_code == 200
    assert response.json() == [third]


@pytest.mark.req("TC-09", "AC-03.1、FR-09、S-04")
def test_employee_without_requests_gets_empty_list(client, three_requests):
    response = client.get("/api/employees/E003/leave-requests")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.req("TC-09", "FR-09、S-03")
def test_unknown_employee_list_returns_404(client, three_requests):
    response = client.get("/api/employees/E999/leave-requests")

    assert response.status_code == 404
    assert [(e["field"], e["code"]) for e in response.json()["errors"]] == [("employee_id", "employee_not_found")]


@pytest.mark.req("TC-09", "FR-01、S-03")
def test_employees_are_listed_by_id(client):
    response = client.get("/api/employees")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "E001", "name": "林小美"},
        {"id": "E002", "name": "陳大文"},
        {"id": "E003", "name": "張志豪"},
    ]


@pytest.mark.req("TC-10", "AC-03.2、NFR-03")
def test_requests_survive_app_restart(tmp_path, baseline):
    db_path = tmp_path / "persist.db"
    with TestClient(create_app(db_path=db_path, today=date(2026, 10, 28))) as first_client:
        saved = first_client.post("/api/leave-requests", json=baseline).json()

    with TestClient(create_app(db_path=db_path, today=date(2026, 10, 28))) as second_client:
        response = second_client.get("/api/employees/E001/leave-requests")

    assert response.json() == [saved]


@pytest.mark.req("TC-11", "NFR-02")
def test_reason_with_html_and_sql_is_saved_verbatim(client, baseline):
    reason = "<b>x</b>'); DROP TABLE leave_requests;--"

    created = client.post("/api/leave-requests", json={**baseline, "reason": reason})

    assert created.status_code == 201
    assert created.json()["reason"] == reason
    listed = client.get("/api/employees/E001/leave-requests")
    assert listed.status_code == 200
    assert [row["reason"] for row in listed.json()] == [reason]
