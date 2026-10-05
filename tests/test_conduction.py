from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from examination.models import AttemptOptionOrder, AttemptQuestion, Exam, ExamAttempt, Result
from examination.services import freeze_paper, start_attempt
from tests.conftest import attach, make_descriptive, make_exam, make_mcq


class ReverseRng:
    def shuffle(self, seq):
        seq.reverse()


def published_paper(faculty, subject, topic, questions=None, **exam_overrides):
    exam = make_exam(faculty, subject, **exam_overrides)
    questions = questions or [make_mcq(faculty, subject, topic, text=f"Question number {index}?") for index in range(3)]
    attach(exam, *questions)
    exam.status = Exam.STATUS_PUBLISHED
    exam.save(update_fields=["status"])
    return exam, questions


@pytest.mark.django_db
def test_start_freezes_shuffled_paper_and_option_order(faculty, student, subject, topic):
    exam, questions = published_paper(faculty, subject, topic)
    attempt = start_attempt(exam, student, rng=ReverseRng())
    master_ids = list(exam.exam_questions.order_by("id").values_list("question_id", flat=True))
    frozen = list(
        AttemptQuestion.objects.filter(attempt=attempt)
        .order_by("display_order")
        .values_list("question_id", flat=True)
    )
    assert frozen == list(reversed(master_ids))
    assert sorted(frozen) == sorted(master_ids)
    first = AttemptQuestion.objects.get(attempt=attempt, display_order=1)
    option_ids = list(
        AttemptOptionOrder.objects.filter(attempt_question=first)
        .order_by("display_order")
        .values_list("option_id", flat=True)
    )
    natural = list(first.question.options.order_by("id").values_list("id", flat=True))
    assert option_ids == list(reversed(natural))
    reloaded = list(
        AttemptQuestion.objects.filter(attempt=attempt)
        .order_by("display_order")
        .values_list("question_id", flat=True)
    )
    assert reloaded == frozen


@pytest.mark.django_db
def test_one_attempt_and_role_window_rules(student_api, faculty_api, faculty, student, subject, topic):
    exam, _questions = published_paper(faculty, subject, topic, title="Single sitting")
    faculty_start = faculty_api.post(f"/api/exams/{exam.id}/start/")
    assert faculty_start.status_code == 403
    first = student_api.post(f"/api/exams/{exam.id}/start/")
    assert first.status_code == 201
    assert first.data["status"] == "IN_PROGRESS"
    assert len(first.data["questions"]) == 3
    for question in first.data["questions"]:
        assert "is_correct" not in question
        for option in question["options"]:
            assert set(option) == {"id", "option_text"}
    second = student_api.post(f"/api/exams/{exam.id}/start/")
    assert second.status_code == 409
    assert ExamAttempt.objects.filter(exam=exam, user=student).count() == 1

    future = make_exam(
        faculty,
        subject,
        title="Not open yet",
        start_at=timezone.now() + timedelta(hours=2),
        end_at=timezone.now() + timedelta(hours=5),
    )
    attach(future, make_mcq(faculty, subject, topic, text="Future question about graphs?"))
    future.status = Exam.STATUS_PUBLISHED
    future.save(update_fields=["status"])
    early = student_api.post(f"/api/exams/{future.id}/start/")
    assert early.status_code == 400

    closed = make_exam(faculty, subject, title="Already shut")
    attach(closed, make_mcq(faculty, subject, topic, text="Closed question about trees?"))
    closed.status = Exam.STATUS_PUBLISHED
    closed.save(update_fields=["status"])
    Exam.objects.filter(pk=closed.id).update(end_at=timezone.now() - timedelta(minutes=1))
    late = student_api.post(f"/api/exams/{closed.id}/start/")
    assert late.status_code == 400


@pytest.mark.django_db
def test_save_submit_and_double_submit(student_api, faculty, student, subject, topic):
    question = make_mcq(faculty, subject, topic, text="Pick the stable sort algorithm.")
    exam, _ = published_paper(faculty, subject, topic, questions=[question], title="Save flow", pass_marks=Decimal("2.00"))
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    attempt_id = started.data["id"]
    option_id = question.correct_option.id
    saved = student_api.put(
        f"/api/attempts/{attempt_id}/answers/",
        {"answers": [{"question_id": question.id, "selected_option_id": option_id}]},
        format="json",
    )
    assert saved.status_code == 200
    assert saved.data["questions"][0]["selected_option_id"] == option_id
    bad_option = student_api.put(
        f"/api/attempts/{attempt_id}/answers/",
        {"answers": [{"question_id": question.id, "selected_option_id": 999999}]},
        format="json",
    )
    assert bad_option.status_code == 400
    again = student_api.get(f"/api/attempts/{attempt_id}/")
    assert again.data["questions"][0]["selected_option_id"] == option_id
    submitted = student_api.post(f"/api/attempts/{attempt_id}/submit/")
    assert submitted.status_code == 200
    assert submitted.data["status"] == "EVALUATED"
    assert submitted.data["published"] is False
    duplicate = student_api.post(f"/api/attempts/{attempt_id}/submit/")
    assert duplicate.status_code == 409
    hidden = student_api.get(f"/api/results/me/{exam.id}/")
    assert hidden.status_code == 403


