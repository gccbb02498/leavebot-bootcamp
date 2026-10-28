# 05 SDS — LeaveBot 請假系統

- 上游：`docs/04-sad.md`、`docs/03-srs.md`
- 版本：v0.1
- 狀態：草稿，待講師審查
- 負責人：本小組
- 審查者：講師
- 日期：2026-10-28
- 契約變更時，同步更新 `docs/06-test-plan.md` 的 TC。

## 目錄

- [資料模型與不變量](#資料模型與不變量)
- [API 契約](#api-契約)
- [UI 與模組契約](#ui-與模組契約)
- [變更與未決](#變更與未決)

## 資料模型與不變量

員工資料在資料庫初始化時寫入，執行期間不會變動。假單只會新增，本次沒有修改或刪除。

以下欄位由伺服器決定，客戶端無法指定：`id`、`days`、`status`。

| 欄位 | 型別、格式與可空性 | 預設／約束 | 來源 |
|---|---|---|---|
| `employees.id` | TEXT，非空 | 主鍵，例如 `E001` | FR-01 |
| `employees.name` | TEXT，非空 | — | FR-01 |
| `leave_requests.id` | INTEGER，非空 | 主鍵，AUTOINCREMENT | FR-07 |
| `leave_requests.employee_id` | TEXT，非空 | 外鍵指向 `employees.id` | FR-03、FR-09 |
| `leave_requests.leave_type` | TEXT，非空 | `CHECK IN ('annual','personal','sick')` | FR-03 |
| `leave_requests.start_date`、`end_date` | TEXT，非空，格式 `YYYY-MM-DD` | 由程式保證 `end_date >= start_date` | FR-04 |
| `leave_requests.period` | TEXT，非空 | `CHECK IN ('full','am','pm')` | FR-03、FR-05 |
| `leave_requests.days` | REAL，非空 | `CHECK (days > 0)`，值是 0.5 的倍數，由後端計算 | FR-05、FR-07 |
| `leave_requests.reason` | TEXT，可空 | 存去掉前後空白後的值；未填時存 NULL；`len` ≤ 200 | FR-06、S-04 |
| `leave_requests.status` | TEXT，非空 | `DEFAULT 'pending'`，`CHECK (status = 'pending')` | FR-07、ADR-03 |

**種子員工**（S-03）：三位都是虛構人物。

| id | name |
|---|---|
| E001 | 林小美 |
| E002 | 陳大文 |
| E003 | 張志豪 |

- 初始化：`init_db` 以 `CREATE TABLE IF NOT EXISTS` 建表，再用 `INSERT OR IGNORE` 寫入種子員工，可重複執行。
- 外鍵：每條連線都要執行 `PRAGMA foreign_keys = ON`。
- 交易邊界：一次 POST 只寫入一筆，在 `with conn:` 中完成。發生例外就回滾，筆數不變。
- 拒絕不存檔：驗證失敗時根本不會呼叫寫入函式（NFR-01）。
- 重試與重複送出：不去重（D-03、NG-04）。同樣內容的兩次 POST 會產生兩筆，`id` 不同。前端靠停用按鈕防止連點。
- 持久性：資料存在檔案型 SQLite，重啟後仍在（NFR-03）。

## API 契約

所有回應都是 JSON，路徑都在 `/api/` 之下，同來源呼叫，不開 CORS。

**錯誤格式**：所有 4xx 和 5xx 回應都用同一個格式（S-02）。

```json
{"errors": [{"field": "end_date", "code": "end_before_start", "message": "結束日期不可早於開始日期"}]}
```

`field` 是欄位名稱；不屬於單一欄位的錯誤，`field` 為 `null`。`message` 是給使用者看的中文文案，前端照原文顯示。測試以 `code` 判斷，不比對 `message` 的文字。

### API-01｜GET /api/health

用途：檢查服務是否在線（票 000）。

- 成功：`200 {"status": "ok"}`。
- 失敗：服務沒有啟動時，連線會失敗，首頁顯示「無法連線」。

### API-02｜GET /api/employees（FR-01）

頁面載入時呼叫，用來填入下拉選單。沒有副作用。

- 成功：`200`，依 `id` 由小到大排序：

  ```json
  [{"id": "E001", "name": "林小美"}, {"id": "E002", "name": "陳大文"}, {"id": "E003", "name": "張志豪"}]
  ```

- 失敗：資料庫錯誤時回 `500`，`code` 為 `storage_error`。

### API-03｜POST /api/leave-requests（FR-02～FR-08）

員工按下「送出」時呼叫。只有驗證全部通過，才會新增一筆 `pending` 假單。

- 請求：

  ```json
  {"employee_id": "E001", "leave_type": "annual", "start_date": "2026-11-02", "end_date": "2026-11-04", "period": "full", "reason": "家庭旅遊"}
  ```

  - 必填：`employee_id`、`leave_type`、`start_date`、`end_date`、`period`。
  - 選填：`reason`，可以是字串、`null`，或整個省略。
  - 未知欄位：包括 `status`、`days` 在內，出現就整筆拒絕（S-01）。

- 成功：`201`，回傳完整的假單：

  ```json
  {"id": 1, "employee_id": "E001", "leave_type": "annual", "start_date": "2026-11-02", "end_date": "2026-11-04", "period": "full", "days": 3, "reason": "家庭旅遊", "status": "pending"}
  ```

- 失敗：`422` 加錯誤清單時，資料不變。`500 storage_error` 時，交易已回滾，資料也不變。
- 錯誤碼與檢查順序：

| 階段 | code | field | 條件 | 範例 message |
|---|---|---|---|---|
| 0 | `invalid_body` | `null` | 本文不是 JSON 物件，例如陣列或格式錯誤；出現時不再做其他檢查 | 請求格式錯誤 |
| 1 | `unknown_field` | 該欄位名稱 | 欄位不在上面列出的 6 個之中 | 不接受欄位 status |
| 1 | `missing` | 該欄位 | 必填欄位沒給、是 `null`，或去掉前後空白後是空字串 | 請填寫結束日期 |
| 1 | `invalid_type` | 該欄位 | 值不是字串；`reason` 則是不是字串也不是 `null` | 欄位格式錯誤 |
| 1 | `employee_not_found` | `employee_id` | 不在員工表中 | 查無此員工 |
| 1 | `invalid_choice` | `leave_type` 或 `period` | 不在合法值之中 | 假別不正確 |
| 1 | `invalid_date` | `start_date` 或 `end_date` | 不符合 `^\d{4}-\d{2}-\d{2}$`，或不是存在的日期，例如 `2026-02-30` | 日期格式不正確 |
| 1 | `reason_too_long` | `reason` | 去掉前後空白後，`len` > 200 | 理由最多 200 字 |
| 2 | `end_before_start` | `end_date` | `end_date < start_date` | 結束日期不可早於開始日期 |
| 2 | `half_day_multi_day` | `period` | `period` 是 `am` 或 `pm`，但 `start_date != end_date` | 半天假只能選同一天 |
| 2 | `no_workdays` | `null` | 算出的天數是 0 | 所選期間沒有工作日 |

- 檢查順序的規則：
  - 階段 1 把所有欄位錯誤一次收集完再回傳。
  - 只有 `start_date`、`end_date`、`period` 三個欄位在階段 1 都沒有錯，才進入階段 2。
  - 階段 2 依表格順序檢查，遇到第一個錯誤就停止。
  - 階段 2 不受 `employee_id`、`leave_type`、`reason` 的錯誤影響，所以錯誤清單可能同時包含兩個階段的錯誤。
- `days` 在 JSON 中是數字，例如 `3` 或 `0.5`。測試以數值相等判斷，例如 `3 == 3.0`。

### API-04｜GET /api/employees/{employee_id}/leave-requests（FR-09）

選擇員工時，以及送出成功後呼叫。沒有副作用。

- 成功：`200`，回傳該員工的假單陣列，每筆欄位和 API-03 的成功回應相同。
- 失敗：員工不存在時回 `404`，錯誤為 `{"field": "employee_id", "code": "employee_not_found"}`。資料庫錯誤時回 `500 storage_error`。
- 讀取語意：
  - 只回傳 `employee_id` 等於路徑參數的假單。
  - 依 `id` 由大到小排序，也就是新的在前（S-04）。
  - 沒有假單時回 `200 []`。

## UI 與模組契約

### UI-01｜請假頁 `index.html`（US-01～US-03）

**載入**

1. 呼叫 API-02，填入員工下拉選單，第一項是「請選擇員工」，值為空。
2. 選擇員工後呼叫 API-04，重新繪製「我的假單」。

**表單**

- 欄位：假別下拉、開始日期與結束日期（`<input type="date">`）、時段下拉、理由（`<textarea>`）。
- 前端不做業務驗證，也不設 `maxlength`。原因是瀏覽器以 UTF-16 計數，和後端的 `len` 不一致。

**送出**

1. 按下送出後，立即把按鈕設為 `disabled`，再呼叫 API-03。
2. `201`：顯示「已送出、待審核，共 N 天」；保留所選員工，重設其他欄位；重新呼叫 API-04。
3. `422`：逐條顯示 `errors[].message`，保留全部輸入。
4. `500` 或網路錯誤：顯示「無法存檔，請稍後再試」，保留全部輸入。
5. 不論哪一種結果，在 `finally` 中恢復按鈕（FR-10）。

**列表**

- 每筆顯示日期範圍、假別、時段、天數、狀態。
- 中文對照：
  - 假別：`annual` 特休、`personal` 事假、`sick` 病假。
  - 時段：`full` 整天、`am` 上午、`pm` 下午。
  - 狀態：`pending` 待審核。
- 沒有假單時顯示「尚無假單」（S-04）。
- 所有伺服器回來的文字，包括理由與錯誤訊息，都以 `textContent` 寫入，不使用 `innerHTML`（NFR-02）。

**驗證責任分工**：伺服器負責全部規則，客戶端只負責防連點和顯示結果。

### 模組（`backend/app/`）

**`leave_days.count_leave_days(start: date, end: date, period: str) -> float`**（FR-05）

- 前提：`start <= end`；`period` 是 `am` 或 `pm` 時，`start == end`。違反前提時拋出 `ValueError`。
- `full`：回傳包含首尾、週一至週五的天數。
- `am`／`pm`：當天是工作日回 `0.5`，否則回 `0`。
- 不讀時鐘，不讀資料庫。

**`validation.validate_leave_request(payload: object, employee_ids: set[str]) -> tuple[LeaveInput | None, list[FieldError]]`**（FR-02～FR-06）

- 依 API-03 的錯誤表與順序檢查。
- 成功時回傳 `(LeaveInput, [])`，`LeaveInput` 已包含 `days`；`reason` 已去掉前後空白，空字串轉為 `None`。
- 失敗時回傳 `(None, errors)`。
- 純函式，`employee_ids` 由呼叫端從資料庫取得。
- `FieldError(field: str | None, code: str, message: str)`。
- `LeaveInput(employee_id, leave_type, start_date: date, end_date: date, period, reason: str | None, days: float)`。

**`db`**（FR-01、FR-07、FR-09）

- `connect(db_path) -> sqlite3.Connection`：設定 `row_factory = sqlite3.Row`，開啟外鍵。
- `init_db(db_path) -> None`：可重複執行，必要時建立父目錄。
- `list_employees(conn) -> list[dict]`。
- `employee_ids(conn) -> set[str]`。
- `insert_leave_request(conn, data: LeaveInput) -> dict`：在交易中執行 INSERT，`status` 交給 DEFAULT 決定，回傳新增的那一列。
- `list_leave_requests(conn, employee_id: str) -> list[dict]`。
- 所有 SQL 都用 `?` 參數，不拼接字串（NFR-02）。

**`main.create_app(db_path: str | Path | None = None, today: date | None = None) -> FastAPI`**（ADR-02）

- 資料庫路徑：參數 → 環境變數 `LEAVEBOT_DB` → `backend/data/leavebot.db`。
- 今天：參數 → `LEAVEBOT_TODAY`（`YYYY-MM-DD`，格式錯誤時啟動失敗）→ `date.today()`。解析結果存在 `app.state.today`。
- 目前沒有任何規則讀取「今天」（D-02）。保留這個接縫，是為了讓 AC-01.3 的前提「今天是 X」在測試中明確可控，也讓日後使用「今天」的規則有固定的注入點。
- lifespan 啟動時呼叫 `init_db`。
- 每個請求透過 dependency 開啟一條連線，並在 `finally` 中關閉。這可以避免 Windows 上暫存資料庫檔被鎖住、無法刪除。
- 登記順序：所有 `/api` 路由先登記，最後才 `app.mount("/", StaticFiles(directory=<static>, html=True))`。
- 模組層 `app = create_app()` 只給 uvicorn 使用。

**測試注入**（NFR-04）

- `conftest.py` 的 fixture 用 `create_app(db_path=tmp_path / "test.db", today=date(2026, 10, 28))` 建立 app，並以 `with TestClient(app) as client:` 觸發 lifespan。
- 測試不使用模組層的 `app`。
- `today` 的值依 SRS X-01 的裁決調整。

## 變更與未決

**相容性**：這是第一版，沒有既有資料或 API，不需要遷移。之後若加入其他狀態（C1），要遷移 ADR-03 的 CHECK 約束。卡 J 把理由上限改成 100 時，影響 `reason_too_long` 的條件，以及 S-04 的「`len` ≤ 200」。

**決策紀錄**（小組在 2026-10-28 確認）

| ID | 決策 | 解決的 SRS 項目 |
|---|---|---|
| S-01 | 未知欄位（包括 `status`、`days`）整筆拒絕，回 422 `unknown_field` | X-02 |
| S-02 | 422 一次回傳全部欄位錯誤，格式為 `{"errors":[{field, code, message}]}`；日期與天數規則在日期欄位都合法後才檢查 | 未決：多錯誤與錯誤碼 |
| S-03 | 初始化時建立三位虛構員工；查詢名單外員工回 404 `employee_not_found` | FR-01 名單、未決：名單外查詢 |
| S-04 | 列表新到舊；理由存去掉前後空白後的值，未填存 NULL；字數用 Python `len`，表情符號可能算 2 字以上；空狀態顯示「尚無假單」 | 未決：排序、空狀態、理由保存、字數定義 |

**未決**

- SRS X-01：測試要注入哪一天作為「今天」，由講師決定。這只影響 conftest 的值，不影響任何契約。

> 審查重點：欄位、狀態碼、錯誤及資料副作用可直接實作；前後端契約一致；FR／NFR 有落點；測試者可據此建立獨立預期。
