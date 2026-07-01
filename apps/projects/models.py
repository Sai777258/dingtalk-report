"""
Project model — represents a company project for work-hour tracking.

Projects are manually created by admins. Each project has a primary name
plus optional aliases used to match work-log text during sync.
"""
from django.db import models


class Project(models.Model):
    """A project that work hours are tracked against."""

    class Status(models.TextChoices):
        ACTIVE = "active", "进行中"
        ARCHIVED = "archived", "已归档"

    name = models.CharField(max_length=200, unique=True, verbose_name="项目名称")
    code = models.CharField(
        max_length=50, unique=True, verbose_name="项目代号",
        help_text="简短代号，如 'PROJ-A'",
    )
    aliases = models.JSONField(
        default=list, verbose_name="别名列表",
        help_text="日志文本中可能出现的其他名称，如 ['项目A', 'A项目', 'ProjA']",
    )
    product_managers = models.ManyToManyField(
        "accounts.User",
        related_name="managed_projects",
        verbose_name="产品经理",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="状态",
    )
    description = models.TextField(blank=True, verbose_name="项目描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["name"]
        verbose_name = "项目"
        verbose_name_plural = "项目"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def match_text(self, text):
        """Check if any project name/alias appears in the given text."""
        candidates = [self.name, self.code] + (self.aliases or [])
        for candidate in candidates:
            if candidate and candidate in text:
                return True
        return False
