"""
DingTalk models — SyncLog for tracking data synchronization operations.
"""
from django.db import models


class SyncLog(models.Model):
    """Records each dingtalk work-report sync run."""

    class SyncType(models.TextChoices):
        INCREMENTAL = "incremental", "增量同步"
        DEEP = "deep", "深度同步"
        FULL = "full", "全量对账"
        MANUAL = "manual", "手动触发"

    class SyncStatus(models.TextChoices):
        RUNNING = "running", "运行中"
        SUCCESS = "success", "成功"
        FAILED = "failed", "失败"
        PARTIAL = "partial", "部分成功"

    sync_type = models.CharField(
        max_length=20, choices=SyncType.choices, default=SyncType.MANUAL, verbose_name="同步类型"
    )
    status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.RUNNING,
        verbose_name="状态",
    )

    # Time tracking
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    # Stats
    records_fetched = models.IntegerField(default=0, verbose_name="获取记录数")
    records_parsed = models.IntegerField(default=0, verbose_name="解析记录数")
    records_skipped = models.IntegerField(default=0, verbose_name="跳过记录数")

    # Metadata
    request_params = models.JSONField(default=dict, verbose_name="请求参数")
    response_summary = models.JSONField(default=dict, verbose_name="响应摘要")
    error_message = models.TextField(blank=True, verbose_name="错误信息")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "同步日志"
        verbose_name_plural = "同步日志"

    def __str__(self):
        started = self.started_at.strftime("%m-%d %H:%M") if self.started_at else "?"
        return f"{self.get_sync_type_display()} ({started}) — {self.get_status_display()}"

    @property
    def duration(self):
        """Sync duration in seconds, or None if still running."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
