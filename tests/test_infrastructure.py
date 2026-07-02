"""
Comprehensive infrastructure test — validates all 6 steps.
Run: python manage.py test tests.test_infrastructure
"""
import json
from datetime import date

from django.test import TestCase, Client
from django.db import connection
from django.contrib.auth import authenticate

from apps.accounts.models import User, Department
from apps.projects.models import Project
from apps.reports.models import ReportTemplate, WorkReport, ReportContent
from apps.dingtalk.models import SyncLog
from apps.dingtalk.client import client as dt_client
from apps.dingtalk.token_manager import token_manager
from apps.stats.models import WorkEntry


class InfrastructureTest(TestCase):
    """End-to-end validation of Steps 1-6."""

    @classmethod
    def setUpTestData(cls):
        # Ensure demo data exists
        import os
        from django.core.management import call_command
        call_command("seed_demo", stdout=open(os.devnull, "w"))

        cls.admin = User.objects.get(username="admin")
        cls.dept_mgr_l1 = User.objects.get(username="dept_mgr_l1")
        cls.dept_mgr_l2 = User.objects.get(username="dept_mgr_l2")
        cls.proj_mgr = User.objects.get(username="proj_mgr")
        cls.employee = User.objects.get(username="employee")
        cls.tech_dept = Department.objects.get(name="技术部")
        cls.product_dept = Department.objects.get(name="产品部")

    # ==================================================================
    # 1. System check
    # ==================================================================
    def test_01_django_system_check(self):
        from django.core.management import call_command
        call_command("check", verbosity=0)
        self.assertTrue(True)

    # ==================================================================
    # 2. Database tables
    # ==================================================================
    def test_02_database_tables_exist(self):
        tables = connection.introspection.table_names()
        expected = [
            "accounts_department", "accounts_user",
            "dingtalk_synclog",
            "projects_project", "projects_project_product_managers",
            "reports_reporttemplate", "reports_workreport", "reports_reportcontent",
            "stats_workentry",
        ]
        for t in expected:
            self.assertIn(t, tables, f"Table missing: {t}")

    def test_02b_demo_data(self):
        self.assertGreaterEqual(User.objects.count(), 5)
        self.assertGreaterEqual(Department.objects.count(), 5)

    # ==================================================================
    # 3. Authentication
    # ==================================================================
    def test_03_admin_auth(self):
        user = authenticate(username="admin", password="admin123")
        self.assertIsNotNone(user)
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_superuser)

    def test_03_employee_auth(self):
        user = authenticate(username="employee", password="admin123")
        self.assertIsNotNone(user)
        self.assertTrue(user.is_employee)

    def test_03_wrong_password(self):
        user = authenticate(username="admin", password="wrong")
        self.assertIsNone(user)

    # ==================================================================
    # 4. API endpoints
    # ==================================================================
    def test_04_demo_login_success(self):
        c = Client()
        resp = c.post(
            "/api/auth/demo-login/",
            data=json.dumps({"username": "admin", "password": "admin123"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("user", data)
        self.assertIn("role_display", data["user"])

    def test_04_demo_login_wrong_password(self):
        c = Client()
        resp = c.post(
            "/api/auth/demo-login/",
            data=json.dumps({"username": "admin", "password": "wrong"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_04_me_endpoint_authenticated(self):
        c = Client()
        resp = c.post(
            "/api/auth/demo-login/",
            data=json.dumps({"username": "admin", "password": "admin123"}),
            content_type="application/json",
        )
        token = resp.json()["access"]
        resp2 = c.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["username"], "admin")

    def test_04_me_endpoint_unauthenticated(self):
        c = Client()
        resp = c.get("/api/auth/me/")
        self.assertEqual(resp.status_code, 401)

    def test_04_all_roles_can_login(self):
        c = Client()
        for username in ["admin", "dept_mgr_l1", "dept_mgr_l2", "proj_mgr", "employee"]:
            resp = c.post(
                "/api/auth/demo-login/",
                data=json.dumps({"username": username, "password": "admin123"}),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200, f"{username} login failed")

    # ==================================================================
    # 5. DingTalk client (demo mode)
    # ==================================================================
    def test_05_demo_mode_active(self):
        self.assertTrue(dt_client._demo_mode())

    def test_05_token_manager_demo(self):
        self.assertIn("mock", token_manager.get_token())

    def test_05_get_report_list(self):
        result = dt_client.get_report_list(1700000000000, 1700100000000)
        self.assertIn("data_list", result)
        self.assertIsInstance(result["has_more"], bool)
        self.assertGreater(len(result["data_list"]), 0)
        r0 = result["data_list"][0]
        self.assertIn("report_id", r0)
        self.assertIn("creator_name", r0)
        self.assertIn("contents", r0)
        self.assertGreaterEqual(len(r0["contents"]), 5)

    def test_05_pagination_end(self):
        result = dt_client.get_report_list(1700000000000, 1700100000000, cursor=3)
        self.assertFalse(result["has_more"])
        self.assertEqual(result["data_list"], [])

    def test_05_get_user_info(self):
        user_info = dt_client.get_user_info_by_code("demo_admin")
        self.assertIn("result", user_info)
        self.assertIn("userid", user_info["result"])

    # ==================================================================
    # 6. ORM models
    # ==================================================================
    def test_06_project_crud(self):
        proj = Project.objects.create(
            name="测试项目", code="TEST-01",
            aliases=["测试", "TEST"],
        )
        proj.product_managers.add(self.proj_mgr)
        self.assertIsNotNone(proj.pk)
        self.assertTrue(proj.match_text("【测试项目】开发"))
        self.assertTrue(proj.match_text("TEST-01"))
        self.assertFalse(proj.match_text("无关内容"))

    def test_06_report_template(self):
        tmpl = ReportTemplate.objects.create(
            name="测试模板",
            fields=[{"key": "今日完成工作", "type": "text"}],
        )
        self.assertIsNotNone(tmpl.pk)

    def test_06_work_report_and_content(self):
        tmpl = ReportTemplate.objects.create(name="测试", fields=[])
        sync_log = SyncLog.objects.create(sync_type="manual")
        report = WorkReport.objects.create(
            dingtalk_report_id="test_006",
            creator=self.employee,
            department=self.tech_dept,
            report_date=date.today(),
            sync_log=sync_log,
        )
        self.assertIsNotNone(report.pk)
        self.assertEqual(report.creator, self.employee)

        content = ReportContent.objects.create(
            report=report, field_key="今日完成工作",
            field_value="测试内容", order=1,
        )
        self.assertEqual(report.contents.count(), 1)

    def test_06_work_entry(self):
        proj = Project.objects.create(name="WF", code="WF")
        sync = SyncLog.objects.create(sync_type="manual")
        report = WorkReport.objects.create(
            dingtalk_report_id="test_006_wf",
            creator=self.employee,
            report_date=date.today(),
        )
        entry = WorkEntry.objects.create(
            report=report,
            employee=self.employee,
            department=self.tech_dept,
            project=proj,
            date=date.today(),
            hours=3.5,
            task_description="测试",
            confidence=85,
            is_categorized=True,
        )
        self.assertEqual(entry.hours, 3.5)
        self.assertFalse(entry.is_low_confidence)
        self.assertTrue(entry.is_categorized)

    def test_06_low_confidence_entry(self):
        report = WorkReport.objects.create(
            dingtalk_report_id="test_006_low",
            creator=self.employee,
            report_date=date.today(),
        )
        entry = WorkEntry.objects.create(
            report=report,
            employee=self.employee,
            date=date.today(),
            hours=2.0,
            confidence=30,
            is_categorized=False,
        )
        self.assertTrue(entry.is_low_confidence)
        self.assertFalse(entry.is_categorized)

    # ==================================================================
    # 7. Role/permission system
    # ==================================================================
    def test_07_role_properties(self):
        self.assertTrue(self.admin.is_admin)
        self.assertTrue(self.dept_mgr_l1.is_dept_manager_l1)
        self.assertTrue(self.dept_mgr_l2.is_dept_manager_l2)
        self.assertTrue(self.proj_mgr.is_project_manager)
        self.assertTrue(self.employee.is_employee)
        # Admin and L1 see all data
        self.assertTrue(self.admin.is_any_manager or self.admin.is_admin)
        self.assertTrue(self.dept_mgr_l1.is_any_manager)

    def test_07a_l1_sees_all_data(self):
        """L1 dept manager has same data scope as admin."""
        from apps.accounts.permissions import get_visible_department_ids
        admin_ids = get_visible_department_ids(self.admin)
        l1_ids = get_visible_department_ids(self.dept_mgr_l1)
        self.assertEqual(set(admin_ids), set(l1_ids))
        # Both should see all departments
        all_dept_count = Department.objects.count()
        self.assertEqual(len(l1_ids), all_dept_count)

    def test_07b_l2_sees_only_own_dept(self):
        """L2 dept manager only sees their own department."""
        from apps.accounts.permissions import get_visible_department_ids
        l2_ids = get_visible_department_ids(self.dept_mgr_l2)
        self.assertEqual(l2_ids, [self.dept_mgr_l2.department_id])

    def test_07_can_view_department(self):
        self.assertTrue(self.admin.can_view_department(self.tech_dept))
        self.assertTrue(self.dept_mgr_l1.can_view_department(self.product_dept))
        self.assertTrue(self.dept_mgr_l2.can_view_department(self.dept_mgr_l2.department))
        self.assertTrue(self.employee.can_view_department(self.tech_dept))

    # ==================================================================
    # 8. Admin site
    # ==================================================================
    def test_08_admin_site_accessible(self):
        c = Client()
        c.login(username="admin", password="admin123")
        resp = c.get("/admin/")
        self.assertEqual(resp.status_code, 200)

    def test_08_all_models_registered(self):
        c = Client()
        c.login(username="admin", password="admin123")
        content = c.get("/admin/").content.decode("utf-8")
        models = ["部门", "用户", "同步日志", "项目",
                   "报告模板", "工作日志", "日志内容", "工时记录"]
        for name in models:
            self.assertIn(name, content, f"Model not in admin: {name}")

    # ==================================================================
    # 9. Cross-app FK integrity
    # ==================================================================
    def test_09_cross_app_foreign_keys(self):
        self.assertIsNotNone(
            WorkReport._meta.get_field("creator").remote_field
        )
        self.assertIsNotNone(
            WorkReport._meta.get_field("sync_log").remote_field
        )
        self.assertIsNotNone(
            WorkEntry._meta.get_field("project").remote_field
        )
        self.assertIsNotNone(
            WorkEntry._meta.get_field("report").remote_field
        )

    # ==================================================================
    # 10. DB indexes
    # ==================================================================
    def test_10_work_entry_indexes(self):
        indexes = [idx.fields for idx in WorkEntry._meta.indexes]
        flat = [tuple(f) for f in indexes]
        self.assertIn(("employee", "date"), flat)
        self.assertIn(("department", "date"), flat)
        self.assertIn(("project", "date"), flat)
        self.assertIn(("is_categorized",), flat)
