"""
Management command to seed mock work reports and entries for UI testing.

Creates:
- 4 projects (项目A, 项目B, 项目C, 内部工具)
- 1 report template (日报)
- ~60 WorkReports across 10 working days for 5 users
- ReportContent for each report
- ~150 WorkEntry records (parsed hours) linked to projects

Usage:
    python manage.py seed_reports
    python manage.py seed_reports --days 5   # fewer days
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User, Department
from apps.projects.models import Project
from apps.reports.models import ReportTemplate, WorkReport, ReportContent
from apps.dingtalk.models import SyncLog
from apps.stats.models import WorkEntry


# ---- Project definitions ----
DEMO_PROJECTS = [
    {
        "name": "项目A",
        "code": "PROJ-A",
        "aliases": ["A项目", "ProjectA", "【项目A】"],
        "pm_username": "proj_mgr",
    },
    {
        "name": "项目B",
        "code": "PROJ-B",
        "aliases": ["B项目", "数据平台", "【项目B】"],
        "pm_username": "proj_mgr",
    },
    {
        "name": "项目C",
        "code": "PROJ-C",
        "aliases": ["C项目", "客户端", "【项目C】"],
        "pm_username": "proj_mgr",
    },
    {
        "name": "内部工具",
        "code": "TOOL",
        "aliases": ["工具", "运维平台", "【内部工具】"],
        "pm_username": "proj_mgr",
    },
]

# ---- Realistic work content templates per department ----
TECH_TASKS = [
    ("【项目A】完成用户登录模块开发，修复了3个边界条件bug", 3.0, "development"),
    ("【项目A】编写登录模块单元测试，覆盖率提升至85%", 2.0, "testing"),
    ("【项目B】优化数据导出接口查询性能，从5s降到0.8s", 4.0, "development"),
    ("【项目B】修复数据导出中文字符乱码问题", 1.5, "development"),
    ("【项目C】重构客户端网络层，统一错误处理逻辑", 3.5, "development"),
    ("【项目C】客户端兼容性测试，覆盖iOS/Android 8个机型", 3.0, "testing"),
    ("【内部工具】搭建自动化部署流水线，配置GitLab CI", 2.5, "development"),
    ("【内部工具】运维平台添加日志聚合检索功能", 3.0, "development"),
    ("代码Review：审查了5个MR，提出了12条优化建议", 2.0, "other"),
    ("参加技术方案评审会议，讨论项目C架构选型", 1.5, "meeting"),
    ("编写项目A接口文档，对接前端联调", 2.0, "documentation"),
    ("修复线上告警：项目B服务内存泄漏问题排查", 3.0, "development"),
    ("搭建后端微服务基础框架（Spring Boot + K8s）", 4.0, "development"),
    ("处理测试环境数据库迁移脚本异常", 1.0, "other"),
    ("技术分享：Kubernetes生产环境最佳实践", 1.5, "meeting"),
]

PRODUCT_TASKS = [
    ("【项目A】梳理用户反馈，整理下个迭代需求池（23条）", 2.5, "documentation"),
    ("【项目B】绘制数据看板原型图 v2.0（Figma）", 3.0, "design"),
    ("【项目B】与客户沟通数据报表自定义需求", 1.5, "meeting"),
    ("【项目C】竞品分析：对比飞书、企业微信文档模块", 2.0, "documentation"),
    ("【内部工具】运维平台用户访谈，收集痛点8条", 2.0, "meeting"),
    ("撰写项目A Q3产品路线图", 2.5, "documentation"),
    ("参加需求评审会，评估项目C新功能可行性", 1.5, "meeting"),
    ("【项目A】用户验收测试（UAT）协调与跟进", 2.0, "testing"),
]

MARKET_TASKS = [
    ("【项目A】准备产品发布会演示文稿", 3.0, "documentation"),
    ("【项目B】客户现场演示及技术答疑", 2.0, "meeting"),
    ("【项目C】整理销售话术及竞品对比表", 2.5, "documentation"),
    ("【内部工具】内部推广方案策划", 2.0, "documentation"),
    ("参加公司季度业务复盘会议", 2.0, "meeting"),
    ("客户回访：项目B使用反馈收集（4家客户）", 3.0, "meeting"),
]

# Tasks for 今日未完成工作 / 需协调工作 / 明日计划
UNFINISHED_TASKS = [
    "【项目A】密码重置功能仍在开发中，需后端配合接口联调",
    "【项目B】数据导出支持Excel格式还需要1天",
    "【项目C】移动端适配部分机型仍有兼容问题",
]

COORDINATION_TASKS = [
    "需要运维配合部署项目A测试环境",
    "需设计组提供项目B看板最终设计稿",
    "需前端确认项目C接口字段定义",
]

TOMORROW_PLANS = [
    "完成密码重置功能开发 + 接口联调",
    "继续项目B性能优化 + 编写技术文档",
    "项目C移动端适配 + 回归测试",
    "参加需求评审会议 + 代码Review",
    "整理技术债务清单 + 制定优化计划",
]

NOTES = [
    "今日效率较高，项目A进展顺利",
    "下午被线上问题打断约1小时",
    "今天主要时间花在Code Review上",
    "",
    "本周工时正常，无需额外关注",
]


class Command(BaseCommand):
    help = "创建 Demo 工作日志与工时数据"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=10,
            help="生成最近多少天的工作日志 (default: 10)",
        )

    def handle(self, *args, **options):
        days = options["days"]

        # ---- Projects ----
        self.stdout.write("创建 Demo 项目...")
        projects = {}
        pm = User.objects.get(username="proj_mgr")
        for proj_info in DEMO_PROJECTS:
            proj, created = Project.objects.get_or_create(
                code=proj_info["code"],
                defaults={
                    "name": proj_info["name"],
                    "aliases": proj_info["aliases"],
                },
            )
            proj.product_managers.add(pm)
            projects[proj.name] = proj
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] 创建项目: {proj.name} ({proj.code})"))
            else:
                self.stdout.write(f"  --> 项目已存在: {proj.name}")

        # ---- Template ----
        template, _ = ReportTemplate.objects.get_or_create(
            name="日报",
            defaults={
                "dingtalk_template_id": "demo_daily_template",
                "fields": [
                    {"key": "今日完成工作", "type": "text"},
                    {"key": "今日未完成工作", "type": "text"},
                    {"key": "需协调工作", "type": "text"},
                    {"key": "明日重点工作计划", "type": "text"},
                    {"key": "备注", "type": "text"},
                ],
            },
        )

        # ---- SyncLog ----
        sync_log = SyncLog.objects.create(
            sync_type="manual",
            status="success",
            records_fetched=0,
            records_parsed=0,
        )

        # ---- Users & departments ----
        users = list(User.objects.all())
        dept_map = {
            "技术部": Department.objects.get(name="技术部"),
            "产品部": Department.objects.get(name="产品部"),
            "市场部": Department.objects.get(name="市场部"),
        }

        # Map usernames to their department & task pool
        user_config = {
            "admin": ("技术部", TECH_TASKS),
            "employee": ("技术部", TECH_TASKS),
            "dept_mgr_l1": ("技术部", TECH_TASKS),
            "dept_mgr_l2": ("技术部", TECH_TASKS),
            "proj_mgr": ("产品部", PRODUCT_TASKS),
        }

        # Generate working days (Mon-Fri only)
        today = date.today()
        working_days = []
        d = today - timedelta(days=days)
        while d <= today:
            if d.weekday() < 5:  # Mon=0 ... Fri=4
                working_days.append(d)
            d += timedelta(days=1)

        self.stdout.write(f"\n生成 {len(users)} 个用户 x {len(working_days)} 天的日志...")

        report_count = 0
        entry_count = 0

        # Start sequence after the highest existing report ID to avoid collision
        last_report = WorkReport.objects.order_by("-id").first()
        report_id_seq = (last_report.id + 1000) if last_report else 1000

        for work_date in working_days:
            for user in users:
                # ~80% chance of having a report on any given day
                if random.random() > 0.8:
                    continue

                dept_name, task_pool = user_config.get(user.username, ("技术部", TECH_TASKS))
                dept = dept_map.get(dept_name)

                # Pick 2-4 tasks for today
                n_tasks = random.randint(2, 4)
                today_tasks = random.sample(task_pool, min(n_tasks, len(task_pool)))

                # Build contents
                completed_text = "\n".join(f"{i+1}. {t[0]}" for i, t in enumerate(today_tasks))
                unfinished = random.choice(UNFINISHED_TASKS)
                coordination = random.choice(COORDINATION_TASKS)
                tomorrow = random.choice(TOMORROW_PLANS)
                note = random.choice(NOTES)

                raw_contents = [
                    {"key": "今日完成工作", "value": completed_text},
                    {"key": "今日未完成工作", "value": unfinished},
                    {"key": "需协调工作", "value": coordination},
                    {"key": "明日重点工作计划", "value": tomorrow},
                    {"key": "备注", "value": note},
                ]

                # Create WorkReport
                report_id_seq += 1
                report = WorkReport.objects.create(
                    dingtalk_report_id=f"demo_report_{report_id_seq:05d}",
                    template=template,
                    creator=user,
                    department=dept or user.department,
                    report_date=work_date,
                    create_time=timezone.make_aware(
                        timezone.datetime.combine(
                            work_date, timezone.datetime.min.time()
                        ).replace(hour=random.randint(17, 20), minute=random.randint(0, 59))
                    ),
                    raw_contents={"contents": raw_contents},
                    status="submitted",
                    sync_log=sync_log,
                )

                # Create ReportContent rows
                for idx, field in enumerate(raw_contents):
                    ReportContent.objects.create(
                        report=report,
                        field_key=field["key"],
                        field_value=field["value"],
                        order=idx + 1,
                    )

                # Create WorkEntry rows for each task
                for task_desc, hours, task_type in today_tasks:
                    # Determine which project this task belongs to
                    matched_project = None
                    for proj_name, proj in projects.items():
                        if proj_name in task_desc or f"【{proj_name}】" in task_desc:
                            matched_project = proj
                            break

                    # Alternate confidence
                    confidence = random.choice([85, 90, 95, 70, 60, 100])

                    WorkEntry.objects.create(
                        report=report,
                        employee=user,
                        department=dept or user.department,
                        project=matched_project,
                        date=work_date,
                        hours=hours,
                        task_description=task_desc,
                        task_type=task_type,
                        status="completed",
                        confidence=confidence,
                        raw_text=task_desc,
                        is_categorized=matched_project is not None,
                    )
                    entry_count += 1

                report_count += 1

        # Update sync_log with actual counts
        sync_log.records_fetched = report_count
        sync_log.records_parsed = entry_count
        sync_log.save(update_fields=["records_fetched", "records_parsed"])

        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] 数据生成完成! "
            f"日志: {report_count} 条, 工时: {entry_count} 条, "
            f"日期范围: {working_days[0]} ~ {working_days[-1]}"
        ))

        # Summary
        self.stdout.write("\n数据摘要:")
        for proj_name, proj in projects.items():
            total_hours = sum(
                e.hours for e in WorkEntry.objects.filter(project=proj)
            )
            entry_n = WorkEntry.objects.filter(project=proj).count()
            self.stdout.write(f"  * {proj_name} ({proj.code}): {entry_n} 条记录, 共 {total_hours}h")

        uncategorized = WorkEntry.objects.filter(project__isnull=True).count()
        self.stdout.write(f"  * 未归类: {uncategorized} 条记录")
        self.stdout.write(f"\n  管理后台: http://127.0.0.1:8000/admin/")
