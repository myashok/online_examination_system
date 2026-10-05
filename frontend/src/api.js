const ACCESS = "oes_access";
const REFRESH = "oes_refresh";

export function errorMessage(error) {
  const data = error.data;
  if (!data) return error.message || "Request failed";
  if (typeof data.detail === "string") return data.detail;
  if (typeof data === "string") return data;
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(" ") : value}`)
    .join(" ");
}

async function raw(path, options) {
  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  const response = await fetch(path, {
    method: options.method || "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  return { response, data };
}

export async function api(path, { method = "GET", body, auth = true, retried = false } = {}) {
  const run = (token) => raw(path, { method, body, token });
  let token = auth ? localStorage.getItem(ACCESS) : null;
  let { response, data } = await run(token);
  if (response.status === 401 && auth && !retried && localStorage.getItem(REFRESH) && !path.includes("/auth/login")) {
    const refreshed = await raw("/api/auth/refresh/", {
      method: "POST",
      body: { refresh: localStorage.getItem(REFRESH) },
    });
    if (refreshed.response.ok && refreshed.data.access) {
      localStorage.setItem(ACCESS, refreshed.data.access);
      ({ response, data } = await run(refreshed.data.access));
      if (response.status === 401) retried = true;
    }
  }
  if (!response.ok) {
    const error = new Error(errorMessage({ data, message: response.statusText }));
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

export function saveSession(payload) {
  localStorage.setItem(ACCESS, payload.access);
  localStorage.setItem(REFRESH, payload.refresh);
}

export function clearSession() {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

export function hasSession() {
  return Boolean(localStorage.getItem(ACCESS));
}

export function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : "—";
}

export function when(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export async function downloadAuth(path, fallbackName) {
  const run = (token) =>
    fetch(path, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  let token = localStorage.getItem(ACCESS);
  let response = await run(token);
  if (response.status === 401 && localStorage.getItem(REFRESH)) {
    const refreshed = await raw("/api/auth/refresh/", {
      method: "POST",
      body: { refresh: localStorage.getItem(REFRESH) },
    });
    if (refreshed.response.ok && refreshed.data.access) {
      localStorage.setItem(ACCESS, refreshed.data.access);
      response = await run(refreshed.data.access);
    }
  }
  if (!response.ok) {
    let data = null;
    const text = await response.text();
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }
    const error = new Error(errorMessage({ data, message: response.statusText }));
    error.status = response.status;
    error.data = data;
    throw error;
  }
  const blob = await response.blob();
  const header = response.headers.get("Content-Disposition") || "";
  let filename = fallbackName;
  if (header) {
    const match = header.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
    if (match) {
      filename = decodeURIComponent(match[1] || match[2]).trim();
    }
  }
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.style.display = "none";
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    link.remove();
    window.URL.revokeObjectURL(url);
  }, 1000);
  return filename;
}

export function downloadCsvRows(filename, rows) {
  const csvContent = "\ufeff" + rows.map((row) =>
    row.map((cell) => {
      const str = cell === null || cell === undefined ? "" : String(cell);
      if (str.includes(",") || str.includes('"') || str.includes("\n")) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    }).join(",")
  ).join("\r\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.style.display = "none";
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    link.remove();
    window.URL.revokeObjectURL(url);
  }, 1000);
}
