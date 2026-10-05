from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdmin, IsAnyRole, IsFacultyOrAdmin, IsStudent
from catalog.models import Question
from examination.models import Exam, ExamAttempt, ExamQuestion, Result
from examination.reports import (
    admin_summary,
    admin_summary_csv,
    faculty_exam_csv,
    faculty_exam_report,
    faculty_topic_analysis,
    student_history,
    student_history_csv,
)
from examination.serializers import (
    DrawSerializer,
    ExamReadSerializer,
    ExamWriteSerializer,
    MarksSerializer,
    SaveAnswersSerializer,
)
from examination.services import (
    ExamRuleError,
    add_exam_question,
    attempt_payload,
    award_descriptive,
    close_exam,
    draw_questions,
    ensure_open,
    paper_total,
    publish_exam,
    publish_result,
    remove_exam_question,
    save_answers,
    start_attempt,
    submit_attempt,
    unpublish_exam,
)


def _rule_response(exc):
    return Response({"detail": exc.message}, status=exc.status)


def _exam_or_404(pk):
    return Exam.objects.select_related("subject", "created_by").filter(pk=pk).first()


class ExamListCreateView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request):
        exams = Exam.objects.select_related("subject", "created_by").order_by("-id")
        status_filter = request.query_params.get("status")
        if status_filter:
            exams = exams.filter(status=status_filter)
        subject = request.query_params.get("subject")
        if subject:
            exams = exams.filter(subject_id=subject)
        return Response(ExamReadSerializer(exams, many=True).data)

    def post(self, request):
        serializer = ExamWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam = serializer.save(created_by=request.user, status=Exam.STATUS_DRAFT)
        return Response(ExamReadSerializer(exam).data, status=status.HTTP_201_CREATED)


