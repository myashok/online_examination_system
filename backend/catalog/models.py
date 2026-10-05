from django.conf import settings
from django.db import models


class Subject(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        db_table = "subjects"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="topics")
    name = models.CharField(max_length=150)

    class Meta:
        db_table = "topics"
        constraints = [
            models.UniqueConstraint(fields=["subject", "name"], name="topic_subject_name_uniq"),
        ]
        ordering = ["subject_id", "name"]

    def __str__(self):
        return f"{self.subject.name}: {self.name}"


class Question(models.Model):
    TYPE_MCQ = "MCQ"
    TYPE_DESCRIPTIVE = "DESCRIPTIVE"
    TYPE_CHOICES = [
        (TYPE_MCQ, "MCQ"),
        (TYPE_DESCRIPTIVE, "Descriptive"),
    ]
    DIFFICULTY_EASY = "EASY"
    DIFFICULTY_MEDIUM = "MEDIUM"
    DIFFICULTY_HARD = "HARD"
    DIFFICULTY_CHOICES = [
        (DIFFICULTY_EASY, "Easy"),
        (DIFFICULTY_MEDIUM, "Medium"),
        (DIFFICULTY_HARD, "Hard"),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="questions")
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name="questions")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    marks = models.DecimalField(max_digits=6, decimal_places=2)
    explanation = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="questions",
    )
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "questions"
        indexes = [
            models.Index(fields=["subject", "type", "difficulty"], name="question_bank_idx"),
            models.Index(fields=["active"], name="question_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(type__in=["MCQ", "DESCRIPTIVE"]),
                name="question_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(difficulty__in=["EASY", "MEDIUM", "HARD"]),
                name="question_difficulty_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(marks__gt=0),
                name="question_marks_positive",
            ),
        ]

    def __str__(self):
        return f"{self.type} {self.id}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "question_options"

    def __str__(self):
        return self.option_text[:40]
