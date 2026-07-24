"""
Standalone validation helpers for the attendance module.

These are used by the service layer *before* touching the database so
that API callers get a clean, predictable error message instead of an
IntegrityError from a DB constraint.
"""
from datetime import date

from rest_framework.exceptions import ValidationError


def validate_not_future_date(attendance_date):
    if attendance_date > date.today():
        raise ValidationError({'attendance_date': 'Attendance date cannot be in the future.'})


def validate_checkout_after_checkin(check_in_time, check_out_time):
    if check_in_time and check_out_time and check_out_time <= check_in_time:
        raise ValidationError({'check_out_time': 'Check-out time must be greater than check-in time.'})


def validate_working_hours_non_negative(working_hours):
    if working_hours is not None and working_hours < 0:
        raise ValidationError({'working_hours': 'Working hours cannot be negative.'})


def validate_employee_active(employee):
    if not employee.is_active:
        raise ValidationError({'employee': 'Employee is not active.'})


def validate_not_already_checked_in(attendance):
    if attendance is not None and attendance.is_checked_in:
        raise ValidationError({'detail': 'Employee has already checked in today.'})


def validate_has_checked_in(attendance):
    if attendance is None or not attendance.is_checked_in:
        raise ValidationError({'detail': 'Employee must check in before checking out.'})


def validate_not_already_checked_out(attendance):
    if attendance is not None and attendance.is_checked_out:
        raise ValidationError({'detail': 'Employee has already checked out today.'})


def validate_not_payroll_locked(attendance):
    if attendance is not None and attendance.is_payroll_locked:
        raise ValidationError({'detail': 'This attendance record is locked because payroll has been generated.'})


def validate_no_duplicate_attendance(employee, attendance_date, existing_pk=None):
    from .models import Attendance

    qs = Attendance.objects.filter(employee=employee, attendance_date=attendance_date)
    if existing_pk:
        qs = qs.exclude(pk=existing_pk)
    if qs.exists():
        raise ValidationError({'detail': 'Attendance record already exists for this employee on this date.'})
