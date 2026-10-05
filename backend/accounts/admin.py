from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "active", "created_at")
    search_fields = ("name", "email")
    list_filter = ("role", "active")
