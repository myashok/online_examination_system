import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api";
import Layout from "../components/Layout";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }
    setLoading(true);
    try {
      await api("/api/auth/register/", { method: "POST", body: form, auth: false });
      setMessage("Account created successfully! Redirecting to sign in…");
      setTimeout(() => navigate("/login"), 1000);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <div className="auth-card-container">
        <form className="card auth-card" onSubmit={submit}>
          <div className="auth-header">
            <span className="auth-badge">Student Portal</span>
            <h1>Create Student Account</h1>
            <p className="muted">Self-register to enroll in online tests and track results</p>
          </div>
          <div className="grid">
            <label>
              Full Name
              <input
                placeholder="Jane Doe"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                required
              />
            </label>
            <label>
              Institutional Email
              <input
                type="email"
                placeholder="jane@university.edu"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                required
              />
            </label>
            <label>
              Password (min 8 characters)
              <input
                type="password"
                placeholder="Minimum 8 characters"
                value={form.password}
                onChange={(e) => set("password", e.target.value)}
                required
                minLength={8}
              />
            </label>
            {error && <p className="error" role="alert">{error}</p>}
            {message && <p className="ok" role="status">{message}</p>}
            <button className="primary" type="submit" disabled={loading}>
              {loading ? "Creating account…" : "Register Account"}
            </button>
          </div>
          <p className="auth-footer-text">
            Already registered? <Link to="/login">Sign in here</Link>
          </p>
        </form>
      </div>
    </Layout>
  );
}
