from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User
from auditlog.services import record_audit


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "role", "active", "created_at"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name is required")
        return value.strip()

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
            role=User.ROLE_STUDENT,
            active=True,
        )


class AdminCreateUserSerializer(RegisterSerializer):
    role = serializers.ChoiceField(choices=[User.ROLE_FACULTY, User.ROLE_ADMIN])

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
            role=validated_data["role"],
            active=True,
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "role", "active"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name is required")
        return value.strip()

    def validate_role(self, value):
        if value not in {User.ROLE_STUDENT, User.ROLE_FACULTY, User.ROLE_ADMIN}:
            raise serializers.ValidationError("Invalid role")
        return value


class OESTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_field = self.username_field
        if username_field in attrs and isinstance(attrs[username_field], str):
            attrs[username_field] = attrs[username_field].lower().strip()
        email = attrs.get(username_field, "")
        try:
            data = super().validate(attrs)
        except Exception:
            record_audit(None, "LOGIN", "user", None, f"failed:{email}")
            raise
        data["user"] = UserSerializer(self.user).data
        record_audit(self.user, "LOGIN", "user", self.user.id, "success")
        return data
