"""
Account API URL configuration.

Endpoints:
    POST /api/auth/demo-login/  — Demo mode login (username + password → JWT)
    POST /api/auth/token/refresh/ — Refresh access token using refresh token
    GET  /api/auth/me/          — Current user profile
"""
from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("demo-login/", views.DemoLoginView.as_view(), name="demo-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", views.CurrentUserView.as_view(), name="current-user"),
]
