import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../auth";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const home = user?.role === "ADMIN" ? "/admin" : user?.role === "FACULTY" ? "/faculty/exams" : "/student";
  
  const roleDisplay = {
    ADMIN: { label: "Administrator", badgeClass: "role-admin" },
    FACULTY: { label: "Faculty", badgeClass: "role-faculty" },
    STUDENT: { label: "Student", badgeClass: "role-student" },
  }[user?.role] || { label: user?.role || "", badgeClass: "" };

  return (
    <div className={user?.role === "STUDENT" ? "shell editorial" : "shell"}>
      <header className="topbar">
        <Link className="brand" to={user ? home : "/login"}>
          <span className="brand-icon">📝</span>
          <span>ONLINE EXAMINATION SYSTEM</span>
        </Link>
        {user && (
          <nav className="nav">
            {user.role === "STUDENT" && (
              <>
                <NavLink to="/student" end className={({ isActive }) => (isActive ? "active" : "")}>
                  Available Exams
                </NavLink>
                <NavLink to="/student/results" className={({ isActive }) => (isActive ? "active" : "")}>
                  My Results & History
                </NavLink>
              </>
            )}
            {(user.role === "FACULTY" || user.role === "ADMIN") && (
              <>
                <NavLink to="/faculty/questions" className={({ isActive }) => (isActive ? "active" : "")}>
                  Question Bank
                </NavLink>
                <NavLink to="/faculty/exams" className={({ isActive }) => (isActive ? "active" : "")}>
                  Exams
                </NavLink>
                <NavLink to="/faculty/evaluation" className={({ isActive }) => (isActive ? "active" : "")}>
                  Evaluation
                </NavLink>
              </>
            )}
            {user.role === "ADMIN" && (
              <>
                <NavLink to="/admin" end className={({ isActive }) => (isActive ? "active" : "")}>
                  Overview
                </NavLink>
                <NavLink to="/admin/users" className={({ isActive }) => (isActive ? "active" : "")}>
                  Users
                </NavLink>
                <NavLink to="/admin/audit" className={({ isActive }) => (isActive ? "active" : "")}>
                  Audit Log
                </NavLink>
              </>
            )}
            <div className="user-profile">
              <span className={`role-badge ${roleDisplay.badgeClass}`}>{roleDisplay.label}</span>
              <span className="user-name" title={user.email}>{user.name}</span>
            </div>
            <button className="linkish signout-btn" type="button" onClick={logout} title="Sign out of system">
              Sign out
            </button>
          </nav>
        )}
      </header>
      <main className="page">{children}</main>
    </div>
  );
}
