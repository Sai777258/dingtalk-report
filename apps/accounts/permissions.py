"""
Permission utility functions for role-based QuerySet filtering.

All endpoints use these to limit data visibility:
- admin / executive: see everything
- dept_manager: own department + sub-departments
- product_manager: own data + projects they manage
- employee: own data only
"""
from django.db.models import Q
from apps.accounts.models import Department


def get_visible_department_ids(user):
    """
    Return a list of department IDs the user can see.

    - admin/executive: all departments
    - dept_manager: own department + all descendants
    - others: own department only (for identity, but they only see their own data)
    """
    if user.is_admin or user.is_executive:
        return list(Department.objects.values_list("id", flat=True))

    if not user.department:
        return []

    ids = [user.department_id]

    if user.is_dept_manager:
        # Collect all sub-departments recursively.
        children = _collect_descendant_ids(user.department_id)
        ids.extend(children)

    return ids


def _collect_descendant_ids(parent_id):
    """Return all descendant department IDs for a given parent."""
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
    - admin/executive: all reports
    - dept_manager: reports from visible departments
    - product_manager: own reports + reports with work entries in managed projects
    - employee: own reports only
    """
    if user.is_admin or user.is_executive:
        return queryset

    if user.is_dept_manager:
        dept_ids = get_visible_department_ids(user)
        return queryset.filter(department_id__in=dept_ids)

    if user.is_product_manager:
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
    - admin/executive: all entries
    - dept_manager: entries from visible departments
    - product_manager: own entries + entries in managed projects
    - employee: own entries only
    """
    if user.is_admin or user.is_executive:
        return queryset

    if user.is_dept_manager:
        dept_ids = get_visible_department_ids(user)
        return queryset.filter(department_id__in=dept_ids)

    if user.is_product_manager:
        # Own entries OR entries in managed projects
        return queryset.filter(
            Q(employee=user)
            | Q(project__product_managers=user)
        )

    # employee (default): own entries only
    return queryset.filter(employee=user)
