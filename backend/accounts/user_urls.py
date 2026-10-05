from django.urls import path

from accounts.views import UserDetailView, UserListCreateView

urlpatterns = [
    path("", UserListCreateView.as_view()),
    path("<int:pk>/", UserDetailView.as_view()),
]
