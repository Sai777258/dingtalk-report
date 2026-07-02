"""
API root URL configuration.

All /api/ routes are registered here.
"""
from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("reports/", include("apps.reports.urls")),
    path("stats/", include("apps.stats.urls")),
]
