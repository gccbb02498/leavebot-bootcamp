import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

# SRS X-01 未裁定前先注入 2026-10-28（docs/06-test-plan.md）。
TODAY = date(2026, 10, 28)
DEV_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "leavebot.db"

# 測試計畫「基準合法申請」
BASELINE = {
    "employee_id": "E001",
    "leave_type": "annual",
    "start_date": "2026-11-02",
    "end_date": "2026-11-04",
    "period": "full",
    "reason": "家庭旅遊",
}


@pytest.fixture(scope="session", autouse=True)
def dev_db_untouched():
    # NFR-04：測試不得建立開發資料庫。
    existed_before = DEV_DB_PATH.exists()
    yield
    if not existed_before:
        assert not DEV_DB_PATH.exists(), "測試建立了開發資料庫 backend/data/leavebot.db"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def client(db_path):
    app = create_app(db_path=db_path, today=TODAY)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def baseline():
    return dict(BASELINE)


@pytest.fixture
def count_rows(db_path):
    def _count() -> int:
        conn = sqlite3.connect(db_path)
        try:
            return conn.execute("SELECT COUNT(*) FROM leave_requests").fetchone()[0]
        finally:
            conn.close()

    return _count
