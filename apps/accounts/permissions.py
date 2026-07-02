"""
Permission utility functions for role-based QuerySet filtering.

All endpoints use these to limit data visibility:
- admin / dept_manager_l1: see everything (L1 = same data scope as admin)
- dept_manager_l2: own department only
- project_manager: own data + projects they manage
- employee: own data only

Intended for future LDAP integration: roles and department assignments
will be synced from LDAP; the filtering logic here stays unchanged.
"""
from django.db.models import Q
from apps.accounts.models import Department


def get_visible_department_ids(user):
    """
    Return a list of department IDs the user can see.

    - admin / dept_manager_l1: all departments
    - dept_manager_l2: own department only
    - others: own department only (for identity display, but they only see their own data)
    """
    if user.is_admin or user.is_dept_manager_l1:
        return list(Department.objects.values_list("id", flat=True))

    if not user.department:
        return []

    return [user.department_id]


def _collect_descendant_ids(parent_id):
    """Return all descendant department IDs for a given parent (recursive)."""
    result = []
    children = Department.objects.filter(parent_id=parent_id).values_list("id", flat=True)
    for child_id in children:
        result.append(child_id)
        result.extend(_collect_descendant_ids(child_id))
    return result


def apply_report_access_filter(queryset, user):
    """
    Filter WorkReport queryset based on user role.

    Rules:
    - admin / dept_manager_l1: all reports
    - dept_manager_l2: reports from own department
    - project_manager: own reports + reports with work entries in managed projects
    - employee: own reports only
    """
    if user.is_admin or user.is_dept_manager_l1:
        return queryset

    if user.is_dept_manager_l2:
        return queryset.filter(department_id=user.department_id)

    if user.is_project_manager:
        # Own reports OR reports that contain work entries in managed projects
        return queryset.filter(
            Q(creator=user)
            | Q(work_entries__project__product_managers=user)
        ).distinct()

    # employee (default): own reports only
    return queryset.filter(creator=user)


def apply_work_entry_access_filter(queryset, user):
    """
    Filter WorkEntry queryset based on user role.

    Rules:
    - admin / dept_manager_l1: all entries
    - dept_manager_l2: entries from own department
    - project_manager: own entries + entries in managed projects
    - employee: own entries only
    """
    if user.is_admin or user.is_dept_manager_l1:
        return queryset

    if user.is_dept_manager_l2:
        return queryset.filter(department_id=user.department_id)

    if user.is_project_manager:
        # Own entries OR entries in managed projects
        return queryset.filter(
            Q(employee=user)
            | Q(project__product_managers=user)
        )

    # employee (default): own entries only
    return queryset.filter(employee=user)
