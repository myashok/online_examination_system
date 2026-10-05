from django.urls import path

from accounts.views import LoginView, MeView, RefreshView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("refresh/", RefreshView.as_view()),
    path("me/", MeView.as_view()),
]
