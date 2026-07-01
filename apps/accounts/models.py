"""
User and Department models for the project management system.

User extends Django's AbstractUser with:
- DingTalk identity fields (user_id, union_id, open_id)
- Role-based access control (admin, executive, dept_manager, product_manager, employee)
- Department association
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Department(models.Model):
    """Company organizational structure."""
    name = models.CharField(max_length=100, unique=True, verbose_name="部门名称")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="children", verbose_name="上级部门"
    )
    dingtalk_dept_id = models.BigIntegerField(
        null=True, blank=True, unique=True, verbose_name="钉钉部门ID"
    )
    manager = models.ForeignKey(
        "User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="managed_departments", verbose_name="部门经理"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["name"]
        verbose_name = "部门"
        verbose_name_plural = "部门"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Extended user model with DingTalk identity and role-based permissions."""
    class Role(models.TextChoices):
        ADMIN = "admin", "系统管理员"
        EXECUTIVE = "executive", "公司高层"
        DEPT_MANAGER = "dept_manager", "部门经理"
        PRODUCT_MANAGER = "product_manager", "产品经理"
        EMPLOYEE = "employee", "普通员工"

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.EMPLOYEE, verbose_name="角色"
    )
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="members", verbose_name="所属部门"
    )
    # DingTalk identity fields
    dingtalk_user_id = models.CharField(
        max_length=128, unique=True, null=True, blank=True, verbose_name="钉钉UserID"
    )
    dingtalk_union_id = models.CharField(
        max_length=128, unique=True, null=True, blank=True, verbose_name="钉钉UnionID"
    )
    dingtalk_open_id = models.CharField(
        max_length=128, null=True, blank=True, verbose_name="钉钉OpenID"
    )
    avatar_url = models.URLField(null=True, blank=True, verbose_name="头像URL")
    mobile = models.CharField(max_length=20, null=True, blank=True, verbose_name="手机号")
    job_title = models.CharField(max_length=100, null=True, blank=True, verbose_name="职位")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # ---- Role check helpers ----
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_executive(self):
        return self.role == self.Role.EXECUTIVE

    @property
    def is_dept_manager(self):
        return self.role == self.Role.DEPT_MANAGER

    @property
    def is_product_manager(self):
        return self.role == self.Role.PRODUCT_MANAGER

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    def can_view_department(self, dept):
        """Check if user can view a specific department's data."""
        if self.is_admin or self.is_executive:
            return True
        if self.is_dept_manager:
            # Can view own department and sub-departments
            return dept == self.department or (
                dept.parent and dept.parent == self.department
            )
        return dept == self.department

    def can_view_project(self, project):
        """Check if user can view a specific project's data."""
        if self.is_admin or self.is_executive:
            return True
        if self.is_product_manager:
            return project.product_managers.filter(pk=self.pk).exists()
        if self.is_dept_manager:
            return project.work_entries.filter(
                employee__department=self.department
            ).exists()
        return project.work_entries.filter(employee=self).exists()
