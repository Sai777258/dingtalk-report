"""
API views for WorkReport listing and detail.
"""
from datetime import date, timedelta

from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from apps.accounts.permissions import apply_report_access_filter
from .models import WorkReport
from .serializers import ReportListSerializer, ReportDetailSerializer


class ReportListPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 50
    ordering = "-report_date"


class ReportListView(generics.ListAPIView):
    """
    GET /api/reports/
    Query params: ?page=1&page_size=15&date_from=2026-06-01&date_to=2026-06-30
                  &username=admin&department=技术部&search=项目A
    """
    serializer_class = ReportListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ReportListPagination

    def get_queryset(self):
        qs = WorkReport.objects.select_related("creator", "department") \
            .annotate(entry_count=Count("work_entries"))

        # Exclude demo seed data — only show real imported reports
        qs = qs.exclude(dingtalk_report_id__startswith="demo_report_")

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(report_date__gte=date_from)
        if date_to:
            qs = qs.filter(report_date__lte=date_to)
        if not date_from and not date_to:
            qs = qs.filter(report_date__gte=date.today() - timedelta(days=30))

        username = self.request.query_params.get("username")
        if username:
            qs = qs.filter(creator__username=username)

        department = self.request.query_params.get("department")
        if department:
            qs = qs.filter(department__name=department)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(contents__field_value__icontains=search)
            ).distinct()

        # Role-based access filter
        qs = apply_report_access_filter(qs, self.request.user)

        return qs


class ReportDetailView(generics.RetrieveAPIView):
    """
    GET /api/reports/{id}/
    """
    serializer_class = ReportDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WorkReport.objects.select_related("creator", "department") \
            .prefetch_related("contents", "work_entries__project", "work_entries__employee")
        # Exclude demo seed data
        qs = qs.exclude(dingtalk_report_id__startswith="demo_report_")
        return apply_report_access_filter(qs, self.request.user)
