"""
DRF serializers for WorkReport, ReportContent, and nested WorkEntry display.
"""
from rest_framework import serializers

from apps.stats.serializers import WorkEntrySerializer
from .models import WorkReport, ReportContent


class ReportContentSerializer(serializers.ModelSerializer):
    """Single template-field content row."""

    class Meta:
        model = ReportContent
        fields = ["id", "field_key", "field_value", "order"]


class ReportListSerializer(serializers.ModelSerializer):
    """Compact report info for list view."""

    creator_name = serializers.CharField(source="creator.get_full_name", read_only=True)
    creator_username = serializers.CharField(source="creator.username", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    entry_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkReport
        fields = [
            "id", "dingtalk_report_id",
            "creator_name", "creator_username", "department_name",
            "report_date", "status",
            "entry_count", "created_at",
        ]


class ReportDetailSerializer(serializers.ModelSerializer):
    """Full report with contents and parsed work entries."""

    creator_name = serializers.CharField(source="creator.get_full_name", read_only=True)
    creator_username = serializers.CharField(source="creator.username", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    contents = ReportContentSerializer(many=True, read_only=True)
    work_entries = WorkEntrySerializer(many=True, read_only=True)

    class Meta:
        model = WorkReport
        fields = [
            "id", "dingtalk_report_id",
            "creator_name", "creator_username", "department_name",
            "report_date", "create_time", "status",
            "contents", "work_entries", "raw_contents", "created_at",
        ]
