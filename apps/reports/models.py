"""
WorkReport and ReportContent models.

WorkReport stores the raw DingTalk work-log data (preserved for audit).
ReportContent splits each report by template fields (今日完成工作, 明日计划, etc.).
"""
from django.db import models


class ReportTemplate(models.Model):
    """A DingTalk work-report template (e.g., 日报, 周报)."""

    name = models.CharField(max_length=100, verbose_name="模板名称")
    dingtalk_template_id = models.CharField(
        max_length=128, unique=True, null=True, blank=True,
        verbose_name="钉钉模板ID",
    )
    fields = models.JSONField(
        default=list, verbose_name="字段定义",
        help_text="模板字段列表，如 [{key: '今日完成工作', type: 'text'}, ...]",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        ordering = ["name"]
        verbose_name = "报告模板"
        verbose_name_plural = "报告模板"

    def __str__(self):
        return self.name


class WorkReport(models.Model):
    """A single work report fetched from DingTalk.

    Stores the complete raw JSON in raw_contents for auditability.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        SUBMITTED = "submitted", "已提交"

    dingtalk_report_id = models.CharField(
        max_length=128, unique=True, verbose_name="钉钉报告ID",
    )
    template = models.ForeignKey(
        ReportTemplate, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reports",
        verbose_name="模板",
    )
    creator = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE,
        related_name="work_reports", verbose_name="创建人",
    )
    department = models.ForeignKey(
        "accounts.Department", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="work_reports",
        verbose_name="所属部门",
    )
    report_date = models.DateField(verbose_name="报告日期")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="钉钉创建时间")
    raw_contents = models.JSONField(
        default=dict, verbose_name="原始内容",
        help_text="钉钉返回的原始 JSON，保留完整不可篡改",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name="状态",
    )
    sync_log = models.ForeignKey(
        "dingtalk.SyncLog", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reports",
        verbose_name="同步批次",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="入库时间")

    class Meta:
        ordering = ["-report_date", "-create_time"]
        verbose_name = "工作日志"
        verbose_name_plural = "工作日志"

    def __str__(self):
        creator_name = self.creator.get_full_name() or self.creator.username
        return f"{creator_name} — {self.report_date}"


class ReportContent(models.Model):
    """A single template-field value extracted from a WorkReport.

    One WorkReport typically has 5-7 ReportContent rows, one per template field
    (今日完成工作, 今日未完成工作, 需协调工作, 明日重点工作计划, 备注, etc.).
    """

    report = models.ForeignKey(
        WorkReport, on_delete=models.CASCADE,
        related_name="contents", verbose_name="所属日志",
    )
    field_key = models.CharField(max_length=50, verbose_name="字段名")
    field_value = models.TextField(blank=True, verbose_name="字段内容")
    extracted_entries = models.JSONField(
        default=list, verbose_name="提取条目",
        help_text="从该字段解析出的结构化条目列表",
    )
    order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        ordering = ["report", "order"]
        verbose_name = "日志内容"
        verbose_name_plural = "日志内容"

    def __str__(self):
        return f"{self.report} — {self.field_key}"
