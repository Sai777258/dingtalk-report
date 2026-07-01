"""
DRF serializers for User and authentication.
"""
from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Department


class DepartmentSerializer(serializers.ModelSerializer):
    """Nested department info for user display."""

    class Meta:
        model = Department
        fields = ["id", "name"]


class UserSerializer(serializers.ModelSerializer):
    """User profile returned after login / on /api/auth/me/."""
    department = DepartmentSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name",
            "role", "role_display", "department",
            "avatar_url", "mobile", "job_title", "email",
        ]


class DemoLoginSerializer(serializers.Serializer):
    """Accepts username + password; returns JWT tokens + user profile.

    Only active when settings.DINGTALK_DEMO_MODE is True.
    """
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        if not settings.DINGTALK_DEMO_MODE:
            raise serializers.ValidationError("Demo 登录仅在 Demo 模式下可用")

        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError("用户名或密码错误")
        if not user.is_active:
            raise serializers.ValidationError("该账号已被禁用")

        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
