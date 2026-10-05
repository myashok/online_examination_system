# Data dictionary

Source of truth for domain tables: `database/schema.sql`, generated from the migrated MySQL 8 schema. Character set `utf8mb4`, collation `utf8mb4_unicode_ci`. Engine InnoDB.

The running application connects as `oes_app` (SELECT, INSERT, UPDATE, DELETE). `oes_migrator` applies this DDL and Django migrations. Grants: `database/grants.sql`.

Django also creates `django_migrations`, `django_content_type`, `django_session`, `django_admin_log`, `auth_group`, `auth_group_permissions`, and `auth_permission`. Those are framework tables, not domain entities.

Reports are computed in Python from the tables below. There is no report table.

`attempt_option_orders` freezes the shuffled MCQ option order for one question on one attempt.

## `users`

Application user. Email is the login name. Password is stored in `password_hash` (Argon2id for new hashes; PBKDF2 still verifies).

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| password_hash | varchar(128) | Django `password` field, `db_column=password_hash` |
| last_login | datetime(6) | nullable |
| name | varchar(150) | |
| email | varchar(254) UNIQUE | |
| role | varchar(20) | CHECK `STUDENT`, `FACULTY`, `ADMIN`. Index `user_role_idx` |
| active | tinyint(1) | maps to `is_active` |
| created_at | datetime(6) | |

## `subjects`

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| name | varchar(150) UNIQUE | |

## `topics`

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| name | varchar(150) | |
| subject_id | bigint FK → subjects.id | UNIQUE (`subject_id`, `name`) as `topic_subject_name_uniq` |

## `questions`

Question bank. Not the student paper.

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| type | varchar(20) | CHECK `MCQ`, `DESCRIPTIVE` |
| text | longtext | |
| difficulty | varchar(10) | CHECK `EASY`, `MEDIUM`, `HARD` |
| marks | decimal(6,2) | CHECK `marks > 0` |
| explanation | longtext | nullable; shown to the student only after result publish |
| active | tinyint(1) | Index `question_active_idx` |
| created_by_id | bigint FK → users.id | |
| subject_id | bigint FK → subjects.id | |
| topic_id | bigint FK → topics.id | |

Index `question_bank_idx` on (`subject_id`, `type`, `difficulty`).

## `question_options`

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| option_text | longtext | |
| is_correct | tinyint(1) | |
| question_id | bigint FK → questions.id | CASCADE from Django |

MCQ rules (four options, one correct) are enforced in the API, not as a table CHECK.

## `exams`

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| title | varchar(200) | |
| instructions | longtext | |
| start_at | datetime(6) | |
| end_at | datetime(6) | CHECK `end_at > start_at` |
| duration_minutes | int unsigned | CHECK `> 0` |
| pass_marks | decimal(6,2) | CHECK `>= 0` |
| negative_mark | decimal(6,2) | CHECK `>= 0` |
| status | varchar(20) | CHECK `DRAFT`, `PUBLISHED`, `CLOSED` |
| created_by_id | bigint FK → users.id | |
| subject_id | bigint FK → subjects.id | |

Index `exam_window_idx` on (`status`, `start_at`, `end_at`).

## `exam_questions`

Master paper. Unique (`exam_id`, `question_id`) as `exam_question_uniq`.

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| exam_id | bigint FK → exams.id | |
| question_id | bigint FK → questions.id | |

## `exam_attempts`

One row per student per exam (`one_attempt_per_student` on `exam_id`, `user_id`).

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| started_at | datetime(6) | |
| submitted_at | datetime(6) | nullable until submit |
| status | varchar(20) | CHECK `IN_PROGRESS`, `SUBMITTED`, `EVALUATED` |
| exam_id | bigint FK → exams.id | |
| user_id | bigint FK → users.id | Index `attempt_user_idx` |

## `attempt_questions`

Frozen shuffled paper for one attempt. Unique (`attempt_id`, `question_id`) and (`attempt_id`, `display_order`).

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| display_order | int unsigned | |
| question_id | bigint FK → questions.id | |
| attempt_id | bigint FK → exam_attempts.id | |

## `attempt_option_orders`

Frozen shuffled MCQ option order for one frozen question. Unique (`attempt_question_id`, `option_id`) and (`attempt_question_id`, `display_order`).

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| display_order | int unsigned | |
| option_id | bigint FK → question_options.id | |
| attempt_question_id | bigint FK → attempt_questions.id | |

## `attempt_answers`

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| descriptive_text | longtext | nullable |
| marked_for_review | tinyint(1) | default 0. Candidate review flag; not used in scoring |
| awarded_marks | decimal(6,2) | nullable until scored |
| evaluated_at | datetime(6) | nullable |
| evaluated_by_id | bigint FK → users.id | nullable, SET NULL |
| question_id | bigint FK → questions.id | |
| selected_option_id | bigint FK → question_options.id | nullable |
| attempt_id | bigint FK → exam_attempts.id | Unique with `question_id` as `attempt_answer_uniq` |

Index `answer_attempt_idx` on `attempt_id`.

## `results`

One result per attempt (`attempt_id` UNIQUE) and per (`user_id`, `exam_id`) as `one_result_per_student_exam`.

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| objective_marks | decimal(6,2) | CHECK `>= 0` |
| descriptive_marks | decimal(6,2) | CHECK `>= 0` |
| total_marks | decimal(6,2) | CHECK `>= 0` |
| max_marks | decimal(6,2) | paper total |
| status | varchar(10) | CHECK `PASS`, `FAIL` |
| published | tinyint(1) | student cannot see the paper/result until true |
| generated_at | datetime(6) | |
| attempt_id | bigint FK → exam_attempts.id | |
| exam_id | bigint FK → exams.id | |
| user_id | bigint FK → users.id | |

## `audit_logs`

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint PK | |
| action | varchar(32) | CHECK `LOGIN`, `START`, `SAVE`, `SUBMIT`, `EVALUATE`, `PUBLISH`. Index `audit_action_idx` |
| entity | varchar(32) | |
| entity_id | bigint unsigned | nullable |
| at | datetime(6) | |
| detail | longtext | |
| user_id | bigint FK → users.id | nullable. Index `audit_user_at_idx` on (`user_id`, `at`) |

## Live row counts (observed 2026-10-05 after `seed_demo`)

Do not treat these as fixtures. They were read from database `oes`.

- users: 6 rows (five seed accounts plus leftover `report.student@oes.local`)
- exams: Operating Systems Midterm `PUBLISHED`; Database Quiz (Draft) `DRAFT`
- exam_attempts: student EVALUATED; student3 SUBMITTED; report.student EVALUATED; student2 none
- results: student PASS published 2.00 / 2.00 / 4.00 / 10.00; report.student FAIL published 0.50 / 2.00 / 2.50 / 10.00
- questions: 6; exam_questions: 5 on the midterm
