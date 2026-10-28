import pytest


@pytest.mark.req("TC-01", "AC-01.1、FR-07")
def test_valid_request_is_saved_as_pending_and_listed(client, baseline):
    response = client.post("/api/leave-requests", json=baseline)

    assert response.status_code == 201
    created = response.json()
    assert created["days"] == 3
    assert created["status"] == "pending"
    assert created["reason"] == "家庭旅遊"
    assert created["employee_id"] == "E001"

    listed = client.get("/api/employees/E001/leave-requests")
    assert listed.status_code == 200
    assert listed.json() == [created]


@pytest.mark.req("TC-03", "AC-01.2、FR-05、FR-07")
@pytest.mark.parametrize(
    ("changes", "expected_days"),
    [
        ({"leave_type": "personal", "start_date": "2026-11-06", "end_date": "2026-11-09", "period": "full"}, 2),
        ({"leave_type": "sick", "start_date": "2026-11-06", "end_date": "2026-11-06", "period": "am"}, 0.5),
    ],
    ids=["a-cross-weekend", "b-half-day"],
)
def test_saved_days_are_computed_by_backend(client, baseline, changes, expected_days):
    response = client.post("/api/leave-requests", json={**baseline, **changes})

    assert response.status_code == 201
    assert response.json()["days"] == expected_days
    listed = client.get("/api/employees/E001/leave-requests").json()
    assert [row["days"] for row in listed] == [expected_days]


@pytest.mark.req("TC-04", "AC-01.3、FR-04")
def test_past_dates_are_accepted(client, baseline):
    # 前提：注入的今天是 2026-10-28（conftest）。
    payload = {**baseline, "leave_type": "sick", "start_date": "2026-10-19", "end_date": "2026-10-20", "period": "full"}

    response = client.post("/api/leave-requests", json=payload)

    assert response.status_code == 201
    assert response.json()["days"] == 2
    assert response.json()["status"] == "pending"
