"""
Django Admin configuration for Department and User models.

Customized for Chinese-friendly management of users, departments, and roles.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Department, User


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "manager", "dingtalk_dept_id", "member_count", "created_at"]
    list_filter = ["parent"]
    search_fields = ["name", "dingtalk_dept_id"]
    ordering = ["name"]
    raw_id_fields = ["parent", "manager"]
    autocomplete_fields = ["parent", "manager"]

    fieldsets = (
        (_("基本信息"), {"fields": ("name", "parent")}),
        (_("管理"), {"fields": ("manager", "dingtalk_dept_id")}),
    )

    def member_count(self, obj):
        count = obj.members.count()
        return f"{count} 人"
    member_count.short_description = "成员数"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username", "get_full_name", "role_badge", "department",
        "mobile", "is_active", "dingtalk_user_id", "date_joined",
    ]
    list_filter = ["role", "department", "is_active", "is_staff", "is_superuser"]
    search_fields = ["username", "first_name", "last_name", "mobile", "dingtalk_user_id"]
    ordering = ["-date_joined"]
    autocomplete_fields = ["department"]

    # ---- Fieldsets ----
    fieldsets = (
        (_("登录信息"), {
            "fields": ("username", "password"),
        }),
        (_("个人信息"), {
            "fields": ("first_name", "last_name", "email"),
        }),
        (_("角色与部门"), {
            "fields": ("role", "department", "job_title"),
        }),
        (_("权限"), {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("钉钉身份"), {
            "fields": ("dingtalk_user_id", "dingtalk_union_id", "dingtalk_open_id", "avatar_url"),
        }),
        (_("联系方式"), {
            "fields": ("mobile",),
        }),
        (_("重要日期"), {
            "fields": ("last_login", "date_joined"),
        }),
    )

    # For add form: show fewer fields
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "password1", "password2",
                "role", "department", "first_name", "last_name",
            ),
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    get_full_name.short_description = "姓名"
    get_full_name.admin_order_field = "last_name"

    def role_badge(self, obj):
        role_colors = {
            "admin": "#f56c6c",
            "executive": "#e6a23c",
            "dept_manager": "#409eff",
            "product_manager": "#67c23a",
            "employee": "#909399",
        }
        color = role_colors.get(obj.role, "#909399")
        return (
            f'<span style="display:inline-block;padding:2px 8px;'
            f'border-radius:4px;background:{color};color:#fff;'
            f'font-size:12px;">{obj.get_role_display()}</span>'
        )
    role_badge.short_description = "角色"
    role_badge.allow_tags = True
    role_badge.admin_order_field = "role"
