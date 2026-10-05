from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from catalog.models import Question, QuestionOption, Subject, Topic
from examination.models import Exam, ExamAttempt, ExamQuestion
from examination.services import (
    award_descriptive,
    publish_exam,
    publish_result,
    save_answers,
    start_attempt,
    submit_attempt,
)


class Command(BaseCommand):
    help = "Load demo users, a question bank, and one open exam. Re-running resets demo passwords and the open window."

    def handle(self, *args, **options):
        accounts = [
            ("admin@oes.local", "Admin@12345", "Administrator", User.ROLE_ADMIN),
            ("faculty@oes.local", "Faculty@12345", "Faculty User", User.ROLE_FACULTY),
            ("student@oes.local", "Student@12345", "Student User", User.ROLE_STUDENT),
            ("student2@oes.local", "Student@12345", "Second Student", User.ROLE_STUDENT),
            ("student3@oes.local", "Student@12345", "Third Student", User.ROLE_STUDENT),
        ]
        users = {}
        for email, password, name, role in accounts:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email=email, password=password, name=name, role=role, active=True)
            else:
                user.name = name
                user.role = role
                user.active = True
                user.set_password(password)
                user.save()
            users[email] = user
        faculty = users["faculty@oes.local"]

        operating, _ = Subject.objects.get_or_create(name="Operating Systems")
        databases, _ = Subject.objects.get_or_create(name="Database Management Systems")
        processes, _ = Topic.objects.get_or_create(subject=operating, name="Processes")
        memory, _ = Topic.objects.get_or_create(subject=operating, name="Memory")
        keys, _ = Topic.objects.get_or_create(subject=databases, name="Keys")

        def mcq(subject, topic, text, options, correct, difficulty, marks="2.00"):
            question = Question.objects.filter(text=text).first()
            if question is None:
                question = Question.objects.create(
                    subject=subject,
                    topic=topic,
                    type=Question.TYPE_MCQ,
                    text=text,
                    difficulty=difficulty,
                    marks=Decimal(marks),
                    explanation="Shown to the student only after the result is published.",
                    created_by=faculty,
                    active=True,
                )
                QuestionOption.objects.bulk_create(
                    [
                        QuestionOption(question=question, option_text=label, is_correct=index == correct)
                        for index, label in enumerate(options)
                    ]
                )
            return question

        def descriptive(subject, topic, text):
            question = Question.objects.filter(text=text).first()
            if question is None:
                question = Question.objects.create(
                    subject=subject,
                    topic=topic,
                    type=Question.TYPE_DESCRIPTIVE,
                    text=text,
                    difficulty=Question.DIFFICULTY_MEDIUM,
                    marks=Decimal("2.00"),
                    created_by=faculty,
                    active=True,
                )
            return question

        paper = [
            mcq(
                operating,
                processes,
                "Which component of the operating system selects the next process to run?",
                ["Compiler", "Scheduler", "Linker", "Loader"],
                1,
                Question.DIFFICULTY_EASY,
            ),
            mcq(
                operating,
                processes,
                "A deadlock requires which of the following conditions?",
                ["Mutual exclusion", "Preemption", "A single process", "Infinite memory"],
                0,
                Question.DIFFICULTY_MEDIUM,
            ),
            mcq(
                operating,
                memory,
                "Paging is a technique used for:",
                ["CPU scheduling", "Deadlock prevention", "Virtual memory", "Disk formatting"],
                2,
                Question.DIFFICULTY_EASY,
            ),
            mcq(
                operating,
                memory,
                "Thrashing occurs when:",
                ["The CPU is idle", "Pages are faulted continuously", "A process terminates", "The disk is full"],
                1,
                Question.DIFFICULTY_HARD,
            ),
            descriptive(operating, processes, "Explain the difference between a process and a thread."),
        ]
        mcq(
            databases,
            keys,
            "A primary key must be:",
            ["Duplicate", "Nullable", "Unique and not null", "A foreign key only"],
            2,
            Question.DIFFICULTY_EASY,
        )

        now = timezone.now()
        exam = Exam.objects.filter(title="Operating Systems Midterm").first()
        if exam is None:
            exam = Exam.objects.create(
                subject=operating,
                title="Operating Systems Midterm",
                instructions="Answer every question. The paper is submitted when the timer ends.",
                start_at=now - timedelta(minutes=15),
                end_at=now + timedelta(hours=3),
                duration_minutes=30,
                pass_marks=Decimal("4.00"),
                negative_mark=Decimal("0.50"),
                status=Exam.STATUS_DRAFT,
                created_by=faculty,
            )
        else:
            exam.start_at = now - timedelta(minutes=15)
            exam.end_at = now + timedelta(hours=3)
            exam.save(update_fields=["start_at", "end_at"])

        if not exam.exam_questions.exists():
            if exam.status != Exam.STATUS_DRAFT:
                exam.status = Exam.STATUS_DRAFT
                exam.save(update_fields=["status"])
            ExamQuestion.objects.bulk_create(
                [ExamQuestion(exam=exam, question=question) for question in paper]
            )
            publish_exam(exam, faculty)
        elif exam.status == Exam.STATUS_DRAFT:
            publish_exam(exam, faculty)

        exam.refresh_from_db()
        self._demonstrate_attempts(exam, paper, users["student@oes.local"], users["student3@oes.local"], faculty)

        if not Exam.objects.filter(title="Database Quiz (Draft)").exists():
            Exam.objects.create(
                subject=databases,
                title="Database Quiz (Draft)",
                instructions="Draft exam. Students cannot see it.",
                start_at=now + timedelta(days=1),
                end_at=now + timedelta(days=1, hours=2),
                duration_minutes=20,
                pass_marks=Decimal("2.00"),
                negative_mark=Decimal("0.00"),
                status=Exam.STATUS_DRAFT,
                created_by=faculty,
            )

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        for email, password, _name, role in accounts:
            self.stdout.write(f"{role}: {email} / {password}")

    def _demonstrate_attempts(self, exam, paper, student, pending_student, faculty):
        if exam.status != Exam.STATUS_PUBLISHED:
            return
        descriptive = next(question for question in paper if question.type == Question.TYPE_DESCRIPTIVE)
        if not ExamAttempt.objects.filter(exam=exam, user=student).exists():
            attempt = start_attempt(exam, student)
            answers = []
            for index, question in enumerate(paper):
                if question.type != Question.TYPE_MCQ:
                    answers.append(
                        {
                            "question_id": question.id,
                            "descriptive_text": "A process has its own address space. Threads inside it share that space.",
                        }
                    )
                    continue
                option = question.options.filter(is_correct=(index != 1)).first()
                answers.append({"question_id": question.id, "selected_option_id": option.id})
            save_answers(attempt, answers, student)
            submit_attempt(attempt)
            attempt.refresh_from_db()
            result = award_descriptive(
                attempt,
                [{"question_id": descriptive.id, "awarded_marks": Decimal("2.00")}],
                faculty,
            )
            publish_result(result, faculty)
        if not ExamAttempt.objects.filter(exam=exam, user=pending_student).exists():
            attempt = start_attempt(exam, pending_student)
            answers = []
            for question in paper:
                if question.type != Question.TYPE_MCQ:
                    continue
                option = question.options.filter(is_correct=True).first()
                answers.append({"question_id": question.id, "selected_option_id": option.id})
            save_answers(attempt, answers, pending_student)
            submit_attempt(attempt)
