# API catalogue

Base URL for the Django process: `http://127.0.0.1:8000`.

The Vite dev server at `http://127.0.0.1:5173` proxies `/api` to that origin. Authenticated routes send `Authorization: Bearer <access>`. JSON request and response bodies use UTF-8. Decimal marks are strings.

JWT access lifetime is eight hours. Refresh lifetime is one day. Login records an audit row (`LOGIN`). Failed login also records `LOGIN` with `detail` `failed:<email>`.

Roles: `STUDENT`, `FACULTY`, `ADMIN`. Inactive users cannot authenticate.

This catalogue describes the implemented REST API. It does not include proctoring, OTP, CAPTCHA, webcam, lockdown, or a coding sandbox.

## Health

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/health/` | none | `{"status":"ok","application":"ONLINE EXAMINATION SYSTEM"}` |

There is no `/health/` route.

## Auth

| Method | Path | Auth | Body | Success |
| --- | --- | --- | --- | --- |
| POST | `/api/auth/register/` | none | `{name, email, password}` | 201 user. Role is always `STUDENT`. |
| POST | `/api/auth/login/` | none | `{email, password}` | 200 `{access, refresh, user}` |
| POST | `/api/auth/refresh/` | none | `{refresh}` | 200 `{access}` |
| GET | `/api/auth/me/` | any role | — | 200 current user |

User object: `{id, name, email, role, active, created_at}`.

## Users (admin)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/users/` | ADMIN | Optional `?role=` |
| POST | `/api/users/` | ADMIN | `{name, email, password, role}` where `role` is `FACULTY` or `ADMIN` |
| GET | `/api/users/<id>/` | ADMIN | |
| PATCH | `/api/users/<id>/` | ADMIN | `{name?, role?, active?}`. An admin cannot deactivate their own account. |

A student calling these routes receives 403.

## Catalog

GET on subjects and topics is any authenticated role. Writes are FACULTY or ADMIN. Questions are FACULTY or ADMIN only.

| Method | Path | Notes |
| --- | --- | --- |
| GET, POST | `/api/subjects/` | `{id, name}` |
| GET, PATCH, DELETE | `/api/subjects/<id>/` | DELETE 409 if in use |
| GET, POST | `/api/topics/` | GET optional `?subject=`. Body `{subject, name}` |
| PATCH, DELETE | `/api/topics/<id>/` | DELETE 409 if in use |
| GET, POST | `/api/questions/` | GET filters: `subject`, `topic`, `type`, `difficulty`, `active=true\|false`, `q` or `search` (case-insensitive stem match) |
| GET, PATCH, DELETE | `/api/questions/<id>/` | DELETE 409 if linked to an exam or attempt. Attempted questions cannot change stem, marks, type, difficulty, subject, topic, or options. |
| POST | `/api/questions/<id>/activate/` | `active=true` |
| POST | `/api/questions/<id>/deactivate/` | `active=false` |

MCQ create/update requires exactly four options and exactly one `is_correct: true`. Descriptive questions must not send options. `type` is `MCQ` or `DESCRIPTIVE`. `difficulty` is `EASY`, `MEDIUM`, or `HARD`.

## Exams (faculty / admin)

| Method | Path | Notes |
| --- | --- | --- |
| GET, POST | `/api/exams/` | GET optional `?status=` `?subject=`. POST creates `DRAFT`. |
| GET, PATCH, DELETE | `/api/exams/<id>/` | PATCH only while `DRAFT`. DELETE only draft without attempts (409 otherwise). GET includes paper questions and `total_marks`. |
| POST | `/api/exams/<id>/questions/` | `{question_id}` add to paper |
| DELETE | `/api/exams/<exam_id>/questions/<question_id>/` | remove from paper |
| POST | `/api/exams/<id>/draw/` | `{easy, medium, hard, descriptive, replace}` rule-based draw from the bank |
| POST | `/api/exams/<id>/publish/` | paper must be non-empty |
| POST | `/api/exams/<id>/unpublish/` | |
| POST | `/api/exams/<id>/close/` | |

Exam statuses: `DRAFT`, `PUBLISHED`, `CLOSED`. Write fields: `subject`, `title`, `instructions`, `start_at`, `end_at`, `duration_minutes` (1–300, not longer than the window), `pass_marks`, `negative_mark`.

