"use strict";

const LEAVE_TYPE_LABELS = { annual: "特休", personal: "事假", sick: "病假" };
const PERIOD_LABELS = { full: "整天", am: "上午", pm: "下午" };
const STATUS_LABELS = { pending: "待審核" };
const STORAGE_FAILED = "無法存檔，請稍後再試";

const employeeSelect = document.getElementById("employee");
const form = document.getElementById("leave-form");
const submitButton = document.getElementById("submit");
const messageEl = document.getElementById("message");
const errorsEl = document.getElementById("errors");
const requestsEl = document.getElementById("requests");
const emptyEl = document.getElementById("empty");

async function checkHealth() {
  const statusEl = document.getElementById("health-status");
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    if (response.ok && data.status === "ok") {
      statusEl.textContent = "已連線";
      statusEl.className = "status ok";
      return;
    }
  } catch (error) {
    // 落到下方顯示「無法連線」
  }
  statusEl.textContent = "無法連線";
  statusEl.className = "status error";
}

async function loadEmployees() {
  const response = await fetch("/api/employees");
  if (!response.ok) {
    return;
  }
  for (const employee of await response.json()) {
    const option = document.createElement("option");
    option.value = employee.id;
    option.textContent = `${employee.id} ${employee.name}`;
    employeeSelect.appendChild(option);
  }
}

async function loadRequests() {
  requestsEl.replaceChildren();
  emptyEl.hidden = true;
  const employeeId = employeeSelect.value;
  if (!employeeId) {
    return;
  }
  const response = await fetch(`/api/employees/${encodeURIComponent(employeeId)}/leave-requests`);
  if (!response.ok) {
    return;
  }
  const rows = await response.json();
  emptyEl.hidden = rows.length > 0;
  for (const row of rows) {
    requestsEl.appendChild(renderRequest(row));
  }
}

function renderRequest(row) {
  const item = document.createElement("li");
  const summary = document.createElement("div");
  // 伺服器回來的文字一律用 textContent（NFR-02）。
  summary.textContent = [
    `${row.start_date}～${row.end_date}`,
    LEAVE_TYPE_LABELS[row.leave_type] ?? row.leave_type,
    PERIOD_LABELS[row.period] ?? row.period,
    `${row.days} 天`,
    STATUS_LABELS[row.status] ?? row.status,
  ].join("｜");
  item.appendChild(summary);
  if (row.reason !== null) {
    const reason = document.createElement("div");
    reason.className = "reason";
    reason.textContent = row.reason;
    item.appendChild(reason);
  }
  return item;
}

function showMessage(text, isError) {
  messageEl.textContent = text;
  messageEl.className = isError ? "message error" : "message ok";
}

function showErrors(errors) {
  errorsEl.replaceChildren();
  for (const error of errors) {
    const item = document.createElement("li");
    item.textContent = error.message;
    errorsEl.appendChild(item);
  }
}

function collectPayload() {
  const reason = form.elements.reason.value;
  return {
    employee_id: employeeSelect.value,
    leave_type: form.elements.leave_type.value,
    start_date: form.elements.start_date.value,
    end_date: form.elements.end_date.value,
    period: form.elements.period.value,
    reason: reason === "" ? null : reason,
  };
}

async function submitRequest(event) {
  event.preventDefault();
  // 先停用按鈕再呼叫 API，防止連點（FR-10）。
  submitButton.disabled = true;
  showMessage("", false);
  showErrors([]);
  try {
    const response = await fetch("/api/leave-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });
    if (response.status === 201) {
      const created = await response.json();
      showMessage(`已送出、待審核，共 ${created.days} 天`, false);
      form.reset();
      await loadRequests();
    } else if (response.status === 422) {
      const body = await response.json();
      showErrors(body.errors);
    } else {
      showMessage(STORAGE_FAILED, true);
    }
  } catch (error) {
    showMessage(STORAGE_FAILED, true);
  } finally {
    submitButton.disabled = false;
  }
}

employeeSelect.addEventListener("change", () => {
  showMessage("", false);
  showErrors([]);
  loadRequests();
});
form.addEventListener("submit", submitRequest);

checkHealth();
loadEmployees();
