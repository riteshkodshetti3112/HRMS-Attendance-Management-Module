"""
Role-based permissions for the attendance module.

Role is read from `request.user.employee_profile.role`, falling back to
Django's built-in `is_staff` / `is_superuser` flags so the module still
behaves sensibly against plain Django admin accounts.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


def _employee_profile(user):
    return getattr(user, 'employee_profile', None)


def get_role(user):
    if user.is_superuser:
        return 'ADMIN'
    profile = _employee_profile(user)
    if profile is not None:
        return profile.role
    if user.is_staff:
        return 'HR'
    return 'EMPLOYEE'


class IsHRorAdmin(BasePermission):
    """Grants access to HR staff and Admins only."""

    message = 'Only HR or Admin users may perform this action.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and get_role(request.user) in ('HR', 'ADMIN'))


class IsAdminOnly(BasePermission):
    """Grants access to Admins only (e.g. destructive operations)."""

    message = 'Only Admin users may perform this action.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and get_role(request.user) == 'ADMIN')


class IsSelfOrHRorAdmin(BasePermission):
    """
    Employees may only read/act on their own attendance records.
    HR/Admin may access any record.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        role = get_role(request.user)
        if role in ('HR', 'ADMIN'):
            return True
        profile = _employee_profile(request.user)
        return profile is not None and obj.employee_id == profile.id


class IsEmployeeProfileOwner(BasePermission):
    """Used on the /my-attendance/ and /my-summary/ style endpoints."""

    message = 'An employee profile is required to use this endpoint.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _employee_profile(request.user) is not None
        )


class ReadOnlyOrHRorAdmin(BasePermission):
    """Anyone authenticated may read; only HR/Admin may write."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return get_role(request.user) in ('HR', 'ADMIN')
