import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadAuth, errorMessage, money, when } from "../api";
import Layout from "../components/Layout";

function localStamp(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function QuestionBank() {
  const [questions, setQuestions] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [previewQuestion, setPreviewQuestion] = useState(null);
  const [filters, setFilters] = useState({ q: "", subject: "", topic: "", difficulty: "", type: "", active: "" });

  function setFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  async function load(nextFilters = filters) {
    const params = new URLSearchParams();
    if (nextFilters.q.trim()) params.set("q", nextFilters.q.trim());
    if (nextFilters.subject) params.set("subject", nextFilters.subject);
    if (nextFilters.topic) params.set("topic", nextFilters.topic);
    if (nextFilters.difficulty) params.set("difficulty", nextFilters.difficulty);
    if (nextFilters.type) params.set("type", nextFilters.type);
    if (nextFilters.active) params.set("active", nextFilters.active);
    const query = params.toString();
    setQuestions(await api(`/api/questions/${query ? `?${query}` : ""}`));
  }

  useEffect(() => {
    api("/api/subjects/").then(setSubjects).catch((err) => setError(errorMessage(err)));
    api("/api/topics/").then(setTopics).catch((err) => setError(errorMessage(err)));
    load().catch((err) => setError(errorMessage(err)));
  }, []);

  async function apply(event) {
    event.preventDefault();
    setError("");
    try {
      await load(filters);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function reset() {
    const empty = { q: "", subject: "", topic: "", difficulty: "", type: "", active: "" };
    setFilters(empty);
    setError("");
    try {
      await load(empty);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function toggleActive(question) {
    setError("");
    setSuccess("");
    try {
      const endpoint = question.active ? `/api/questions/${question.id}/deactivate/` : `/api/questions/${question.id}/activate/`;
      await api(endpoint, { method: "POST" });
      setSuccess(`Question ${question.id} ${question.active ? "deactivated" : "activated"} successfully.`);
      await load(filters);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function deleteQuestion(question) {
    if (!window.confirm(`Are you sure you want to delete question #${question.id}? This action cannot be undone.`)) {
      return;
    }
    setError("");
    setSuccess("");
    try {
      await api(`/api/questions/${question.id}/`, { method: "DELETE" });
      setSuccess(`Question #${question.id} deleted successfully.`);
      await load(filters);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const mcqCount = questions.filter((q) => q.type === "MCQ").length;
  const descCount = questions.filter((q) => q.type === "DESCRIPTIVE").length;
  const activeCount = questions.filter((q) => q.active).length;

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>Question Bank</h1>
          <p className="lede">Manage reusable items, configure MCQ answer keys, and organize questions by topic.</p>
        </div>
        <Link className="button primary" to="/faculty/questions/new">
          ＋ Create New Question
        </Link>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {success && <p className="ok" role="status">{success}</p>}

      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">Total Questions</span>
          <span className="kpi-value text-primary">{questions.length}</span>
          <span className="kpi-sub">In current view</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Multiple Choice (MCQ)</span>
          <span className="kpi-value">{mcqCount}</span>
          <span className="kpi-sub">Auto-scored</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Descriptive Items</span>
          <span className="kpi-value">{descCount}</span>
          <span className="kpi-sub">Manually evaluated</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Active for Exams</span>
          <span className="kpi-value text-success">{activeCount}</span>
          <span className="kpi-sub">Available to draw</span>
        </div>
      </div>

      <form className="card toolbar question-toolbar" onSubmit={apply}>
        <label>
          Search Keyword
          <input
            value={filters.q}
            onChange={(event) => setFilter("q", event.target.value)}
            placeholder="Search question text…"
          />
        </label>
        <label>
          Subject
          <select value={filters.subject} onChange={(event) => setFilter("subject", event.target.value)}>
            <option value="">All subjects</option>
            {subjects.map((sub) => (
              <option key={sub.id} value={sub.id}>{sub.name}</option>
            ))}
          </select>
        </label>
        <label>
          Topic
          <select value={filters.topic} onChange={(event) => setFilter("topic", event.target.value)}>
            <option value="">All topics</option>
            {topics
              .filter((t) => !filters.subject || String(t.subject) === String(filters.subject))
              .map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.subject_name ? `${topic.subject_name} · ${topic.name}` : topic.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Difficulty
          <select value={filters.difficulty} onChange={(event) => setFilter("difficulty", event.target.value)}>
            <option value="">All</option>
            <option value="EASY">Easy</option>
            <option value="MEDIUM">Medium</option>
            <option value="HARD">Hard</option>
          </select>
        </label>
        <label>
          Type
          <select value={filters.type} onChange={(event) => setFilter("type", event.target.value)}>
            <option value="">All</option>
            <option value="MCQ">MCQ</option>
            <option value="DESCRIPTIVE">Descriptive</option>
          </select>
        </label>
        <div className="row toolbar-actions">
          <button className="primary" type="submit">Filter</button>
          <button className="ghost" type="button" onClick={reset}>Reset</button>
        </div>
      </form>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Question Prompt</th>
              <th>Type</th>
              <th>Topic & Subject</th>
              <th>Difficulty</th>
              <th>Marks</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {questions.map((question) => (
              <tr key={question.id}>
                <td style={{ maxWidth: "340px" }}>
                  <strong>{question.text}</strong>
                  {question.explanation && (
                    <div className="muted text-xs truncate">💡 {question.explanation}</div>
                  )}
                </td>
                <td>
                  <span className={`badge ${question.type === "MCQ" ? "badge-mcq" : "badge-desc"}`}>
                    {question.type}
                  </span>
                </td>
                <td>
                  <div>{question.topic_name}</div>
                  <div className="muted text-xs">{question.subject_name}</div>
                </td>
                <td>
                  <span className={`badge ${
                    question.difficulty === "EASY" ? "ok" :
                    question.difficulty === "MEDIUM" ? "warn" : "bad"
                  }`}>
                    {question.difficulty}
                  </span>
                </td>
                <td>{question.marks}</td>
                <td>
                  <span className={`badge ${question.active ? "ok" : "muted"}`}>
                    {question.active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <div className="row table-action-btns">
                    <button
                      className="ghost small"
                      type="button"
                      onClick={() => setPreviewQuestion(question)}
                      title="Preview question and answer key"
                    >
                      👁 View
                    </button>
                    <button
                      className="ghost small"
                      type="button"
                      onClick={() => toggleActive(question)}
                      title={question.active ? "Deactivate from exams" : "Activate for exams"}
                    >
                      {question.active ? "Deactivate" : "Activate"}
                    </button>
                    <button
                      className="ghost small text-danger"
                      type="button"
                      onClick={() => deleteQuestion(question)}
                      title="Delete question"
                    >
                      🗑
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {questions.length === 0 && (
          <div className="empty-state p-6">
            <p className="muted">No questions match the current criteria.</p>
          </div>
        )}
      </div>

      {/* Question Preview Modal */}
      {previewQuestion && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h2>Question Details #{previewQuestion.id}</h2>
              <button className="linkish modal-close" type="button" onClick={() => setPreviewQuestion(null)}>✕</button>
            </div>
            <div className="modal-body stack">
              <div className="between">
                <span className="badge">{previewQuestion.subject_name} · {previewQuestion.topic_name}</span>
                <span className="badge">{previewQuestion.type} · {previewQuestion.difficulty} · {previewQuestion.marks} marks</span>
              </div>

              <h3>{previewQuestion.text}</h3>

              {previewQuestion.type === "MCQ" ? (
                <div className="preview-options stack">
                  <h4>Answer Options:</h4>
                  {previewQuestion.options?.map((opt, i) => (
                    <div
                      key={opt.id || i}
                      className={`preview-option-item ${opt.is_correct ? "correct" : ""}`}
                    >
                      <span className="option-indicator">{opt.is_correct ? "✓" : "○"}</span>
                      <span>{opt.option_text}</span>
                      {opt.is_correct && <span className="tag-correct">Correct Option</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="notice-banner info">
                  📝 <strong>Descriptive Item:</strong> Requires manual score assignment by faculty during evaluation.
                </div>
              )}

              {previewQuestion.explanation && (
                <div className="explanation-callout">
                  <strong>Explanation & Rubric:</strong> {previewQuestion.explanation}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="primary" type="button" onClick={() => setPreviewQuestion(null)}>
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

export function QuestionForm() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    subject: "",
    topic: "",
    type: "MCQ",
    text: "",
    difficulty: "EASY",
    marks: "2.00",
    explanation: "",
    options: ["", "", "", ""],
    correct: 0,
  });

  useEffect(() => {
    api("/api/subjects/").then(setSubjects).catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(() => {
    if (!form.subject) return;
    api(`/api/topics/?subject=${form.subject}`).then(setTopics).catch((err) => setError(errorMessage(err)));
  }, [form.subject]);

  function set(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");

    if (form.type === "MCQ") {
      const emptyOption = form.options.some((opt) => !opt.trim());
      if (emptyOption) {
        setError("All 4 MCQ options must be filled.");
        return;
      }
    }

    setLoading(true);
    const payload = {
      subject: Number(form.subject),
      topic: Number(form.topic),
      type: form.type,
      text: form.text,
      difficulty: form.difficulty,
      marks: form.marks,
      explanation: form.explanation,
    };
    if (form.type === "MCQ") {
      payload.options = form.options.map((option, index) => ({
        option_text: option,
        is_correct: index === Number(form.correct),
      }));
    }
    try {
      await api("/api/questions/", { method: "POST", body: payload });
      navigate("/faculty/questions");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>Create Question</h1>
          <p className="lede">Define question stem, difficulty level, marks weight, and answer keys.</p>
        </div>
        <Link className="button ghost" to="/faculty/questions">← Back to Question Bank</Link>
      </div>

      <form className="card stack" onSubmit={submit}>
        {error && <p className="error" role="alert">{error}</p>}

        <div className="grid">
          <label>
            Academic Subject
            <select value={form.subject} onChange={(event) => set("subject", event.target.value)} required>
              <option value="">Select Subject</option>
              {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
            </select>
          </label>
          <label>
            Topic Module
            <select value={form.topic} onChange={(event) => set("topic", event.target.value)} required disabled={!form.subject}>
              <option value="">{form.subject ? "Select Topic" : "Choose subject first"}</option>
              {topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.name}</option>)}
            </select>
          </label>
          <label>
            Question Type
            <select value={form.type} onChange={(event) => set("type", event.target.value)}>
              <option value="MCQ">Multiple Choice Question (MCQ)</option>
              <option value="DESCRIPTIVE">Descriptive / Essay</option>
            </select>
          </label>
        </div>

        <label>
          Question Prompt
          <textarea
            placeholder="Enter the full question text here…"
            value={form.text}
            onChange={(event) => set("text", event.target.value)}
            required
            rows={3}
          />
        </label>

        <div className="grid">
          <label>
            Difficulty Level
            <select value={form.difficulty} onChange={(event) => set("difficulty", event.target.value)}>
              <option value="EASY">Easy</option>
              <option value="MEDIUM">Medium</option>
              <option value="HARD">Hard</option>
            </select>
          </label>
          <label>
            Marks Awarded
            <input
              type="text"
              value={form.marks}
              onChange={(event) => set("marks", event.target.value)}
              placeholder="e.g. 2.00"
              required
            />
          </label>
        </div>

        {form.type === "MCQ" && (
          <div className="mcq-options-builder card stack">
            <h3>MCQ Options & Answer Key</h3>
            <p className="muted">Enter all 4 options and mark exactly one radio button as the correct answer.</p>
            {form.options.map((option, index) => (
              <div key={index} className="option-input-row">
                <input
                  type="radio"
                  name="correct_choice"
                  checked={Number(form.correct) === index}
                  onChange={() => set("correct", index)}
                  title="Mark this option as correct"
                />
                <input
                  className="flex-1"
                  placeholder={`Option ${index + 1}`}
                  value={option}
                  onChange={(event) => {
                    const options = [...form.options];
                    options[index] = event.target.value;
                    set("options", options);
                  }}
                  required
                />
                <span className={Number(form.correct) === index ? "badge ok" : "badge"}>
                  {Number(form.correct) === index ? "✓ Correct Key" : "Distractor"}
                </span>
              </div>
            ))}
          </div>
        )}

        <label>
          Explanation / Solution Notes (Optional)
          <textarea
            placeholder="Explanation shown to students after results are published…"
            value={form.explanation}
            onChange={(event) => set("explanation", event.target.value)}
            rows={2}
          />
        </label>

        <div className="row">
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Saving Question…" : "Save Question to Bank"}
          </button>
          <Link className="button ghost" to="/faculty/questions">Cancel</Link>
        </div>
      </form>
    </Layout>
  );
}

export function ExamList() {
  const [exams, setExams] = useState([]);
  const [error, setError] = useState("");
  const [filterTab, setFilterTab] = useState("ALL");

  useEffect(() => {
    api("/api/exams/").then(setExams).catch((err) => setError(errorMessage(err)));
  }, []);

  const draftCount = exams.filter((e) => e.status === "DRAFT").length;
  const publishedCount = exams.filter((e) => e.status === "PUBLISHED").length;
  const closedCount = exams.filter((e) => e.status === "CLOSED").length;

  const filteredExams = exams.filter((exam) => {
    if (filterTab === "DRAFT") return exam.status === "DRAFT";
    if (filterTab === "PUBLISHED") return exam.status === "PUBLISHED";
    if (filterTab === "CLOSED") return exam.status === "CLOSED";
    return true;
  });

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>Examination Management</h1>
          <p className="lede">Draft examination papers, draw questions, publish windows, and monitor performance.</p>
        </div>
        <Link className="button primary" to="/faculty/exams/new">
          ＋ Create New Exam
        </Link>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">Total Exams</span>
          <span className="kpi-value text-primary">{exams.length}</span>
          <span className="kpi-sub">All lifecycles</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Draft Papers</span>
          <span className="kpi-value text-muted">{draftCount}</span>
          <span className="kpi-sub">Editing questions</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Published (Live)</span>
          <span className="kpi-value text-success">{publishedCount}</span>
          <span className="kpi-sub">Open for attempts</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Closed Exams</span>
          <span className="kpi-value text-accent">{closedCount}</span>
          <span className="kpi-sub">Evaluation complete</span>
        </div>
      </div>

      <div className="tab-bar">
        {[
          ["ALL", `All Exams (${exams.length})`],
          ["DRAFT", `Drafts (${draftCount})`],
          ["PUBLISHED", `Live / Published (${publishedCount})`],
          ["CLOSED", `Closed (${closedCount})`],
        ].map(([tab, label]) => (
          <button
            key={tab}
            type="button"
            className={`tab-btn ${filterTab === tab ? "active" : ""}`}
            onClick={() => setFilterTab(tab)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid">
        {filteredExams.map((exam) => (
          <article className="card exam-card" key={exam.id}>
            <div className="between">
              <span className="badge">{exam.subject_name}</span>
              <span className={`badge ${
                exam.status === "PUBLISHED" ? "ok" :
                exam.status === "DRAFT" ? "warn" : ""
              }`}>
                {exam.status}
              </span>
            </div>
            <h2>{exam.title}</h2>
            <div className="exam-meta-pills">
              <span>⏱ {exam.duration_minutes} min duration</span>
              <span>❓ {exam.question_count} questions</span>
              <span>🎯 {exam.total_marks} marks</span>
              <span>✅ Pass: {exam.pass_marks}</span>
            </div>

            <div className="exam-window-box">
              <div className="text-xs muted">
                <strong>Window:</strong> {when(exam.start_at)} → {when(exam.end_at)}
              </div>
            </div>

            <div className="row exam-actions">
              <Link className="button primary flex-1" to={`/faculty/exams/${exam.id}`}>
                {exam.status === "DRAFT" ? "Edit Paper ✏️" : "Manage Exam ⚙️"}
              </Link>
              <Link className="button ghost" to={`/faculty/reports/${exam.id}`} title="View performance report">
                Analytics 📊
              </Link>
            </div>
          </article>
        ))}
        {filteredExams.length === 0 && (
          <div className="card empty-state">
            <p>No exams found in this category.</p>
          </div>
        )}
      </div>
    </Layout>
  );
}

export function ExamForm() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const start = new Date();
  const end = new Date(start.getTime() + 4 * 60 * 60 * 1000); // 4 hours window by default

  const [form, setForm] = useState({
    subject: "",
    title: "",
    instructions: "One attempt per candidate. Server clock is strictly enforced. Answers save automatically.",
    start_at: localStamp(start),
    end_at: localStamp(end),
    duration_minutes: 30,
    pass_marks: "4.00",
    negative_mark: "0.50",
  });

  useEffect(() => {
    api("/api/subjects/").then(setSubjects).catch((err) => setError(errorMessage(err)));
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");

    const startTime = new Date(form.start_at).getTime();
    const endTime = new Date(form.end_at).getTime();
    if (endTime <= startTime) {
      setError("Exam closing time must be after opening time.");
      return;
    }

    setLoading(true);
    try {
      const created = await api("/api/exams/", {
        method: "POST",
        body: {
          ...form,
          subject: Number(form.subject),
          duration_minutes: Number(form.duration_minutes),
          start_at: new Date(form.start_at).toISOString(),
          end_at: new Date(form.end_at).toISOString(),
        },
      });
      navigate(`/faculty/exams/${created.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>Create New Exam</h1>
          <p className="lede">Set up the examination schedule, time limit, and passing thresholds.</p>
        </div>
        <Link className="button ghost" to="/faculty/exams">← Back to Exams</Link>
      </div>

      <form className="card stack" onSubmit={submit}>
        {error && <p className="error" role="alert">{error}</p>}

        <div className="grid">
          <label>
            Subject
            <select
              value={form.subject}
              onChange={(event) => setForm({ ...form, subject: event.target.value })}
              required
            >
              <option value="">Select Subject</option>
              {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
            </select>
          </label>
          <label>
            Exam Title
            <input
              placeholder="e.g. Operating Systems Midterm"
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              required
            />
          </label>
        </div>

        <label>
          Candidate Instructions
          <textarea
            value={form.instructions}
            onChange={(event) => setForm({ ...form, instructions: event.target.value })}
            rows={2}
          />
        </label>

        <div className="grid">
          <label>
            Opens At (Start Window)
            <input
              type="datetime-local"
              value={form.start_at}
              onChange={(event) => setForm({ ...form, start_at: event.target.value })}
              required
            />
          </label>
          <label>
            Closes At (End Window)
            <input
              type="datetime-local"
              value={form.end_at}
              onChange={(event) => setForm({ ...form, end_at: event.target.value })}
              required
            />
          </label>
          <label>
            Attempt Duration (Minutes)
            <input
              type="number"
              min="1"
              value={form.duration_minutes}
              onChange={(event) => setForm({ ...form, duration_minutes: event.target.value })}
              required
            />
          </label>
          <label>
            Pass Marks
            <input
              value={form.pass_marks}
              onChange={(event) => setForm({ ...form, pass_marks: event.target.value })}
              required
            />
          </label>
          <label>
            Negative Mark (Per Incorrect MCQ)
            <input
              value={form.negative_mark}
              onChange={(event) => setForm({ ...form, negative_mark: event.target.value })}
              required
            />
          </label>
        </div>

        <div className="row">
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Creating Draft…" : "Create Draft Exam Paper"}
          </button>
          <Link className="button ghost" to="/faculty/exams">Cancel</Link>
        </div>
      </form>
    </Layout>
  );
}

export function ExamEditor() {
  const { examId } = useParams();
  const [exam, setExam] = useState(null);
  const [bank, setBank] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [draw, setDraw] = useState({ easy: 1, medium: 1, hard: 0, descriptive: 0 });
  const [loadingAction, setLoadingAction] = useState(false);

  async function load() {
    const data = await api(`/api/exams/${examId}/`);
    setExam(data);
    const bankItems = await api(`/api/questions/?subject=${data.subject}&active=true`);
    setBank(bankItems);
  }

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [examId]);

  async function act(path, body = {}) {
    setError("");
    setSuccess("");
    setLoadingAction(true);
    try {
      await api(path, { method: "POST", body });
      await load();
      setSuccess("Exam paper updated successfully.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingAction(false);
    }
  }

  async function removeQuestion(questionId) {
    setError("");
    setSuccess("");
    setLoadingAction(true);
    try {
      await api(`/api/exams/${exam.id}/questions/${questionId}/`, { method: "DELETE" });
      await load();
      setSuccess("Question removed from paper.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingAction(false);
    }
  }

  if (!exam) {
    return (
      <Layout>
        {error ? <p className="error">{error}</p> : <p className="muted">Loading exam paper…</p>}
      </Layout>
    );
  }

  const onPaper = new Set((exam.questions || []).map((question) => question.id));
  const availableBank = bank.filter((question) => !onPaper.has(question.id));

  // Count bank question availability for draw
  const easyAvailable = bank.filter((q) => q.type === "MCQ" && q.difficulty === "EASY").length;
  const mediumAvailable = bank.filter((q) => q.type === "MCQ" && q.difficulty === "MEDIUM").length;
  const hardAvailable = bank.filter((q) => q.type === "MCQ" && q.difficulty === "HARD").length;
  const descAvailable = bank.filter((q) => q.type === "DESCRIPTIVE").length;

  return (
    <Layout>
      <div className="between">
        <div>
          <div className="row">
            <span className="badge">{exam.subject_name}</span>
            <span className={`badge ${exam.status === "PUBLISHED" ? "ok" : exam.status === "DRAFT" ? "warn" : ""}`}>
              {exam.status}
            </span>
          </div>
          <h1>{exam.title}</h1>
          <p className="lede">
            Window: {when(exam.start_at)} → {when(exam.end_at)} · Duration: {exam.duration_minutes} min
          </p>
        </div>
        <div className="row">
          <Link className="button ghost" to={`/faculty/reports/${exam.id}`}>
            View Performance Report 📊
          </Link>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {success && <p className="ok" role="status">{success}</p>}

      {/* Lifecycle Status Banner */}
      <div className={`status-banner ${exam.status.toLowerCase()}`}>
        {exam.status === "DRAFT" && (
          <div>
            <strong>Draft Paper:</strong> Add or remove questions below. When ready, click "Publish Exam" to make it available to students during the scheduled window.
          </div>
        )}
        {exam.status === "PUBLISHED" && (
          <div>
            <strong>Published & Live:</strong> Students can take the test within the window. If no attempts have started, you can unpublish to return to draft.
          </div>
        )}
        {exam.status === "CLOSED" && (
          <div>
            <strong>Closed:</strong> No further attempts are accepted. Candidate submissions can be evaluated and published.
          </div>
        )}
      </div>

      <div className="split">
        {/* Paper Section */}
        <section className="card stack">
          <div className="between">
            <h2>Current Paper Questions ({exam.questions?.length || 0})</h2>
            <div className="paper-summary-badge">
              Total: <strong>{exam.total_marks} Marks</strong> (Pass: {exam.pass_marks})
            </div>
          </div>

          <div className="paper-questions-list stack">
            {(exam.questions || []).map((question, qIdx) => (
              <div className="card paper-q-item" key={question.id}>
                <div className="between">
                  <span className="badge">Q{qIdx + 1} · {question.type} · {question.difficulty} · {question.marks} marks</span>
                  {exam.status === "DRAFT" && (
                    <button
                      className="linkish text-danger small"
                      type="button"
                      onClick={() => removeQuestion(question.id)}
                      disabled={loadingAction}
                      title="Remove question from paper"
                    >
                      ✕ Remove
                    </button>
                  )}
                </div>
                <p className="q-item-text">{question.text}</p>
                {question.type === "MCQ" && (
                  <div className="q-item-options text-xs muted">
                    {question.options?.map((opt) => (
                      <span key={opt.id} className={opt.is_correct ? "correct-opt-text" : ""}>
                        {opt.is_correct ? "✓ " : "• "}{opt.option_text}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {(!exam.questions || exam.questions.length === 0) && (
              <div className="empty-state p-6">
                <p className="muted">No questions on this paper yet. Add questions from the bank or use rule-based draw.</p>
              </div>
            )}
          </div>

          <div className="lifecycle-actions-box">
            {exam.status === "DRAFT" && (
              <button
                className="primary w-full"
                type="button"
                onClick={() => act(`/api/exams/${exam.id}/publish/`)}
                disabled={loadingAction || !exam.questions || exam.questions.length === 0}
              >
                Publish Exam Now →
              </button>
            )}
            {exam.status === "PUBLISHED" && (
              <div className="row w-full">
                <button
                  className="ghost flex-1"
                  type="button"
                  onClick={() => act(`/api/exams/${exam.id}/unpublish/`)}
                  disabled={loadingAction}
                  title="Return to draft if no attempts have started"
                >
                  Unpublish to Draft
                </button>
                <button
                  className="danger flex-1"
                  type="button"
                  onClick={() => act(`/api/exams/${exam.id}/close/`)}
                  disabled={loadingAction}
                >
                  Close Exam
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Bank & Draw Controls (Enabled in Draft Mode) */}
        {exam.status === "DRAFT" ? (
          <section className="card stack">
            <h2>Add Questions to Paper</h2>

            {/* Rule-based Draw */}
            <div className="draw-box card">
              <h3>⚡ Rule-based Auto Draw</h3>
              <p className="muted text-xs">
                Automatically draw random questions matching subject and difficulty constraints from the bank.
              </p>
              <div className="grid draw-inputs-grid">
                <label>
                  Easy MCQ <span className="text-xs muted">({easyAvailable} in bank)</span>
                  <input
                    type="number"
                    min="0"
                    max={easyAvailable}
                    value={draw.easy}
                    onChange={(e) => setDraw({ ...draw, easy: Number(e.target.value) })}
                  />
                </label>
                <label>
                  Medium MCQ <span className="text-xs muted">({mediumAvailable} in bank)</span>
                  <input
                    type="number"
                    min="0"
                    max={mediumAvailable}
                    value={draw.medium}
                    onChange={(e) => setDraw({ ...draw, medium: Number(e.target.value) })}
                  />
                </label>
                <label>
                  Hard MCQ <span className="text-xs muted">({hardAvailable} in bank)</span>
                  <input
                    type="number"
                    min="0"
                    max={hardAvailable}
                    value={draw.hard}
                    onChange={(e) => setDraw({ ...draw, hard: Number(e.target.value) })}
                  />
                </label>
                <label>
                  Descriptive <span className="text-xs muted">({descAvailable} in bank)</span>
                  <input
                    type="number"
                    min="0"
                    max={descAvailable}
                    value={draw.descriptive}
                    onChange={(e) => setDraw({ ...draw, descriptive: Number(e.target.value) })}
                  />
                </label>
              </div>
              <button
                className="primary w-full"
                type="button"
                onClick={() => act(`/api/exams/${exam.id}/draw/`, { ...draw, replace: true })}
                disabled={loadingAction}
              >
                Execute Draw (Replace Paper)
              </button>
            </div>

            {/* Manual Bank Add */}
            <div className="manual-add-section stack">
              <h3>Add Individual Questions</h3>
              <div className="bank-items-scroll">
                {availableBank.map((question) => (
                  <div className="card between bank-item-row" key={question.id}>
                    <div className="bank-item-info">
                      <span className="badge small">{question.type} · {question.difficulty} · {question.marks}m</span>
                      <p className="bank-item-text">{question.text}</p>
                    </div>
                    <button
                      className="primary small"
                      type="button"
                      onClick={() => act(`/api/exams/${exam.id}/questions/`, { question_id: question.id })}
                      disabled={loadingAction}
                    >
                      ＋ Add
                    </button>
                  </div>
                ))}
                {availableBank.length === 0 && (
                  <p className="muted text-xs">All active bank questions for this subject are already on the paper.</p>
                )}
              </div>
            </div>
          </section>
        ) : (
          <section className="card stack">
            <h2>Exam Status</h2>
            <div className="notice-banner info">
              Paper structure is locked while exam is {exam.status}. To modify questions, the exam must be unpublished first.
            </div>
          </section>
        )}
      </div>
    </Layout>
  );
}

export function EvaluationPage() {
  const [queue, setQueue] = useState({ needs_marking: [], ready_to_publish: [] });
  const [selected, setSelected] = useState(null);
  const [marks, setMarks] = useState({});
  const [activeTab, setActiveTab] = useState("NEEDS_MARKING");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    setQueue(await api("/api/evaluation/queue/"));
  }

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, []);

  async function open(attemptId) {
    setError("");
    setSuccess("");
    try {
      const detail = await api(`/api/evaluation/attempts/${attemptId}/`);
      setSelected(detail);
      const next = {};
      detail.questions.filter((question) => question.type === "DESCRIPTIVE").forEach((question) => {
        next[question.question_id] = question.awarded_marks ?? "";
      });
      setMarks(next);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function score() {
    const payload = Object.entries(marks)
      .filter(([, value]) => value !== "")
      .map(([questionId, awarded]) => ({ question_id: Number(questionId), awarded_marks: awarded }));
    if (!payload.length) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await api(`/api/evaluation/attempts/${selected.id}/marks/`, { method: "POST", body: { marks: payload } });
      setSuccess("Descriptive marks saved successfully.");
      await open(selected.id);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function publish(resultId) {
    setError("");
    setSuccess("");
    try {
      await api(`/api/results/${resultId}/publish/`, { method: "POST" });
      setSuccess("Result published to student successfully!");
      setSelected(null);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <Layout>
      <div className="between">
        <div>
          <h1>Evaluation Queue</h1>
          <p className="lede">Grade descriptive answers, review automated MCQ scoring, and publish official results.</p>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {success && <p className="ok" role="status">{success}</p>}

      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">Needs Marking</span>
          <span className="kpi-value text-accent">{queue.needs_marking?.length || 0}</span>
          <span className="kpi-sub">Descriptive items pending</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Ready to Publish</span>
          <span className="kpi-value text-success">{queue.ready_to_publish?.length || 0}</span>
          <span className="kpi-sub">Scorecard calculated</span>
        </div>
      </div>

      <div className="split">
        {/* Left Queue Panel */}
        <aside className="card stack">
          <div className="tab-bar compact">
            <button
              className={`tab-btn ${activeTab === "NEEDS_MARKING" ? "active" : ""}`}
              onClick={() => setActiveTab("NEEDS_MARKING")}
            >
              Needs Marking ({queue.needs_marking?.length || 0})
            </button>
            <button
              className={`tab-btn ${activeTab === "READY" ? "active" : ""}`}
              onClick={() => setActiveTab("READY")}
            >
              Ready to Publish ({queue.ready_to_publish?.length || 0})
            </button>
          </div>

          {activeTab === "NEEDS_MARKING" && (
            <div className="queue-list stack">
              {queue.needs_marking?.map((item) => (
                <button
                  key={item.attempt_id}
                  className={`ghost queue-item-btn ${selected?.id === item.attempt_id ? "selected-queue" : ""}`}
                  onClick={() => open(item.attempt_id)}
                >
                  <div className="queue-item-name">{item.student}</div>
                  <div className="queue-item-meta">{item.exam_title}</div>
                </button>
              ))}
              {(!queue.needs_marking || queue.needs_marking.length === 0) && (
                <p className="muted p-4">No submissions awaiting grading.</p>
              )}
            </div>
          )}

          {activeTab === "READY" && (
            <div className="queue-list stack">
              {queue.ready_to_publish?.map((item) => (
                <div key={item.result_id} className="card queue-publish-card">
                  <div>
                    <strong>{item.student}</strong>
                    <div className="muted text-xs">Total Score: {item.total_marks}</div>
                  </div>
                  <div className="row">
                    <button className="ghost small" onClick={() => open(item.attempt_id)}>Review</button>
                    <button className="primary small" onClick={() => publish(item.result_id)}>Publish</button>
                  </div>
                </div>
              ))}
              {(!queue.ready_to_publish || queue.ready_to_publish.length === 0) && (
                <p className="muted p-4">No results pending publication.</p>
              )}
            </div>
          )}
        </aside>

        {/* Right Candidate Review & Grading Panel */}
        <section className="card stack">
          {!selected ? (
            <div className="empty-state p-8">
              <span className="empty-icon">👈</span>
              <h3>Select a candidate submission</h3>
              <p className="muted">Choose an attempt from the left queue to grade descriptive responses.</p>
            </div>
          ) : (
            <>
              <div className="between evaluation-header">
                <div>
                  <span className="badge">Candidate Attempt #{selected.id}</span>
                  <h2>{selected.student.name}</h2>
                  <p className="muted">{selected.student.email} · Submitted: {when(selected.submitted_at)}</p>
                </div>
                {selected.result && (
                  <div className="evaluation-result-badge">
                    <span className={`badge big ${selected.result.published ? "ok" : "warn"}`}>
                      {selected.result.published ? "Published" : "Unpublished Result"}
                    </span>
                    <div className="text-xs muted mt-1">Score: {selected.result.total_marks} / {selected.result.max_marks}</div>
                  </div>
                )}
              </div>

              <div className="evaluation-questions stack">
                {selected.questions.map((question, qIdx) => (
                  <div className="card eval-q-card" key={question.question_id}>
                    <div className="between">
                      <span className="badge">
                        Q{qIdx + 1} · {question.type} · Max {question.marks} marks
                      </span>
                      {question.type === "MCQ" ? (
                        <span className="badge ok">
                          Auto-scored: {question.awarded_marks} / {question.marks}
                        </span>
                      ) : (
                        <span className="badge warn">Descriptive</span>
                      )}
                    </div>

                    <h4 className="eval-q-text">{question.text}</h4>

                    {question.type === "MCQ" ? (
                      <p className="muted text-xs">
                        Student selected: <strong>{question.selected_option_id || "Unanswered"}</strong> · Score awarded: {question.awarded_marks}
                      </p>
                    ) : (
                      <div className="stack">
                        <div className="student-response-box">
                          <span className="text-xs text-muted">Candidate Response:</span>
                          <p>{question.descriptive_text || <span className="muted italic">No response submitted</span>}</p>
                        </div>
                        <div className="grade-input-box">
                          <label>
                            Award Marks (0.00 to {question.marks})
                            <input
                              type="number"
                              step="0.5"
                              min="0"
                              max={question.marks}
                              value={marks[question.question_id] ?? ""}
                              onChange={(event) => setMarks({ ...marks, [question.question_id]: event.target.value })}
                            />
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="row evaluation-action-bar">
                <button className="primary" type="button" onClick={score} disabled={saving}>
                  {saving ? "Saving Marks…" : "Save Descriptive Marks"}
                </button>
                {selected.result && !selected.result.published && (
                  <button className="button ok-btn" type="button" onClick={() => publish(selected.result.id)}>
                    Publish Official Result
                  </button>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </Layout>
  );
}

export function FacultyReport() {
  const { examId } = useParams();
  const [report, setReport] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [candidateFilter, setCandidateFilter] = useState("");
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportNote, setExportNote] = useState("");

  useEffect(() => {
    Promise.all([
      api(`/api/reports/faculty/exams/${examId}/`),
      api(`/api/reports/faculty/exams/${examId}/analysis/`),
    ])
      .then(([summary, rows]) => {
        setReport(summary);
        setAnalysis(rows);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [examId]);

  async function exportCsv() {
    setError("");
    setExportNote("");
    setExporting(true);
    try {
      const filename = await downloadAuth(
        `/api/reports/faculty/exams/${examId}/export/`,
        `exam-${examId}-report.csv`
      );
      setExportNote(`Downloaded ${filename} successfully.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  const filteredCandidates = (report?.candidates || []).filter((cand) => {
    if (!candidateFilter.trim()) return true;
    const query = candidateFilter.toLowerCase();
    return (
      cand.student_name.toLowerCase().includes(query) ||
      cand.student_email.toLowerCase().includes(query)
    );
  });

  return (
    <Layout>
      <div className="between">
        <div>
          <div className="row">
            <span className="badge">{report?.subject || "Subject"}</span>
            <span className="badge">{report?.status || "Status"}</span>
          </div>
          <h1>{report?.title || "Exam Performance Report"}</h1>
          <p className="lede">
            Passing mark: {report?.pass_marks} · Comprehensive candidate roster and topic breakdown.
          </p>
        </div>
        <div className="row">
          <Link className="button ghost" to={`/faculty/exams/${examId}`}>
            ← Exam Settings
          </Link>
          <button
            className="primary"
            type="button"
            onClick={exportCsv}
            disabled={exporting || !report}
          >
            {exporting ? "Generating CSV…" : "📥 Export CSV Report"}
          </button>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {exportNote && <p className="ok" role="status">{exportNote}</p>}

      {report && (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Participation</span>
              <span className="kpi-value text-primary">
                {report.submitted} <span className="metric-denom">/ {report.registered_students}</span>
              </span>
              <span className="kpi-sub">
                {report.participation_rate ? `${(Number(report.participation_rate) * 100).toFixed(1)}% Turnout` : "—"}
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Pass / Fail Ratio</span>
              <span className="kpi-value text-success">
                {report.pass_count} <span className="metric-denom">Pass</span> · {report.fail_count} <span className="metric-denom">Fail</span>
              </span>
              <span className="kpi-sub">
                {report.published > 0
                  ? `${((report.pass_count / (report.published || 1)) * 100).toFixed(1)}% Pass Rate`
                  : "No published results"}
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Class Average</span>
              <span className="kpi-value">{money(report.average_total)}</span>
              <span className="kpi-sub">Out of passing {report.pass_marks}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Highest / Lowest</span>
              <span className="kpi-value text-accent">
                {money(report.highest)} <span className="metric-denom">/ {money(report.lowest)}</span>
              </span>
              <span className="kpi-sub">Score range</span>
            </div>
          </div>

          {/* Candidate Results Table */}
          <div className="card stack">
            <div className="between">
              <h2>Candidate Roster ({report.candidates?.length || 0})</h2>
              <input
                className="search-input"
                placeholder="Filter candidate by name or email…"
                value={candidateFilter}
                onChange={(e) => setCandidateFilter(e.target.value)}
              />
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Attempt Status</th>
                  <th>Objective</th>
                  <th>Descriptive</th>
                  <th>Total Score</th>
                  <th>Result</th>
                  <th>Published</th>
                </tr>
              </thead>
              <tbody>
                {filteredCandidates.map((row) => (
                  <tr key={row.attempt_id}>
                    <td>
                      <strong>{row.student_name}</strong>
                      <div className="muted text-xs">{row.student_email}</div>
                    </td>
                    <td>
                      <span className={`badge ${row.attempt_status === "SUBMITTED" ? "warn" : row.attempt_status === "EVALUATED" ? "ok" : ""}`}>
                        {row.attempt_status}
                      </span>
                    </td>
                    <td>{row.objective_marks || "—"}</td>
                    <td>{row.descriptive_marks || "—"}</td>
                    <td>
                      <strong>{row.total_marks ? `${row.total_marks} / ${row.max_marks}` : "—"}</strong>
                    </td>
                    <td>
                      {row.result_status ? (
                        <span className={`badge ${row.result_status === "PASS" ? "ok" : "bad"}`}>
                          {row.result_status}
                        </span>
                      ) : "—"}
                    </td>
                    <td>
                      <span className={`badge ${row.published ? "ok" : "muted"}`}>
                        {row.published ? "Published" : "Unpublished"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredCandidates.length === 0 && (
              <p className="muted p-4">No candidates match the filter.</p>
            )}
          </div>

          {/* Topic and Difficulty Analysis Table */}
          {analysis?.rows?.length > 0 && (
            <div className="card stack">
              <h2>Topic & Difficulty Analysis</h2>
              <table className="table">
                <thead>
                  <tr>
                    <th>Topic</th>
                    <th>Difficulty</th>
                    <th>Type</th>
                    <th>Questions</th>
                    <th>Responses</th>
                    <th>Correct</th>
                    <th>Avg Awarded</th>
                    <th>Avg Percentage</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.rows.map((row, i) => (
                    <tr key={i}>
                      <td><strong>{row.topic}</strong></td>
                      <td>
                        <span className={`badge ${row.difficulty === "EASY" ? "ok" : row.difficulty === "MEDIUM" ? "warn" : "bad"}`}>
                          {row.difficulty}
                        </span>
                      </td>
                      <td>{row.type}</td>
                      <td>{row.questions}</td>
                      <td>{row.responses}</td>
                      <td>{row.correct}</td>
                      <td>{row.average_awarded}</td>
                      <td>
                        <div className="row">
                          <span>{row.average_percent}%</span>
                          <div className="progress-bar-bg">
                            <div className="progress-bar-fill" style={{ width: `${Math.min(100, Number(row.average_percent))}%` }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}
