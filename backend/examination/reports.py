import csv
import io
from decimal import Decimal

from django.db.models import Avg, Count, Max, Min, Q
from django.http import HttpResponse
from django.utils import timezone

from accounts.models import User
from catalog.models import Question
from examination.models import AttemptAnswer, AttemptQuestion, Exam, ExamAttempt, Result
from examination.services import money


def faculty_exam_report(exam):
    attempts = ExamAttempt.objects.filter(exam=exam)
    published = Result.objects.filter(exam=exam, published=True)
    aggregate = published.aggregate(
        average=Avg("total_marks"),
        highest=Max("total_marks"),
        lowest=Min("total_marks"),
    )
    students = User.objects.filter(role=User.ROLE_STUDENT, active=True).count()
    submitted = attempts.exclude(status=ExamAttempt.STATUS_IN_PROGRESS).count()
    return {
        "exam_id": exam.id,
        "title": exam.title,
        "subject": exam.subject.name,
        "status": exam.status,
        "registered_students": students,
        "started": attempts.count(),
        "submitted": submitted,
        "in_progress": attempts.filter(status=ExamAttempt.STATUS_IN_PROGRESS).count(),
        "evaluated": attempts.filter(status=ExamAttempt.STATUS_EVALUATED).count(),
        "published": published.count(),
        "pass_count": published.filter(status=Result.STATUS_PASS).count(),
        "fail_count": published.filter(status=Result.STATUS_FAIL).count(),
        "average_total": money(aggregate["average"]) if aggregate["average"] is not None else None,
        "highest": money(aggregate["highest"]) if aggregate["highest"] is not None else None,
        "lowest": money(aggregate["lowest"]) if aggregate["lowest"] is not None else None,
        "pass_marks": money(exam.pass_marks),
        "participation_rate": (
            str((Decimal(submitted) / Decimal(students)).quantize(Decimal("0.0001")))
            if students
            else None
        ),
        "candidates": faculty_candidate_rows(exam),
    }


def faculty_candidate_rows(exam):
    attempts = (
        ExamAttempt.objects.filter(exam=exam)
        .select_related("user")
        .order_by("user__name", "id")
    )
    results = {
        result.attempt_id: result
        for result in Result.objects.filter(exam=exam)
    }
    rows = []
    for attempt in attempts:
        result = results.get(attempt.id)
        rows.append(
            {
                "attempt_id": attempt.id,
                "student_name": attempt.user.name,
                "student_email": attempt.user.email,
                "attempt_status": attempt.status,
                "started_at": attempt.started_at,
                "submitted_at": attempt.submitted_at,
                "objective_marks": money(result.objective_marks) if result else None,
                "descriptive_marks": money(result.descriptive_marks) if result else None,
                "total_marks": money(result.total_marks) if result else None,
                "max_marks": money(result.max_marks) if result else None,
                "result_status": result.status if result else None,
                "published": bool(result and result.published),
            }
        )
    return rows


def faculty_topic_analysis(exam):
    answers = AttemptAnswer.objects.filter(
        attempt__exam=exam,
        awarded_marks__isnull=False,
    ).select_related("question__topic")
    paper = AttemptQuestion.objects.filter(attempt__exam=exam).select_related("question__topic")
    grouped = {}
    for slot in paper:
        question = slot.question
        key = (question.topic_id, question.difficulty, question.type)
        bucket = grouped.setdefault(
            key,
            {
                "topic": question.topic.name,
                "difficulty": question.difficulty,
                "type": question.type,
                "question_ids": set(),
                "responses": 0,
                "correct": 0,
                "awarded": Decimal("0"),
                "possible": Decimal("0"),
            },
        )
        bucket["question_ids"].add(question.id)
    for answer in answers:
        question = answer.question
        key = (question.topic_id, question.difficulty, question.type)
        bucket = grouped.get(key)
        if bucket is None:
            continue
        bucket["responses"] += 1
        bucket["awarded"] += answer.awarded_marks
        bucket["possible"] += question.marks
        if question.type == Question.TYPE_MCQ and answer.awarded_marks == question.marks:
            bucket["correct"] += 1
    rows = []
    for bucket in grouped.values():
        possible = bucket["possible"]
        rows.append(
            {
                "topic": bucket["topic"],
                "difficulty": bucket["difficulty"],
                "type": bucket["type"],
                "questions": len(bucket["question_ids"]),
                "responses": bucket["responses"],
                "correct": bucket["correct"],
                "average_awarded": money(
                    bucket["awarded"] / bucket["responses"] if bucket["responses"] else Decimal("0")
                ),
                "average_percent": money(
                    (bucket["awarded"] / possible * Decimal("100")) if possible else Decimal("0")
                ),
            }
        )
    rows.sort(key=lambda row: (row["topic"], row["difficulty"], row["type"]))
    return {"exam_id": exam.id, "title": exam.title, "rows": rows}


