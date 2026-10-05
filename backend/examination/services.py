import random
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from auditlog.services import record_audit
from catalog.models import Question
from examination.models import (
    AttemptAnswer,
    AttemptOptionOrder,
    AttemptQuestion,
    Exam,
    ExamAttempt,
    ExamQuestion,
    Result,
)


class ExamRuleError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def paper_total(exam):
    total = ExamQuestion.objects.filter(exam=exam).aggregate(total=Sum("question__marks"))["total"]
    return total or Decimal("0.00")


def attempt_max_marks(attempt):
    total = AttemptQuestion.objects.filter(attempt=attempt).aggregate(total=Sum("question__marks"))[
        "total"
    ]
    return total or Decimal("0.00")


def deadline(attempt):
    duration_end = attempt.started_at + timedelta(minutes=attempt.exam.duration_minutes)
    return min(duration_end, attempt.exam.end_at)


def remaining_seconds(attempt):
    if attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        return 0
    remaining = (deadline(attempt) - timezone.now()).total_seconds()
    return max(0, int(remaining))


def money(value):
    if value is None:
        return None
    return str(Decimal(value).quantize(Decimal("0.01")))


def add_exam_question(exam, question):
    if exam.status != Exam.STATUS_DRAFT:
        raise ExamRuleError("Questions can only be changed while the exam is a draft")
    if question.subject_id != exam.subject_id:
        raise ExamRuleError("Question subject does not match the exam subject")
    if not question.active:
        raise ExamRuleError("Inactive questions cannot be added")
    if ExamQuestion.objects.filter(exam=exam, question=question).exists():
        raise ExamRuleError("Question is already on this exam")
    return ExamQuestion.objects.create(exam=exam, question=question)


def remove_exam_question(exam, question_id):
    if exam.status != Exam.STATUS_DRAFT:
        raise ExamRuleError("Questions can only be changed while the exam is a draft")
    deleted, _ = ExamQuestion.objects.filter(exam=exam, question_id=question_id).delete()
    if not deleted:
        raise ExamRuleError("Question is not on this exam", 404)


def draw_questions(exam, easy, medium, hard, descriptive, replace=True, rng=None):
    if exam.status != Exam.STATUS_DRAFT:
        raise ExamRuleError("Questions can only be drawn while the exam is a draft")
    counts = {
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "descriptive": descriptive,
    }
    for name, count in counts.items():
        if count < 0:
            raise ExamRuleError(f"{name} count cannot be negative")
    if easy + medium + hard + descriptive < 1:
        raise ExamRuleError("Draw at least one question")
    rng = rng or random.SystemRandom()
    specs = [
        (Question.TYPE_MCQ, Question.DIFFICULTY_EASY, easy),
        (Question.TYPE_MCQ, Question.DIFFICULTY_MEDIUM, medium),
        (Question.TYPE_MCQ, Question.DIFFICULTY_HARD, hard),
        (Question.TYPE_DESCRIPTIVE, None, descriptive),
    ]
    with transaction.atomic():
        if replace:
            ExamQuestion.objects.filter(exam=exam).delete()
        taken = set(ExamQuestion.objects.filter(exam=exam).values_list("question_id", flat=True))
        chosen = []
        for qtype, difficulty, count in specs:
            if count == 0:
                continue
            pool = Question.objects.filter(subject=exam.subject, active=True, type=qtype).exclude(
                id__in=taken
            )
            if difficulty:
                pool = pool.filter(difficulty=difficulty)
            pool = list(pool)
            label = f"{difficulty} {qtype}" if difficulty else qtype
            if len(pool) < count:
                raise ExamRuleError(f"Not enough active {label} questions in this subject")
            pick = rng.sample(pool, count)
            chosen.extend(pick)
            taken.update(question.id for question in pick)
        ExamQuestion.objects.bulk_create(
            [ExamQuestion(exam=exam, question=question) for question in chosen]
        )
    return chosen


