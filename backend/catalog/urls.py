from django.urls import path

from catalog.views import (
    QuestionActiveView,
    QuestionDetailView,
    QuestionListCreateView,
    SubjectDetailView,
    SubjectListCreateView,
    TopicDetailView,
    TopicListCreateView,
)

urlpatterns = [
    path("subjects/", SubjectListCreateView.as_view()),
    path("subjects/<int:pk>/", SubjectDetailView.as_view()),
    path("topics/", TopicListCreateView.as_view()),
    path("topics/<int:pk>/", TopicDetailView.as_view()),
    path("questions/", QuestionListCreateView.as_view()),
    path("questions/<int:pk>/", QuestionDetailView.as_view()),
    path(
        "questions/<int:pk>/activate/",
        QuestionActiveView.as_view(),
        {"active": True},
    ),
    path(
        "questions/<int:pk>/deactivate/",
        QuestionActiveView.as_view(),
        {"active": False},
    ),
]
