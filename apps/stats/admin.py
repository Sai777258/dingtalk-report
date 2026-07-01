"""
WorkEntry admin configuration.
"""
from django.contrib import admin

from .models import WorkEntry


@admin.register(WorkEntry)
class WorkEntryAdmin(admin.ModelAdmin):
    list_display = [
        "employee_name", "project_name", "date", "hours",
        "task_type_display", "status_badge", "confidence_badge", "is_categorized",
    ]
    list_filter = [
        "task_type", "status", "is_categorized", "date",
        "department", "project",
    ]
    search_fields = [
        "task_description", "raw_text",
        "employee__username", "employee__first_name",
        "project__name",
    ]
    readonly_fields = ["report", "confidence", "raw_text"]
    autocomplete_fields = ["employee", "project", "department"]

    fieldsets = (
        ("基本信息", {"fields": ("date", "hours", "task_type", "status")}),
        ("关联", {"fields": ("employee", "department", "project", "report")}),
        ("解析质量", {"fields": ("confidence", "is_categorized")}),
        ("内容", {"fields": ("task_description", "raw_text")}),
    )

    def employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username
    employee_name.short_description = "员工"
    employee_name.admin_order_field = "employee__last_name"

    def project_name(self, obj):
        return obj.project.name if obj.project else "未归类"
    project_name.short_description = "项目"
    project_name.admin_order_field = "project__name"

    def task_type_display(self, obj):
        return obj.get_task_type_display()
    task_type_display.short_description = "任务类型"
    task_type_display.admin_order_field = "task_type"

    def status_badge(self, obj):
        colors = {
            "completed": "#67c23a",
            "incomplete": "#f56c6c",
            "in_progress": "#409eff",
            "planned": "#e6a23c",
        }
        color = colors.get(obj.status, "#909399")
        return (
            f'<span style="display:inline-block;padding:2px 8px;'
            f'border-radius:4px;background:{color};color:#fff;'
            f'font-size:12px;">{obj.get_status_display()}</span>'
        )
    status_badge.short_description = "状态"
    status_badge.admin_order_field = "status"

    def confidence_badge(self, obj):
        if obj.confidence >= 80:
            color = "#67c23a"
        elif obj.confidence >= 50:
            color = "#e6a23c"
        else:
            color = "#f56c6c"
        return (
            f'<span style="display:inline-block;padding:2px 8px;'
            f'border-radius:4px;background:{color};color:#fff;'
            f'font-size:12px;">{obj.confidence}%</span>'
        )
    confidence_badge.short_description = "置信度"
    confidence_badge.admin_order_field = "confidence"