def publish_exam(exam, actor):
    if exam.status != Exam.STATUS_DRAFT:
        raise ExamRuleError("Only a draft exam can be published")
    links = list(ExamQuestion.objects.filter(exam=exam).select_related("question"))
    if not links:
        raise ExamRuleError("Add at least one question before publishing")
    for link in links:
        if not link.question.active:
            raise ExamRuleError("Every question on the paper must be active")
        if link.question.subject_id != exam.subject_id:
            raise ExamRuleError("The paper contains a question from another subject")
    total = sum((link.question.marks for link in links), Decimal("0"))
    if exam.pass_marks > total:
        raise ExamRuleError("Pass marks cannot exceed the paper total")
    if exam.end_at <= timezone.now():
        raise ExamRuleError("The exam window has already ended")
    exam.status = Exam.STATUS_PUBLISHED
    exam.save(update_fields=["status"])
    record_audit(actor, "PUBLISH", "exam", exam.id, exam.title)
    return exam


def close_exam(exam):
    if exam.status != Exam.STATUS_PUBLISHED:
        raise ExamRuleError("Only a published exam can be closed")
    exam.status = Exam.STATUS_CLOSED
    exam.save(update_fields=["status"])
    return exam


def unpublish_exam(exam):
    if exam.status != Exam.STATUS_PUBLISHED:
        raise ExamRuleError("Only a published exam can return to draft")
    if ExamAttempt.objects.filter(exam=exam).exists():
        raise ExamRuleError("An exam that already has attempts cannot return to draft")
    exam.status = Exam.STATUS_DRAFT
    exam.save(update_fields=["status"])
    return exam


def freeze_paper(attempt, rng=None):
    rng = rng or random.SystemRandom()
    links = list(ExamQuestion.objects.filter(exam=attempt.exam).select_related("question"))
    if not links:
        raise ExamRuleError("Exam has no questions")
    rng.shuffle(links)
    for index, link in enumerate(links, start=1):
        attempt_question = AttemptQuestion.objects.create(
            attempt=attempt,
            question=link.question,
            display_order=index,
        )
        if link.question.type != Question.TYPE_MCQ:
            continue
        options = list(link.question.options.all())
        if len(options) != 4 or sum(1 for option in options if option.is_correct) != 1:
            raise ExamRuleError("MCQ paper items must have exactly four options and one answer")
        rng.shuffle(options)
        AttemptOptionOrder.objects.bulk_create(
            [
                AttemptOptionOrder(
                    attempt_question=attempt_question,
                    option=option,
                    display_order=position,
                )
                for position, option in enumerate(options, start=1)
            ]
        )


def start_attempt(exam, user, rng=None):
    if user.role != "STUDENT":
        raise ExamRuleError("Only a student can start an exam", 403)
    if not user.active:
        raise ExamRuleError("Account is inactive", 403)
    if exam.status != Exam.STATUS_PUBLISHED:
        raise ExamRuleError("Exam is not open for attempts")
    now = timezone.now()
    if now < exam.start_at:
        raise ExamRuleError("Exam window has not opened")
    if now >= exam.end_at:
        raise ExamRuleError("Exam window has ended")
    try:
        with transaction.atomic():
            attempt = ExamAttempt.objects.create(
                exam=exam,
                user=user,
                started_at=now,
                status=ExamAttempt.STATUS_IN_PROGRESS,
            )
            freeze_paper(attempt, rng=rng)
    except IntegrityError as exc:
        raise ExamRuleError("An attempt for this exam already exists", 409) from exc
    record_audit(user, "START", "attempt", attempt.id, f"exam={exam.id}")
    return attempt


def _lock_attempt(attempt_id):
    return ExamAttempt.objects.select_for_update().select_related("exam").get(pk=attempt_id)


def submit_attempt(attempt, auto=False):
    with transaction.atomic():
        locked = _lock_attempt(attempt.id)
        if locked.status != ExamAttempt.STATUS_IN_PROGRESS:
            if auto:
                return locked
            raise ExamRuleError("Attempt is already submitted", 409)
        locked.submitted_at = timezone.now()
        locked.status = ExamAttempt.STATUS_SUBMITTED
        locked.save(update_fields=["submitted_at", "status"])
        score_mcq(locked)
        result = finalize_result(locked)
        record_audit(
            locked.user,
            "SUBMIT",
            "attempt",
            locked.id,
            "auto" if auto else "manual",
        )
        locked.refresh_from_db()
        if result is not None:
            locked.result = result
        return locked


def ensure_open(attempt):
    attempt.refresh_from_db()
    if attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        return attempt
    if timezone.now() >= deadline(attempt):
        return submit_attempt(attempt, auto=True)
    return attempt


