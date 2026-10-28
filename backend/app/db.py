import sqlite3
from pathlib import Path

from app.validation import LeaveInput

SEED_EMPLOYEES = [
    ("E001", "林小美"),
    ("E002", "陳大文"),
    ("E003", "張志豪"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leave_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    leave_type  TEXT NOT NULL CHECK (leave_type IN ('annual', 'personal', 'sick')),
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    period      TEXT NOT NULL CHECK (period IN ('full', 'am', 'pm')),
    days        REAL NOT NULL CHECK (days > 0),
    reason      TEXT,
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status = 'pending')
);
"""

LEAVE_COLUMNS = "id, employee_id, leave_type, start_date, end_date, period, days, reason, status"


def connect(db_path: str | Path) -> sqlite3.Connection:
    # 連線只屬於單一請求；FastAPI 可能在不同執行緒開啟與使用它。
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA)
            conn.executemany(
                "INSERT OR IGNORE INTO employees (id, name) VALUES (?, ?)", SEED_EMPLOYEES
            )
    finally:
        conn.close()


def list_employees(conn: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in conn.execute("SELECT id, name FROM employees ORDER BY id")]


def employee_ids(conn: sqlite3.Connection) -> set[str]:
    return {row["id"] for row in conn.execute("SELECT id FROM employees")}


def insert_leave_request(conn: sqlite3.Connection, data: LeaveInput) -> dict:
    with conn:
        cursor = conn.execute(
            "INSERT INTO leave_requests"
            " (employee_id, leave_type, start_date, end_date, period, days, reason)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                data.employee_id,
                data.leave_type,
                data.start_date.isoformat(),
                data.end_date.isoformat(),
                data.period,
                data.days,
                data.reason,
            ),
        )
    row = conn.execute(
        f"SELECT {LEAVE_COLUMNS} FROM leave_requests WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return dict(row)


def list_leave_requests(conn: sqlite3.Connection, employee_id: str) -> list[dict]:
    rows = conn.execute(
        f"SELECT {LEAVE_COLUMNS} FROM leave_requests WHERE employee_id = ? ORDER BY id DESC",
        (employee_id,),
    )
    return [dict(row) for row in rows]
