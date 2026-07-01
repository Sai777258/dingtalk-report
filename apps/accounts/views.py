"""
Account views: demo login, user profile, logout.
"""
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import DemoLoginSerializer, UserSerializer


class DemoLoginView(APIView):
    """POST /api/auth/demo-login/

    Authenticate with username + password and receive JWT tokens.
    Only available when DINGTALK_DEMO_MODE = True.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not settings.DINGTALK_DEMO_MODE:
            return Response(
                {"detail": "Demo 登录仅在 Demo 模式下可用"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DemoLoginSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    """GET /api/auth/me/ — Return the current authenticated user's profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