def save_answers(attempt, items, actor):
    attempt = ensure_open(attempt)
    if attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        raise ExamRuleError("Attempt is not in progress", 409)
    if attempt.user_id != actor.id:
        raise ExamRuleError("You cannot save another student's paper", 403)
    paper = {
        row.question_id: row
        for row in AttemptQuestion.objects.filter(attempt=attempt).select_related("question")
    }
    with transaction.atomic():
        for item in items:
            question_id = item.get("question_id")
            slot = paper.get(question_id)
            if slot is None:
                raise ExamRuleError("Question is not on this attempt")
            answer, _ = AttemptAnswer.objects.get_or_create(attempt=attempt, question_id=question_id)
            if slot.question.type == Question.TYPE_MCQ:
                option_id = item.get("selected_option_id")
                if option_id in ("", None):
                    answer.selected_option = None
                else:
                    allowed = AttemptOptionOrder.objects.filter(
                        attempt_question=slot,
                        option_id=option_id,
                    ).exists()
                    if not allowed:
                        raise ExamRuleError("Selected option does not belong to this question")
                    answer.selected_option_id = option_id
                answer.descriptive_text = None
            else:
                if item.get("selected_option_id") not in (None, ""):
                    raise ExamRuleError("A descriptive question does not take an option")
                text = (item.get("descriptive_text") or "").strip()
                answer.descriptive_text = text or None
                answer.selected_option = None
            if "marked_for_review" in item and item.get("marked_for_review") is not None:
                answer.marked_for_review = bool(item.get("marked_for_review"))
            answer.save()
    record_audit(actor, "SAVE", "attempt", attempt.id, f"count={len(items)}")
    return attempt


def score_mcq(attempt):
    negative = attempt.exam.negative_mark
    slots = AttemptQuestion.objects.filter(
        attempt=attempt,
        question__type=Question.TYPE_MCQ,
    ).select_related("question")
    now = timezone.now()
    for slot in slots:
        answer, _ = AttemptAnswer.objects.get_or_create(attempt=attempt, question=slot.question)
        if answer.selected_option_id is None:
            answer.awarded_marks = Decimal("0.00")
        elif answer.selected_option.is_correct:
            answer.awarded_marks = slot.question.marks
        else:
            answer.awarded_marks = Decimal("0.00") - negative
        answer.evaluated_at = now
        answer.save()


def objective_total(attempt):
    total = AttemptAnswer.objects.filter(
        attempt=attempt,
        question__type=Question.TYPE_MCQ,
    ).aggregate(total=Sum("awarded_marks"))["total"]
    total = total or Decimal("0.00")
    if total < 0:
        return Decimal("0.00")
    return total


def descriptive_pending(attempt):
    question_ids = list(
        AttemptQuestion.objects.filter(
            attempt=attempt,
            question__type=Question.TYPE_DESCRIPTIVE,
        ).values_list("question_id", flat=True)
    )
    if not question_ids:
        return False
    scored = AttemptAnswer.objects.filter(
        attempt=attempt,
        question_id__in=question_ids,
        awarded_marks__isnull=False,
    ).count()
    return scored < len(question_ids)


def descriptive_total(attempt):
    total = AttemptAnswer.objects.filter(
        attempt=attempt,
        question__type=Question.TYPE_DESCRIPTIVE,
        awarded_marks__isnull=False,
    ).aggregate(total=Sum("awarded_marks"))["total"]
    return total or Decimal("0.00")


def finalize_result(attempt):
    if descriptive_pending(attempt):
        return None
    existing = Result.objects.filter(attempt=attempt).first()
    if existing and existing.published:
        raise ExamRuleError("A published result cannot be recalculated")
    objective = objective_total(attempt)
    descriptive = descriptive_total(attempt)
    total = objective + descriptive
    maximum = attempt_max_marks(attempt)
    outcome = Result.STATUS_PASS if total >= attempt.exam.pass_marks else Result.STATUS_FAIL
    now = timezone.now()
    if existing:
        existing.objective_marks = objective
        existing.descriptive_marks = descriptive
        existing.total_marks = total
        existing.max_marks = maximum
        existing.status = outcome
        existing.generated_at = now
        existing.save()
        result = existing
    else:
        result = Result.objects.create(
            attempt=attempt,
            user=attempt.user,
            exam=attempt.exam,
            objective_marks=objective,
            descriptive_marks=descriptive,
            total_marks=total,
            max_marks=maximum,
            status=outcome,
            published=False,
            generated_at=now,
        )
    if attempt.status != ExamAttempt.STATUS_EVALUATED:
        attempt.status = ExamAttempt.STATUS_EVALUATED
        attempt.save(update_fields=["status"])
    return result


