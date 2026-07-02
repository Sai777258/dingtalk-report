"""
Management command to import work reports from the external DingTalk log database.

External DB schema (discovered via discover_mysql_schema):
  daily_logs  — one row per user per day (log_date + user_id unique)
  log_items   — individual work items within a daily log (already parsed!)
  users       — employee records with dingtalk_user_id
  departments — org structure with dingtalk_dept_id

log_items already contains: project_name, work_type, work_hours, work_content
— no NLP parsing needed for hours!

Usage:
    python manage.py import_from_external_db --dry-run --limit 5
    python manage.py import_from_external_db --sync-type incremental
    python manage.py import_from_external_db --start-date 2026-06-01
"""
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.dingtalk.models import SyncLog
from apps.reports.models import WorkReport, ReportContent
from apps.stats.models import WorkEntry
from apps.reports.import_utils import (
    get_external_connection,
    resolve_user,
    resolve_department,
    resolve_template,
    match_project,
)

# ---------------------------------------------------------------------------
# SQL: fetch daily logs with user/dept info
# ---------------------------------------------------------------------------
DAILY_LOGS_QUERY = """
    SELECT
        dl.id            AS log_id,
        dl.user_id       AS ext_user_id,
        dl.log_date      AS report_date,
        dl.raw_content   AS raw_content,
        dl.is_template   AS is_template,
        dl.created_at    AS created_at,
        u.dingtalk_user_id AS dingtalk_user_id,
        u.user_name      AS user_name,
        u.dept_id        AS ext_dept_id,
        d.dept_name      AS dept_name,
        d.dingtalk_dept_id AS dingtalk_dept_id
    FROM daily_logs dl
    JOIN users u       ON u.id = dl.user_id
    JOIN departments d ON d.id = u.dept_id
    WHERE {where_clause}
    ORDER BY dl.log_date ASC, dl.id ASC
"""

# ---------------------------------------------------------------------------
# SQL: fetch log items for a given daily_log
# ---------------------------------------------------------------------------
LOG_ITEMS_QUERY = """
    SELECT
        id             AS item_id,
        project_name   AS project_name,
        work_type      AS work_type,
        work_hours     AS work_hours,
        work_content   AS work_content,
        sort_order     AS sort_order
    FROM log_items
    WHERE log_id = %s
    ORDER BY sort_order, id
"""

# Map external work_type values to our task_type choices
WORK_TYPE_MAP = {
    "产品开发": "development",
    "开发": "development",
    "测试": "testing",
    "测试调试": "testing",
    "调试": "testing",
    "会议": "meeting",
    "文档": "documentation",
    "设计": "design",
    "运维": "other",
    "技术支持": "other",
    "需求": "documentation",
    "评审": "meeting",
    "沟通": "meeting",
    "其他": "other",
}


