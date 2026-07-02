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

from django.db.models import Sum, Count
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
        qs = WorkEntry.objects.select_related("employee", "project", "department")

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

        this_month_hours = this_month_qs.aggregate(t=Sum("hours"))["t"] or 0
        last_month_hours = base_qs.filter(
            date__gte=last_month_start, date__lte=last_month_end
        ).aggregate(t=Sum("hours"))["t"] or 0

        total_reports = this_month_qs.values("report").distinct().count()
        active_projects = this_month_qs.exclude(project__isnull=True).values("project").distinct().count()
        active_employees = this_month_qs.values("employee").distinct().count()

        days_with_data = this_month_qs.values("date").distinct().count()
        avg_daily = round(float(this_month_hours) / days_with_data, 1) if days_with_data > 0 else 0

        pstats = this_month_qs.values("project_id", "project__name", "project__code").annotate(
            hours=Sum("hours"), entry_count=Count("id"),
        ).order_by("-hours")
        total_p_hours = sum(p["hours"] for p in pstats) or 1
        project_breakdown = [{
            "project_id": p["project_id"],
            "project_name": p["project__name"] or "未归类",
            "project_code": p["project__code"] or "",
            "hours": float(p["hours"]),
            "entry_count": p["entry_count"],
            "percentage": round(float(p["hours"]) / float(total_p_hours) * 100, 1),
        } for p in pstats]

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
            "active_projects": active_projects,
            "active_employees": active_employees,
            "avg_daily_hours": round(avg_daily, 1),
            "project_breakdown": project_breakdown,
            "employee_breakdown": employee_breakdown,
            "daily_trend": daily_trend,
        }

    # ------------------------------------------------------------------
    # Employee view
    # ------------------------------------------------------------------
    def _get_employee_view(self, qs):
        """Group: employee → project → work_type"""
        qs = qs.exclude(report__dingtalk_report_id__startswith="demo_report_")
        entries = qs.values(
            "employee_id", "employee__first_name", "employee__username",
            "department__name",
            "project_id", "project__name", "project__code",
            "task_type",
        ).annotate(
            hours=Sum("hours"), entry_count=Count("id"),
        ).order_by("employee_id", "-hours")

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
                }
                emp["projects"].append(proj)
                emp["project_map"][pid] = proj

            target = emp["project_map"].get(pid) if pid else None
            if target is None:
                # Uncategorized entry — still counts toward employee total
                emp["total_hours"] += float(e["hours"] or 0)
                continue

            target["total_hours"] += float(e["hours"] or 0)
            target["entry_count"] += e["entry_count"]
            emp["total_hours"] += float(e["hours"] or 0)

            wtype = {
                "type": e["task_type"],
                "display": TASK_TYPE_DISPLAY.get(e["task_type"], e["task_type"]),
                "hours": float(e["hours"] or 0),
            }
            target["work_types"].append(wtype)

        # Clean up project_map
        for emp in emp_map.values():
            emp["project_count"] = len(emp["projects"])
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
            child_hours = sum(c["total_hours"] for c in node["children"])
            node["total_hours"] = round(node["total_hours"] + child_hours, 1)
            for child in node["children"]:
                rollup(child)

        for root in roots:
            rollup(root)

        total_hours = round(sum(r["total_hours"] for r in roots), 1)

        return {
            "total_hours": total_hours,
            "departments": roots,
        }
