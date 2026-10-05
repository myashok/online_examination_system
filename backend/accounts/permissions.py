from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "active", False)
            and user.role in self.allowed_roles
        )


class IsAdmin(HasRole):
    allowed_roles = ("ADMIN",)


class IsFacultyOrAdmin(HasRole):
    allowed_roles = ("FACULTY", "ADMIN")


class IsStudent(HasRole):
    allowed_roles = ("STUDENT",)


class IsAnyRole(HasRole):
    allowed_roles = ("STUDENT", "FACULTY", "ADMIN")
