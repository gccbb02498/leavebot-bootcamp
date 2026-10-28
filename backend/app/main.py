import os
import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.validation import INVALID_BODY, FieldError, validate_leave_request

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_DB_PATH = BASE_DIR.parent / "data" / "leavebot.db"


def _resolve_db_path(db_path: str | Path | None) -> Path:
    # 參數 → LEAVEBOT_DB → backend/data/leavebot.db（SDS create_app）
    if db_path is not None:
        return Path(db_path)
    env_value = os.environ.get("LEAVEBOT_DB")
    if env_value:
        return Path(env_value)
    return DEFAULT_DB_PATH


def _resolve_today(today: date | None) -> date:
    # 參數 → LEAVEBOT_TODAY（YYYY-MM-DD，格式錯誤時啟動失敗）→ date.today()
    if today is not None:
        return today
    env_value = os.environ.get("LEAVEBOT_TODAY")
    if env_value:
        return date.fromisoformat(env_value)
    return date.today()


def _error_response(status_code: int, errors: list[FieldError]) -> JSONResponse:
    # 所有 4xx／5xx 共用 {"errors": [{field, code, message}]}（SDS S-02）。
    return JSONResponse(
        {"errors": [{"field": e.field, "code": e.code, "message": e.message} for e in errors]},
        status_code=status_code,
    )


def create_app(db_path: str | Path | None = None, today: date | None = None) -> FastAPI:
    resolved_db_path = _resolve_db_path(db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 建表在啟動時進行，import 本身不建立資料庫（ADR-02）。
        db.init_db(resolved_db_path)
        yield

    app = FastAPI(title="LeaveBot", lifespan=lifespan)
    app.state.db_path = resolved_db_path
    app.state.today = _resolve_today(today)

    def get_conn() -> Iterator[sqlite3.Connection]:
        # 每個請求一條連線，finally 關閉，避免 Windows 鎖住暫存資料庫檔。
        conn = db.connect(resolved_db_path)
        try:
            yield conn
        finally:
            conn.close()

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request: Request, exc: sqlite3.Error) -> JSONResponse:
        # 寫入在 with conn: 中，例外時已回滾，筆數不變。
        return _error_response(500, [FieldError(None, "storage_error", "無法存檔，請稍後再試")])

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/employees")
    def list_employees(conn: sqlite3.Connection = Depends(get_conn)):
        return db.list_employees(conn)

    @app.post("/api/leave-requests")
    async def create_leave_request(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
        try:
            payload = await request.json()
        except ValueError:
            return _error_response(422, [INVALID_BODY])
        data, errors = validate_leave_request(payload, db.employee_ids(conn))
        if errors:
            return _error_response(422, errors)
        return JSONResponse(db.insert_leave_request(conn, data), status_code=201)

    @app.get("/api/employees/{employee_id}/leave-requests")
    def list_leave_requests(employee_id: str, conn: sqlite3.Connection = Depends(get_conn)):
        if employee_id not in db.employee_ids(conn):
            return _error_response(404, [FieldError("employee_id", "employee_not_found", "查無此員工")])
        return db.list_leave_requests(conn, employee_id)

    # 所有 /api 路由登記完才掛靜態目錄。
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
