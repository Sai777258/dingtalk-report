"""
DRF serializers for WorkEntry and dashboard aggregation.
"""
from rest_framework import serializers

from .models import WorkEntry


class WorkEntrySerializer(serializers.ModelSerializer):
    """Single work entry with related names."""

    employee_name = serializers.CharField(source="employee.get_full_name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    task_type_display = serializers.CharField(source="get_task_type_display", read_only=True)

    class Meta:
        model = WorkEntry
        fields = [
            "id", "date", "hours",
            "employee_name", "project_name", "project_code",
            "task_description", "task_type", "task_type_display",
            "confidence", "is_categorized",
        ]


class ProjectStatSerializer(serializers.Serializer):
    """Aggregated hours per project."""
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    project_code = serializers.CharField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()
    percentage = serializers.FloatField()


class EmployeeStatSerializer(serializers.Serializer):
    """Aggregated hours per employee."""
    employee_id = serializers.IntegerField()
    employee_name = serializers.CharField()
    department_name = serializers.CharField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()


class DailyTrendSerializer(serializers.Serializer):
    """Hours aggregated by day."""
    date = serializers.DateField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    report_count = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    """Full dashboard aggregation response."""
    total_hours_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_hours_last_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_reports_this_month = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    avg_daily_hours = serializers.DecimalField(max_digits=5, decimal_places=1)
    project_breakdown = ProjectStatSerializer(many=True)
    employee_breakdown = EmployeeStatSerializer(many=True)
    daily_trend = DailyTrendSerializer(many=True)