def award_descriptive(attempt, marks_list, faculty):
    if attempt.status == ExamAttempt.STATUS_IN_PROGRESS:
        raise ExamRuleError("The attempt is still in progress")
    existing = Result.objects.filter(attempt=attempt).first()
    if existing and existing.published:
        raise ExamRuleError("Published results cannot be marked again")
    if not marks_list:
        raise ExamRuleError("Provide at least one descriptive score")
    with transaction.atomic():
        for item in marks_list:
            question = Question.objects.filter(pk=item["question_id"]).first()
            if question is None:
                raise ExamRuleError("Question not found", 404)
            if question.type != Question.TYPE_DESCRIPTIVE:
                raise ExamRuleError("Only descriptive questions are marked manually")
            if not AttemptQuestion.objects.filter(attempt=attempt, question=question).exists():
                raise ExamRuleError("Question is not on this attempt")
            awarded = Decimal(item["awarded_marks"])
            if awarded < 0 or awarded > question.marks:
                raise ExamRuleError("Awarded marks must be between 0 and the question marks")
            answer, _ = AttemptAnswer.objects.get_or_create(attempt=attempt, question=question)
            answer.awarded_marks = awarded
            answer.evaluated_by = faculty
            answer.evaluated_at = timezone.now()
            answer.save()
        result = finalize_result(attempt)
    record_audit(
        faculty,
        "EVALUATE",
        "attempt",
        attempt.id,
        ",".join(str(item["question_id"]) for item in marks_list),
    )
    return result


def publish_result(result, actor):
    if result.published:
        raise ExamRuleError("Result is already published")
    if result.attempt.status != ExamAttempt.STATUS_EVALUATED:
        raise ExamRuleError("Score every descriptive answer before publishing")
    if descriptive_pending(result.attempt):
        raise ExamRuleError("Score every descriptive answer before publishing")
    result.published = True
    result.save(update_fields=["published"])
    record_audit(actor, "PUBLISH", "result", result.id, f"exam={result.exam_id}")
    return result


def attempt_payload(attempt, reveal=False):
    if not reveal:
        attempt = ensure_open(attempt)
    slots = (
        AttemptQuestion.objects.filter(attempt=attempt)
        .select_related("question__topic")
        .prefetch_related("option_orders__option")
        .order_by("display_order")
    )
    answers = {
        answer.question_id: answer
        for answer in AttemptAnswer.objects.filter(attempt=attempt).select_related("selected_option")
    }
    questions = []
    for slot in slots:
        question = slot.question
        answer = answers.get(question.id)
        if question.type == Question.TYPE_MCQ:
            ordered = sorted(slot.option_orders.all(), key=lambda row: row.display_order)
            options = []
            for row in ordered:
                option = {"id": row.option_id, "option_text": row.option.option_text}
                if reveal:
                    option["is_correct"] = row.option.is_correct
                options.append(option)
        else:
            options = []
        entry = {
            "question_id": question.id,
            "display_order": slot.display_order,
            "type": question.type,
            "text": question.text,
            "marks": money(question.marks),
            "difficulty": question.difficulty,
            "topic": question.topic.name,
            "options": options,
            "selected_option_id": answer.selected_option_id if answer else None,
            "descriptive_text": answer.descriptive_text if answer else None,
            "marked_for_review": bool(answer.marked_for_review) if answer else False,
        }
        if reveal:
            entry["awarded_marks"] = (
                money(answer.awarded_marks) if answer and answer.awarded_marks is not None else None
            )
            entry["explanation"] = question.explanation
        questions.append(entry)
    return {
        "id": attempt.id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "deadline": deadline(attempt),
        "remaining_seconds": remaining_seconds(attempt),
        "server_time": timezone.now(),
        "exam": {
            "id": attempt.exam_id,
            "title": attempt.exam.title,
            "instructions": attempt.exam.instructions,
            "duration_minutes": attempt.exam.duration_minutes,
            "pass_marks": money(attempt.exam.pass_marks),
            "negative_mark": money(attempt.exam.negative_mark),
            "subject": attempt.exam.subject.name,
        },
        "questions": questions,
    }
