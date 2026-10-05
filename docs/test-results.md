# Test results

Recorded from a real pytest run. Cases below are listed only because they executed.

Command (project root `/agent/online-examination-system`):

```bash
OES_DB_USER=oes_migrator OES_DB_PASSWORD=oes_migrator_pass ./backend/.venv/bin/pytest -v --tb=no
```

The application user `oes_app` is DML-only. Tests that create `test_oes` and inspect grants therefore run as `oes_migrator`.

## Output

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /agent/online-examination-system/backend/.venv/bin/python3
cachedir: .pytest_cache
django: version: 5.2.17, settings: config.settings (from ini)
rootdir: /agent/online-examination-system
configfile: pytest.ini
testpaths: tests
plugins: django-4.14.0
collecting ... collected 35 items

tests/test_audit.py::test_audit_covers_login_start_save_submit_evaluate_publish PASSED [  2%]
tests/test_auth.py::test_student_self_registers_as_student_only PASSED   [  5%]
tests/test_auth.py::test_duplicate_email_and_weak_password_rejected PASSED [  8%]
tests/test_auth.py::test_login_and_me PASSED                             [ 11%]
tests/test_auth.py::test_inactive_user_cannot_authenticate PASSED        [ 14%]
tests/test_auth.py::test_admin_creates_faculty_and_student_cannot PASSED [ 17%]
tests/test_auth.py::test_anonymous_api_requires_token PASSED             [ 20%]
tests/test_conduction.py::test_start_freezes_shuffled_paper_and_option_order PASSED [ 22%]
tests/test_conduction.py::test_one_attempt_and_role_window_rules PASSED  [ 25%]
tests/test_conduction.py::test_save_submit_and_double_submit PASSED      [ 28%]
tests/test_conduction.py::test_mark_for_review_persists_on_save PASSED   [ 31%]
tests/test_conduction.py::test_negative_marking_floors_at_zero PASSED    [ 34%]
tests/test_conduction.py::test_unanswered_mcq_scores_zero_and_expiry_autosubmits PASSED [ 37%]
tests/test_conduction.py::test_timer_uses_the_earlier_of_duration_and_window PASSED [ 40%]
tests/test_conduction.py::test_closed_exam_rejects_new_start PASSED      [ 42%]
tests/test_conduction.py::test_freeze_paper_helper_keeps_the_full_set PASSED [ 45%]
tests/test_evaluation.py::test_descriptive_is_manual_then_published PASSED [ 48%]
tests/test_evaluation.py::test_zero_descriptive_creates_unpublished_result PASSED [ 51%]
tests/test_exams.py::test_faculty_creates_draft_and_student_cannot PASSED [ 54%]
tests/test_exams.py::test_question_must_match_subject_and_be_active PASSED [ 57%]
tests/test_exams.py::test_publish_rules PASSED                           [ 60%]
tests/test_exams.py::test_rule_based_draw PASSED                         [ 62%]
tests/test_exams.py::test_duration_cannot_exceed_window PASSED           [ 65%]
tests/test_questions.py::test_faculty_creates_mcq_with_one_correct_option PASSED [ 68%]
tests/test_questions.py::test_mcq_option_rules[<lambda>0] PASSED         [ 71%]
tests/test_questions.py::test_mcq_option_rules[<lambda>1] PASSED         [ 74%]
tests/test_questions.py::test_mcq_option_rules[<lambda>2] PASSED         [ 77%]
tests/test_questions.py::test_mcq_option_rules[<lambda>3] PASSED         [ 80%]
tests/test_questions.py::test_descriptive_rejects_options_and_student_cannot_write PASSED [ 82%]
tests/test_questions.py::test_topic_must_match_subject PASSED            [ 85%]
tests/test_questions.py::test_deactivate_question PASSED                 [ 88%]
tests/test_questions.py::test_question_bank_filters_by_topic_difficulty_and_search PASSED [ 91%]
tests/test_reports.py::test_reports_are_queries_and_role_gated PASSED    [ 94%]
tests/test_grants.py::test_application_user_cannot_change_schema PASSED  [ 97%]
tests/test_privileges.py::test_application_user_cannot_create_tables PASSED [100%]

============================== 35 passed in 6.57s ==============================
```

## What these tests cover

Auth and roles, MCQ option rules, exam publish and draw, one attempt, frozen option order, save/submit, mark for review, question-bank topic/difficulty/keyword filters, CSV exam and institution export, negative marking floor, auto-submit on expiry, descriptive marking then publish, report role gating, and `oes_app` DDL denial.

They do not cover a browser UI, proctoring, OTP, CAPTCHA, webcam, lockdown, or a coding sandbox.
