"""
Management command to discover the schema of the external DingTalk log database.

Usage:
    python manage.py discover_mysql_schema
    python manage.py discover_mysql_schema --table dingtalk_report  # single table
    python manage.py discover_mysql_schema --output-file fixtures/external_db_schema.json
"""
import json
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "探查外部 MySQL 钉钉日志库的表结构"

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            help="仅探查指定表（默认：所有表）",
        )
        parser.add_argument(
            "--output-file",
            help="将 schema 导出为 JSON 文件",
        )
        parser.add_argument(
            "--sample",
            type=int,
            default=0,
            help="每张表取 N 条样本数据（默认 0，不取样）",
        )

    def handle(self, *args, **options):
        if not settings.EXTERNAL_DB_ENABLED:
            raise CommandError(
                "外部数据库未启用。请在 .env 中设置 EXTERNAL_DB_ENABLED=True "
                "并配置 EXTERNAL_DB_HOST / EXTERNAL_DB_USER / EXTERNAL_DB_PASSWORD"
            )

        # Credential check
        missing = []
        for key in ("EXTERNAL_DB_HOST", "EXTERNAL_DB_USER", "EXTERNAL_DB_PASSWORD"):
            if not getattr(settings, key, None):
                missing.append(key)
        if missing:
            raise CommandError(f"缺少外部数据库凭据: {', '.join(missing)}")

        import pymysql

        conn = None
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
            self.stdout.write(self.style.SUCCESS(
                f"[OK] 已连接 {settings.EXTERNAL_DB_HOST}:{settings.EXTERNAL_DB_PORT}/{settings.EXTERNAL_DB_NAME}"
            ))
        except pymysql.err.OperationalError as e:
            raise CommandError(f"连接外部数据库失败: {e}")

        schema_data = {}
        try:
            with conn.cursor() as cursor:
                # List tables
                target_table = options.get("table")
                if target_table:
                    cursor.execute(f"SHOW TABLES LIKE %s", (target_table,))
                else:
                    cursor.execute("SHOW TABLES")

                tables = [row[list(row.keys())[0]] for row in cursor.fetchall()]

                if not tables:
                    self.stdout.write(self.style.WARNING("未找到任何表"))
                    return

                self.stdout.write(f"\n找到 {len(tables)} 张表:\n")

                for table_name in tables:
                    self.stdout.write(self.style.SUCCESS(f"=== {table_name} ==="))

                    # Column descriptions
                    cursor.execute(f"DESCRIBE `{table_name}`")
                    columns = cursor.fetchall()
                    self.stdout.write(f"  字段 ({len(columns)}):")
                    for col in columns:
                        null_mark = "NULL" if col.get("Null", "YES") == "YES" else "NOT NULL"
                        key_mark = f" [{col.get('Key', '')}]" if col.get("Key") else ""
                        default = f" DEFAULT {col.get('Default')}" if col.get("Default") is not None else ""
                        self.stdout.write(
                            f"    {col['Field']:<30} {col['Type']:<20} {null_mark:<8}{key_mark}{default}"
                        )

                    # CREATE TABLE statement
                    cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                    create_row = cursor.fetchone()
                    if create_row:
                        create_sql = create_row.get("Create Table", "")
                        self.stdout.write(f"\n  DDL:\n{create_sql}\n")

                    # Row count
                    cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table_name}`")
                    count_row = cursor.fetchone()
                    row_count = count_row["cnt"] if count_row else 0
                    self.stdout.write(f"  行数: {row_count:,}\n")

                    # Sample data
                    sample_n = options.get("sample", 0)
                    if sample_n > 0 and row_count > 0:
                        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {sample_n}")
                        samples = cursor.fetchall()
                        self.stdout.write(f"  样本数据 ({len(samples)} 条):")
                        for i, sample in enumerate(samples):
                            self.stdout.write(f"    --- 第 {i+1} 条 ---")
                            for key, value in sample.items():
                                val_str = str(value)
                                if len(val_str) > 120:
                                    val_str = val_str[:120] + "..."
                                self.stdout.write(f"      {key}: {val_str}")
                        self.stdout.write("")

                    # Build schema data for JSON export
                    schema_data[table_name] = {
                        "columns": [
                            {
                                "field": col["Field"],
                                "type": col["Type"],
                                "null": col.get("Null", "YES") == "YES",
                                "key": col.get("Key", ""),
                                "default": str(col.get("Default")) if col.get("Default") is not None else None,
                            }
                            for col in columns
                        ],
                        "row_count": row_count,
                        "create_table": create_sql if create_row else "",
                    }

        finally:
            conn.close()

        # JSON export
        output_file = options.get("output_file")
        if output_file:
            from pathlib import Path
            out_path = Path(output_file)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(schema_data, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"\n[OK] Schema 已导出至 {out_path}"))

        # Summary
        total_rows = sum(t["row_count"] for t in schema_data.values())
        self.stdout.write(f"\n汇总: {len(schema_data)} 张表, 共 {total_rows:,} 条记录")
