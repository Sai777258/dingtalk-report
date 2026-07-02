"""
Shared utilities for importing data from the external DingTalk log database.

Provides connection management, user/department resolution, and text parsing
used by both the schema discovery and ETL import commands.
"""
import re
import logging
from django.conf import settings
from django.core.management import CommandError

logger = logging.getLogger(__name__)


# ---- Connection ----

def get_external_connection():
    """
    Open and return a read-only pymysql connection to the external DB.

    Uses DictCursor so rows are keyed by column name.
    Raises CommandError if the external DB is not enabled or connection fails.
    """
    if not settings.EXTERNAL_DB_ENABLED:
        raise CommandError("外部数据库未启用 (EXTERNAL_DB_ENABLED=False)")

    import pymysql

    try:
        conn = pymysql.connect(
            host=settings.EXTERNAL_DB_HOST,
            port=settings.EXTERNAL_DB_PORT,
            user=settings.EXTERNAL_DB_USER,
            password=settings.EXTERNAL_DB_PASSWORD,
            database=settings.EXTERNAL_DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return conn
    except pymysql.err.OperationalError as e:
        code, msg = e.args if len(e.args) == 2 else (0, str(e))
        if "Access denied" in msg:
            raise CommandError(
                f"MySQL 认证失败 — 请检查 .env 中的 EXTERNAL_DB_USER / EXTERNAL_DB_PASSWORD\n"
                f"  详情: {msg}"
            )
        raise CommandError(
            f"无法连接外部数据库 {settings.EXTERNAL_DB_HOST}:{settings.EXTERNAL_DB_PORT}\n"
            f"  详情: {msg}"
        )


# ---- User / Department resolution ----

def resolve_user(external_user_id, external_username=None):
    """
    Find or create a local User record matching an external identity.

    Resolution order:
    1. Look up by dingtalk_user_id
    2. Look up by external username (if provided)
    3. Create a placeholder User

    Returns (user, created_placeholder: bool).
    """
    from apps.accounts.models import User

    if external_user_id:
        user = User.objects.filter(dingtalk_user_id=str(external_user_id)).first()
        if user:
            return user, False

    if external_username:
        user = User.objects.filter(username=external_username).first()
        if user:
            return user, False

    # Create placeholder
    username = f"dt_import_{external_user_id}" if external_user_id else f"dt_import_unknown_{User.objects.count()}"
    # Ensure unique username
    base_username = username
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{suffix}"
        suffix += 1

    user = User.objects.create(
        username=username,
        dingtalk_user_id=str(external_user_id) if external_user_id else None,
        role=User.Role.EMPLOYEE,
        first_name=external_username or username,
        is_active=True,
    )
    logger.warning("Created placeholder user: %s (dingtalk_user_id=%s)", username, external_user_id)
    return user, True


def resolve_department(external_dept_id, external_dept_name=None):
    """
    Find or create a local Department record matching an external identity.

    Resolution order:
    1. Look up by dingtalk_dept_id
    2. Look up by name (if provided)
    3. Create a placeholder Department

    Returns (department, created_placeholder: bool).
    """
    from apps.accounts.models import Department

    if external_dept_id:
        dept = Department.objects.filter(dingtalk_dept_id=external_dept_id).first()
        if dept:
            return dept, False

    if external_dept_name:
        dept = Department.objects.filter(name=external_dept_name).first()
        if dept:
            return dept, False

    # Create placeholder
    name = external_dept_name or f"外部部门_{external_dept_id}"
    dept = Department.objects.create(
        name=name,
        dingtalk_dept_id=external_dept_id,
    )
    logger.warning("Created placeholder department: %s (dingtalk_dept_id=%s)", name, external_dept_id)
    return dept, True


def resolve_template(template_name="日报"):
    """
    Find or create a ReportTemplate with the given name.
    """
    from apps.reports.models import ReportTemplate

    template, _ = ReportTemplate.objects.get_or_create(
        name=template_name,
        defaults={
            "dingtalk_template_id": f"imported_{template_name}",
            "fields": [
                {"key": "今日完成工作", "type": "text"},
                {"key": "今日未完成工作", "type": "text"},
                {"key": "需协调工作", "type": "text"},
                {"key": "明日重点工作计划", "type": "text"},
                {"key": "备注", "type": "text"},
            ],
        },
    )
    return template


# ---- Text parsing ----

# Patterns for extracting hours from work descriptions
HOUR_PATTERNS = [
    (re.compile(r"耗时\s*(\d+(?:\.\d+)?)\s*小时"), 1.0),       # 耗时3.5小时
    (re.compile(r"耗时\s*(\d+(?:\.\d+)?)\s*[hH]"), 1.0),       # 耗时3h
    (re.compile(r"(\d+(?:\.\d+)?)\s*小时"), 1.0),               # 3.5小时
    (re.compile(r"(\d+(?:\.\d+)?)\s*[hH](?!\s*[zZ])"), 1.0),   # 3h (not 3hz)
    (re.compile(r"耗时\s*(\d+(?:\.\d+)?)\s*分钟"), 1.0 / 60),   # 耗时30分钟 → 0.5
    (re.compile(r"(\d+(?:\.\d+)?)\s*分钟"), 1.0 / 60),          # 30分钟 → 0.5
    (re.compile(r"(\d+(?:\.\d+)?)\s*天"), 8.0),                 # 1天 → 8h
]


def parse_hours_from_text(text):
    """
    Try to extract work hours from a free-text description.

    Returns (hours: float, confidence: int).
    Confidence: 80+ if hours found via pattern, 30 if estimated.
    """
    if not text:
        return 0.0, 0

    for pattern, multiplier in HOUR_PATTERNS:
        match = pattern.search(text)
        if match:
            hours = float(match.group(1)) * multiplier
            return round(hours, 2), 85

    return 0.0, 0


def estimate_hours_from_entries(entry_texts, total_hours=8.0):
    """
    When no explicit hours are found, distribute total_hours evenly across entries.

    Returns a list of (hours, confidence) tuples, one per entry.
    """
    if not entry_texts:
        return []

    n = len(entry_texts)
    hours_each = round(total_hours / n, 2)
    return [(hours_each, 30) for _ in entry_texts]


def match_project(text, projects_cache=None):
    """
    Try to match a text description to a known Project.

    Uses Project.match_text() which checks name, code, and aliases.
    Returns Project or None.
    """
    from apps.projects.models import Project

    if projects_cache is None:
        projects_cache = list(Project.objects.filter(status="active"))

    for proj in projects_cache:
        if proj.match_text(text):
            return proj
    return None


# ---- Content helpers ----

def split_content_lines(value_text):
    """
    Split a content field value into individual task lines.

    Handles common formats:
    - Numbered: "1. task A\n2. task B"
    - Dashed: "- task A\n- task B"
    - Plain newlines

    Returns a list of non-empty, stripped task strings.
    """
    if not value_text:
        return []

    lines = []
    for line in value_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip common numbering prefixes: "1.", "1、", "1)", "- ", "* "
        line = re.sub(r"^[\d]+[\.\、\)]\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        if line:
            lines.append(line)
    return lines
