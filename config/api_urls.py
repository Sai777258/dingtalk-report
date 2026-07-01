"""
API root URL configuration.

All /api/ routes are registered here.
"""
from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    # Future app routes:
    # path("reports/", include("apps.reports.urls")),
    # path("projects/", include("apps.projects.urls")),
    # path("stats/", include("apps.stats.urls")),
    # path("exports/", include("apps.exports.urls")),
    # path("dingtalk/", include("apps.dingtalk.urls")),
]
