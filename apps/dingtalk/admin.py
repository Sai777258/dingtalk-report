"""
DingTalk admin configuration.
"""
from django.contrib import admin

from .models import SyncLog


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = [
        "sync_type_display", "status_badge", "started_at", "completed_at",
        "records_fetched", "records_parsed", "records_skipped", "duration_display",
    ]
    list_filter = ["sync_type", "status"]
    search_fields = ["error_message"]
    ordering = ["-created_at"]
    readonly_fields = [
        "sync_type", "status", "started_at", "completed_at",
        "records_fetched", "records_parsed", "records_skipped",
        "request_params", "response_summary", "error_message",
    ]

    fieldsets = (
        ("基本信息", {"fields": ("sync_type", "status")}),
        ("时间", {"fields": ("started_at", "completed_at")}),
        ("统计", {"fields": ("records_fetched", "records_parsed", "records_skipped")}),
        ("详情", {"fields": ("request_params", "response_summary", "error_message")}),
    )

    def sync_type_display(self, obj):
        return obj.get_sync_type_display()
    sync_type_display.short_description = "同步类型"
    sync_type_display.admin_order_field = "sync_type"

    def status_badge(self, obj):
        colors = {
            "running": "#409eff",
            "success": "#67c23a",
            "failed": "#f56c6c",
            "partial": "#e6a23c",
        }
        color = colors.get(obj.status, "#909399")
        return (
            f'<span style="display:inline-block;padding:2px 8px;'
            f'border-radius:4px;background:{color};color:#fff;'
            f'font-size:12px;">{obj.get_status_display()}</span>'
        )
    status_badge.short_description = "状态"
    status_badge.allow_tags = True
    status_badge.admin_order_field = "status"

    def duration_display(self, obj):
        d = obj.duration
        if d is None:
            return "—"
        if d < 60:
            return f"{d:.1f} 秒"
        if d < 3600:
            return f"{d / 60:.1f} 分钟"
        return f"{d / 3600:.1f} 小时"
    duration_display.short_description = "耗时"
