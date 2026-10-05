import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadAuth, downloadCsvRows, errorMessage, money, when } from "../api";
import Layout from "../components/Layout";

function clock(seconds) {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  const rest = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function answered(question, answer = {}) {
  if (question.type === "MCQ") return answer.selected_option_id != null;
  return Boolean((answer.descriptive_text || "").trim());
}

function paletteClass(item, itemIndex, index, answer = {}) {
  const classes = [];
  if (itemIndex === index) classes.push("current");
  if (answered(item, answer)) classes.push("answered");
  if (answer.marked_for_review) classes.push("marked");
  return classes.join(" ");
}

export function StudentHome({ history = false }) {
  const [exams, setExams] = useState([]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [filterTab, setFilterTab] = useState("ALL");
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [briefingExam, setBriefingExam] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportNote, setExportNote] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api("/api/student/exams/").then(setExams).catch((err) => setError(errorMessage(err)));
    api("/api/reports/student/history/").then(setRows).catch((err) => setError(errorMessage(err)));
  }, []);

  async function start(examId) {
    setError("");
    try {
      const paper = await api(`/api/exams/${examId}/start/`, { method: "POST" });
      navigate(`/student/attempts/${paper.id}`);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function exportHistory() {
    setExporting(true);
    setError("");
    setExportNote("");
    try {
      const filename = await downloadAuth("/api/reports/student/history/export/", "my-exam-history.csv");
      setExportNote(`Downloaded ${filename} successfully.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  const availableCount = exams.filter((e) => e.state === "AVAILABLE").length;
  const inProgressCount = exams.filter((e) => e.state === "IN_PROGRESS").length;
  const completedCount = rows.filter((r) => r.attempt_status !== "IN_PROGRESS").length;
  const passedCount = rows.filter((r) => r.result_status === "PASS").length;

  const filteredExams = exams.filter((exam) => {
    if (filterTab === "AVAILABLE") return exam.state === "AVAILABLE";
    if (filterTab === "IN_PROGRESS") return exam.state === "IN_PROGRESS";
    if (filterTab === "COMPLETED") return exam.state === "SUBMITTED" || exam.state === "EVALUATED";
    return true;
  });

  const filteredRows = rows.filter((row) => {
    if (historyFilter === "PASSED") return row.result_status === "PASS";
    if (historyFilter === "FAILED") return row.result_status === "FAIL";
    if (historyFilter === "PENDING") return !row.published;
    return true;
  });

  const nextExam = exams.find((exam) => exam.state === "IN_PROGRESS") || exams.find((exam) => exam.state === "AVAILABLE");

  function guidance(exam) {
    if (exam.state === "AVAILABLE") return "Server countdown begins on start. Single attempt rule applies.";
    if (exam.state === "IN_PROGRESS") return "Attempt is actively running on the server.";
    if (exam.result_published) return "Final scorecard evaluated and published.";
    return "Submitted. Objective items are scored. Descriptive items wait for faculty.";
  }

  return (
    <Layout>
      <div className="ed-home">
        <div>
          <h1 className="page-title">{history ? "Exam history" : "Student Dashboard"}</h1>
          <p className="lede">
            {history
              ? "Review past attempts, evaluation status, and published scorecards."
              : "View scheduled examination papers, active timers, and pending submissions."}
          </p>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {exportNote && <p className="ok" role="status">{exportNote}</p>}

        {!history && (
          <div className="ed-columns">
            <aside className="ed-side">
              <section className="card">
                <h2 className="exam-serif-title">Do this next</h2>
                {nextExam ? (
                  <>
                    <p className="lede" style={{ marginBottom: 16 }}>{guidance(nextExam)}</p>
                    <h3 className="exam-serif-title">{nextExam.title}</h3>
                    <div className="ed-meta" style={{ marginBottom: 16 }}>
                      <span className={nextExam.state === "IN_PROGRESS" ? "pill progress" : "pill"}>{nextExam.state === "IN_PROGRESS" ? "In Progress" : "Ready to Start"}</span>
                      <span className="pill">{nextExam.duration_minutes} mins</span>
                    </div>
                    {nextExam.state === "IN_PROGRESS" ? (
                      <Link className="button primary" to={`/student/attempts/${nextExam.attempt_id}`}>Continue attempt</Link>
                    ) : (
                      <button className="primary" type="button" onClick={() => setBriefingExam(nextExam)}>Start exam</button>
                    )}
                  </>
                ) : (
                  <p className="lede">Nothing is waiting. A paper appears here when faculty publishes it.</p>
                )}
              </section>
              <section className="card stack">
                <h3 className="exam-serif-title">Overview</h3>
                <div className="ed-stat"><span>Available to take</span><span className="pill">{availableCount}</span></div>
                <div className="ed-stat"><span>In progress</span><span className="pill progress">{inProgressCount}</span></div>
                <div className="ed-stat"><span>Submitted</span><span className="pill">{completedCount}</span></div>
                <div className="ed-stat"><span>Passed</span><span className="pill pass">{passedCount}</span></div>
              </section>
            </aside>
            <section className="ed-main">
              <div className="ed-tabs">
                {[
                  ["ALL", `All Exams (${exams.length})`],
                  ["AVAILABLE", `Available (${availableCount})`],
                  ["IN_PROGRESS", `In Progress (${inProgressCount})`],
                  ["COMPLETED", "Submitted & Past"],
                ].map(([tab, label]) => (
                  <button key={tab} type="button" className={filterTab === tab ? "active" : ""} onClick={() => setFilterTab(tab)}>{label}</button>
                ))}
              </div>
              {filteredExams.map((exam) => (
                <article className="card ed-row" key={exam.id}>
                  <div>
                    <div className="ed-meta">
                      <span className="pill">{exam.subject}</span>
                      <span className={`pill ${exam.state === "IN_PROGRESS" ? "progress" : exam.result_published ? "pass" : ""}`}>
                        {exam.state === "AVAILABLE" ? "Ready to Start" : exam.state === "IN_PROGRESS" ? "In Progress" : exam.result_published ? "Result Ready" : "Submitted"}
                      </span>
                    </div>
                    <h3 className="exam-serif-title">{exam.title}</h3>
                    <p className="ed-meta">{exam.duration_minutes} mins · {exam.question_count} questions · {exam.total_marks} max marks · Pass {exam.pass_marks}</p>
                    <p className="lede" style={{ fontSize: 14, marginTop: 8 }}>{guidance(exam)}</p>
                  </div>
                  <div>
                    {exam.state === "AVAILABLE" && <button className="primary" type="button" onClick={() => setBriefingExam(exam)}>Start Exam</button>}
                    {exam.state === "IN_PROGRESS" && <Link className="button primary" to={`/student/attempts/${exam.attempt_id}`}>Continue</Link>}
                    {exam.result_published && <Link className="button ghost" to={`/student/results/${exam.id}`}>View Scorecard</Link>}
                  </div>
                </article>
              ))}
              {filteredExams.length === 0 && <p className="lede">No exams match this filter.</p>}
            </section>
          </div>
        )}

        {history && (
          <section className="card">
            <div className="ed-row" style={{ marginBottom: 16 }}>
              <h2 className="exam-serif-title">Examination records</h2>
              <button className="ghost" type="button" onClick={exportHistory} disabled={exporting || rows.length === 0}>
                {exporting ? "Generating CSV…" : "Export CSV"}
              </button>
            </div>
            <div className="ed-tabs" style={{ marginBottom: 16 }}>
              {[["ALL", "All"], ["PASSED", "Passed"], ["FAILED", "Failed"], ["PENDING", "Pending"]].map(([tab, label]) => (
                <button key={tab} type="button" className={historyFilter === tab ? "active" : ""} onClick={() => setHistoryFilter(tab)}>{label}</button>
              ))}
            </div>
            <table className="table">
              <thead>
                <tr><th>Exam</th><th>Status</th><th>Result</th><th>Marks</th><th>Submitted</th><th></th></tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => (
                  <tr key={row.attempt_id}>
                    <td><strong>{row.title}</strong><div className="muted">{row.subject}</div></td>
                    <td>{row.attempt_status}</td>
                    <td>{row.published ? row.result_status : "Pending"}</td>
                    <td>{row.published ? `${row.total_marks} / ${row.max_marks}` : "—"}</td>
                    <td>{when(row.submitted_at)}</td>
                    <td>
                      {row.published && <Link className="button ghost" to={`/student/results/${row.exam_id}`}>View Scorecard</Link>}
                      {!row.published && row.attempt_status === "IN_PROGRESS" && <Link className="button primary" to={`/student/attempts/${row.attempt_id}`}>Continue</Link>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredRows.length === 0 && <p className="lede">No examination attempts found.</p>}
          </section>
        )}

        {briefingExam && (
          <div className="modal-backdrop">
            <div className="modal-dialog card">
              <h2 className="exam-serif-title">Before you start</h2>
              <h3 className="exam-serif-title">{briefingExam.title}</h3>
              <p className="lede">{briefingExam.instructions || "Read the rules, then start. The server clock begins immediately."}</p>
              <p className="ed-meta">{briefingExam.duration_minutes} minutes · {briefingExam.question_count} questions · {briefingExam.total_marks} marks · Pass {briefingExam.pass_marks} · Negative {briefingExam.negative_mark} · One attempt</p>
              <p className="lede">Answers save on the server. When the timer reaches zero, the paper submits itself.</p>
              <div className="row">
                <button className="ghost" type="button" onClick={() => setBriefingExam(null)}>Cancel</button>
                <button className="primary" type="button" onClick={() => { const examId = briefingExam.id; setBriefingExam(null); start(examId); }}>Start now</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

export function ExamRoom() {
  const { attemptId } = useParams();
  const [paper, setPaper] = useState(null);
  const [answers, setAnswers] = useState({});
  const [remaining, setRemaining] = useState(0);
  const [index, setIndex] = useState(0);
  const [filter, setFilter] = useState("ALL");
  const [note, setNote] = useState("");
  const [savingState, setSavingState] = useState("idle"); // idle, saving, saved, error
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const finishing = useRef(false);

  useEffect(() => {
    api(`/api/attempts/${attemptId}/`)
      .then((data) => {
        setPaper(data);
        setRemaining(data.remaining_seconds || 0);
        const next = {};
        data.questions.forEach((question) => {
          next[question.question_id] = {
            selected_option_id: question.selected_option_id,
            descriptive_text: question.descriptive_text || "",
            marked_for_review: Boolean(question.marked_for_review),
          };
        });
        setAnswers(next);
        if (data.status !== "IN_PROGRESS") setDone(true);
      })
      .catch((err) => {
        if (err.status === 403) setDone(true);
        else setError(errorMessage(err));
      });
  }, [attemptId]);

  useEffect(() => {
    const timer = setInterval(() => {
      setRemaining((value) => {
        if (value <= 1) {
          clearInterval(timer);
          return 0;
        }
        return value - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  async function save(nextAnswers = answers) {
    if (!paper || paper.status !== "IN_PROGRESS") return;
    setSavingState("saving");
    try {
      const payload = paper.questions.map((question) => ({
        question_id: question.question_id,
        selected_option_id: nextAnswers[question.question_id]?.selected_option_id ?? null,
        descriptive_text: question.type === "DESCRIPTIVE" ? nextAnswers[question.question_id]?.descriptive_text || "" : null,
        marked_for_review: Boolean(nextAnswers[question.question_id]?.marked_for_review),
      }));
      const data = await api(`/api/attempts/${attemptId}/answers/`, { method: "PUT", body: { answers: payload } });
      setPaper(data);
      setRemaining(data.remaining_seconds || 0);
      setSavingState("saved");
      setNote("Auto-saved to server");
      if (data.status !== "IN_PROGRESS") setDone(true);
    } catch (err) {
      setSavingState("error");
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    if (!paper || paper.status !== "IN_PROGRESS") return undefined;
    const handle = setInterval(() => {
      save().catch((err) => setError(errorMessage(err)));
    }, 15000);
    return () => clearInterval(handle);
  }, [paper, answers, attemptId]);

  async function submit() {
    setError("");
    try {
      if (paper?.status === "IN_PROGRESS") await save();
      await api(`/api/attempts/${attemptId}/submit/`, { method: "POST" });
      setDone(true);
    } catch (err) {
      if (err.status === 409) setDone(true);
      else setError(errorMessage(err));
    }
  }

  useEffect(() => {
    if (paper?.status === "IN_PROGRESS" && remaining === 0 && !finishing.current) {
      finishing.current = true;
      submit();
    }
  }, [remaining, paper]);

  if (done) {
    return (
      <Layout>
        <div className="card completion-card">
          <div className="completion-icon">✅</div>
          <h1>Paper Submitted Successfully</h1>
          <p className="lede">
            Your responses have been securely submitted to the examination server.
          </p>
          <div className="completion-details">
            <p><strong>Objective questions (MCQ)</strong> are evaluated automatically.</p>
            <p><strong>Descriptive items</strong> are placed in the faculty grading queue.</p>
            <p>Results will be accessible on your dashboard once published by the instructor.</p>
          </div>
          <div className="row">
            <Link className="button primary" to="/student">
              Return to Student Dashboard
            </Link>
            <Link className="button ghost" to="/student/results">
              View History
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  if (!paper) {
    return (
      <Layout>
        <p className="muted">Loading examination paper…</p>
        {error && <p className="error">{error}</p>}
      </Layout>
    );
  }

  const question = paper.questions[index];
  const answer = answers[question.question_id] || {};
  const answeredCount = paper.questions.filter((item) => answered(item, answers[item.question_id])).length;
  const reviewCount = paper.questions.filter((item) => answers[item.question_id]?.marked_for_review).length;
  const notAnswered = paper.questions.length - answeredCount;

  function update(patch) {
    const next = { ...answers, [question.question_id]: { ...answer, ...patch } };
    setAnswers(next);
    save(next).catch((err) => setError(errorMessage(err)));
  }

  function clearAnswer() {
    if (question.type === "MCQ") {
      update({ selected_option_id: null });
    } else {
      update({ descriptive_text: "" });
    }
  }

  function matchesFilter(item, itemIndex) {
    const current = answers[item.question_id] || {};
    if (filter === "ANSWERED") return answered(item, current);
    if (filter === "NOT_ANSWERED") return !answered(item, current);
    if (filter === "REVIEW") return Boolean(current.marked_for_review);
    return true;
  }

  return (
    <Layout>
      <header className="ed-row" style={{ alignItems: "flex-end", marginBottom: 32 }}>
        <div>
          <h1 className="page-title">{paper.exam.title}</h1>
          <p className="lede">{paper.exam.instructions || "Read each question carefully before submitting your final paper."}</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="muted">{savingState === "saving" ? "Saving responses…" : "Saved on server"}</div>
          <div className="muted">Remaining time</div>
          <div className={remaining < 300 ? "ed-clock late" : "ed-clock"}>{clock(remaining)}</div>
        </div>
      </header>

      {remaining < 300 && remaining > 0 && (
        <div className="alert-banner warning">
          ⚠️ <strong>Time warning:</strong> Less than {Math.ceil(remaining / 60)} minutes remaining! Please review your answers.
        </div>
      )}

      {error && <p className="error" role="alert">{error}</p>}

      <div className="ed-columns">
        <aside className="card stack" style={{ width: 320, flex: "0 0 320px" }}>
          <div>
            <h2 style={{ fontFamily: "Inter, sans-serif", fontSize: 14, letterSpacing: "0.12em", textTransform: "uppercase" }}>Navigator</h2>
            <div className="ed-meta">
              <span className="pill progress">{answeredCount} Answered</span>
              <span className="pill">{notAnswered} Unanswered</span>
              <span className="pill outline">{reviewCount} Marked</span>
            </div>
          </div>

          <div className="ed-tabs">
            {[
              ["ALL", "All"],
              ["ANSWERED", "Answered"],
              ["NOT_ANSWERED", "Unanswered"],
              ["REVIEW", "Marked"],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={filter === value ? "active" : ""}
                onClick={() => setFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="ed-nav-grid">
            {paper.questions.map((item, itemIndex) => (
              matchesFilter(item, itemIndex) ? (
                <button
                  key={item.question_id}
                  className={paletteClass(item, itemIndex, index, answers[item.question_id])}
                  onClick={() => setIndex(itemIndex)}
                  title={answers[item.question_id]?.marked_for_review ? `Q${itemIndex + 1} (Marked for review)` : `Question ${itemIndex + 1}`}
                >
                  {itemIndex + 1}
                </button>
              ) : null
            ))}
          </div>

          <div className="legend">
            <span><i className="swatch answered" /> Answered</span>
            <span><i className="swatch blank" /> Unanswered</span>
            <span><i className="swatch marked" /> Marked</span>
            <span><i className="swatch current" /> Current</span>
          </div>
        </aside>

        <section className="card stack question-section">
          <div className="between question-meta-header">
            <span className="badge">
              Question {index + 1} of {paper.questions.length} · {question.topic} · {question.difficulty} · {question.marks} marks
            </span>
            <div className="row">
              {answer.marked_for_review && <span className="badge warn">Marked for review</span>}
              <span className="badge">{question.type}</span>
            </div>
          </div>

          <h2 className="question-text">{question.text}</h2>

          {question.type === "MCQ" ? (
            <div className="options-stack">
              {question.options.map((option) => (
                <label
                  className={answer.selected_option_id === option.id ? "option selected" : "option"}
                  key={option.id}
                >
                  <input
                    type="radio"
                    name={`q-${question.question_id}`}
                    checked={answer.selected_option_id === option.id}
                    onChange={() => update({ selected_option_id: option.id })}
                  />
                  <span>{option.option_text}</span>
                </label>
              ))}
              {answer.selected_option_id != null && (
                <button
                  type="button"
                  className="linkish clear-btn"
                  onClick={clearAnswer}
                  title="Clear choice to avoid negative mark penalty"
                >
                  ✕ Clear Selection (Avoid negative mark)
                </button>
              )}
            </div>
          ) : (
            <div className="descriptive-container">
              <label>
                Your Answer (Descriptive Response)
                <textarea
                  rows={8}
                  placeholder="Type your structured explanation or response here…"
                  value={answer.descriptive_text || ""}
                  onChange={(event) => update({ descriptive_text: event.target.value })}
                />
              </label>
            </div>
          )}

          <div className="exam-footer-nav between">
            <div className="row">
              <button
                className="ghost"
                type="button"
                disabled={index === 0}
                onClick={() => setIndex(index - 1)}
              >
                ← Previous
              </button>
              <button
                className="ghost"
                type="button"
                disabled={index === paper.questions.length - 1}
                onClick={() => setIndex(index + 1)}
              >
                Next →
              </button>
            </div>

            <div className="row">
              <button
                className={answer.marked_for_review ? "primary review-active" : "ghost"}
                type="button"
                onClick={() => update({ marked_for_review: !answer.marked_for_review })}
              >
                {answer.marked_for_review ? "★ Marked for Review" : "☆ Mark for Review"}
              </button>
              <button
                className="primary"
                type="button"
                onClick={() => setShowSubmitModal(true)}
              >
                Submit Paper
              </button>
            </div>
          </div>
        </section>
      </div>

      {/* Submit Confirmation Modal */}
      {showSubmitModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h2>Confirm Paper Submission</h2>
              <button className="linkish modal-close" type="button" onClick={() => setShowSubmitModal(false)}>✕</button>
            </div>
            <div className="modal-body stack">
              <p>Are you sure you want to finish and submit your paper?</p>
              
              <div className="submit-summary-grid">
                <div className="summary-item ok">
                  <span className="summary-num">{answeredCount}</span>
                  <span className="summary-label">Answered</span>
                </div>
                <div className="summary-item muted">
                  <span className="summary-num">{notAnswered}</span>
                  <span className="summary-label">Unanswered</span>
                </div>
                <div className="summary-item warn">
                  <span className="summary-num">{reviewCount}</span>
                  <span className="summary-label">Marked for Review</span>
                </div>
              </div>

              {notAnswered > 0 && (
                <div className="notice-banner warning">
                  ⚠️ You have <strong>{notAnswered} unanswered questions</strong>. Once submitted, you cannot resume or alter your responses.
                </div>
              )}

              {reviewCount > 0 && (
                <div className="notice-banner info">
                  ℹ️ You have <strong>{reviewCount} questions marked for review</strong>.
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="ghost" type="button" onClick={() => setShowSubmitModal(false)}>
                Return to Exam
              </button>
              <button
                className="primary"
                type="button"
                onClick={() => {
                  setShowSubmitModal(false);
                  submit();
                }}
              >
                Yes, Submit My Paper
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

export function ResultPage() {
  const { examId } = useParams();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/api/results/me/${examId}/`)
      .then(setResult)
      .catch((err) => setError(errorMessage(err)));
  }, [examId]);

  function exportResultCsv() {
    if (!result) return;
    const rows = [
      ["ONLINE EXAMINATION SYSTEM"],
      ["Student Scorecard & Detailed Breakdown"],
      ["Exam Title", result.exam.title],
      ["Result Status", result.result.status],
      ["Total Marks", `${result.result.total_marks} / ${result.result.max_marks}`],
      ["Objective Marks", result.result.objective_marks],
      ["Descriptive Marks", result.result.descriptive_marks],
      ["Passing Marks", result.result.pass_marks],
      [],
      ["Question Number", "Type", "Topic", "Marks Awarded", "Max Marks", "Question Prompt", "Your Answer / Option", "Correct Option", "Explanation"],
    ];

    result.questions.forEach((q, idx) => {
      let yourAnswer = "";
      let correctAnswer = "";
      if (q.type === "MCQ") {
        const studentChoice = q.options.find((opt) => opt.id === q.selected_option_id);
        const correctChoice = q.options.find((opt) => opt.is_correct);
        yourAnswer = studentChoice ? studentChoice.option_text : "No answer";
        correctAnswer = correctChoice ? correctChoice.option_text : "";
      } else {
        yourAnswer = q.descriptive_text || "No response provided";
        correctAnswer = "Manual faculty evaluation";
      }

      rows.push([
        idx + 1,
        q.type,
        q.topic,
        q.awarded_marks ?? 0,
        q.marks,
        q.text,
        yourAnswer,
        correctAnswer,
        q.explanation || "",
      ]);
    });

    const slug = "".join ? "scorecard" : "exam";
    downloadCsvRows(`scorecard-exam-${examId}.csv`, rows);
  }

  function handlePrint() {
    window.print();
  }

  return (
    <Layout>
      <div className="between no-print">
        <div>
          <h1 className="page-title">Exam Scorecard</h1>
          <p className="lede">Official performance statement and question analysis.</p>
        </div>
        <div className="row">
          <button className="ghost" type="button" onClick={handlePrint}>Print scorecard</button>
          <button className="ghost" type="button" onClick={exportResultCsv}>Export CSV</button>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      {result && (
        <div className="stack printable-area">
          <div className="card scorecard-summary">
            <div className="between">
              <div>
                <span className="badge">{result.exam.subject_name || "Examination"}</span>
                <h2>{result.exam.title}</h2>
              </div>
              <div className="scorecard-status-badge">
                <span className={`badge big ${result.result.status === "PASS" ? "ok" : "bad"}`}>
                  {result.result.status === "PASS" ? "PASSED" : "FAILED"}
                </span>
              </div>
            </div>

            <div className="score-grid">
              <div className="scorecard-metric-box">
                <span className="metric-box-label">Total Score</span>
                <span className="score-num">
                  {result.result.total_marks} <span className="metric-denom">/ {result.result.max_marks}</span>
                </span>
                <span className="metric-box-sub">
                  {((Number(result.result.total_marks) / Number(result.result.max_marks)) * 100).toFixed(1)}% Score
                </span>
              </div>

              <div className="scorecard-metric-box">
                <span className="metric-box-label">Objective (MCQ)</span>
                <span className="metric-box-val">{result.result.objective_marks}</span>
                <span className="metric-box-sub">Automated evaluation</span>
              </div>

              <div className="scorecard-metric-box">
                <span className="metric-box-label">Descriptive</span>
                <span className="metric-box-val">{result.result.descriptive_marks}</span>
                <span className="metric-box-sub">Faculty evaluated</span>
              </div>

              <div className="scorecard-metric-box">
                <span className="metric-box-label">Passing Required</span>
                <span className="metric-box-val">{result.result.pass_marks}</span>
                <span className="metric-box-sub">Min required to pass</span>
              </div>
            </div>
          </div>

          <h2 className="section-title">Question-by-Question Analysis</h2>

          {result.questions.map((question, qIdx) => {
            const isCorrect = question.type === "MCQ" && question.awarded_marks === question.marks;
            const isNegative = question.type === "MCQ" && Number(question.awarded_marks) < 0;
            const isUnanswered = question.type === "MCQ" && question.selected_option_id == null;

            return (
              <article
                className={`card result-question-card ${
                  isCorrect ? "result-correct" : isNegative ? "result-incorrect" : ""
                }`}
                key={question.question_id}
              >
                <div className="between">
                  <span className="badge">Question {qIdx + 1} · {question.topic} · {question.type}</span>
                  <div className="row">
                    <span className="badge">
                      Awarded: <strong>{question.awarded_marks ?? "—"}</strong> / {question.marks} marks
                    </span>
                    {question.type === "MCQ" && (
                      <span className={`badge ${isCorrect ? "ok" : isUnanswered ? "" : "bad"}`}>
                        {isCorrect ? "✓ Correct" : isUnanswered ? "Unanswered" : "✗ Incorrect"}
                      </span>
                    )}
                  </div>
                </div>

                <h3>{question.text}</h3>

                {question.type === "MCQ" ? (
                  <div className="result-options-list">
                    {question.options.map((option) => {
                      const isChosen = question.selected_option_id === option.id;
                      const isOptionCorrect = option.is_correct;
                      let optionClass = "q-option";
                      if (isOptionCorrect) optionClass += " correct";
                      if (isChosen && !isOptionCorrect) optionClass += " wrong";

                      return (
                        <div key={option.id} className={optionClass}>
                          <span className="option-indicator">
                            {isOptionCorrect ? "✓" : isChosen ? "✗" : "○"}
                          </span>
                          <span className="option-text">{option.option_text}</span>
                          <div className="option-tags">
                            {isOptionCorrect && <span className="tag-correct">Correct Answer</span>}
                            {isChosen && <span className="tag-chosen">Your Choice</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="descriptive-review-box">
                    <p className="label">Your Submitted Response:</p>
                    <div className="student-response-content">
                      {question.descriptive_text || <span className="muted">No response submitted</span>}
                    </div>
                  </div>
                )}

                {question.explanation && (
                  <div className="explanation-callout">
                    <strong>💡 Explanation:</strong> {question.explanation}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </Layout>
  );
}
