import pytest

from auditlog.models import AuditLog
from tests.conftest import attach, make_descriptive, make_exam, make_mcq


@pytest.mark.django_db
def test_audit_covers_login_start_save_submit_evaluate_publish(
    api, faculty, student, subject, topic
):
    registered = api.post(
        "/api/auth/register/",
        {"name": "Audit Student", "email": "audit@test.edu", "password": "ExamPass@123"},
        format="json",
    )
    assert registered.status_code == 201
    login = api.post(
        "/api/auth/login/",
        {"email": "audit@test.edu", "password": "ExamPass@123"},
        format="json",
    )
    assert login.status_code == 200
    failed = api.post(
        "/api/auth/login/",
        {"email": "audit@test.edu", "password": "not-the-password"},
        format="json",
    )
    assert failed.status_code == 401

    question = make_mcq(faculty, subject, topic, text="Audit objective question text.")
    descriptive = make_descriptive(faculty, subject, topic, text="Audit descriptive question text.")
    exam = make_exam(faculty, subject, title="Audit exam", pass_marks="1.00", negative_mark="0")
    attach(exam, question, descriptive)
    exam.status = "PUBLISHED"
    exam.save(update_fields=["status"])

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    started = api.post(f"/api/exams/{exam.id}/start/")
    attempt_id = started.data["id"]
    api.put(
        f"/api/attempts/{attempt_id}/answers/",
        {
            "answers": [
                {"question_id": question.id, "selected_option_id": question.correct_option.id},
                {"question_id": descriptive.id, "descriptive_text": "A short answer."},
            ]
        },
        format="json",
    )
    api.post(f"/api/attempts/{attempt_id}/submit/")

    from tests.conftest import login as as_user

    faculty_client = as_user(api, faculty)
    marked = faculty_client.post(
        f"/api/evaluation/attempts/{attempt_id}/marks/",
        {"marks": [{"question_id": descriptive.id, "awarded_marks": "4.00"}]},
        format="json",
    )
    faculty_client.post(f"/api/results/{marked.data['result']['id']}/publish/")

    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert {"LOGIN", "START", "SAVE", "SUBMIT", "EVALUATE", "PUBLISH"} <= actions
    assert AuditLog.objects.filter(action="LOGIN", detail__startswith="failed:").exists()
    assert AuditLog.objects.filter(action="LOGIN", detail="success").exists()

    student_view = as_user(api, student)
    assert student_view.get("/api/audit-logs/").status_code == 403
