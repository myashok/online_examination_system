import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage, saveSession } from "../api";
import { useAuth } from "../auth";
import Layout from "../components/Layout";

function homeFor(role) {
  if (role === "ADMIN") return "/admin";
  if (role === "FACULTY") return "/faculty/exams";
  return "/student";
}

export default function Login() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function performLogin(loginEmail, loginPass) {
    setError("");
    setLoading(true);
    try {
      const data = await api("/api/auth/login/", {
        method: "POST",
        body: { email: loginEmail, password: loginPass },
        auth: false,
      });
      saveSession(data);
      setUser(data.user);
      navigate(homeFor(data.user.role));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    await performLogin(email, password);
  }

  function fillDemo(demoEmail, demoPass) {
    setEmail(demoEmail);
    setPassword(demoPass);
    performLogin(demoEmail, demoPass);
  }

  return (
    <Layout>
      <div className="auth-card-container">
        <form className="card auth-card" onSubmit={submit}>
          <div className="auth-header">
            <span className="auth-badge">Secure Portal</span>
            <h1>Sign in to your account</h1>
            <p className="muted">Enter your institutional credentials or use the 1-click demo accounts below</p>
          </div>

          <div className="grid">
            <label>
              Email address
              <input
                type="email"
                placeholder="name@oes.local"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="primary" type="submit" disabled={loading}>
              {loading ? "Authenticating..." : "Sign in"}
            </button>
          </div>

          <p className="auth-footer-text">
            New student? <Link to="/register">Create student account</Link>
          </p>

          <div className="demo">
            <p><strong>Quick 1-Click Demo Logins:</strong></p>
            <div className="demo-buttons">
              <button
                type="button"
                className="demo-btn student-demo"
                onClick={() => fillDemo("student@oes.local", "Student@12345")}
                disabled={loading}
              >
                🎓 Student
              </button>
              <button
                type="button"
                className="demo-btn faculty-demo"
                onClick={() => fillDemo("faculty@oes.local", "Faculty@12345")}
                disabled={loading}
              >
                👨‍🏫 Faculty
              </button>
              <button
                type="button"
                className="demo-btn admin-demo"
                onClick={() => fillDemo("admin@oes.local", "Admin@12345")}
                disabled={loading}
              >
                🛡️ Admin
              </button>
            </div>
            <div className="demo-credentials-text">
              <span>Pass for all demo accounts: <code>Student@12345</code> / <code>Faculty@12345</code> / <code>Admin@12345</code></span>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
}