class ExamDetailView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        data = ExamReadSerializer(exam).data
        links = ExamQuestion.objects.filter(exam=exam).select_related(
            "question__topic",
            "question__subject",
        ).prefetch_related("question__options")
        data["questions"] = [
            {
                "id": link.question_id,
                "text": link.question.text,
                "type": link.question.type,
                "difficulty": link.question.difficulty,
                "marks": str(link.question.marks),
                "topic": link.question.topic.name,
                "active": link.question.active,
                "options": [
                    {
                        "id": option.id,
                        "option_text": option.option_text,
                        "is_correct": option.is_correct,
                    }
                    for option in link.question.options.all()
                ],
            }
            for link in links
        ]
        data["total_marks"] = str(paper_total(exam))
        return Response(data)

    def patch(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        if exam.status != Exam.STATUS_DRAFT:
            return Response(
                {"detail": "Only a draft exam can be edited"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ExamWriteSerializer(exam, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ExamReadSerializer(exam).data)

    def delete(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        if exam.status != Exam.STATUS_DRAFT or exam.attempts.exists():
            return Response(
                {"detail": "Only a draft exam without attempts can be deleted"},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            exam.delete()
        except ProtectedError:
            return Response(
                {"detail": "Exam cannot be deleted"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExamQuestionAddView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        question = Question.objects.filter(pk=request.data.get("question_id")).first()
        if question is None:
            return Response({"detail": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            add_exam_question(exam, question)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(ExamReadSerializer(exam).data, status=status.HTTP_201_CREATED)


class ExamQuestionRemoveView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def delete(self, request, exam_id, question_id):
        exam = _exam_or_404(exam_id)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            remove_exam_question(exam, question_id)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExamDrawView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = DrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            draw_questions(
                exam,
                easy=data["easy"],
                medium=data["medium"],
                hard=data["hard"],
                descriptive=data["descriptive"],
                replace=data["replace"],
            )
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(ExamReadSerializer(exam).data)


class ExamPublishView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            publish_exam(exam, request.user)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(ExamReadSerializer(exam).data)


class ExamCloseView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            close_exam(exam)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(ExamReadSerializer(exam).data)


class ExamUnpublishView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            unpublish_exam(exam)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(ExamReadSerializer(exam).data)


class StudentExamListView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        now = timezone.now()
        exams = Exam.objects.filter(status__in=[Exam.STATUS_PUBLISHED, Exam.STATUS_CLOSED]).select_related(
            "subject"
        )
        attempts = {
            attempt.exam_id: attempt
            for attempt in ExamAttempt.objects.filter(user=request.user).select_related("exam")
        }
        results = {
            result.exam_id: result
            for result in Result.objects.filter(user=request.user)
        }
        rows = []
        for exam in exams.order_by("start_at"):
            attempt = attempts.get(exam.id)
            result = results.get(exam.id)
            if attempt and attempt.status == ExamAttempt.STATUS_IN_PROGRESS:
                attempt = ensure_open(attempt)
            if attempt is None:
                if exam.status != Exam.STATUS_PUBLISHED:
                    continue
                if now < exam.start_at:
                    state = "UPCOMING"
                elif now >= exam.end_at:
                    state = "MISSED"
                else:
                    state = "AVAILABLE"
            elif attempt.status == ExamAttempt.STATUS_IN_PROGRESS:
                state = "IN_PROGRESS"
            else:
                state = attempt.status
            rows.append(
                {
                    "id": exam.id,
                    "title": exam.title,
                    "subject": exam.subject.name,
                    "instructions": exam.instructions,
                    "start_at": exam.start_at,
                    "end_at": exam.end_at,
                    "duration_minutes": exam.duration_minutes,
                    "pass_marks": str(exam.pass_marks),
                    "negative_mark": str(exam.negative_mark),
                    "status": exam.status,
                    "state": state,
                    "attempt_id": attempt.id if attempt else None,
                    "total_marks": str(paper_total(exam)),
                    "question_count": exam.exam_questions.count(),
                    "result_published": bool(result and result.published),
                }
            )
        return Response(rows)


class ExamStartView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, pk):
        exam = _exam_or_404(pk)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            attempt = start_attempt(exam, request.user)
            payload = attempt_payload(attempt, reveal=False)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(payload, status=status.HTTP_201_CREATED)


class AttemptListView(APIView):
    permission_classes = [IsAnyRole]

    def get(self, request):
        attempts = ExamAttempt.objects.select_related("exam", "user").order_by("-started_at")
        if request.user.role == User.ROLE_STUDENT:
            attempts = attempts.filter(user=request.user)
        exam_id = request.query_params.get("exam")
        if exam_id:
            attempts = attempts.filter(exam_id=exam_id)
        return Response(
            [
                {
                    "id": attempt.id,
                    "exam_id": attempt.exam_id,
                    "exam_title": attempt.exam.title,
                    "user_id": attempt.user_id,
                    "user_name": attempt.user.name,
                    "user_email": attempt.user.email,
                    "status": attempt.status,
                    "started_at": attempt.started_at,
                    "submitted_at": attempt.submitted_at,
                }
                for attempt in attempts
            ]
        )


def _load_attempt(pk):
    return (
        ExamAttempt.objects.select_related("exam__subject", "user")
        .filter(pk=pk)
        .first()
    )


class AttemptDetailView(APIView):
    permission_classes = [IsAnyRole]

    def get(self, request, pk):
        attempt = _load_attempt(pk)
        if attempt is None:
            return Response({"detail": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role == User.ROLE_STUDENT and attempt.user_id != request.user.id:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role != User.ROLE_STUDENT and attempt.status == ExamAttempt.STATUS_IN_PROGRESS:
            return Response(
                {"detail": "This attempt is still in progress"},
                status=status.HTTP_403_FORBIDDEN,
            )
        reveal = False
        if request.user.role == User.ROLE_STUDENT:
            result = Result.objects.filter(attempt=attempt).first()
            if attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
                if result and result.published:
                    reveal = True
                else:
                    return Response(
                        {"detail": "The result is not published yet", "status": attempt.status},
                        status=status.HTTP_403_FORBIDDEN,
                    )
        else:
            reveal = True
        return Response(attempt_payload(attempt, reveal=reveal))


class AttemptSaveView(APIView):
    permission_classes = [IsStudent]

    def put(self, request, pk):
        attempt = _load_attempt(pk)
        if attempt is None or attempt.user_id != request.user.id:
            return Response({"detail": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = SaveAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attempt = save_answers(attempt, serializer.validated_data["answers"], request.user)
            payload = attempt_payload(attempt, reveal=False)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(payload)


class AttemptSubmitView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, pk):
        attempt = _load_attempt(pk)
        if attempt is None or attempt.user_id != request.user.id:
            return Response({"detail": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            attempt = submit_attempt(attempt, auto=False)
        except ExamRuleError as exc:
            return _rule_response(exc)
        result = Result.objects.filter(attempt=attempt).first()
        return Response(
            {
                "id": attempt.id,
                "status": attempt.status,
                "submitted_at": attempt.submitted_at,
                "result_ready": result is not None,
                "published": bool(result and result.published),
            }
        )


class EvaluationQueueView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request):
        exam_id = request.query_params.get("exam")
        pending = ExamAttempt.objects.filter(status=ExamAttempt.STATUS_SUBMITTED).select_related(
            "exam",
            "user",
        )
        ready = Result.objects.filter(published=False).select_related("attempt", "exam", "user")
        if exam_id:
            pending = pending.filter(exam_id=exam_id)
            ready = ready.filter(exam_id=exam_id)
        return Response(
            {
                "needs_marking": [
                    {
                        "attempt_id": attempt.id,
                        "exam_id": attempt.exam_id,
                        "exam_title": attempt.exam.title,
                        "student": attempt.user.name,
                        "email": attempt.user.email,
                        "submitted_at": attempt.submitted_at,
                        "stage": "NEEDS_MARKING",
                    }
                    for attempt in pending.order_by("submitted_at")
                ],
                "ready_to_publish": [
                    {
                        "attempt_id": result.attempt_id,
                        "result_id": result.id,
                        "exam_id": result.exam_id,
                        "exam_title": result.exam.title,
                        "student": result.user.name,
                        "email": result.user.email,
                        "total_marks": str(result.total_marks),
                        "max_marks": str(result.max_marks),
                        "status": result.status,
                        "stage": "READY_TO_PUBLISH",
                    }
                    for result in ready.order_by("generated_at")
                ],
            }
        )


class EvaluationDetailView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request, pk):
        attempt = _load_attempt(pk)
        if attempt is None:
            return Response({"detail": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)
        if attempt.status == ExamAttempt.STATUS_IN_PROGRESS:
            return Response(
                {"detail": "This attempt is still in progress"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = attempt_payload(attempt, reveal=True)
        result = Result.objects.filter(attempt=attempt).first()
        payload["result"] = None
        if result:
            payload["result"] = {
                "id": result.id,
                "objective_marks": str(result.objective_marks),
                "descriptive_marks": str(result.descriptive_marks),
                "total_marks": str(result.total_marks),
                "max_marks": str(result.max_marks),
                "status": result.status,
                "published": result.published,
                "generated_at": result.generated_at,
            }
        payload["student"] = {"id": attempt.user_id, "name": attempt.user.name, "email": attempt.user.email}
        return Response(payload)


class EvaluationMarksView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk):
        attempt = _load_attempt(pk)
        if attempt is None:
            return Response({"detail": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = MarksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = award_descriptive(attempt, serializer.validated_data["marks"], request.user)
        except ExamRuleError as exc:
            return _rule_response(exc)
        body = {"attempt_id": attempt.id, "result": None}
        if result:
            attempt.refresh_from_db()
            body["attempt_status"] = attempt.status
            body["result"] = {
                "id": result.id,
                "objective_marks": str(result.objective_marks),
                "descriptive_marks": str(result.descriptive_marks),
                "total_marks": str(result.total_marks),
                "max_marks": str(result.max_marks),
                "status": result.status,
                "published": result.published,
            }
        else:
            attempt.refresh_from_db()
            body["attempt_status"] = attempt.status
        return Response(body)


class MyResultsView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        return Response(student_history(request.user))


class MyResultDetailView(APIView):
    permission_classes = [IsStudent]

    def get(self, request, exam_id):
        result = (
            Result.objects.select_related("attempt__exam__subject", "attempt__user")
            .filter(user=request.user, exam_id=exam_id)
            .first()
        )
        if result is None or not result.published:
            return Response(
                {"detail": "Result is not published"},
                status=status.HTTP_403_FORBIDDEN,
            )
        payload = attempt_payload(result.attempt, reveal=True)
        payload["result"] = {
            "id": result.id,
            "objective_marks": str(result.objective_marks),
            "descriptive_marks": str(result.descriptive_marks),
            "total_marks": str(result.total_marks),
            "max_marks": str(result.max_marks),
            "status": result.status,
            "published": True,
            "pass_marks": str(result.exam.pass_marks),
            "generated_at": result.generated_at,
        }
        return Response(payload)


class ResultPublishView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def post(self, request, pk):
        result = Result.objects.select_related("attempt", "exam").filter(pk=pk).first()
        if result is None:
            return Response({"detail": "Result not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            publish_result(result, request.user)
        except ExamRuleError as exc:
            return _rule_response(exc)
        return Response(
            {
                "id": result.id,
                "published": result.published,
                "status": result.status,
                "total_marks": str(result.total_marks),
            }
        )


class StudentHistoryReportView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        return Response(student_history(request.user))


class StudentHistoryExportView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        return student_history_csv(request.user)


class StudentExamReportView(APIView):
    permission_classes = [IsStudent]

    def get(self, request, exam_id):
        view = MyResultDetailView()
        return view.get(request, exam_id)


class FacultyExamReportView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request, exam_id):
        exam = _exam_or_404(exam_id)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(faculty_exam_report(exam))


class FacultyExamExportView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request, exam_id):
        exam = _exam_or_404(exam_id)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        return faculty_exam_csv(exam)


class FacultyAnalysisView(APIView):
    permission_classes = [IsFacultyOrAdmin]

    def get(self, request, exam_id):
        exam = _exam_or_404(exam_id)
        if exam is None:
            return Response({"detail": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(faculty_topic_analysis(exam))


class AdminSummaryView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(admin_summary())


class AdminSummaryExportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return admin_summary_csv()
