from django.conf import settings
from django.db import models


class Exam(models.Model):
    STATUS_DRAFT = "DRAFT"
    STATUS_PUBLISHED = "PUBLISHED"
    STATUS_CLOSED = "CLOSED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_CLOSED, "Closed"),
    ]

    subject = models.ForeignKey("catalog.Subject", on_delete=models.PROTECT, related_name="exams")
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True, default="")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2)
    negative_mark = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="exams",
    )

    class Meta:
        db_table = "exams"
        indexes = [
            models.Index(fields=["status", "start_at", "end_at"], name="exam_window_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="exam_window_order",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gt=0),
                name="exam_duration_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(pass_marks__gte=0),
                name="exam_pass_marks_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(negative_mark__gte=0),
                name="exam_negative_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "PUBLISHED", "CLOSED"]),
                name="exam_status_valid",
            ),
        ]

    def __str__(self):
        return self.title


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_questions")
    question = models.ForeignKey(
        "catalog.Question",
        on_delete=models.PROTECT,
        related_name="exam_links",
    )

    class Meta:
        db_table = "exam_questions"
        constraints = [
            models.UniqueConstraint(fields=["exam", "question"], name="exam_question_uniq"),
        ]


class ExamAttempt(models.Model):
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_EVALUATED = "EVALUATED"
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_EVALUATED, "Evaluated"),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="attempts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    started_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)

    class Meta:
        db_table = "exam_attempts"
        indexes = [
            models.Index(fields=["user"], name="attempt_user_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["exam", "user"], name="one_attempt_per_student"),
            models.CheckConstraint(
                condition=models.Q(status__in=["IN_PROGRESS", "SUBMITTED", "EVALUATED"]),
                name="attempt_status_valid",
            ),
        ]


class AttemptQuestion(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name="paper")
    question = models.ForeignKey(
        "catalog.Question",
        on_delete=models.PROTECT,
        related_name="attempt_links",
    )
    display_order = models.PositiveIntegerField()

    class Meta:
        db_table = "attempt_questions"
        ordering = ["display_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="attempt_question_uniq",
            ),
            models.UniqueConstraint(
                fields=["attempt", "display_order"],
                name="attempt_order_uniq",
            ),
        ]


class AttemptOptionOrder(models.Model):
    """Frozen MCQ option permutation for one question on one attempt."""

    attempt_question = models.ForeignKey(
        AttemptQuestion,
        on_delete=models.CASCADE,
        related_name="option_orders",
    )
    option = models.ForeignKey(
        "catalog.QuestionOption",
        on_delete=models.PROTECT,
        related_name="attempt_orders",
    )
    display_order = models.PositiveIntegerField()

    class Meta:
        db_table = "attempt_option_orders"
        ordering = ["display_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt_question", "option"],
                name="attempt_option_uniq",
            ),
            models.UniqueConstraint(
                fields=["attempt_question", "display_order"],
                name="attempt_option_order_uniq",
            ),
        ]


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("catalog.Question", on_delete=models.PROTECT, related_name="answers")
    selected_option = models.ForeignKey(
        "catalog.QuestionOption",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="selections",
    )
    descriptive_text = models.TextField(null=True, blank=True)
    marked_for_review = models.BooleanField(default=False)
    awarded_marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="evaluations",
    )
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attempt_answers"
        indexes = [
            models.Index(fields=["attempt"], name="answer_attempt_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="attempt_answer_uniq",
            ),
        ]


class Result(models.Model):
    STATUS_PASS = "PASS"
    STATUS_FAIL = "FAIL"
    STATUS_CHOICES = [
        (STATUS_PASS, "Pass"),
        (STATUS_FAIL, "Fail"),
    ]

    attempt = models.OneToOneField(ExamAttempt, on_delete=models.CASCADE, related_name="result")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="results",
    )
    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="results")
    objective_marks = models.DecimalField(max_digits=6, decimal_places=2)
    descriptive_marks = models.DecimalField(max_digits=6, decimal_places=2)
    total_marks = models.DecimalField(max_digits=6, decimal_places=2)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    published = models.BooleanField(default=False)
    generated_at = models.DateTimeField()

    class Meta:
        db_table = "results"
        constraints = [
            models.UniqueConstraint(fields=["user", "exam"], name="one_result_per_student_exam"),
            models.CheckConstraint(
                condition=models.Q(status__in=["PASS", "FAIL"]),
                name="result_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(objective_marks__gte=0),
                name="result_objective_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(descriptive_marks__gte=0),
                name="result_descriptive_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(total_marks__gte=0),
                name="result_total_non_negative",
            ),
        ]