@pytest.mark.django_db
def test_mark_for_review_persists_on_save(student_api, faculty, subject, topic):
    question = make_mcq(faculty, subject, topic, text="Flag this item and come back later.")
    exam, _ = published_paper(faculty, subject, topic, questions=[question], title="Review flag")
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    attempt_id = started.data["id"]
    assert started.data["questions"][0]["marked_for_review"] is False
    flagged = student_api.put(
        f"/api/attempts/{attempt_id}/answers/",
        {
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": None,
                    "marked_for_review": True,
                }
            ]
        },
        format="json",
    )
    assert flagged.status_code == 200
    assert flagged.data["questions"][0]["marked_for_review"] is True
    assert flagged.data["questions"][0]["selected_option_id"] is None
    reloaded = student_api.get(f"/api/attempts/{attempt_id}/")
    assert reloaded.data["questions"][0]["marked_for_review"] is True
    cleared = student_api.put(
        f"/api/attempts/{attempt_id}/answers/",
        {
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": question.correct_option.id,
                    "marked_for_review": False,
                }
            ]
        },
        format="json",
    )
    assert cleared.data["questions"][0]["marked_for_review"] is False
    assert cleared.data["questions"][0]["selected_option_id"] == question.correct_option.id


@pytest.mark.django_db
def test_negative_marking_floors_at_zero(student_api, faculty, student, subject, topic):
    questions = [
        make_mcq(faculty, subject, topic, text=f"Wrong pick {index}?", marks="1.00")
        for index in range(3)
    ]
    exam, _ = published_paper(
        faculty,
        subject,
        topic,
        questions=questions,
        title="Penalty paper",
        pass_marks=Decimal("1.00"),
        negative_mark=Decimal("1.00"),
    )
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    answers = []
    for question in questions:
        wrong = question.options.filter(is_correct=False).first()
        answers.append({"question_id": question.id, "selected_option_id": wrong.id})
    student_api.put(
        f"/api/attempts/{started.data['id']}/answers/",
        {"answers": answers},
        format="json",
    )
    student_api.post(f"/api/attempts/{started.data['id']}/submit/")
    result = Result.objects.get(exam=exam, user=student)
    assert result.objective_marks == Decimal("0.00")
    assert result.total_marks == Decimal("0.00")
    assert result.status == "FAIL"
    assert result.published is False


@pytest.mark.django_db
def test_unanswered_mcq_scores_zero_and_expiry_autosubmits(student_api, faculty, student, subject, topic):
    question = make_mcq(faculty, subject, topic, text="Leave this one blank please.")
    exam, _ = published_paper(faculty, subject, topic, questions=[question], title="Blank and timer")
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    attempt = ExamAttempt.objects.get(pk=started.data["id"])
    attempt.started_at = timezone.now() - timedelta(hours=2)
    attempt.save(update_fields=["started_at"])
    expired = student_api.put(
        f"/api/attempts/{attempt.id}/answers/",
        {"answers": [{"question_id": question.id, "selected_option_id": question.correct_option.id}]},
        format="json",
    )
    assert expired.status_code == 409
    attempt.refresh_from_db()
    assert attempt.status == "EVALUATED"
    answer = attempt.answers.get(question=question)
    assert answer.awarded_marks == Decimal("0.00")
    assert answer.selected_option_id is None


@pytest.mark.django_db
def test_timer_uses_the_earlier_of_duration_and_window(student_api, faculty, subject, topic):
    question = make_mcq(faculty, subject, topic, text="Short window question here.")
    exam, _ = published_paper(
        faculty,
        subject,
        topic,
        questions=[question],
        title="Short window",
        duration_minutes=30,
    )
    Exam.objects.filter(pk=exam.id).update(end_at=timezone.now() + timedelta(seconds=90))
    started = student_api.post(f"/api/exams/{exam.id}/start/")
    assert started.status_code == 201
    assert started.data["remaining_seconds"] <= 90


@pytest.mark.django_db
def test_closed_exam_rejects_new_start(student_api, faculty_api, faculty, subject, topic):
    question = make_mcq(faculty, subject, topic, text="Closing time question text.")
    exam, _ = published_paper(faculty, subject, topic, questions=[question], title="Closable")
    closed = faculty_api.post(f"/api/exams/{exam.id}/close/")
    assert closed.status_code == 200
    denied = student_api.post(f"/api/exams/{exam.id}/start/")
    assert denied.status_code == 400


@pytest.mark.django_db
def test_freeze_paper_helper_keeps_the_full_set(faculty, student, subject, topic):
    descriptive = make_descriptive(faculty, subject, topic)
    exam, questions = published_paper(faculty, subject, topic)
    attach(exam, descriptive)
    attempt = start_attempt(exam, student)
    frozen = set(AttemptQuestion.objects.filter(attempt=attempt).values_list("question_id", flat=True))
    assert descriptive.id in frozen
    assert frozen == {question.id for question in questions} | {descriptive.id}
    descriptive_slot = AttemptQuestion.objects.get(attempt=attempt, question=descriptive)
    assert descriptive_slot.option_orders.count() == 0
    mcq_slot = AttemptQuestion.objects.filter(attempt=attempt, question__type="MCQ").first()
    assert mcq_slot.option_orders.count() == 4