class Command(BaseCommand):
    help = "从外部 MySQL 钉钉日志库导入工作汇报数据"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅验证连接并统计可导入记录数，不实际写入",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="最多导入 N 条日志（0 = 不限制）",
        )
        parser.add_argument(
            "--start-date",
            help="仅导入此日期及之后的日志 (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--end-date",
            help="仅导入此日期及之前的日志 (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--sync-type",
            choices=["full", "incremental"],
            default="full",
            help="full=全量, incremental=仅导入本地最新日期之后的数据",
        )
        parser.add_argument(
            "--skip-template",
            action="store_true",
            help="跳过 is_template=1 的模板日志",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]
        sync_type = options["sync_type"]
        skip_template = options["skip_template"]

        label = "试运行" if dry_run else "正式导入"
        self.stdout.write(self.style.NOTICE(f"[*] 外部数据库导入 ({label}模式, {sync_type})..."))

        # ---- Date range ----
        date_from = options.get("start_date")
        date_to = options.get("end_date")

        if sync_type == "incremental":
            last_report = WorkReport.objects.order_by("-report_date").first()
            if last_report and last_report.report_date:
                inc_from = last_report.report_date.isoformat()
                date_from = max(date_from, inc_from) if date_from else inc_from
                self.stdout.write(f"  增量: 拉取 >= {date_from}")
            else:
                self.stdout.write("  本地无数据，增量退化为全量")

        # ---- Build WHERE ----
        conditions = []
        params = []

        if skip_template:
            conditions.append("dl.is_template = 0")

        if date_from:
            conditions.append("dl.log_date >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("dl.log_date <= %s")
            params.append(date_to)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = DAILY_LOGS_QUERY.format(where_clause=where_clause)
        if limit > 0:
            query += f" LIMIT {int(limit)}"

        # ---- Connect ----
        conn = get_external_connection()
        db_label = conn.db.decode() if isinstance(conn.db, bytes) else conn.db
        self.stdout.write(f"  已连接: {conn.host}:{conn.port}/{db_label}")

        # ---- SyncLog ----
        sync_log = SyncLog.objects.create(
            sync_type="incremental" if sync_type == "incremental" else "full",
            status="running",
            started_at=timezone.now(),
            request_params={
                "date_from": date_from, "date_to": date_to,
                "limit": limit, "dry_run": dry_run,
                "skip_template": skip_template,
            },
        )

        # ---- Count ----
        count_sql = f"SELECT COUNT(*) AS cnt FROM ({query}) AS _sub"
        try:
            with conn.cursor() as cur:
                cur.execute(count_sql, params)
                total = cur.fetchone()["cnt"]
        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = f"查询失败: {e}"
            sync_log.completed_at = timezone.now()
            sync_log.save()
            conn.close()
            raise CommandError(f"查询外部数据库失败: {e}")

        self.stdout.write(f"  符合条件的日志: {total:,} 条")

        if dry_run:
            sync_log.status = "success"
            sync_log.records_fetched = total
            sync_log.completed_at = timezone.now()
            sync_log.save()
            conn.close()
            self.stdout.write(self.style.SUCCESS(f"\n[OK] 试运行完成 — 共 {total} 条日志可供导入"))
            return

        if total == 0:
            sync_log.status = "success"
            sync_log.completed_at = timezone.now()
            sync_log.save()
            conn.close()
            self.stdout.write("  无新数据需要导入")
            return

        # ---- Pre-load caches ----
        from apps.projects.models import Project
        projects_cache = list(Project.objects.filter(status="active"))
        template = resolve_template("日报")

        records_fetched = 0
        records_imported = 0
        records_skipped = 0
        total_entries = 0
        error_count = 0

        try:
            with conn.cursor() as cur:
                cur.execute(query, params)

                for dl_row in cur:
                    records_fetched += 1
                    log_id = dl_row["log_id"]

                    # Build a dingtalk_report_id: "ext_daily_{id}"
                    report_id = f"ext_daily_{log_id}"

                    # Dedup
                    if WorkReport.objects.filter(dingtalk_report_id=report_id).exists():
                        records_skipped += 1
                        continue

                    try:
                        with transaction.atomic():
                            entry_n = self._import_one_log(
                                dl_row, report_id, template, projects_cache, conn
                            )
                            total_entries += entry_n
                        records_imported += 1
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(
                            f"  [ERROR] 日志 {log_id}: {e}"
                        ))
                        if error_count > 20:
                            raise CommandError(f"错误过多 ({error_count})，已中止")

                    if records_fetched % 20 == 0:
                        self.stdout.write(
                            f"  进度: {records_fetched}/{total} "
                            f"(导入 {records_imported}, 跳过 {records_skipped})"
                        )

        finally:
            conn.close()

        # ---- Finalize SyncLog ----
        sync_log.status = "success" if error_count == 0 else "partial"
        sync_log.records_fetched = records_fetched
        sync_log.records_parsed = records_imported
        sync_log.records_skipped = records_skipped
        sync_log.completed_at = timezone.now()
        sync_log.response_summary = {
            "work_entries_created": total_entries,
            "error_count": error_count,
        }
        sync_log.save()

        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] 导入完成! "
            f"日志: {records_imported} 条, 工时条目: {total_entries} 条, "
            f"跳过: {records_skipped}, 错误: {error_count}"
        ))

    # ------------------------------------------------------------------
    def _import_one_log(self, dl_row, report_id, template, projects_cache, conn):
        """Import one daily_log + its log_items. Returns entry count."""
        from apps.projects.models import Project

        # --- Resolve user ---
        dt_uid = dl_row.get("dingtalk_user_id")
        user_name = dl_row.get("user_name")
        user, _ = resolve_user(str(dt_uid) if dt_uid else None, user_name)

        # --- Resolve department ---
        dt_dept_id = dl_row.get("dingtalk_dept_id")
        dept_name = dl_row.get("dept_name")
        department, _ = resolve_department(dt_dept_id, dept_name)

        # --- Parse dates ---
        report_date = _parse_date(dl_row.get("report_date"))
        create_time = _parse_datetime(dl_row.get("created_at"))

        # --- Build contents from log_items ---
        items = self._fetch_log_items(conn, dl_row["log_id"])
        completed_text = "\n".join(
            f"{i+1}. {it['work_content']}" for i, it in enumerate(items)
        )

        raw_contents = {
            "contents": [
                {"key": "今日完成工作", "value": completed_text},
                {"key": "今日未完成工作", "value": ""},
                {"key": "需协调工作", "value": ""},
                {"key": "明日重点工作计划", "value": ""},
                {"key": "备注", "value": ""},
            ]
        }
        # Also store original raw_content if present
        if dl_row.get("raw_content"):
            raw_contents["_raw_text"] = dl_row["raw_content"]

        # --- Create WorkReport ---
        report = WorkReport.objects.create(
            dingtalk_report_id=report_id,
            template=template,
            creator=user,
            department=department or user.department,
            report_date=report_date or date.today(),
            create_time=create_time,
            raw_contents=raw_contents,
            status="submitted",
        )

        # --- Create ReportContent ---
        ReportContent.objects.create(
            report=report,
            field_key="今日完成工作",
            field_value=completed_text,
            order=1,
        )

        # --- Create WorkEntry per log_item ---
        entry_count = 0
        for item in items:
            hours = float(item["work_hours"] or 0)
            work_content = item["work_content"] or ""
            project_name = item["project_name"] or ""
            work_type_raw = item["work_type"] or ""

            if hours <= 0 and not work_content:
                continue

            # Project matching
            project = None
            if project_name:
                project = match_project(project_name, projects_cache)
                if not project:
                    # Create project on-the-fly
                    project, _ = Project.objects.get_or_create(
                        name=project_name,
                        defaults={"code": _project_code(project_name), "aliases": [project_name]},
                    )
                    # Add to cache so subsequent items find it
                    projects_cache.append(project)

            # Map work_type
            task_type = WORK_TYPE_MAP.get(work_type_raw, "other")

            WorkEntry.objects.create(
                report=report,
                employee=user,
                department=department or user.department,
                project=project,
                date=report_date or date.today(),
                hours=hours,
                task_description=work_content,
                task_type=task_type,
                status="completed",
                confidence=90 if project else 80,
                raw_text=f"[{project_name}] {work_content}" if project_name else work_content,
                is_categorized=project is not None,
            )
            entry_count += 1

        return entry_count

    def _fetch_log_items(self, conn, log_id):
        """Fetch log_items for a given daily_log id from the external DB."""
        with conn.cursor() as cur:
            cur.execute(LOG_ITEMS_QUERY, (log_id,))
            return cur.fetchall()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return timezone.make_aware(value) if timezone.is_naive(value) else value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return timezone.make_aware(dt)
            except ValueError:
                continue
    return None


def _project_code(name):
    """Derive a project code from a Chinese name (simple pinyin-like slug)."""
    import re
    # Take first 3 chars + first letter of remaining, uppercase
    code = re.sub(r"[^a-zA-Z0-9一-鿿]", "", name)[:8].upper()
    return code or "PROJ"
