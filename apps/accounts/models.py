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
    """Extended user model with DingTalk identity and role-based permissions.

    Roles (future: synced from LDAP group membership):
      admin           — full data access + manage users/roles/system
      dept_manager_l1 — full data access (same as admin), no user/system management
      dept_manager_l2 — single department data only
      project_manager — own data + managed projects' data
      employee        — own data only
    """
    class Role(models.TextChoices):
        ADMIN = "admin", "系统管理员"
        DEPT_MANAGER_L1 = "dept_manager_l1", "一级部门管理"
        DEPT_MANAGER_L2 = "dept_manager_l2", "二级部门管理"
        PROJECT_MANAGER = "project_manager", "项目经理"
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
    def is_dept_manager_l1(self):
        return self.role == self.Role.DEPT_MANAGER_L1

    @property
    def is_dept_manager_l2(self):
        return self.role == self.Role.DEPT_MANAGER_L2

    @property
    def is_project_manager(self):
        return self.role == self.Role.PROJECT_MANAGER

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_any_manager(self):
        """True if user has any manager-level role (L1, L2, or project)."""
        return self.role in (
            self.Role.DEPT_MANAGER_L1,
            self.Role.DEPT_MANAGER_L2,
            self.Role.PROJECT_MANAGER,
        )

    def can_view_department(self, dept):
        """Check if user can view a specific department's data.

        Uses get_visible_department_ids() for consistent filtering
        (lazy-imported to avoid circular dependency).
        """
        from apps.accounts.permissions import get_visible_department_ids
        if self.is_admin or self.is_dept_manager_l1:
            return True
        return dept.id in get_visible_department_ids(self)

    def can_view_project(self, project):
        """Check if user can view a specific project's data."""
        if self.is_admin or self.is_dept_manager_l1:
            return True
        if self.is_project_manager:
            return project.product_managers.filter(pk=self.pk).exists()
        if self.is_dept_manager_l2:
            return project.work_entries.filter(
                employee__department=self.department
            ).exists()
        return project.work_entries.filter(employee=self).exists()
