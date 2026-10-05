from decimal import Decimal

import pytest

from examination.models import ExamAttempt, Result
from tests.conftest import attach, make_descriptive, make_exam, make_mcq


def open_exam(faculty, subject, topic):
    mcq = make_mcq(faculty, subject, topic, text="Capital of the sorting world?")
    descriptive = make_descriptive(faculty, subject, topic, text="Explain stability of sorting.")
    exam = make_exam(
        faculty,
        subject,
        title="Mixed paper",
        pass_marks=Decimal("4.00"),
        negative_mark=Decimal("0.50"),
    )
    attach(exam, mcq, descriptive)
    exam.status = "PUBLISHED"
    exam.save(update_fields=["status"])
    return exam, mcq, descriptive


@pytest.mark.django_db
def test_descriptive_is_manual_then_published(
    student_api, faculty_api, student, faculty, subject, topic
):
    exam, mcq, descriptive = open_exam(faculty, subject, topic)
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    attempt_id = started.data["id"]
    wrong = mcq.options.filter(is_correct=False).first()
    student_api.put(
        f"/api/attempts/{attempt_id}/answers/",
        {
            "answers": [
                {"question_id": mcq.id, "selected_option_id": wrong.id},
                {
                    "question_id": descriptive.id,
                    "descriptive_text": "A stable sort keeps equal keys in their original order.",
                },
            ]
        },
        format="json",
    )
    submitted = student_api.post(f"/api/attempts/{attempt_id}/submit/")
    assert submitted.status_code == 200
    assert submitted.data["status"] == "SUBMITTED"
    assert submitted.data["result_ready"] is False
    attempt = ExamAttempt.objects.get(pk=attempt_id)
    mcq_answer = attempt.answers.get(question=mcq)
    assert mcq_answer.awarded_marks == Decimal("-0.50")
    descriptive_answer = attempt.answers.get(question=descriptive)
    assert descriptive_answer.awarded_marks is None

    student_mark = student_api.post(
        f"/api/evaluation/attempts/{attempt_id}/marks/",
        {"marks": [{"question_id": descriptive.id, "awarded_marks": "4.00"}]},
        format="json",
    )
    assert student_mark.status_code == 403

    too_high = faculty_api.post(
        f"/api/evaluation/attempts/{attempt_id}/marks/",
        {"marks": [{"question_id": descriptive.id, "awarded_marks": "9.00"}]},
        format="json",
    )
    assert too_high.status_code == 400

    marked = faculty_api.post(
        f"/api/evaluation/attempts/{attempt_id}/marks/",
        {"marks": [{"question_id": descriptive.id, "awarded_marks": "3.00"}]},
        format="json",
    )
    assert marked.status_code == 200
    assert marked.data["result"]["objective_marks"] == "0.00"
    assert marked.data["result"]["descriptive_marks"] == "3.00"
    assert marked.data["result"]["total_marks"] == "3.00"
    assert marked.data["result"]["status"] == "FAIL"

    remarked = faculty_api.post(
        f"/api/evaluation/attempts/{attempt_id}/marks/",
        {"marks": [{"question_id": descriptive.id, "awarded_marks": "5.00"}]},
        format="json",
    )
    assert remarked.status_code == 200
    assert remarked.data["result"]["total_marks"] == "5.00"
    assert remarked.data["result"]["status"] == "PASS"
    assert remarked.data["result"]["published"] is False

    hidden = student_api.get(f"/api/results/me/{exam.id}/")
    assert hidden.status_code == 403
    result_id = remarked.data["result"]["id"]
    published = faculty_api.post(f"/api/results/{result_id}/publish/")
    assert published.status_code == 200
    visible = student_api.get(f"/api/results/me/{exam.id}/")
    assert visible.status_code == 200
    assert visible.data["result"]["status"] == "PASS"
    revealed = {row["question_id"]: row for row in visible.data["questions"]}
    assert "is_correct" in revealed[mcq.id]["options"][0]
    locked = faculty_api.post(
        f"/api/evaluation/attempts/{attempt_id}/marks/",
        {"marks": [{"question_id": descriptive.id, "awarded_marks": "1.00"}]},
        format="json",
    )
    assert locked.status_code == 400
    assert Result.objects.get(pk=result_id).published is True


@pytest.mark.django_db
def test_zero_descriptive_creates_unpublished_result(student_api, faculty, student, subject, topic):
    question = make_mcq(faculty, subject, topic, text="Only an objective item here.")
    exam = make_exam(faculty, subject, title="Objective only", pass_marks=Decimal("2.00"), negative_mark=Decimal("0"))
    attach(exam, question)
    exam.status = "PUBLISHED"
    exam.save(update_fields=["status"])
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    student_api.put(
        f"/api/attempts/{started.data['id']}/answers/",
        {
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": question.correct_option.id,
                }
            ]
        },
        format="json",
    )
    submitted = student_api.post(f"/api/attempts/{started.data['id']}/submit/")
    assert submitted.data["status"] == "EVALUATED"
    result = Result.objects.get(user=student, exam=exam)
    assert result.descriptive_marks == Decimal("0.00")
    assert result.objective_marks == Decimal("2.00")
    assert result.status == "PASS"
    assert result.published is False
