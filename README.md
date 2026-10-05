# ONLINE EXAMINATION SYSTEM

An online examination application for the MCSP-232 project. It supports
student exam attempts, faculty paper creation and evaluation, administrative
reporting, and CSV exports.

## Technology

- Django 5 and Django REST Framework
- SimpleJWT authentication
- React 18 and Vite
- MySQL 8
- Nginx and Gunicorn in Docker
- pytest and pytest-django

The project uses Python and Django, not the Java/Spring alternative mentioned
in the original synopsis.

## Quick start with Docker

### Requirements

- Docker Desktop, Colima, or another Docker Engine
- Docker Compose v2 (`docker compose`)
- Port `8080` available

### Build and start

Run from the project root:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8080
```

The first start may take longer because Docker downloads MySQL, Python, Node,
and Nginx images. The backend waits for MySQL, applies migrations, loads demo
data, and then starts Gunicorn.

Run in the background:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

Check the application health endpoint:

```bash
curl http://127.0.0.1:8080/api/health/
```

Expected response:

```json
{"status":"ok","application":"ONLINE EXAMINATION SYSTEM"}
```

### Rebuild after code changes

Rebuild and recreate the containers while keeping database data:

```bash
docker compose down
docker compose up --build
```

For a completely clean rebuild, including deletion of the MySQL volume:

```bash
docker compose down -v
docker compose up --build
```

Warning: `docker compose down -v` permanently removes local examination
attempts, users, and other data stored in the Compose database volume. Demo
data is recreated on the next start.

### Stop the application

Stop containers and keep the database volume:

```bash
docker compose down
```

### Logs and diagnostics

Follow logs from every service:

```bash
docker compose logs -f
```

Follow one service:

```bash
docker compose logs -f backend
docker compose logs -f web
docker compose logs -f mysql
```

Restart one service:

```bash
docker compose restart backend
```

## Docker services

- `mysql` — MySQL 8 with the persistent `oes_mysql` volume
- `backend` — migrations, demonstration seed, and Gunicorn on the internal
  Docker network
- `web` — Nginx serving the React production build on host port `8080`

Nginx sends `/api/` requests to the backend and serves React routes through
`index.html`.

The backend uses two database accounts:

- `oes_migrator` — schema migrations and test database creation
- `oes_app` — runtime `SELECT`, `INSERT`, `UPDATE`, and `DELETE` operations

The Compose passwords are local demonstration values defined in
`docker-compose.yml`. Replace them and `OES_SECRET_KEY` before any real
deployment.

## Demo accounts

The `seed_demo` command is idempotent for demonstration users, questions, and
exams. It resets the demo passwords and keeps the published midterm open for
three hours. It does not delete extra accounts created through the application.

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@oes.local` | `Admin@12345` |
| Faculty | `faculty@oes.local` | `Faculty@12345` |
| Student | `student@oes.local` | `Student@12345` |
| Student | `student2@oes.local` | `Student@12345` |
| Student | `student3@oes.local` | `Student@12345` |

Initial demonstration states, unless the persistent volume already contains an
attempt:

- `student@oes.local` has an evaluated and published result for Operating
  Systems Midterm.
- `student2@oes.local` has no attempt and can start the available exam.
- `student3@oes.local` has a submitted attempt waiting in the faculty
  evaluation queue.
- `Database Quiz (Draft)` is visible to staff but hidden from students.

## Application workflows

### Student

1. Sign in or create a student account.
2. Open **Available Exams**.
3. Read the instructions and start an available exam.
4. Answer MCQ or descriptive questions.
5. Use the question navigator and mark questions for review.
6. Answers save to the server automatically.
7. Submit manually, or allow the server timer to auto-submit.
8. Open **My Results & History** after faculty publishes the result.
9. Print a scorecard or export available history and result data.

Only one attempt per student and exam is allowed. The server controls the
timer, shuffled question order, and shuffled MCQ option order.

### Faculty

1. Create and search MCQ or descriptive questions in **Question Bank**.
2. Create a draft exam.
3. Add fixed questions or use the rule-based draw.
4. Publish the exam for students.
5. Close it when no more attempts should begin.
6. Open **Evaluation** and award descriptive marks.
7. Publish the calculated result separately.
8. Open an exam report and export its CSV.

### Admin

Admins can use all faculty features and can also:

- view institution performance totals
- export the institution summary CSV
- create faculty or administrator accounts
- activate or deactivate users
- inspect the audit log

## Included features

- Student self-registration and role-based access
- Argon2 password hashes, with PBKDF2 hashes still accepted
- JWT access and refresh tokens
- MCQ questions with exactly four options and one correct answer
- Descriptive questions and manual marking
- Question search by keyword, subject, topic, type, and difficulty
- Draft, published, unpublished, and closed exam states
- Fixed papers and rule-based random draws
- One attempt per student
- Server timer, auto-save, manual submit, and auto-submit
- Mark-for-review question navigation
- Frozen shuffled questions and MCQ option orders
- Objective scoring and negative marking, floored at zero
- Separate result evaluation and publication
- Student attempt history and scorecards
- Faculty topic and difficulty analysis
- Admin institution summary and audit log
- CSV exports for student history, exam performance, and institution summary

