"""
API views for dashboard aggregation and work entry listing.

DashboardView supports 4 views via ?view= param:
  (default) — summary KPI + charts data
  employee  — per-employee → projects → work types
  project   — per-project → employees → work types
  department — department tree → employees → projects → entries
"""
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Sum, Count, Avg, Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import apply_work_entry_access_filter, get_visible_department_ids
from apps.accounts.models import Department
from .models import WorkEntry
from .serializers import WorkEntrySerializer

TASK_TYPE_DISPLAY = {
    "development": "开发",
    "testing": "测试",
    "meeting": "会议",
    "documentation": "文档",
    "design": "设计",
    "other": "其他",
}


class WorkEntryListView(generics.ListAPIView):
    """
    GET /api/stats/entries/
    Query params: ?project_id=1&employee_id=2&date_from=2026-06-01&date_to=2026-06-30
    """
    serializer_class = WorkEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WorkEntry.objects.select_related("employee", "project", "department").exclude(
            report__dingtalk_report_id__startswith="demo_report_"
        )

        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        employee_id = self.request.query_params.get("employee_id")
        if employee_id:
            qs = qs.filter(employee_id=employee_id)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(date__lte=date_to)

        qs = apply_work_entry_access_filter(qs, self.request.user)
        return qs


class DashboardView(APIView):
    """
    GET /api/stats/dashboard/

    Query params:
      ?view=employee|project|department   (default: summary)
      ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        view = request.query_params.get("view", "").lower()
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        # Exclude demo seed data — only show real imported reports
        entries = WorkEntry.objects.exclude(
            report__dingtalk_report_id__startswith="demo_report_"
        )

        # Apply date filters if provided, otherwise default to this month
        if date_from or date_to:
            base_qs = apply_work_entry_access_filter(entries, request.user)
            if date_from:
                base_qs = base_qs.filter(date__gte=date_from)
            if date_to:
                base_qs = base_qs.filter(date__lte=date_to)
            this_month_qs = base_qs
        else:
            base_qs = apply_work_entry_access_filter(entries, request.user)
            today = date.today()
            this_month_start = today.replace(day=1)
            this_month_qs = base_qs.filter(date__gte=this_month_start, date__lte=today)

        if view == "employee":
            return Response(self._get_employee_view(this_month_qs))
        elif view == "project":
            return Response(self._get_project_view(this_month_qs))
        elif view == "department":
            return Response(self._get_department_view(this_month_qs, request.user))
        else:
            return Response(self._get_summary(base_qs, this_month_qs))

    # ------------------------------------------------------------------
    # Summary (existing logic)
    # ------------------------------------------------------------------
    def _get_summary(self, base_qs, this_month_qs):
        # Exclude demo seed data
        this_month_qs = this_month_qs.exclude(report__dingtalk_report_id__startswith="demo_report_")
        base_qs = base_qs.exclude(report__dingtalk_report_id__startswith="demo_report_")

        today = date.today()
        this_month_start = today.replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # Working days so far this month (for submission rate).
        # Stop at yesterday — today's reports haven't been submitted yet.
        yesterday = today - timedelta(days=1)
        working_days = 0
        d = this_month_start
        while d <= yesterday:
            if d.weekday() < 5:
                working_days += 1
            d += timedelta(days=1)

        this_month_hours = this_month_qs.aggregate(t=Sum("hours"))["t"] or 0
        last_month_hours = base_qs.filter(
            date__gte=last_month_start, date__lte=last_month_end
        ).aggregate(t=Sum("hours"))["t"] or 0

        last_month_reports = base_qs.filter(
            date__gte=last_month_start, date__lte=last_month_end
        ).values("report").distinct().count()

        total_reports = this_month_qs.values("report").distinct().count()
        active_projects = this_month_qs.exclude(project__isnull=True).values("project").distinct().count()
        active_employees = this_month_qs.values("employee").distinct().count()

        days_with_data = this_month_qs.values("date").distinct().count()
        avg_daily = round(float(this_month_hours) / days_with_data, 1) if days_with_data > 0 else 0

        # Work type distribution
        wt_stats = this_month_qs.values("task_type").annotate(
            hours=Sum("hours"),
        ).order_by("-hours")
        total_wt_hours = sum(w["hours"] for w in wt_stats) or 1
        work_type_breakdown = [{
            "type": w["task_type"],
            "display": TASK_TYPE_DISPLAY.get(w["task_type"], w["task_type"]),
            "hours": float(w["hours"]),
            "percentage": round(float(w["hours"]) / float(total_wt_hours) * 100, 1),
        } for w in wt_stats]

        work_type_structure = self._get_work_type_structure(
            this_month_qs,
            float(this_month_hours),
            days_with_data,
        )

        pstats = list(this_month_qs.values("project_id", "project__name", "project__code").annotate(
            hours=Sum("hours"), entry_count=Count("id"),
            employee_count=Count("employee_id", distinct=True),
            avg_confidence=Avg("confidence"),
            low_confidence_count=Count("id", filter=Q(confidence__lt=50)),
        ).order_by("-hours"))
        total_p_hours = sum(p["hours"] for p in pstats) or 1

        project_type_map = self._get_project_type_map(this_month_qs)
        project_employee_map = self._get_project_employee_map(this_month_qs)
        project_count = len([p for p in pstats if p["project_id"]])
        project_breakdown = []
        for p in pstats:
            project = {
                "project_id": p["project_id"],
                "project_name": p["project__name"] or "未归类",
                "project_code": p["project__code"] or "",
                "hours": float(p["hours"]),
                "entry_count": p["entry_count"],
                "employee_count": p["employee_count"],
                "percentage": round(float(p["hours"]) / float(total_p_hours) * 100, 1),
                "avg_confidence": round(float(p["avg_confidence"] or 0), 1),
                "low_confidence_count": p["low_confidence_count"],
            }
            project.update(self._get_project_health(
                project,
                project_count,
                project_type_map.get(p["project_id"], []),
                project_employee_map.get(p["project_id"], []),
                days_with_data,
            ))
            project_breakdown.append(project)

        estats = this_month_qs.values(
            "employee_id", "employee__first_name", "employee__username", "department__name",
        ).annotate(
            hours=Sum("hours"), entry_count=Count("id"),
        ).order_by("-hours")
        employee_breakdown = [{
            "employee_id": e["employee_id"],
            "employee_name": e["employee__first_name"] or e["employee__username"],
            "department_name": e["department__name"] or "",
            "hours": float(e["hours"]),
            "entry_count": e["entry_count"],
        } for e in estats]

        department_breakdown = self._get_department_breakdown(
            this_month_qs,
            float(this_month_hours),
            days_with_data,
        )

        thirty_days_ago = today - timedelta(days=29)
        dailies = base_qs.filter(date__gte=thirty_days_ago, date__lte=today).values(
            "date"
        ).annotate(
            hours=Sum("hours"), report_count=Count("report_id", distinct=True),
        ).order_by("date")
        daily_trend = [{
            "date": d["date"].isoformat() if hasattr(d["date"], "isoformat") else str(d["date"]),
            "hours": float(d["hours"]),
            "report_count": d["report_count"],
        } for d in dailies]

        return {
            "total_hours_this_month": float(this_month_hours),
            "total_hours_last_month": float(last_month_hours),
            "total_reports_this_month": total_reports,
            "total_reports_last_month": last_month_reports,
            "active_projects": active_projects,
            "active_employees": active_employees,
            "avg_daily_hours": round(avg_daily, 1),
            "working_days_this_month": working_days,
            "project_breakdown": project_breakdown,
            "employee_breakdown": employee_breakdown,
            "department_breakdown": department_breakdown,
            "work_type_breakdown": work_type_breakdown,
            "work_type_structure": work_type_structure,
            "daily_trend": daily_trend,
            "alerts": self._get_summary_alerts(
                this_month_qs,
                float(this_month_hours),
                days_with_data,
                project_breakdown,
            ),
        }

    def _get_project_type_map(self, qs):
        """Return project_id -> sorted work type distribution."""
        type_map = defaultdict(list)
        rows = qs.values("project_id", "task_type").annotate(hours=Sum("hours")).order_by(
            "project_id", "-hours",
        )
        totals = defaultdict(float)
        for row in rows:
            totals[row["project_id"]] += float(row["hours"] or 0)
            type_map[row["project_id"]].append({
                "type": row["task_type"],
                "display": TASK_TYPE_DISPLAY.get(row["task_type"], row["task_type"]),
                "hours": float(row["hours"] or 0),
            })

        for project_id, items in type_map.items():
            total = totals[project_id] or 1
            for item in items:
                item["percentage"] = round(item["hours"] / total * 100, 1)
            items.sort(key=lambda x: x["hours"], reverse=True)
        return type_map

    def _get_project_employee_map(self, qs):
        """Return project_id -> sorted employee hour distribution."""
        employee_map = defaultdict(list)
        rows = qs.values(
            "project_id", "employee_id", "employee__first_name", "employee__username",
        ).annotate(hours=Sum("hours")).order_by("project_id", "-hours")
        for row in rows:
            employee_map[row["project_id"]].append({
                "employee_id": row["employee_id"],
                "employee_name": row["employee__first_name"] or row["employee__username"],
                "hours": float(row["hours"] or 0),
            })
        return employee_map

    def _get_project_health(self, project, project_count, type_items, employee_items, days_with_data):
        """Score project health using signals that work for a single imported day."""
        score = 100
        risks = []
        status = "ok"

        if not project["project_id"]:
            return {
                "health_status": "critical",
                "health_label": "待归类",
                "health_score": 40,
                "risk_tags": ["未归类"],
                "top_work_type": None,
                "top_work_type_percentage": 0,
                "dominant_employee_percentage": 0,
                "avg_hours_per_employee": 0,
            }

        if project["percentage"] >= 60 and project_count > 1:
            score -= 20
            risks.append("投入集中")

        observed_days = max(days_with_data, 1)
        avg_hours_per_employee = round(
            project["hours"] / max(project["employee_count"], 1) / observed_days,
            1,
        )
        if project["employee_count"] <= 1 and project["hours"] >= 8:
            score -= 25
            risks.append("人员单点")
        elif avg_hours_per_employee >= 10:
            score -= 15
            risks.append("人均偏高")

        top_type = type_items[0] if type_items else None
        top_type_pct = top_type["percentage"] if top_type else 0
        if top_type and top_type_pct >= 75:
            score -= 10
            risks.append("类型单一")
        if top_type and top_type["type"] == "meeting" and top_type_pct >= 40:
            score -= 15
            risks.append("会议偏高")

        dominant_employee_pct = 0
        if employee_items and project["hours"] > 0:
            dominant_employee_pct = round(employee_items[0]["hours"] / project["hours"] * 100, 1)
            if project["employee_count"] > 1 and dominant_employee_pct >= 70:
                score -= 15
                risks.append("个人占比高")

        if project["low_confidence_count"] > 0:
            score -= 15
            risks.append("需复核")

        score = max(score, 0)
        if score < 60:
            status = "critical"
            label = "需处理"
        elif score < 80:
            status = "warning"
            label = "需关注"
        else:
            label = "健康"

        return {
            "health_status": status,
            "health_label": label,
            "health_score": score,
            "risk_tags": risks[:3] or ["节奏正常"],
            "top_work_type": top_type["display"] if top_type else "暂无",
            "top_work_type_percentage": top_type_pct,
            "dominant_employee_percentage": dominant_employee_pct,
            "avg_hours_per_employee": avg_hours_per_employee,
        }

    def _get_department_breakdown(self, qs, total_hours, days_with_data):
        """Department load and efficiency signals for the overview dashboard."""
        rows = list(qs.values("department_id", "department__name").annotate(
            hours=Sum("hours"),
            entry_count=Count("id"),
            report_count=Count("report_id", distinct=True),
            employee_count=Count("employee_id", distinct=True),
            project_count=Count("project_id", filter=Q(project__isnull=False), distinct=True),
            low_confidence_count=Count("id", filter=Q(confidence__lt=50)),
        ).order_by("-hours"))

        project_map = self._get_department_project_map(qs)
        type_map = self._get_department_type_map(qs)
        safe_total_hours = total_hours or 1
        observed_days = max(days_with_data, 1)
        departments = []

        for row in rows:
            dept_id = row["department_id"]
            hours = float(row["hours"] or 0)
            employee_count = row["employee_count"] or 0
            avg_daily = round(hours / max(employee_count, 1) / observed_days, 1)
            top_project = project_map.get(dept_id, [None])[0]
            top_type = type_map.get(dept_id, [None])[0]

            dept = {
                "department_id": dept_id,
                "department_name": row["department__name"] or "未分配",
                "hours": hours,
                "entry_count": row["entry_count"],
                "report_count": row["report_count"],
                "employee_count": employee_count,
                "project_count": row["project_count"],
                "percentage": round(hours / safe_total_hours * 100, 1),
                "avg_hours_per_employee": avg_daily,
                "low_confidence_count": row["low_confidence_count"],
                "top_project": top_project["name"] if top_project else "暂无",
                "top_project_percentage": top_project["percentage"] if top_project else 0,
                "top_work_type": top_type["display"] if top_type else "暂无",
                "top_work_type_percentage": top_type["percentage"] if top_type else 0,
            }
            dept.update(self._get_department_load_health(dept))
            departments.append(dept)

        return departments

    def _get_department_project_map(self, qs):
        """Return department_id -> sorted project distribution."""
        project_map = defaultdict(list)
        totals = defaultdict(float)
        rows = qs.exclude(project__isnull=True).values(
            "department_id", "project_id", "project__name",
        ).annotate(hours=Sum("hours")).order_by("department_id", "-hours")
        for row in rows:
            dept_id = row["department_id"]
            hours = float(row["hours"] or 0)
            totals[dept_id] += hours
            project_map[dept_id].append({
                "project_id": row["project_id"],
                "name": row["project__name"] or "未命名项目",
                "hours": hours,
            })

        for dept_id, items in project_map.items():
            total = totals[dept_id] or 1
            for item in items:
                item["percentage"] = round(item["hours"] / total * 100, 1)
            items.sort(key=lambda x: x["hours"], reverse=True)
        return project_map

    def _get_department_type_map(self, qs):
        """Return department_id -> sorted work type distribution."""
        type_map = defaultdict(list)
        totals = defaultdict(float)
        rows = qs.values("department_id", "task_type").annotate(
            hours=Sum("hours"),
        ).order_by("department_id", "-hours")
        for row in rows:
            dept_id = row["department_id"]
            hours = float(row["hours"] or 0)
            totals[dept_id] += hours
            type_map[dept_id].append({
                "type": row["task_type"],
                "display": TASK_TYPE_DISPLAY.get(row["task_type"], row["task_type"]),
                "hours": hours,
            })

        for dept_id, items in type_map.items():
            total = totals[dept_id] or 1
            for item in items:
                item["percentage"] = round(item["hours"] / total * 100, 1)
            items.sort(key=lambda x: x["hours"], reverse=True)
        return type_map

    def _get_department_load_health(self, dept):
        """Classify department load without treating hours as direct performance."""
        avg_daily = dept["avg_hours_per_employee"]
        score = 100
        status = "ok"
        risks = []

        if avg_daily < 2:
            status = "info"
            label = "负载偏低"
            score -= 25
            risks.append("投入偏低")
        elif avg_daily < 4:
            status = "info"
            label = "轻负载"
            score -= 10
            risks.append("负载较轻")
        elif avg_daily <= 8:
            label = "负载均衡"
        elif avg_daily <= 10:
            status = "warning"
            label = "负载偏高"
            score -= 15
            risks.append("人均偏高")
        else:
            status = "critical"
            label = "负载过高"
            score -= 35
            risks.append("可能过载")

        if dept["employee_count"] <= 1 and dept["hours"] >= 8:
            score -= 15
            risks.append("人员单点")
        if dept["top_project_percentage"] >= 70 and dept["project_count"] > 1:
            score -= 10
            risks.append("项目集中")
        if dept["top_work_type_percentage"] >= 75:
            score -= 8
            risks.append("类型单一")
        if dept["top_work_type"] == TASK_TYPE_DISPLAY.get("meeting") and dept["top_work_type_percentage"] >= 40:
            score -= 12
            risks.append("会议偏高")
        if dept["low_confidence_count"] > 0:
            score -= 10
            risks.append("需复核")

        score = max(score, 0)
        if score < 60:
            status = "critical"
            label = "需处理"
        elif score < 80 and status == "ok":
            status = "warning"
            label = "需关注"

        return {
            "load_status": status,
            "load_label": label,
            "load_score": score,
            "risk_tags": risks[:3] or ["负载稳定"],
        }

    def _get_work_type_structure(self, qs, total_hours, days_with_data):
        """Work type structure diagnostics for the overview dashboard."""
        rows = list(qs.values("task_type").annotate(
            hours=Sum("hours"),
            entry_count=Count("id"),
            employee_count=Count("employee_id", distinct=True),
            project_count=Count("project_id", filter=Q(project__isnull=False), distinct=True),
            department_count=Count("department_id", distinct=True),
            low_confidence_count=Count("id", filter=Q(confidence__lt=50)),
        ).order_by("-hours"))

        safe_total_hours = total_hours or 1
        observed_days = max(days_with_data, 1)
        items = []

        for row in rows:
            hours = float(row["hours"] or 0)
            employee_count = row["employee_count"] or 0
            item = {
                "type": row["task_type"],
                "display": TASK_TYPE_DISPLAY.get(row["task_type"], row["task_type"]),
                "hours": hours,
                "entry_count": row["entry_count"],
                "employee_count": employee_count,
                "project_count": row["project_count"],
                "department_count": row["department_count"],
                "percentage": round(hours / safe_total_hours * 100, 1),
                "avg_hours_per_employee": round(hours / max(employee_count, 1) / observed_days, 1),
                "low_confidence_count": row["low_confidence_count"],
            }
            item.update(self._get_work_type_structure_health(item))
            items.append(item)

        return items

    def _get_work_type_structure_health(self, item):
        """Classify work type structure without assuming one ideal ratio for every team."""
        score = 100
        status = "ok"
        label = "结构正常"
        risks = []
        percentage = item["percentage"]
        task_type = item["type"]

        if percentage >= 70:
            score -= 18
            status = "warning"
            label = "占比过高"
            risks.append("结构集中")

        if task_type == "meeting" and percentage >= 40:
            score -= 25
            status = "critical" if percentage >= 55 else "warning"
            label = "会议偏高"
            risks.append("协作成本高")
        elif task_type == "other" and percentage >= 35:
            score -= 20
            status = "critical" if percentage >= 50 else "warning"
            label = "其他偏高"
            risks.append("分类需细化")

        if item["avg_hours_per_employee"] >= 8:
            score -= 12
            if status == "ok":
                status = "warning"
                label = "负载偏高"
            risks.append("人均偏高")

        if item["project_count"] <= 1 and item["hours"] >= 8:
            score -= 8
            risks.append("项目单一")

        if item["low_confidence_count"] > 0:
            score -= 10
            risks.append("需复核")

        score = max(score, 0)
        if score < 60:
            status = "critical"
            if label == "结构正常":
                label = "需处理"
        elif score < 80 and status == "ok":
            status = "warning"
            label = "需关注"

        return {
            "structure_status": status,
            "structure_label": label,
            "structure_score": score,
            "risk_tags": risks[:3] or ["结构稳定"],
        }

    def _get_summary_alerts(self, qs, total_hours, days_with_data, project_breakdown):
        """Build single-period alerts that still work when only one day of data exists."""
        alerts = []
        entry_count = qs.count()

        if entry_count == 0:
            return [{
                "level": "info",
                "title": "暂无可分析数据",
                "message": "当前时间范围内没有工作条目，导入日志后会自动生成异常提醒。",
                "metric": "0 条",
                "action": "先确认日志是否已同步",
            }]

        safe_total_hours = total_hours or 1

        uncategorized_qs = qs.filter(project__isnull=True)
        uncategorized_hours = float(uncategorized_qs.aggregate(t=Sum("hours"))["t"] or 0)
        uncategorized_count = uncategorized_qs.count()
        uncategorized_pct = round(uncategorized_hours / safe_total_hours * 100, 1)
        if uncategorized_count > 0:
            alerts.append({
                "level": "critical" if uncategorized_pct >= 20 else "warning",
                "title": "存在未归类工时",
                "message": f"{uncategorized_count} 条记录未匹配到项目，会影响项目投入判断。",
                "metric": f"{uncategorized_pct}%",
                "action": "补充项目别名或人工归类",
            })

        low_confidence_count = qs.filter(confidence__lt=50).count()
        if low_confidence_count > 0:
            alerts.append({
                "level": "warning",
                "title": "解析置信度偏低",
                "message": f"{low_confidence_count} 条记录低于 50 分，可能需要复核工时或项目识别。",
                "metric": f"{low_confidence_count} 条",
                "action": "抽查原始日志内容",
            })

        observed_days = max(days_with_data, 1)
        overloads = qs.values(
            "employee_id", "employee__first_name", "employee__username",
        ).annotate(
            hours=Sum("hours"),
        ).order_by("-hours")[:3]
        high_load_people = []
        for person in overloads:
            avg_hours = float(person["hours"] or 0) / observed_days
            if avg_hours >= 10:
                high_load_people.append({
                    "employee_id": person["employee_id"],
                    "name": person["employee__first_name"] or person["employee__username"],
                    "hours": round(avg_hours, 1),
                })
        if high_load_people:
            top = high_load_people[0]
            alerts.append({
                "level": "warning",
                "title": "单人日均工时偏高",
                "message": f"{top['name']} 日均 {top['hours']}h，可能存在加班、补录或拆分不充分。",
                "metric": f"{top['hours']}h",
                "action": "查看员工视角明细",
                "action_view": "employee",
                "employee_id": top["employee_id"],
            })

        categorized_projects = [p for p in project_breakdown if p.get("project_id")]
        if categorized_projects:
            top_project = categorized_projects[0]
            if len(categorized_projects) == 1:
                alerts.append({
                    "level": "info",
                    "title": "项目投入集中",
                    "message": f"当前只有 {top_project['project_name']} 有归类工时，适合继续观察后续数据。",
                    "metric": "1 项",
                    "action": "确认是否符合实际项目范围",
                })
            elif top_project["percentage"] >= 60:
                alerts.append({
                    "level": "warning",
                    "title": "项目投入过度集中",
                    "message": f"{top_project['project_name']} 占本期归类工时 {top_project['percentage']}%。",
                    "metric": f"{top_project['percentage']}%",
                    "action": "确认资源倾斜是否符合预期",
                })

        if not alerts:
            alerts.append({
                "level": "ok",
                "title": "暂无明显异常",
                "message": "当前数据质量和投入分布没有触发异常阈值。",
                "metric": "正常",
                "action": "继续观察后续工作日",
            })

        return alerts[:4]

    # ------------------------------------------------------------------
    # Employee view
    # ------------------------------------------------------------------
    def _get_employee_view(self, qs):
        """Group: employee → project → work_type + entries with detail."""
        qs = qs.exclude(report__dingtalk_report_id__startswith="demo_report_")
        entries = qs.select_related("employee", "project", "department").values(
            "id",
            "employee_id", "employee__first_name", "employee__username",
            "department__name",
            "project_id", "project__name", "project__code",
            "task_type", "date", "hours", "task_description",
        ).order_by("employee_id", "project_id", "-date", "-hours")

        # Group in memory
        emp_map = {}
        for e in entries:
            eid = e["employee_id"]
            if eid not in emp_map:
                emp_map[eid] = {
                    "employee_id": eid,
                    "employee_name": e["employee__first_name"] or e["employee__username"],
                    "employee_username": e["employee__username"],
                    "department_name": e["department__name"] or "",
                    "total_hours": 0,
                    "project_count": 0,
                    "projects": [],
                    "project_map": {},
                }

            emp = emp_map[eid]
            pid = e["project_id"]

            if pid and pid not in emp["project_map"]:
                proj = {
                    "project_id": pid,
                    "project_name": e["project__name"] or "未归类",
                    "project_code": e["project__code"] or "",
                    "total_hours": 0,
                    "entry_count": 0,
                    "work_types": [],
                    "work_type_map": {},
                    "entries": [],
                }
                emp["projects"].append(proj)
                emp["project_map"][pid] = proj

            target = emp["project_map"].get(pid) if pid else None
            if target is None:
                # Uncategorized entry — still counts toward employee total
                emp["total_hours"] += float(e["hours"] or 0)
                continue

            hours = float(e["hours"] or 0)
            task_type = e["task_type"]
            target["total_hours"] += hours
            target["entry_count"] += 1
            emp["total_hours"] += hours

            if task_type not in target["work_type_map"]:
                wtype = {
                    "type": task_type,
                    "display": TASK_TYPE_DISPLAY.get(task_type, task_type),
                    "hours": 0,
                }
                target["work_types"].append(wtype)
                target["work_type_map"][task_type] = wtype
            target["work_type_map"][task_type]["hours"] += hours

            target["entries"].append({
                "id": e["id"],
                "date": e["date"].isoformat() if hasattr(e["date"], "isoformat") else str(e["date"]),
                "hours": hours,
                "task_description": e["task_description"] or "",
                "work_type": TASK_TYPE_DISPLAY.get(task_type, task_type),
                "type": task_type,
            })

        # Clean up project_map
        for emp in emp_map.values():
            emp["project_count"] = len(emp["projects"])
            emp["total_hours"] = round(emp["total_hours"], 1)
            for proj in emp["projects"]:
                proj["total_hours"] = round(proj["total_hours"], 1)
                del proj["work_type_map"]
                proj["work_types"] = sorted(proj["work_types"], key=lambda w: w["hours"], reverse=True)
                for wt in proj["work_types"]:
                    wt["hours"] = round(wt["hours"], 1)
                proj["entries"].sort(key=lambda entry: entry["date"], reverse=True)
            emp["projects"] = sorted(emp["projects"], key=lambda p: p["total_hours"], reverse=True)
            del emp["project_map"]

        # Sort employees by total hours descending
        employees = sorted(emp_map.values(), key=lambda x: x["total_hours"], reverse=True)
        total_hours = sum(emp["total_hours"] for emp in employees)

        return {
            "total_hours": round(total_hours, 1),
            "employee_count": len(employees),
            "employees": employees,
        }

    # ------------------------------------------------------------------
    # Project view
    # ------------------------------------------------------------------
    def _get_project_view(self, qs):
        """Group: project → work_type → employee → entries with detail"""
        qs = qs.exclude(report__dingtalk_report_id__startswith="demo_report_")
        entries = qs.select_related("employee", "project").values(
            "project_id", "project__name", "project__code",
            "department_id", "department__name",
            "employee_id", "employee__first_name", "employee__username",
            "task_type", "date", "hours", "task_description",
        ).order_by("project_id", "task_type", "employee_id", "-hours")

        proj_map = {}
        for e in entries:
            pid = e["project_id"]
            if pid is None:
                continue  # skip uncategorized for project view

            if pid not in proj_map:
                proj_map[pid] = {
                    "project_id": pid,
                    "project_name": e["project__name"] or "未归类",
                    "project_code": e["project__code"] or "",
                    "total_hours": 0,
                    "employee_set": set(),
                    "department_set": set(),
                    "work_types": [],
                    "work_type_map": {},
                    "type_breakdown": [],
                    "type_breakdown_map": {},
                }

            proj = proj_map[pid]
            eid = e["employee_id"]
            did = e["department_id"]
            hours = float(e["hours"] or 0)
            wt_key = e["task_type"]

            proj["total_hours"] += hours
            proj["employee_set"].add(eid)
            if did:
                proj["department_set"].add(did)

            # --- Project-level work type aggregation ---
            if wt_key not in proj["work_type_map"]:
                wt = {"type": wt_key, "display": TASK_TYPE_DISPLAY.get(wt_key, wt_key), "hours": 0}
                proj["work_types"].append(wt)
                proj["work_type_map"][wt_key] = wt
            proj["work_type_map"][wt_key]["hours"] += hours

            # --- Type breakdown (work_type → employees → entries) ---
            if wt_key not in proj["type_breakdown_map"]:
                tb = {
                    "type": wt_key,
                    "display": TASK_TYPE_DISPLAY.get(wt_key, wt_key),
                    "hours": 0,
                    "employee_set": set(),
                    "employees": [],
                    "employee_map": {},
                }
                proj["type_breakdown"].append(tb)
                proj["type_breakdown_map"][wt_key] = tb

            tb = proj["type_breakdown_map"][wt_key]
            tb["hours"] += hours

            if eid not in tb["employee_set"]:
                tb["employee_set"].add(eid)
                emp_entry = {
                    "employee_id": eid,
                    "employee_name": e["employee__first_name"] or e["employee__username"],
                    "employee_username": e["employee__username"],
                    "department_name": e["department__name"] or "",
                    "hours": 0,
                    "entries": [],
                }
                tb["employees"].append(emp_entry)
                tb["employee_map"][eid] = len(tb["employees"]) - 1

            emp_idx = tb["employee_map"][eid]
            tb["employees"][emp_idx]["hours"] += hours
            tb["employees"][emp_idx]["entries"].append({
                "date": e["date"].isoformat() if hasattr(e["date"], "isoformat") else str(e["date"]),
                "hours": hours,
                "task_description": e["task_description"] or "",
            })

        # Clean up and finalize
        for proj in proj_map.values():
            proj["total_hours"] = round(proj["total_hours"], 1)
            proj["employee_count"] = len(proj["employee_set"])
            proj["department_count"] = len(proj["department_set"])
            del proj["employee_set"], proj["department_set"], proj["work_type_map"]

            proj["work_types"] = sorted(proj["work_types"], key=lambda w: w["hours"], reverse=True)
            for wt in proj["work_types"]:
                wt["hours"] = round(wt["hours"], 1)

            del proj["type_breakdown_map"]
            for tb in proj["type_breakdown"]:
                tb["hours"] = round(tb["hours"], 1)
                tb["employee_count"] = len(tb["employee_set"])
                del tb["employee_set"], tb["employee_map"]
                for emp in tb["employees"]:
                    emp["hours"] = round(emp["hours"], 1)
                    emp["entries"].sort(key=lambda x: x["date"], reverse=True)
                tb["employees"].sort(key=lambda x: x["hours"], reverse=True)
            proj["type_breakdown"].sort(key=lambda x: x["hours"], reverse=True)

        projects = sorted(proj_map.values(), key=lambda x: x["total_hours"], reverse=True)
        total_hours = round(sum(p["total_hours"] for p in projects), 1)

        return {
            "total_hours": total_hours,
            "project_count": len(projects),
            "projects": projects,
        }

    # ------------------------------------------------------------------
    # Department view
    # ------------------------------------------------------------------
    def _get_department_view(self, qs, user):
        """Group: department tree → employees → projects → entries with detail"""
        qs = qs.exclude(report__dingtalk_report_id__startswith="demo_report_")
        visible_ids = get_visible_department_ids(user)
        all_depts = Department.objects.filter(id__in=visible_ids).select_related("parent")

        # Build department node map
        dept_map = {}
        for d in all_depts:
            dept_map[d.id] = {
                "department_id": d.id,
                "department_name": d.name,
                "parent_id": d.parent_id,
                "total_hours": 0,
                "children": [],
                "employees": [],
                "employee_map": {},
            }

        # Build tree
        roots = []
        for d in all_depts:
            node = dept_map[d.id]
            if d.parent_id and d.parent_id in dept_map:
                dept_map[d.parent_id]["children"].append(node)
            else:
                roots.append(node)

        # Fetch all entries with full detail
        entries = qs.select_related("employee", "project").values(
            "department_id",
            "employee_id", "employee__first_name", "employee__username",
            "project_id", "project__name", "project__code",
            "task_type", "date", "hours", "task_description",
        ).order_by("department_id", "employee_id", "-hours")

        for e in entries:
            dept_id = e["department_id"]
            if dept_id not in dept_map:
                # Add uncategorized entries to a general bucket
                continue

            dept_node = dept_map[dept_id]
            eid = e["employee_id"]
            pid = e["project_id"]

            if eid not in dept_node["employee_map"]:
                emp = {
                    "employee_id": eid,
                    "employee_name": e["employee__first_name"] or e["employee__username"],
                    "employee_username": e["employee__username"],
                    "total_hours": 0,
                    "projects": [],
                    "project_map": {},
                }
                dept_node["employees"].append(emp)
                dept_node["employee_map"][eid] = emp

            emp = dept_node["employee_map"][eid]
            hours = float(e["hours"] or 0)
            emp["total_hours"] += hours
            dept_node["total_hours"] += hours

            if pid and pid not in emp["project_map"]:
                proj = {
                    "project_id": pid,
                    "project_name": e["project__name"] or "未归类",
                    "project_code": e["project__code"] or "",
                    "hours": 0,
                    "work_types": [],
                    "work_type_map": {},
                    "entries": [],
                }
                emp["projects"].append(proj)
                emp["project_map"][pid] = proj

            proj = emp["project_map"].get(pid) if pid else None
            if proj is None:
                continue

            proj["hours"] += hours
            proj["entries"].append({
                "date": e["date"].isoformat() if hasattr(e["date"], "isoformat") else str(e["date"]),
                "hours": hours,
                "task_description": e["task_description"] or "",
                "work_type": TASK_TYPE_DISPLAY.get(e["task_type"], e["task_type"]),
                "type": e["task_type"],
            })

            wt_key = e["task_type"]
            if wt_key not in proj["work_type_map"]:
                wt = {"type": wt_key, "display": TASK_TYPE_DISPLAY.get(wt_key, wt_key), "hours": 0}
                proj["work_types"].append(wt)
                proj["work_type_map"][wt_key] = wt
            proj["work_type_map"][wt_key]["hours"] += hours

        # Clean up
        def clean_dept(node):
            node["total_hours"] = round(node["total_hours"], 1)
            for emp in node["employees"]:
                emp["total_hours"] = round(emp["total_hours"], 1)
                del emp["project_map"]
                for proj in emp["projects"]:
                    proj["hours"] = round(proj["hours"], 1)
                    del proj["work_type_map"]
                    proj["work_types"] = sorted(proj["work_types"], key=lambda w: w["hours"], reverse=True)
                emp["projects"] = sorted(emp["projects"], key=lambda p: p["hours"], reverse=True)
            node["employees"] = sorted(node["employees"], key=lambda e: e["total_hours"], reverse=True)
            node["children"] = sorted(node["children"], key=lambda c: c["total_hours"], reverse=True)
            del node["employee_map"]
            for child in node["children"]:
                clean_dept(child)

        for root in roots:
            clean_dept(root)

        # Propagate children's totals to parents
        def rollup(node):
            for child in node["children"]:
                rollup(child)
            child_hours = sum(c["total_hours"] for c in node["children"])
            node["total_hours"] = round(node["total_hours"] + child_hours, 1)

        for root in roots:
            rollup(root)

        total_hours = round(sum(r["total_hours"] for r in roots), 1)

        return {
            "total_hours": total_hours,
            "departments": roots,
        }
