"""
Management command to seed demo data for local development.

Creates:
- 3 departments: 技术部, 产品部, 市场部
- 5 users (one per role), all with password "admin123"

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --password mypass
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import Department, User


DEMO_DEPARTMENTS = [
    {"name": "技术部", "children": ["前端组", "后端组", "测试组"]},
    {"name": "产品部", "children": ["产品设计组"]},
    {"name": "市场部", "children": ["销售组"]},
]

DEMO_USERS = [
    {"username": "admin", "role": User.Role.ADMIN, "dept": "技术部", "name": "系统管理员"},
    {"username": "executive", "role": User.Role.EXECUTIVE, "dept": None, "name": "公司高层"},
    {"username": "dept_mgr", "role": User.Role.DEPT_MANAGER, "dept": "技术部", "name": "技术经理"},
    {"username": "prod_mgr", "role": User.Role.PRODUCT_MANAGER, "dept": "产品部", "name": "产品经理"},
    {"username": "employee", "role": User.Role.EMPLOYEE, "dept": "技术部", "name": "普通员工"},
]


class Command(BaseCommand):
    help = "创建 Demo 模式的部门与用户数据"

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="admin123",
            help="所有 Demo 用户的密码 (default: admin123)",
        )

    def handle(self, *args, **options):
        password = options["password"]

        # ---- Create departments ----
        self.stdout.write("创建 Demo 部门...")
        top_depts = {}
        for dept_info in DEMO_DEPARTMENTS:
            dept, created = Department.objects.get_or_create(name=dept_info["name"])
            top_depts[dept.name] = dept
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] 创建部门: {dept.name}"))
            else:
                self.stdout.write(f"  --> 部门已存在: {dept.name}")

            for child_name in dept_info.get("children", []):
                child, created = Department.objects.get_or_create(
                    name=child_name,
                    defaults={"parent": dept},
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"    [+] 创建子部门: {child_name}"))
                else:
                    self.stdout.write(f"    --> 子部门已存在: {child_name}")

        # ---- Create users ----
        self.stdout.write("\n创建 Demo 用户...")
        for user_info in DEMO_USERS:
            dept_name = user_info["dept"]
            department = Department.objects.get(name=dept_name) if dept_name else None

            user, created = User.objects.get_or_create(
                username=user_info["username"],
                defaults={
                    "role": user_info["role"],
                    "department": department,
                    "first_name": user_info["name"],
                    "is_staff": user_info["role"] == User.Role.ADMIN,
                    "is_superuser": user_info["role"] == User.Role.ADMIN,
                },
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [+] 创建用户: {user_info['username']} "
                        f"({user_info['role'].label}) -- 密码: {password}"
                    )
                )
            else:
                # Update existing user in case fields changed
                updated = False
                if user.role != user_info["role"]:
                    user.role = user_info["role"]
                    updated = True
                if department and user.department != department:
                    user.department = department
                    updated = True
                if updated:
                    user.save()
                user.set_password(password)
                user.save()
                self.stdout.write(
                    f"  --> 用户已存在(已更新密码): {user_info['username']} "
                    f"({user_info['role'].label})"
                )

        self.stdout.write(self.style.SUCCESS("\n[OK] Demo 数据创建完成!"))
        self.stdout.write("可用账号(密码均为 admin123):")
        for u in DEMO_USERS:
            self.stdout.write(f"  * {u['username']:12s} -> {u['role'].label}")
