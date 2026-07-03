from django.urls import path

from .views import ReportListView, ReportDetailView, ReportExportView

urlpatterns = [
    path("", ReportListView.as_view(), name="report-list"),
    path("export/", ReportExportView.as_view(), name="report-export"),
    path("<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
]
