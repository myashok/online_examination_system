from decimal import Decimal

import pytest

from examination.models import Result
from tests.conftest import attach, make_exam, make_mcq


@pytest.mark.django_db
def test_reports_are_queries_and_role_gated(
    student_api, faculty_api, admin_api, faculty, student, subject, topic
):
    question = make_mcq(faculty, subject, topic, text="Report question about hashing?")
    exam = make_exam(
        faculty,
        subject,
        title="Report exam",
        pass_marks=Decimal("2.00"),
        negative_mark=Decimal("0"),
    )
    attach(exam, question)
    exam.status = "PUBLISHED"
    exam.save(update_fields=["status"])
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    student_api.put(
        f"/api/attempts/{started.data['id']}/answers/",
        {
            "answers": [
                {"question_id": question.id, "selected_option_id": question.correct_option.id}
            ]
        },
        format="json",
    )
    student_api.post(f"/api/attempts/{started.data['id']}/submit/")
    history = student_api.get("/api/reports/student/history/")
    assert history.status_code == 200
    assert history.data[0]["published"] is False
    assert history.data[0]["total_marks"] is None

    faculty_report = faculty_api.get(f"/api/reports/faculty/exams/{exam.id}/")
    assert faculty_report.status_code == 200
    assert faculty_report.data["submitted"] == 1
    assert faculty_report.data["published"] == 0
    assert faculty_report.data["pass_count"] == 0
    assert faculty_report.data["candidates"][0]["student_email"] == student.email

    analysis = faculty_api.get(f"/api/reports/faculty/exams/{exam.id}/analysis/")
    assert analysis.status_code == 200
    assert analysis.data["rows"]
    assert analysis.data["rows"][0]["topic"] == topic.name
    assert analysis.data["rows"][0]["correct"] == 1

    denied_admin = faculty_api.get("/api/reports/admin/summary/")
    assert denied_admin.status_code == 403
    denied_student = student_api.get(f"/api/reports/faculty/exams/{exam.id}/")
    assert denied_student.status_code == 403

    result = Result.objects.get(exam=exam, user=student)
    faculty_api.post(f"/api/results/{result.id}/publish/")
    published_history = student_api.get("/api/reports/student/history/")
    assert published_history.data[0]["published"] is True
    assert published_history.data[0]["result_status"] == "PASS"
    assert published_history.data[0]["total_marks"] == "2.00"

    summary = admin_api.get("/api/reports/admin/summary/")
    assert summary.status_code == 200
    row = next(item for item in summary.data["exams"] if item["exam_id"] == exam.id)
    assert row["pass_count"] == 1
    assert row["fail_count"] == 0
    assert row["average_total"] == "2.00"
    assert summary.data["pass_count"] == 1
    assert "candidates" not in row

    export = faculty_api.get(f"/api/reports/faculty/exams/{exam.id}/export/")
    assert export.status_code == 200
    assert export["Content-Type"].startswith("text/csv")
    assert "attachment;" in export["Content-Disposition"]
    csv_body = export.content.decode("utf-8-sig")
    assert "Exam performance summary" in csv_body
    assert "Student User" in csv_body
    assert "PASS" in csv_body
    assert "Sorting" in csv_body
    denied_export = student_api.get(f"/api/reports/faculty/exams/{exam.id}/export/")
    assert denied_export.status_code == 403

    admin_csv = admin_api.get("/api/reports/admin/summary/export/")
    assert admin_csv.status_code == 200
    assert "Institution performance summary" in admin_csv.content.decode("utf-8-sig")
    faculty_admin_csv = faculty_api.get("/api/reports/admin/summary/export/")
    assert faculty_admin_csv.status_code == 403

    student_history_export = student_api.get("/api/reports/student/history/export/")
    assert student_history_export.status_code == 200
    assert "Student examination history" in student_history_export.content.decode("utf-8-sig")

