from decimal import Decimal

from rest_framework import serializers

from examination.models import Exam
from examination.services import paper_total


class ExamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            "id",
            "subject",
            "title",
            "instructions",
            "start_at",
            "end_at",
            "duration_minutes",
            "pass_marks",
            "negative_mark",
            "status",
            "created_by",
        ]
        read_only_fields = ["id", "status", "created_by"]

    def validate_title(self, value):
        title = value.strip()
        if len(title) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters")
        return title

    def validate_duration_minutes(self, value):
        if value < 1 or value > 300:
            raise serializers.ValidationError("Duration must be between 1 and 300 minutes")
        return value

    def validate_pass_marks(self, value):
        if value < 0:
            raise serializers.ValidationError("Pass marks cannot be negative")
        return value

    def validate_negative_mark(self, value):
        if value < 0:
            raise serializers.ValidationError("Negative mark cannot be negative")
        return value

    def validate(self, attrs):
        start = attrs.get("start_at") or getattr(self.instance, "start_at", None)
        end = attrs.get("end_at") or getattr(self.instance, "end_at", None)
        duration = attrs.get("duration_minutes") or getattr(self.instance, "duration_minutes", None)
        if start and end and end <= start:
            raise serializers.ValidationError({"end_at": "End must be after start"})
        if start and end and duration:
            window = (end - start).total_seconds() / 60
            if duration > window:
                raise serializers.ValidationError(
                    {"duration_minutes": "Duration cannot be longer than the exam window"}
                )
        if self.instance and "subject" in attrs and attrs["subject"].id != self.instance.subject_id:
            if self.instance.exam_questions.exists():
                raise serializers.ValidationError(
                    {"subject": "Remove the paper questions before changing the subject"}
                )
        return attrs


class ExamReadSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    total_marks = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id",
            "subject",
            "subject_name",
            "title",
            "instructions",
            "start_at",
            "end_at",
            "duration_minutes",
            "pass_marks",
            "negative_mark",
            "status",
            "created_by",
            "created_by_name",
            "total_marks",
            "question_count",
        ]

    def get_total_marks(self, exam):
        return str(paper_total(exam).quantize(Decimal("0.01")))

    def get_question_count(self, exam):
        return exam.exam_questions.count()


class DrawSerializer(serializers.Serializer):
    easy = serializers.IntegerField(min_value=0, required=False, default=0)
    medium = serializers.IntegerField(min_value=0, required=False, default=0)
    hard = serializers.IntegerField(min_value=0, required=False, default=0)
    descriptive = serializers.IntegerField(min_value=0, required=False, default=0)
    replace = serializers.BooleanField(required=False, default=True)


class AnswerItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_id = serializers.IntegerField(required=False, allow_null=True)
    descriptive_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    marked_for_review = serializers.BooleanField(required=False)


class SaveAnswersSerializer(serializers.Serializer):
    answers = AnswerItemSerializer(many=True)

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("Provide at least one answer")
        return value


class MarkItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    awarded_marks = serializers.DecimalField(max_digits=6, decimal_places=2)


class MarksSerializer(serializers.Serializer):
    marks = MarkItemSerializer(many=True)

