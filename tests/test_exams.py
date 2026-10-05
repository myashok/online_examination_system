from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from examination.models import Exam
from tests.conftest import attach, make_exam, make_mcq


def exam_body(subject, **overrides):
    now = timezone.now()
    body = {
        "subject": subject.id,
        "title": "Algorithms Quiz",
        "instructions": "Read each question.",
        "start_at": (now - timedelta(hours=1)).isoformat(),
        "end_at": (now + timedelta(hours=4)).isoformat(),
        "duration_minutes": 30,
        "pass_marks": "2.00",
        "negative_mark": "0.25",
    }
    body.update(overrides)
    return body


@pytest.mark.django_db
def test_faculty_creates_draft_and_student_cannot(faculty_api, student_api, subject):
    created = faculty_api.post("/api/exams/", exam_body(subject), format="json")
    assert created.status_code == 201
    assert created.data["status"] == "DRAFT"
    assert created.data["total_marks"] == "0.00"
    denied = student_api.post("/api/exams/", exam_body(subject, title="Student exam"), format="json")
    assert denied.status_code == 403


@pytest.mark.django_db
def test_question_must_match_subject_and_be_active(faculty_api, faculty, subject, topic, other_topic):
    exam = make_exam(faculty, subject, title="Paper build")
    good = make_mcq(faculty, subject, topic, text="Which sort uses a heap structure?")
    wrong_subject = make_mcq(
        faculty,
        other_topic.subject,
        other_topic,
        text="Which device routes packets between networks?",
    )
    mismatch = faculty_api.post(
        f"/api/exams/{exam.id}/questions/",
        {"question_id": wrong_subject.id},
        format="json",
    )
    assert mismatch.status_code == 400
    added = faculty_api.post(
        f"/api/exams/{exam.id}/questions/",
        {"question_id": good.id},
        format="json",
    )
    assert added.status_code == 201
    duplicate = faculty_api.post(
        f"/api/exams/{exam.id}/questions/",
        {"question_id": good.id},
        format="json",
    )
    assert duplicate.status_code == 400
    faculty_api.post(f"/api/questions/{good.id}/deactivate/")
    inactive = make_mcq(faculty, subject, topic, text="Is counting sort comparison based?")
    inactive.active = False
    inactive.save(update_fields=["active"])
    rejected = faculty_api.post(
        f"/api/exams/{exam.id}/questions/",
        {"question_id": inactive.id},
        format="json",
    )
    assert rejected.status_code == 400


@pytest.mark.django_db
def test_publish_rules(faculty_api, faculty, subject, topic):
    exam = make_exam(faculty, subject, title="Publish me", pass_marks=Decimal("50.00"))
    empty = faculty_api.post(f"/api/exams/{exam.id}/publish/")
    assert empty.status_code == 400
    question = make_mcq(faculty, subject, topic, text="Best case of insertion sort is linear?")
    attach(exam, question)
    too_high = faculty_api.post(f"/api/exams/{exam.id}/publish/")
    assert too_high.status_code == 400
    exam.pass_marks = Decimal("2.00")
    exam.save(update_fields=["pass_marks"])
    published = faculty_api.post(f"/api/exams/{exam.id}/publish/")
    assert published.status_code == 200
    assert published.data["status"] == "PUBLISHED"
    locked = faculty_api.patch(
        f"/api/exams/{exam.id}/",
        {"title": "Changed after publish"},
        format="json",
    )
    assert locked.status_code == 400
    removed = faculty_api.delete(f"/api/exams/{exam.id}/questions/{question.id}/")
    assert removed.status_code == 400


@pytest.mark.django_db
def test_rule_based_draw(faculty_api, faculty, subject, topic):
    make_mcq(faculty, subject, topic, text="Easy one about bubble sort.", difficulty="EASY")
    make_mcq(faculty, subject, topic, text="Medium one about merge sort.", difficulty="MEDIUM")
    make_mcq(faculty, subject, topic, text="Hard one about lower bounds.", difficulty="HARD")
    from tests.conftest import make_descriptive

    make_descriptive(faculty, subject, topic, text="Describe the partition step of quicksort.")
    exam = make_exam(faculty, subject, title="Drawn paper")
    drawn = faculty_api.post(
        f"/api/exams/{exam.id}/draw/",
        {"easy": 1, "medium": 1, "hard": 1, "descriptive": 1, "replace": True},
        format="json",
    )
    assert drawn.status_code == 200
    assert drawn.data["question_count"] == 4
    detail = faculty_api.get(f"/api/exams/{exam.id}/")
    kinds = {(row["type"], row["difficulty"]) for row in detail.data["questions"]}
    assert ("MCQ", "EASY") in kinds
    assert ("MCQ", "MEDIUM") in kinds
    assert ("MCQ", "HARD") in kinds
    assert ("DESCRIPTIVE", "MEDIUM") in kinds
    short = faculty_api.post(
        f"/api/exams/{exam.id}/draw/",
        {"easy": 5, "medium": 0, "hard": 0, "descriptive": 0},
        format="json",
    )
    assert short.status_code == 400
    exam.refresh_from_db()
    assert exam.exam_questions.count() == 4


@pytest.mark.django_db
def test_duration_cannot_exceed_window(faculty_api, subject):
    now = timezone.now()
    response = faculty_api.post(
        "/api/exams/",
        exam_body(
            subject,
            title="Too long",
            start_at=(now).isoformat(),
            end_at=(now + timedelta(minutes=10)).isoformat(),
            duration_minutes=30,
        ),
        format="json",
    )
    assert response.status_code == 400
    assert Exam.objects.filter(title="Too long").count() == 0