## Student exams and attempts

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/student/exams/` | STUDENT | Published/closed exams the student may see, with `state` |
| POST | `/api/exams/<id>/start/` | STUDENT | 201 attempt payload. One attempt per student per exam. |
| GET | `/api/attempts/` | any role | Students see only their attempts. Optional `?exam=` |
| GET | `/api/attempts/<id>/` | any role | Student may read in-progress paper. After submit, student needs a published result. Staff cannot read an in-progress attempt. |
| PUT | `/api/attempts/<id>/answers/` | STUDENT | `{answers:[{question_id, selected_option_id?, descriptive_text?, marked_for_review?}]}`. `marked_for_review` is optional; omitting it leaves the stored flag unchanged. |
| POST | `/api/attempts/<id>/submit/` | STUDENT | `{id, status, submitted_at, result_ready, published}` |

Student `state` values: `UPCOMING`, `AVAILABLE`, `MISSED`, `IN_PROGRESS`, `SUBMITTED`, `EVALUATED`. Draft exams are omitted.

Starting an attempt freezes question order in `attempt_questions` and MCQ option order in `attempt_option_orders`. The timer is the earlier of remaining duration and exam `end_at`. Expiry auto-submits. Each attempt question includes `marked_for_review` (boolean). The flag is a navigation aid and is not used in scoring.

## Evaluation and results

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/evaluation/queue/` | FACULTY/ADMIN | `{needs_marking, ready_to_publish}`. Optional `?exam=` |
| GET | `/api/evaluation/attempts/<id>/` | FACULTY/ADMIN | Paper with answers plus `result` if present |
| POST | `/api/evaluation/attempts/<id>/marks/` | FACULTY/ADMIN | `{marks:[{question_id, awarded_marks}]}` |
| POST | `/api/results/<id>/publish/` | FACULTY/ADMIN | Makes the result visible to the student |
| GET | `/api/results/me/` | STUDENT | Same payload as student history |
| GET | `/api/results/me/<exam_id>/` | STUDENT | Full paper with explanations only after publish; 403 otherwise |

Attempt statuses: `IN_PROGRESS`, `SUBMITTED`, `EVALUATED`. Result statuses: `PASS`, `FAIL`. Objective marks are computed on submit. Descriptive marks are faculty-entered. Negative marking cannot take objective marks below zero.

## Reports

Reports are queries. There is no report table.

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/reports/student/history/` | STUDENT | Published results for the caller |
| GET | `/api/reports/student/exams/<exam_id>/` | STUDENT | Same as `/api/results/me/<exam_id>/` |
| GET | `/api/reports/faculty/exams/<exam_id>/` | FACULTY/ADMIN | Counts, pass/fail, average/high/low, `candidates` roster |
| GET | `/api/reports/faculty/exams/<exam_id>/analysis/` | FACULTY/ADMIN | Topic, difficulty, and type buckets |
| GET | `/api/reports/faculty/exams/<exam_id>/export/` | FACULTY/ADMIN | UTF-8 CSV attachment: summary, candidates, topic analysis |
| GET | `/api/reports/admin/summary/` | ADMIN | Per-exam faculty-style rows plus totals |
| GET | `/api/reports/admin/summary/export/` | ADMIN | UTF-8 CSV attachment of the institution summary |

A student calling `/api/reports/admin/summary/` returns 403 `{"detail":"You do not have permission to perform this action."}`.

## Audit

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/audit-logs/` | ADMIN | Newest first, cap 500. Filters: `action`, `user`, `entity` |

Audit actions: `LOGIN`, `START`, `SAVE`, `SUBMIT`, `EVALUATE`, `PUBLISH`.

Django `/admin/` exists for the AUTH_USER_MODEL but is not the student/faculty UI.

## Observed demo responses (live, after `seed_demo`)

These were returned by HTTP against `127.0.0.1:8000` on 2026-10-05. They are not invented.

- `GET /api/health/` → 200 `{"status": "ok", "application": "ONLINE EXAMINATION SYSTEM"}`
- `student2@oes.local` `GET /api/student/exams/` → Operating Systems Midterm `"state": "AVAILABLE"`, `"attempt_id": null`
- `student@oes.local` `GET /api/results/me/1/` → published PASS, objective `"2.00"`, descriptive `"2.00"`, total `"4.00"`, max `"10.00"`
- `faculty@oes.local` `GET /api/evaluation/queue/` → `needs_marking` includes `student3@oes.local` attempt 2, stage `NEEDS_MARKING`
- `admin@oes.local` `GET /api/reports/admin/summary/` and `GET /api/audit-logs/` → 200
- `student@oes.local` `GET /api/reports/admin/summary/` → 403
