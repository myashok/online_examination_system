from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok", "application": "ONLINE EXAMINATION SYSTEM"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("accounts.auth_urls")),
    path("api/users/", include("accounts.user_urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("examination.urls")),
    path("api/audit-logs/", include("auditlog.urls")),
]

admin.site.site_header = "ONLINE EXAMINATION SYSTEM"
admin.site.site_title = "ONLINE EXAMINATION SYSTEM"
