"""
WorkReport & ReportContent admin configuration.
"""
from django.contrib import admin

from .models import ReportTemplate, WorkReport, ReportContent


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "dingtalk_template_id", "is_active", "field_count", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]

    def field_count(self, obj):
        return len(obj.fields or [])
    field_count.short_description = "字段数"


class ReportContentInline(admin.TabularInline):
    model = ReportContent
    extra = 0
    readonly_fields = ["field_key", "field_value", "extracted_entries"]
    can_delete = False


@admin.register(WorkReport)
class WorkReportAdmin(admin.ModelAdmin):
    list_display = [
        "dingtalk_report_id", "creator_name", "department",
        "report_date", "template", "status", "sync_log", "created_at",
    ]
    list_filter = ["status", "report_date", "department"]
    search_fields = ["dingtalk_report_id", "creator__username", "creator__first_name"]
    readonly_fields = ["dingtalk_report_id", "raw_contents", "sync_log"]
    inlines = [ReportContentInline]

    fieldsets = (
        ("基本信息", {"fields": ("dingtalk_report_id", "status", "template")}),
        ("人员", {"fields": ("creator", "department")}),
        ("时间", {"fields": ("report_date", "create_time")}),
        ("原始数据", {"fields": ("raw_contents",)}),
        ("同步", {"fields": ("sync_log",)}),
    )

    def creator_name(self, obj):
        return obj.creator.get_full_name() or obj.creator.username
    creator_name.short_description = "创建人"
    creator_name.admin_order_field = "creator__last_name"


@admin.register(ReportContent)
class ReportContentAdmin(admin.ModelAdmin):
    list_display = ["report", "field_key", "entry_count", "order"]
    list_filter = ["field_key"]
    search_fields = ["field_value"]

    def entry_count(self, obj):
        return len(obj.extracted_entries or [])
    entry_count.short_description = "提取条目数"
