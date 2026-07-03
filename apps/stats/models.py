"""
WorkEntry model — the core analytic unit for work-hour statistics.

Each WorkEntry represents one parsed work item (project + hours + description)
extracted from a WorkReport's free-text content.

Key design decisions:
- department is stored redundantly to avoid JOIN-heavy aggregation queries
- project can be null for entries that couldn't be matched to a known project
- confidence score (0-100) indicates parse reliability
"""
from django.db import models


class WorkEntry(models.Model):
    """A single parsed work-hour record extracted from a work report."""

    class TaskType(models.TextChoices):
        DEVELOPMENT = "development", "开发"
        TESTING = "testing", "测试"
        MEETING = "meeting", "会议"
        DOCUMENTATION = "documentation", "文档"
        DESIGN = "design", "设计"
        OTHER = "other", "其他"

    class EntryStatus(models.TextChoices):
        COMPLETED = "completed", "已完成"
        INCOMPLETE = "incomplete", "未完成"
        IN_PROGRESS = "in_progress", "进行中"
        PLANNED = "planned", "计划中"

    # ---- Source linkage ----
    report = models.ForeignKey(
        "reports.WorkReport", on_delete=models.CASCADE,
        related_name="work_entries", verbose_name="来源日志",
    )
    source_item_id = models.BigIntegerField(
        null=True, blank=True, unique=True, db_index=True,
        verbose_name="外部条目ID",
    )

    # ---- People & org (department is redundant for fast aggregation) ----
    employee = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE,
        related_name="work_entries", verbose_name="员工",
    )
    department = models.ForeignKey(
        "accounts.Department", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="work_entries",
        verbose_name="所属部门",
    )

    # ---- Project (null = uncategorized, pending manual assignment) ----
    project = models.ForeignKey(
        "projects.Project", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="work_entries",
        verbose_name="关联项目",
    )

    # ---- Core fields ----
    date = models.DateField(verbose_name="工作日期")
    hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="工时（小时）",
    )
    task_description = models.TextField(blank=True, verbose_name="任务描述")
    task_type = models.CharField(
        max_length=50,
        choices=TaskType.choices,
        default=TaskType.OTHER,
        verbose_name="任务类型",
    )
    status = models.CharField(
        max_length=20,
        choices=EntryStatus.choices,
        default=EntryStatus.COMPLETED,
        verbose_name="完成状态",
    )

    # ---- Parse quality ----
    confidence = models.IntegerField(
        default=0, verbose_name="置信度",
        help_text="0-100，正则匹配高分，模糊匹配低分，低于阈值的需人工审核",
    )
    raw_text = models.TextField(blank=True, verbose_name="原始文本")
    is_categorized = models.BooleanField(
        default=False, verbose_name="已归类",
        help_text="是否已分配到项目（未归类的项目为 null）",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["employee", "date"]),
            models.Index(fields=["department", "date"]),
            models.Index(fields=["project", "date"]),
            models.Index(fields=["is_categorized"]),
        ]
        verbose_name = "工时记录"
        verbose_name_plural = "工时记录"

    def __str__(self):
        project_name = self.project.name if self.project else "未归类"
        return f"{self.employee} — {project_name} — {self.hours}h @ {self.date}"

    @property
    def is_low_confidence(self):
        """Entries below threshold need human review."""
        return self.confidence < 50
