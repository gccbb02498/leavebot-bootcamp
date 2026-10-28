# 000 骨架：首頁讀到 /api/health

- 估計大小：小，約 20–30 分鐘，含建 venv 和安裝套件。
- 依賴：無。
- 後續：解鎖 `issues/001-submit-leave.md`。
- 狀態：待辦。

## 成果

一個可以安裝、測試、啟動的空白 FastAPI 專案。首頁用 `fetch('/api/health')` 顯示連線結果。**這張票不寫請假邏輯**：不建資料表、不建員工資料，也不做 `/api/health` 以外的 API。

## 要讀的規格

- `course/01-上課/04-STACK.md`：全文，特別是「骨架票 000 的要求」1–5 點，以及「安裝與執行」。
- `docs/05-sds.md`：
  - API-01 `GET /api/health`：回 `200 {"status": "ok"}`。
  - 「`main.create_app`」：只取簽名與路由登記順序。
- `AGENTS.md`：「實作與驗收」與「本專案決策」。

## 工作內容

1. 依 STACK 第 1–3 點建立根目錄 `pyproject.toml`：
   - 套件白名單、`requires-python`、明確的 package discovery 和靜態檔 package data。
   - pytest 設定，並註冊 `req` marker。
2. 依 STACK 第 4 點建立以下檔案：
   - `backend/app/__init__.py`、`backend/app/main.py`
   - `backend/app/static/index.html`、`app.js`、`style.css`
3. `main.py` 直接採用 SDS 的形式 `create_app(db_path=None, today=None) -> FastAPI`，並在模組層寫 `app = create_app()` 給 uvicorn 使用。
   - 這張票只要求簽名和參數解析存在，可以先把值放在 `app.state`。
   - 不建資料庫，也不建立資料庫檔。
4. 所有 `/api` 路由先登記，最後才掛 `StaticFiles(directory=<static>, html=True)` 到 `/`。
5. 首頁在載入時呼叫 `/api/health`：
   - 成功時顯示「已連線」。
   - 失敗時顯示「無法連線」。
   - 文字一律用 `textContent` 寫入。
6. 建立 `backend/tests/` 並加一個 health 測試：
   - 用 `create_app()` 建 app，不使用模組層的 `app`。
   - 這不是業務 TC，不掛 TC 編號。

## 骨架檢查（全部通過才算完成）

- [ ] 依 STACK 的安裝指令可以成功安裝，而且有加 `-c course/01-上課/05-constraints.txt`。實際的 Python 與套件版本記在交付回報裡。
- [ ] `pytest` 實際執行，health 測試通過。
- [ ] `GET /api/health` 回 `200 {"status": "ok"}`。
- [ ] 啟動 uvicorn 後開 `http://127.0.0.1:8000/`，首頁顯示「已連線」。
- [ ] Ctrl+C 停止後再啟動一次，首頁仍然正常。
- [ ] 程式碼裡沒有任何請假相關的路由、資料表或資料庫檔。
- [ ] `git status` 裡沒有 `.venv/`、`backend/data/` 或 `*.egg-info`。

## 驗收指令

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -c course/01-上課/05-constraints.txt -e ".[dev]"
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

macOS／Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -c course/01-上課/05-constraints.txt -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

## 完成時

回報以下內容後就停下，等小組驗收，不接著做 001：

- 測試輸出。
- 實際網址。
- 實際的 Python 與套件版本。
- 沒有驗證的項目。
