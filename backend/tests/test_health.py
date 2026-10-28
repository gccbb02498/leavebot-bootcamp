from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok(tmp_path):
    app = create_app(db_path=tmp_path / "test.db")
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
