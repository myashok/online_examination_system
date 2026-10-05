from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAnyRole, IsFacultyOrAdmin
from catalog.models import Question, Subject, Topic
from catalog.serializers import QuestionSerializer, SubjectSerializer, TopicSerializer


def _missing():
    return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class SubjectListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAnyRole()]
        return [IsFacultyOrAdmin()]

    def get(self, request):
        return Response(SubjectSerializer(Subject.objects.all(), many=True).data)

    def post(self, request):
        serializer = SubjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SubjectDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAnyRole()]
        return [IsFacultyOrAdmin()]

    def get(self, request, pk):
        subject = Subject.objects.filter(pk=pk).first()
        if subject is None:
            return _missing()
        return Response(SubjectSerializer(subject).data)

    def patch(self, request, pk):
        subject = Subject.objects.filter(pk=pk).first()
        if subject is None:
            return _missing()
        serializer = SubjectSerializer(subject, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        subject = Subject.objects.filter(pk=pk).first()
        if subject is None:
            return _missing()
        try:
            subject.delete()
        except ProtectedError:
            return Response(
                {"detail": "Subject is in use and cannot be deleted"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TopicListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAnyRole()]
        return [IsFacultyOrAdmin()]

    def get(self, request):
        topics = Topic.objects.select_related("subject")
        subject_id = request.query_params.get("subject")
        if subject_id:
            topics = topics.filter(subject_id=subject_id)
        return Response(TopicSerializer(topics, many=True).data)

    def post(self, request):
        serializer = TopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TopicDetailView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def patch(self, request, pk):
        topic = Topic.objects.filter(pk=pk).first()
        if topic is None:
            return _missing()
        serializer = TopicSerializer(topic, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        topic = Topic.objects.filter(pk=pk).first()
        if topic is None:
            return _missing()
        try:
            topic.delete()
        except ProtectedError:
            return Response(
                {"detail": "Topic is in use and cannot be deleted"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionListCreateView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request):
        questions = Question.objects.select_related("subject", "topic", "created_by").prefetch_related(
            "options"
        )
        filters = {
            "subject": "subject_id",
            "topic": "topic_id",
            "type": "type",
            "difficulty": "difficulty",
        }
        for param, field in filters.items():
            value = request.query_params.get(param)
            if value:
                questions = questions.filter(**{field: value})
        active = request.query_params.get("active")
        if active in {"true", "false"}:
            questions = questions.filter(active=active == "true")
        search = (request.query_params.get("q") or request.query_params.get("search") or "").strip()
        if search:
            questions = questions.filter(text__icontains=search)
        return Response(QuestionSerializer(questions.order_by("id"), many=True).data)

    def post(self, request):
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.save(created_by=request.user)
        return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)


class QuestionDetailView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get_object(self, pk):
        return (
            Question.objects.select_related("subject", "topic", "created_by")
            .prefetch_related("options")
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk):
        question = self.get_object(pk)
        if question is None:
            return _missing()
        return Response(QuestionSerializer(question).data)

    def patch(self, request, pk):
        question = self.get_object(pk)
        if question is None:
            return _missing()
        serializer = QuestionSerializer(question, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        question.refresh_from_db()
        return Response(QuestionSerializer(self.get_object(pk)).data)

    def delete(self, request, pk):
        question = self.get_object(pk)
        if question is None:
            return _missing()
        try:
            question.delete()
        except ProtectedError:
            return Response(
                {"detail": "Question is on an exam or attempt and cannot be deleted"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionActiveView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk, active):
        question = Question.objects.filter(pk=pk).first()
        if question is None:
            return _missing()
        question.active = active
        question.save(update_fields=["active"])
        return Response(QuestionSerializer(question).data)
