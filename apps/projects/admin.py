"""
Project admin configuration.
"""
from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "status_badge", "pm_list", "work_entry_count", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "code", "aliases"]
    filter_horizontal = ["product_managers"]

    fieldsets = (
        ("基本信息", {"fields": ("name", "code", "status")}),
        ("匹配配置", {"fields": ("aliases",)}),
        ("管理", {"fields": ("product_managers",)}),
        ("描述", {"fields": ("description",)}),
    )

    def status_badge(self, obj):
        color = "#67c23a" if obj.status == "active" else "#909399"
        return (
            f'<span style="display:inline-block;padding:2px 8px;'
            f'border-radius:4px;background:{color};color:#fff;'
            f'font-size:12px;">{obj.get_status_display()}</span>'
        )
    status_badge.short_description = "状态"
    status_badge.admin_order_field = "status"

    def pm_list(self, obj):
        return ", ".join(
            p.get_full_name() or p.username
            for p in obj.product_managers.all()
        )
    pm_list.short_description = "产品经理"

    def work_entry_count(self, obj):
        return obj.work_entries.count()
    work_entry_count.short_description = "工时记录数"
