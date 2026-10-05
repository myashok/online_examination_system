from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from accounts.managers import UserManager


class User(AbstractBaseUser):
    ROLE_STUDENT = "STUDENT"
    ROLE_FACULTY = "FACULTY"
    ROLE_ADMIN = "ADMIN"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_FACULTY, "Faculty"),
        (ROLE_ADMIN, "Admin"),
    ]

    password = models.CharField(max_length=128, db_column="password_hash")
    last_login = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"], name="user_role_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["STUDENT", "FACULTY", "ADMIN"]),
                name="user_role_valid",
            ),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_active(self):
        return self.active

    @is_active.setter
    def is_active(self, value):
        self.active = value

    @property
    def is_staff(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_superuser(self):
        return self.role == self.ROLE_ADMIN

    def has_perm(self, perm, obj=None):
        return self.role == self.ROLE_ADMIN

    def has_module_perms(self, app_label):
        return self.role == self.ROLE_ADMIN
