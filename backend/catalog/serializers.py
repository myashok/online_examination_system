from django.db import transaction
from rest_framework import serializers

from catalog.models import Question, QuestionOption, Subject, Topic


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name"]

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Subject name is required")
        qs = Subject.objects.filter(name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A subject with this name already exists")
        return name


class TopicSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "subject", "subject_name", "name"]

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Topic name is required")
        return name

    def validate(self, attrs):
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)
        name = attrs.get("name") or getattr(self.instance, "name", None)
        if subject and name:
            qs = Topic.objects.filter(subject=subject, name=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("This topic already exists for the subject")
        return attrs


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "option_text", "is_correct"]
        read_only_fields = ["id"]

    def validate_option_text(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError("Option text is required")
        return text


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, required=False)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    topic_name = serializers.CharField(source="topic.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "subject",
            "subject_name",
            "topic",
            "topic_name",
            "type",
            "text",
            "difficulty",
            "marks",
            "explanation",
            "created_by",
            "created_by_name",
            "active",
            "options",
        ]
        read_only_fields = ["id", "created_by"]

    def validate_text(self, value):
        text = value.strip()
        if len(text) < 5:
            raise serializers.ValidationError("Question text must be at least 5 characters")
        return text

    def validate_marks(self, value):
        if value <= 0:
            raise serializers.ValidationError("Marks must be greater than zero")
        return value

    def validate(self, attrs):
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)
        topic = attrs.get("topic") or getattr(self.instance, "topic", None)
        if subject and topic and topic.subject_id != subject.id:
            raise serializers.ValidationError(
                {"topic": "Topic does not belong to the selected subject"}
            )
        qtype = attrs.get("type") or getattr(self.instance, "type", None)
        options = attrs.get("options", serializers.empty)
        if options is serializers.empty and self.instance is None:
            options = [] if qtype == Question.TYPE_DESCRIPTIVE else None
        if qtype == Question.TYPE_MCQ and options is not serializers.empty:
            self._validate_mcq_options(options)
        if qtype == Question.TYPE_DESCRIPTIVE and options not in (serializers.empty, None):
            if len(options) > 0:
                raise serializers.ValidationError(
                    {"options": "Descriptive questions cannot have options"}
                )
        return attrs

    def _validate_mcq_options(self, options):
        if options is None or len(options) != 4:
            raise serializers.ValidationError(
                {"options": "An MCQ must have exactly four options"}
            )
        correct = sum(1 for option in options if option.get("is_correct"))
        if correct != 1:
            raise serializers.ValidationError(
                {"options": "An MCQ must have exactly one correct option"}
            )

    def create(self, validated_data):
        options = validated_data.pop("options", [])
        with transaction.atomic():
            question = Question.objects.create(**validated_data)
            self._replace_options(question, options)
        return question

    def update(self, instance, validated_data):
        from examination.models import AttemptQuestion

        options = validated_data.pop("options", serializers.empty)
        if AttemptQuestion.objects.filter(question=instance).exists():
            locked = {"text", "marks", "type", "difficulty", "subject", "topic"}
            if locked.intersection(validated_data) or options is not serializers.empty:
                raise serializers.ValidationError(
                    "A question that is already on an attempt cannot be changed"
                )
        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()
            if options is not serializers.empty:
                instance.options.all().delete()
                self._replace_options(instance, options or [])
        return instance

    def _replace_options(self, question, options):
        if question.type == Question.TYPE_DESCRIPTIVE:
            return
        QuestionOption.objects.bulk_create(
            [
                QuestionOption(
                    question=question,
                    option_text=option["option_text"],
                    is_correct=option["is_correct"],
                )
                for option in options
            ]
        )
