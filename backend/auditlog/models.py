from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    ACTION_LOGIN = "LOGIN"
    ACTION_START = "START"
    ACTION_SAVE = "SAVE"
    ACTION_SUBMIT = "SUBMIT"
    ACTION_EVALUATE = "EVALUATE"
    ACTION_PUBLISH = "PUBLISH"
    ACTION_CHOICES = [
        (ACTION_LOGIN, "Login"),
        (ACTION_START, "Start"),
        (ACTION_SAVE, "Save"),
        (ACTION_SUBMIT, "Submit"),
        (ACTION_EVALUATE, "Evaluate"),
        (ACTION_PUBLISH, "Publish"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    entity = models.CharField(max_length=32)
    entity_id = models.PositiveBigIntegerField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)
    detail = models.TextField(blank=True, default="")

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["user", "at"], name="audit_user_at_idx"),
            models.Index(fields=["action"], name="audit_action_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    action__in=["LOGIN", "START", "SAVE", "SUBMIT", "EVALUATE", "PUBLISH"]
                ),
                name="audit_action_valid",
            ),
        ]

    def __str__(self):
        return f"{self.action} {self.entity}:{self.entity_id}"