## CSV exports

CSV downloads require an authenticated user with the correct role:

- Student history: **My Results & History → Export CSV**
- Faculty exam report: **Exam report → Export CSV Report**
- Admin summary: **Institution Performance Summary → Export Institution CSV**

CSV responses include a UTF-8 byte-order mark for spreadsheet compatibility.
If a download fails, confirm the user is signed in, has the correct role, and
that `/api/health/` is available through port `8080`.

## Manual development setup

Use this section only when not using Docker Compose.

### Requirements

- Python 3.12
- Node.js 22 and npm
- MySQL 8

### Database

Create the local database and least-privilege accounts:

```bash
sudo mysql < database/grants.sql
```

The local demonstration database accounts are:

- `oes_migrator` / `oes_migrator_pass`
- `oes_app` / `oes_app_pass`

Domain table definitions are documented in `database/schema.sql`. Django
migrations also create its authentication, content type, admin, and session
tables.

### Backend

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

OES_DB_USER=oes_migrator \
OES_DB_PASSWORD=oes_migrator_pass \
python manage.py migrate

OES_DB_USER=oes_app \
OES_DB_PASSWORD=oes_app_pass \
python manage.py seed_demo

OES_DB_USER=oes_app \
OES_DB_PASSWORD=oes_app_pass \
python manage.py runserver 127.0.0.1:8000
```

Backend health check:

```bash
curl http://127.0.0.1:8000/api/health/
```

The correct path is `/api/health/`, not `/health/`.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

### Production frontend build

```bash
cd frontend
npm ci
npm run build
```

The generated files are written to `frontend/dist`.

### Production backend command

```bash
cd backend
OES_DB_USER=oes_app \
OES_DB_PASSWORD=oes_app_pass \
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## Environment variables

Common backend variables:

- `OES_SECRET_KEY`
- `OES_DEBUG`
- `OES_ALLOWED_HOSTS`
- `OES_DB_HOST`
- `OES_DB_PORT`
- `OES_DB_NAME`
- `OES_DB_USER`
- `OES_DB_PASSWORD`

Compose additionally supplies `OES_MIGRATOR_USER`,
`OES_MIGRATOR_PASSWORD`, `OES_APP_USER`, and `OES_APP_PASSWORD` to the
container entrypoint.

`.env.example` contains local defaults. Docker Compose currently defines its
own values directly in `docker-compose.yml`.

## Tests

The tests use the migrator account because Django creates a temporary
`test_oes` database.

Create the backend virtual environment as described above, then run from the
project root:

```bash
OES_DB_USER=oes_migrator \
OES_DB_PASSWORD=oes_migrator_pass \
./backend/.venv/bin/pytest
```

Run one test module:

```bash
OES_DB_USER=oes_migrator \
OES_DB_PASSWORD=oes_migrator_pass \
./backend/.venv/bin/pytest tests/test_reports.py
```

See `docs/test-results.md` for the last recorded test run. Do not treat that
file as proof of the current working tree; run the tests after changing
backend behavior.

## Troubleshooting

### Port 8080 is already in use

Stop the program using the port or change the web mapping in
`docker-compose.yml` from `8080:80` to another host port, such as `8081:80`.

### Docker cannot connect to its daemon

Start Docker Desktop or Colima, then confirm:

```bash
docker info
docker compose version
```

### MySQL initialization changes do not apply

Files in `/docker-entrypoint-initdb.d/` only run when the MySQL volume is first
created. Recreate the volume:

```bash
docker compose down -v
docker compose up --build
```

This deletes all local database data.

### Backend is unhealthy

Inspect both backend and database logs:

```bash
docker compose logs backend
docker compose logs mysql
```

Then check:

```bash
docker compose ps
curl http://127.0.0.1:8080/api/health/
```

### Frontend changes are not visible

The production React files are copied into the web image at build time.
Rebuild that image:

```bash
docker compose up --build -d web
```

If dependencies or shared configuration changed, rebuild the whole stack:

```bash
docker compose down
docker compose up --build
```

## Not included

The project does not currently provide webcam or microphone proctoring,
browser lockdown, OTP, CAPTCHA, IP whitelisting, or an automated programming
judge. These are future-scope features.

## Documentation

- `docs/api-catalogue.md` — HTTP API catalogue
- `docs/data-dictionary.md` — database tables and fields
- `docs/test-results.md` — last recorded pytest run
- `docs/market-research-bmad.md` — market and architecture analysis
- `database/schema.sql` — domain schema reference
- `database/grants.sql` — local MySQL accounts and grants
- `database/docker-init.sql` — initial Compose database grants
