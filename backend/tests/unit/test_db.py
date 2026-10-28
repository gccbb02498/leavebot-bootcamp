import sqlite3

import pytest

from app import db


@pytest.mark.req("TC-08", "FR-07、ADR-03")
def test_table_rejects_status_other_than_pending(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    conn = db.connect(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    "INSERT INTO leave_requests"
                    " (employee_id, leave_type, start_date, end_date, period, days, reason, status)"
                    " VALUES ('E001', 'annual', '2026-11-02', '2026-11-02', 'full', 1, NULL, 'approved')"
                )
    finally:
        conn.close()
