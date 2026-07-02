"""
Management command to backfill User.department for imported users.

Imported users (from import_from_external_db) have department=None on their
User record even though their WorkEntry/WorkReport records reference a
department. This command finds the most common department for each such user
and sets it.

Usage:
    python manage.py backfill_user_departments
    python manage.py backfill_user_departments --dry-run
"""
from collections import Counter
from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.stats.models import WorkEntry


class Command(BaseCommand):
    help = "回填导入用户的 department 关联（从 WorkEntry 记录推断）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅预览，不实际修改数据库",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Find users with department=None who have work entries
        users = User.objects.filter(
            department__isnull=True,
            work_entries__isnull=False,
        ).distinct()

        self.stdout.write(f"找到 {users.count()} 个 department=NULL 且有工时记录的用户\n")

        updated = 0
        for user in users.order_by("username"):
            # Find the most common department from their work entries
            dept_counts = Counter(
                WorkEntry.objects.filter(employee=user)
                .exclude(department__isnull=True)
                .values_list("department_id", "department__name")
            )
            if not dept_counts:
                self.stdout.write(f"  [SKIP] {user.username} — 所有 WorkEntry 无 department")
                continue

            (dept_id, dept_name), count = dept_counts.most_common(1)[0]
            total_entries = WorkEntry.objects.filter(employee=user).count()

            if dry_run:
                self.stdout.write(
                    f"  [DRY-RUN] {user.username:30s} → {dept_name} "
                    f"({count}/{total_entries} entries, {count*100//total_entries}%)"
                )
            else:
                user.department_id = dept_id
                user.save(update_fields=["department"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [+] {user.username:30s} → {dept_name} "
                        f"({count}/{total_entries} entries)"
                    )
                )
            updated += 1

        if dry_run:
            self.stdout.write(f"\n[DRY-RUN] 将更新 {updated} 个用户 (未实际修改)")
        else:
            self.stdout.write(self.style.SUCCESS(f"\n[OK] 已更新 {updated} 个用户"))
