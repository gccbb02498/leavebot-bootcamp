import pytest


def error_pairs(response):
    return [(error["field"], error["code"]) for error in response.json()["errors"]]


@pytest.mark.req("TC-07", "AC-01.4、FR-06、S-04")
def test_blank_reason_is_saved_as_null(client, baseline):
    response = client.post("/api/leave-requests", json={**baseline, "reason": "   "})

    assert response.status_code == 201
    assert response.json()["reason"] is None


@pytest.mark.req("TC-07", "AC-01.4、FR-06、S-04")
def test_reason_of_200_chars_after_strip_is_accepted(client, baseline):
    response = client.post("/api/leave-requests", json={**baseline, "reason": "  " + "假" * 200 + "  "})

    assert response.status_code == 201
    assert response.json()["reason"] == "假" * 200
    assert len(response.json()["reason"]) == 200


@pytest.mark.req("TC-07", "AC-02.2、FR-06、NFR-01")
def test_reason_of_201_chars_is_rejected(client, baseline, count_rows):
    before = count_rows()

    response = client.post("/api/leave-requests", json={**baseline, "reason": "假" * 201})

    assert response.status_code == 422
    assert error_pairs(response) == [("reason", "reason_too_long")]
    assert count_rows() == before


@pytest.mark.req("TC-08", "FR-07、S-01、NFR-01")
@pytest.mark.parametrize(
    ("extra_field", "value"),
    [("status", "approved"), ("days", 0.5)],
    ids=["a-status", "b-days"],
)
def test_client_cannot_set_server_fields(client, baseline, count_rows, extra_field, value):
    before = count_rows()

    response = client.post("/api/leave-requests", json={**baseline, extra_field: value})

    assert response.status_code == 422
    assert error_pairs(response) == [(extra_field, "unknown_field")]
    assert count_rows() == before


# SDS API-03 契約有、測試計畫未編 TC（列為已知缺口）；補測以免非法本文造成未處理例外。
@pytest.mark.req("未編號", "FR-08、SDS invalid_body")
@pytest.mark.parametrize("body", ["[1, 2]", "{not json"], ids=["array", "malformed"])
def test_non_object_body_is_rejected(client, count_rows, body):
    before = count_rows()

    response = client.post(
        "/api/leave-requests", content=body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert error_pairs(response) == [(None, "invalid_body")]
    assert count_rows() == before


@pytest.mark.req("未編號", "FR-08、SDS invalid_type")
def test_non_string_values_are_rejected(client, baseline, count_rows):
    before = count_rows()

    response = client.post("/api/leave-requests", json={**baseline, "start_date": 20261102, "reason": 5})

    assert response.status_code == 422
    assert sorted(error_pairs(response)) == [("reason", "invalid_type"), ("start_date", "invalid_type")]
    assert count_rows() == before
