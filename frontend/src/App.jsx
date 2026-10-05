import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Register from "./pages/Register";
import { ExamRoom, ResultPage, StudentHome } from "./pages/Student";
import {
  EvaluationPage,
  ExamEditor,
  ExamForm,
  ExamList,
  FacultyReport,
  QuestionBank,
  QuestionForm,
} from "./pages/Faculty";
import { AdminAudit, AdminSummary, AdminUsers } from "./pages/Admin";

function Gate({ roles, children }) {
  const { user, ready } = useAuth();
  if (!ready) return <p className="page">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/login" replace />;
  return children;
}

function homeFor(role) {
  if (role === "ADMIN") return "/admin";
  if (role === "FACULTY") return "/faculty/exams";
  return "/student";
}

export default function App() {
  const { user, ready } = useAuth();
  const staff = ["FACULTY", "ADMIN"];
  return (
    <Routes>
      <Route path="/login" element={ready && user ? <Navigate to={homeFor(user.role)} replace /> : <Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/student" element={<Gate roles={["STUDENT"]}><StudentHome /></Gate>} />
      <Route path="/student/results" element={<Gate roles={["STUDENT"]}><StudentHome history /></Gate>} />
      <Route path="/student/results/:examId" element={<Gate roles={["STUDENT"]}><ResultPage /></Gate>} />
      <Route path="/student/attempts/:attemptId" element={<Gate roles={["STUDENT"]}><ExamRoom /></Gate>} />
      <Route path="/faculty" element={<Navigate to="/faculty/exams" replace />} />
      <Route path="/faculty/questions" element={<Gate roles={staff}><QuestionBank /></Gate>} />
      <Route path="/faculty/questions/new" element={<Gate roles={staff}><QuestionForm /></Gate>} />
      <Route path="/faculty/exams" element={<Gate roles={staff}><ExamList /></Gate>} />
      <Route path="/faculty/exams/new" element={<Gate roles={staff}><ExamForm /></Gate>} />
      <Route path="/faculty/exams/:examId" element={<Gate roles={staff}><ExamEditor /></Gate>} />
      <Route path="/faculty/evaluation" element={<Gate roles={staff}><EvaluationPage /></Gate>} />
      <Route path="/faculty/reports/:examId" element={<Gate roles={staff}><FacultyReport /></Gate>} />
      <Route path="/admin" element={<Gate roles={["ADMIN"]}><AdminSummary /></Gate>} />
      <Route path="/admin/users" element={<Gate roles={["ADMIN"]}><AdminUsers /></Gate>} />
      <Route path="/admin/audit" element={<Gate roles={["ADMIN"]}><AdminAudit /></Gate>} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
