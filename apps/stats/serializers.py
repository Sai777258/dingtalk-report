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
    project_id = serializers.IntegerField(allow_null=True)
    project_name = serializers.CharField()
    project_code = serializers.CharField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()
    employee_count = serializers.IntegerField()
    percentage = serializers.FloatField()
    avg_confidence = serializers.FloatField()
    low_confidence_count = serializers.IntegerField()
    health_status = serializers.CharField()
    health_label = serializers.CharField()
    health_score = serializers.IntegerField()
    risk_tags = serializers.ListField(child=serializers.CharField())
    top_work_type = serializers.CharField(allow_null=True)
    top_work_type_percentage = serializers.FloatField()
    dominant_employee_percentage = serializers.FloatField()
    avg_hours_per_employee = serializers.FloatField()


class WorkTypeStatSerializer(serializers.Serializer):
    """Aggregated hours per work type."""
    type = serializers.CharField()
    display = serializers.CharField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    percentage = serializers.FloatField()


class WorkTypeStructureSerializer(serializers.Serializer):
    """Work type structure diagnostics for dashboard overview."""
    type = serializers.CharField()
    display = serializers.CharField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()
    employee_count = serializers.IntegerField()
    project_count = serializers.IntegerField()
    department_count = serializers.IntegerField()
    percentage = serializers.FloatField()
    avg_hours_per_employee = serializers.FloatField()
    low_confidence_count = serializers.IntegerField()
    structure_status = serializers.CharField()
    structure_label = serializers.CharField()
    structure_score = serializers.IntegerField()
    risk_tags = serializers.ListField(child=serializers.CharField())


class DashboardAlertSerializer(serializers.Serializer):
    """Management alert shown on the dashboard overview."""
    level = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
    metric = serializers.CharField()
    action = serializers.CharField()
    action_view = serializers.CharField(required=False)
    employee_id = serializers.IntegerField(required=False)


class DepartmentStatSerializer(serializers.Serializer):
    """Department load and efficiency signals for dashboard overview."""
    department_id = serializers.IntegerField(allow_null=True)
    department_name = serializers.CharField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()
    report_count = serializers.IntegerField()
    employee_count = serializers.IntegerField()
    project_count = serializers.IntegerField()
    percentage = serializers.FloatField()
    avg_hours_per_employee = serializers.FloatField()
    low_confidence_count = serializers.IntegerField()
    top_project = serializers.CharField()
    top_project_percentage = serializers.FloatField()
    top_work_type = serializers.CharField()
    top_work_type_percentage = serializers.FloatField()
    load_status = serializers.CharField()
    load_label = serializers.CharField()
    load_score = serializers.IntegerField()
    risk_tags = serializers.ListField(child=serializers.CharField())


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
    total_reports_last_month = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    avg_daily_hours = serializers.DecimalField(max_digits=5, decimal_places=1)
    working_days_this_month = serializers.IntegerField()
    project_breakdown = ProjectStatSerializer(many=True)
    employee_breakdown = EmployeeStatSerializer(many=True)
    department_breakdown = DepartmentStatSerializer(many=True)
    work_type_breakdown = WorkTypeStatSerializer(many=True)
    work_type_structure = WorkTypeStructureSerializer(many=True)
    daily_trend = DailyTrendSerializer(many=True)
    alerts = DashboardAlertSerializer(many=True)
