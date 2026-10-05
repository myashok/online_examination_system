from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from catalog.models import Question, QuestionOption, Subject, Topic
from examination.models import Exam, ExamQuestion


PASSWORD = "ExamPass@123"


@pytest.fixture
def api():
    return APIClient()


def login(client, user, password=PASSWORD):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@test.edu",
        password=PASSWORD,
        name="Admin User",
        role=User.ROLE_ADMIN,
    )


@pytest.fixture
def faculty(db):
    return User.objects.create_user(
        email="faculty@test.edu",
        password=PASSWORD,
        name="Faculty User",
        role=User.ROLE_FACULTY,
    )


@pytest.fixture
def student(db):
    return User.objects.create_user(
        email="student@test.edu",
        password=PASSWORD,
        name="Student User",
        role=User.ROLE_STUDENT,
    )


@pytest.fixture
def student_two(db):
    return User.objects.create_user(
        email="student2@test.edu",
        password=PASSWORD,
        name="Second Student",
        role=User.ROLE_STUDENT,
    )


@pytest.fixture
def faculty_api(faculty):
    return login(APIClient(), faculty)


@pytest.fixture
def student_api(student):
    return login(APIClient(), student)


@pytest.fixture
def admin_api(admin_user):
    return login(APIClient(), admin_user)


@pytest.fixture
def subject(db):
    return Subject.objects.create(name="Algorithms")


@pytest.fixture
def topic(subject):
    return Topic.objects.create(subject=subject, name="Sorting")


@pytest.fixture
def other_topic(db):
    other = Subject.objects.create(name="Networks")
    return Topic.objects.create(subject=other, name="Routing")


def make_mcq(faculty, subject, topic, text="Which sort is stable?", marks="2.00", difficulty="EASY"):
    question = Question.objects.create(
        subject=subject,
        topic=topic,
        type=Question.TYPE_MCQ,
        text=text,
        difficulty=difficulty,
        marks=Decimal(marks),
        explanation="Merge sort is stable.",
        created_by=faculty,
        active=True,
    )
    correct = QuestionOption.objects.create(question=question, option_text="Merge sort", is_correct=True)
    QuestionOption.objects.create(question=question, option_text="Selection sort", is_correct=False)
    QuestionOption.objects.create(question=question, option_text="Heap sort", is_correct=False)
    QuestionOption.objects.create(question=question, option_text="Quick sort", is_correct=False)
    question.correct_option = correct
    return question


def make_descriptive(faculty, subject, topic, text="Explain quicksort.", marks="5.00"):
    return Question.objects.create(
        subject=subject,
        topic=topic,
        type=Question.TYPE_DESCRIPTIVE,
        text=text,
        difficulty=Question.DIFFICULTY_MEDIUM,
        marks=Decimal(marks),
        explanation="Partition and recurse.",
        created_by=faculty,
        active=True,
    )


def make_exam(faculty, subject, **overrides):
    now = timezone.now()
    payload = {
        "subject": subject,
        "title": "Midterm",
        "instructions": "No second attempt.",
        "start_at": now - timedelta(hours=1),
        "end_at": now + timedelta(hours=3),
        "duration_minutes": 30,
        "pass_marks": Decimal("2.00"),
        "negative_mark": Decimal("0.50"),
        "status": Exam.STATUS_DRAFT,
        "created_by": faculty,
    }
    payload.update(overrides)
    return Exam.objects.create(**payload)


def attach(exam, *questions):
    for question in questions:
        ExamQuestion.objects.create(exam=exam, question=question)


@pytest.fixture
def mcq(faculty, subject, topic):
    return make_mcq(faculty, subject, topic)


@pytest.fixture
def descriptive(faculty, subject, topic):
    return make_descriptive(faculty, subject, topic)
