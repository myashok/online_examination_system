import { useEffect, useState } from "react";
import { api, downloadAuth, errorMessage, money, when } from "../api";
import Layout from "../components/Layout";

export function AdminSummary() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [exportNote, setExportNote] = useState("");
  const [exporting, setExporting] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api("/api/reports/admin/summary/")
      .then(setSummary)
      .catch((err) => setError(errorMessage(err)));
  }, []);

  async function exportCsv() {
    setError("");
    setExportNote("");
    setExporting(true);
    try {
      const filename = await downloadAuth("/api/reports/admin/summary/export/", "institution-summary.csv");
      setExportNote(`Downloaded ${filename} successfully.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  const filteredExams = (summary?.exams || []).filter((exam) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return exam.title.toLowerCase().includes(q) || exam.subject.toLowerCase().includes(q);
  });

  const totalExams = summary?.exams?.length || 0;
  const passRate =
    summary && summary.published_results > 0
      ? ((summary.pass_count / summary.published_results) * 100).toFixed(1)
      : "0";

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>Institution Performance Summary</h1>
          <p className="lede">
            System-wide metrics across all academic departments, examination papers, and candidate outcomes.
          </p>
        </div>
        <button
          className="primary"
          type="button"
          onClick={exportCsv}
          disabled={exporting || !summary}
        >
          {exporting ? "Generating CSV…" : "📥 Export Institution CSV"}
        </button>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {exportNote && <p className="ok" role="status">{exportNote}</p>}

      {summary && (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Published Results</span>
              <span className="kpi-value text-primary">{summary.published_results}</span>
              <span className="kpi-sub">Across all exams</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Institutional Pass Rate</span>
              <span className="kpi-value text-success">{passRate}%</span>
              <span className="kpi-sub">{summary.pass_count} Pass · {summary.fail_count} Fail</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Average Score</span>
              <span className="kpi-value">{money(summary.average_total)}</span>
              <span className="kpi-sub">Mean student marks</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Total Exam Papers</span>
              <span className="kpi-value text-accent">{totalExams}</span>
              <span className="kpi-sub">Managed in system</span>
            </div>
          </div>

          <div className="card stack">
            <div className="between">
              <h2>Examinations Performance Breakdown</h2>
              <input
                className="search-input"
                placeholder="Search exam by title or subject…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th>Exam Title & Subject</th>
                  <th>Status</th>
                  <th>Turnout (Started / Sub)</th>
                  <th>Pass Count</th>
                  <th>Fail Count</th>
                  <th>Class Average</th>
                  <th>Score Range</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredExams.map((exam) => (
                  <tr key={exam.exam_id}>
                    <td>
                      <strong>{exam.title}</strong>
                      <div className="muted text-xs">{exam.subject}</div>
                    </td>
                    <td>
                      <span className={`badge ${exam.status === "PUBLISHED" ? "ok" : exam.status === "DRAFT" ? "warn" : ""}`}>
                        {exam.status}
                      </span>
                    </td>
                    <td>
                      {exam.started} started · {exam.submitted} submitted
                    </td>
                    <td>
                      <span className="badge ok">{exam.pass_count}</span>
                    </td>
                    <td>
                      <span className="badge bad">{exam.fail_count}</span>
                    </td>
                    <td>
                      <strong>{money(exam.average_total)}</strong>
                    </td>
                    <td>
                      {money(exam.highest)} <span className="muted">high</span> · {money(exam.lowest)} <span className="muted">low</span>
                    </td>
                    <td>
                      <a className="button small ghost" href={`/faculty/reports/${exam.exam_id}`}>
                        Full Report 📊
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredExams.length === 0 && (
              <p className="muted p-4">No exams found matching your search.</p>
            )}
          </div>
        </>
      )}
    </Layout>
  );
}

export function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "FACULTY" });

  async function load() {
    setUsers(await api("/api/users/"));
  }

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, []);

  async function create(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await api("/api/users/", { method: "POST", body: form });
      setSuccess(`Account for ${form.name} created successfully.`);
      setForm({ name: "", email: "", password: "", role: "FACULTY" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function toggle(user) {
    const actionName = user.active ? "deactivate" : "activate";
    if (!window.confirm(`Are you sure you want to ${actionName} user ${user.name}?`)) {
      return;
    }
    setError("");
    setSuccess("");
    try {
      await api(`/api/users/${user.id}/`, { method: "PATCH", body: { active: !user.active } });
      setSuccess(`User ${user.name} is now ${!user.active ? "active" : "inactive"}.`);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const filteredUsers = users.filter((user) => {
    if (roleFilter !== "ALL" && user.role !== roleFilter) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return user.name.toLowerCase().includes(q) || user.email.toLowerCase().includes(q);
  });

  const studentCount = users.filter((u) => u.role === "STUDENT").length;
  const facultyCount = users.filter((u) => u.role === "FACULTY").length;
  const adminCount = users.filter((u) => u.role === "ADMIN").length;

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>User Account Management</h1>
          <p className="lede">Manage role permissions, create faculty/admin accounts, and manage active states.</p>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {success && <p className="ok" role="status">{success}</p>}

      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">Total Users</span>
          <span className="kpi-value text-primary">{users.length}</span>
          <span className="kpi-sub">Registered in system</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Students</span>
          <span className="kpi-value">{studentCount}</span>
          <span className="kpi-sub">Self-registered candidates</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Faculty Staff</span>
          <span className="kpi-value text-accent">{facultyCount}</span>
          <span className="kpi-sub">Examiners & evaluators</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Administrators</span>
          <span className="kpi-value text-success">{adminCount}</span>
          <span className="kpi-sub">System operators</span>
        </div>
      </div>

      {/* Account Creation Form */}
      <div className="card stack">
        <h2>Provision New Staff Account</h2>
        <form className="grid user-form-grid" onSubmit={create}>
          <label>
            Full Name
            <input
              placeholder="e.g. Dr. Robert Vance"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
            />
          </label>
          <label>
            Email Address
            <input
              type="email"
              placeholder="robert@oes.local"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              required
            />
          </label>
          <label>
            Password (min 8 chars)
            <input
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              required
              minLength={8}
            />
          </label>
          <label>
            Assigned Role
            <select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
              <option value="FACULTY">Faculty</option>
              <option value="ADMIN">Administrator</option>
            </select>
          </label>
          <div className="form-submit-cell">
            <button className="primary w-full" type="submit" disabled={loading}>
              {loading ? "Creating…" : "＋ Create Account"}
            </button>
          </div>
        </form>
      </div>

      {/* Users Roster Table */}
      <div className="card stack">
        <div className="between">
          <div className="tab-bar compact">
            {[
              ["ALL", `All Users (${users.length})`],
              ["STUDENT", `Students (${studentCount})`],
              ["FACULTY", `Faculty (${facultyCount})`],
              ["ADMIN", `Admins (${adminCount})`],
            ].map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                className={`tab-btn ${roleFilter === tab ? "active" : ""}`}
                onClick={() => setRoleFilter(tab)}
              >
                {label}
              </button>
            ))}
          </div>

          <input
            className="search-input"
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>User Details</th>
              <th>Role</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.id}>
                <td>
                  <strong>{user.name}</strong>
                  <div className="muted text-xs">{user.email}</div>
                </td>
                <td>
                  <span className={`badge ${
                    user.role === "ADMIN" ? "badge-admin" :
                    user.role === "FACULTY" ? "badge-faculty" : "badge-student"
                  }`}>
                    {user.role}
                  </span>
                </td>
                <td>
                  <span className={`badge ${user.active ? "ok" : "bad"}`}>
                    {user.active ? "Active" : "Deactivated"}
                  </span>
                </td>
                <td>
                  <button
                    className={`small ${user.active ? "ghost text-danger" : "primary"}`}
                    type="button"
                    onClick={() => toggle(user)}
                  >
                    {user.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredUsers.length === 0 && (
          <p className="muted p-4">No users match the search criteria.</p>
        )}
      </div>
    </Layout>
  );
}

export function AdminAudit() {
  const [rows, setRows] = useState([]);
  const [action, setAction] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const query = action ? `?action=${action}` : "";
    api(`/api/audit-logs/${query}`).then(setRows).catch((err) => setError(errorMessage(err)));
  }, [action]);

  const filteredLogs = rows.filter((row) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (row.user_email && row.user_email.toLowerCase().includes(q)) ||
      (row.entity && row.entity.toLowerCase().includes(q)) ||
      (row.detail && row.detail.toLowerCase().includes(q))
    );
  });

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>Security & Audit Trail</h1>
          <p className="lede">
            Immutable log tracking user logins, exam attempts, responses, and evaluation publications.
          </p>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="card stack">
        <div className="between">
          <div className="row">
            <label className="filter-inline-label">
              Filter Action:
              <select value={action} onChange={(event) => setAction(event.target.value)}>
                <option value="">All Actions ({rows.length})</option>
                {["LOGIN", "START", "SAVE", "SUBMIT", "EVALUATE", "PUBLISH"].map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </label>
          </div>

          <input
            className="search-input"
            placeholder="Search audit events…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor (User)</th>
              <th>Action</th>
              <th>Target Entity</th>
              <th>Event Details</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((row) => (
              <tr key={row.id}>
                <td className="text-xs whitespace-nowrap">{when(row.at)}</td>
                <td>
                  <strong>{row.user_email || "System"}</strong>
                </td>
                <td>
                  <span className={`badge ${
                    row.action === "LOGIN" ? "badge-action-login" :
                    row.action === "START" ? "badge-action-start" :
                    row.action === "SUBMIT" ? "badge-action-submit" :
                    row.action === "PUBLISH" ? "ok" : "muted"
                  }`}>
                    {row.action}
                  </span>
                </td>
                <td>
                  <span className="badge small">{row.entity} #{row.entity_id}</span>
                </td>
                <td className="text-xs muted" style={{ maxWidth: "300px" }}>
                  {row.detail}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredLogs.length === 0 && (
          <p className="muted p-4">No audit entries found.</p>
        )}
      </div>
    </Layout>
  );
}
