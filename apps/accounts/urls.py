"""
Account API URL configuration.

Endpoints:
    POST /api/auth/demo-login/  — Demo mode login (username + password → JWT)
    GET  /api/auth/me/          — Current user profile
"""
from django.urls import path

from . import views

urlpatterns = [
    path("demo-login/", views.DemoLoginView.as_view(), name="demo-login"),
    path("me/", views.CurrentUserView.as_view(), name="current-user"),
]