def admin_summary():
    exams = Exam.objects.select_related("subject").order_by("id")
    rows = []
    for exam in exams:
        report = faculty_exam_report(exam)
        report.pop("candidates", None)
        rows.append(report)
    totals = Result.objects.filter(published=True).aggregate(
        published=Count("id"),
        average=Avg("total_marks"),
        passes=Count("id", filter=Q(status=Result.STATUS_PASS)),
        fails=Count("id", filter=Q(status=Result.STATUS_FAIL)),
    )
    return {
        "exams": rows,
        "published_results": totals["published"],
        "pass_count": totals["passes"],
        "fail_count": totals["fails"],
        "average_total": money(totals["average"]) if totals["average"] is not None else None,
    }


def _csv_response(filename, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(row)
    payload = "\ufeff" + buffer.getvalue()
    response = HttpResponse(payload, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def faculty_exam_csv(exam):
    summary = faculty_exam_report(exam)
    analysis = faculty_topic_analysis(exam)
    generated = timezone.now().isoformat(timespec="seconds")
    rows = [
        ["ONLINE EXAMINATION SYSTEM"],
        ["Exam performance summary"],
        ["Generated at", generated],
        [],
        ["Exam ID", summary["exam_id"]],
        ["Title", summary["title"]],
        ["Subject", summary["subject"]],
        ["Status", summary["status"]],
        ["Pass marks", summary["pass_marks"]],
        ["Registered students", summary["registered_students"]],
        ["Started", summary["started"]],
        ["Submitted", summary["submitted"]],
        ["In progress", summary["in_progress"]],
        ["Evaluated", summary["evaluated"]],
        ["Published results", summary["published"]],
        ["Pass count", summary["pass_count"]],
        ["Fail count", summary["fail_count"]],
        ["Average total", summary["average_total"] or ""],
        ["Highest", summary["highest"] or ""],
        ["Lowest", summary["lowest"] or ""],
        ["Participation rate", summary["participation_rate"] or ""],
        [],
        ["Candidate results"],
        [
            "Student",
            "Email",
            "Attempt status",
            "Started at",
            "Submitted at",
            "Objective",
            "Descriptive",
            "Total",
            "Max",
            "Result",
            "Published",
        ],
    ]
    for candidate in summary["candidates"]:
        rows.append(
            [
                candidate["student_name"],
                candidate["student_email"],
                candidate["attempt_status"],
                candidate["started_at"] or "",
                candidate["submitted_at"] or "",
                candidate["objective_marks"] or "",
                candidate["descriptive_marks"] or "",
                candidate["total_marks"] or "",
                candidate["max_marks"] or "",
                candidate["result_status"] or "",
                "Yes" if candidate["published"] else "No",
            ]
        )
    rows.extend(
        [
            [],
            ["Topic and difficulty analysis"],
            [
                "Topic",
                "Difficulty",
                "Type",
                "Questions",
                "Responses",
                "Correct",
                "Average awarded",
                "Average percent",
            ],
        ]
    )
    for row in analysis["rows"]:
        rows.append(
            [
                row["topic"],
                row["difficulty"],
                row["type"],
                row["questions"],
                row["responses"],
                row["correct"],
                row["average_awarded"],
                row["average_percent"],
            ]
        )
    slug = "".join(ch if ch.isalnum() else "-" for ch in exam.title).strip("-").lower() or "exam"
    return _csv_response(f"{slug}-{exam.id}-report.csv", rows)


def admin_summary_csv():
    summary = admin_summary()
    generated = timezone.now().isoformat(timespec="seconds")
    rows = [
        ["ONLINE EXAMINATION SYSTEM"],
        ["Institution performance summary"],
        ["Generated at", generated],
        [],
        ["Published results", summary["published_results"]],
        ["Pass count", summary["pass_count"]],
        ["Fail count", summary["fail_count"]],
        ["Average total", summary["average_total"] or ""],
        [],
        [
            "Exam ID",
            "Title",
            "Subject",
            "Status",
            "Registered",
            "Started",
            "Submitted",
            "Pass",
            "Fail",
            "Average",
            "Highest",
            "Lowest",
            "Participation rate",
        ],
    ]
    for exam in summary["exams"]:
        rows.append(
            [
                exam["exam_id"],
                exam["title"],
                exam["subject"],
                exam["status"],
                exam["registered_students"],
                exam["started"],
                exam["submitted"],
                exam["pass_count"],
                exam["fail_count"],
                exam["average_total"] or "",
                exam["highest"] or "",
                exam["lowest"] or "",
                exam["participation_rate"] or "",
            ]
        )
    return _csv_response("institution-summary.csv", rows)


def student_history(user):
    attempts = (
        ExamAttempt.objects.filter(user=user)
        .select_related("exam__subject")
        .order_by("-started_at")
    )
    results = {
        result.attempt_id: result
        for result in Result.objects.filter(user=user)
    }
    rows = []
    for attempt in attempts:
        result = results.get(attempt.id)
        published = bool(result and result.published)
        rows.append(
            {
                "attempt_id": attempt.id,
                "exam_id": attempt.exam_id,
                "title": attempt.exam.title,
                "subject": attempt.exam.subject.name,
                "attempt_status": attempt.status,
                "started_at": attempt.started_at,
                "submitted_at": attempt.submitted_at,
                "published": published,
                "result_status": result.status if published else None,
                "total_marks": money(result.total_marks) if published else None,
                "max_marks": money(result.max_marks) if published else None,
                "objective_marks": money(result.objective_marks) if published else None,
                "descriptive_marks": money(result.descriptive_marks) if published else None,
                "pass_marks": money(attempt.exam.pass_marks),
            }
        )
    return rows


def student_history_csv(user):
    rows = [
        ["ONLINE EXAMINATION SYSTEM"],
        ["Student examination history"],
        ["Student", user.name],
        ["Email", user.email],
        ["Generated at", timezone.now().isoformat(timespec="seconds")],
        [],
        [
            "Exam ID",
            "Exam Title",
            "Subject",
            "Attempt Status",
            "Started At",
            "Submitted At",
            "Result",
            "Score",
            "Max Marks",
            "Objective Marks",
            "Descriptive Marks",
            "Pass Marks",
        ],
    ]
    history = student_history(user)
    for item in history:
        rows.append(
            [
                item["exam_id"],
                item["title"],
                item["subject"],
                item["attempt_status"],
                item["started_at"] or "",
                item["submitted_at"] or "",
                item["result_status"] or "Pending",
                item["total_marks"] or "",
                item["max_marks"] or "",
                item["objective_marks"] or "",
                item["descriptive_marks"] or "",
                item["pass_marks"] or "",
            ]
        )
    slug = "".join(ch if ch.isalnum() else "-" for ch in user.name).strip("-").lower() or "student"
    return _csv_response(f"{slug}-exam-history.csv", rows)
