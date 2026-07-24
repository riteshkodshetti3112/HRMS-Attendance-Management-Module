"""
Service layer for the attendance module.

Views must never talk to the ORM or apply business rules directly —
they call into `AttendanceService`, which owns all business logic
(Module 4). This keeps views thin and makes the rules unit-testable
in isolation from HTTP.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from . import validators
from .models import Attendance, AttendanceStatus
from .utils import (
    days_in_month,
    get_setting,
    is_weekend,
    month_bounds,
    percentage,
    shift_start_datetime,
    timedelta_to_hours,
    to_decimal_hours,
)


class AttendanceService:
    """All attendance business logic lives here."""

    # ------------------------------------------------------------------
    # Check-in / Check-out
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def check_in(employee, remarks='', check_in_time=None):
        """
        Create (or reuse) today's attendance row and stamp check-in time.

        Rules enforced (Module 3):
          * employee must be active
          * only one check-in per employee per day
        """
        validators.validate_employee_active(employee)

        today = timezone.localdate()
        check_in_time = check_in_time or timezone.now()

        attendance = Attendance.objects.filter(
            employee=employee, attendance_date=today
        ).first()

        validators.validate_not_already_checked_in(attendance)
        if attendance is not None:
            validators.validate_not_payroll_locked(attendance)

        late_minutes = AttendanceService._late_arrival_minutes(today, check_in_time)

        if attendance is None:
            attendance = Attendance(
                employee=employee,
                attendance_date=today,
            )

        attendance.check_in_time = check_in_time
        attendance.late_arrival_minutes = late_minutes
        attendance.attendance_status = AttendanceStatus.PRESENT
        if remarks:
            attendance.remarks = remarks
        attendance.save()
        return attendance

    @staticmethod
    @transaction.atomic
    def check_out(employee, remarks='', check_out_time=None, break_hours=None):
        """
        Stamp check-out time on today's record and (re)compute derived
        figures: working hours, overtime, early-checkout minutes.

        Rules enforced (Module 3):
          * employee must have checked in first
          * only one check-out per employee per day
          * check-out must be after check-in
        """
        today = timezone.localdate()
        check_out_time = check_out_time or timezone.now()

        attendance = Attendance.objects.filter(
            employee=employee, attendance_date=today
        ).first()

        validators.validate_has_checked_in(attendance)
        validators.validate_not_already_checked_out(attendance)
        validators.validate_not_payroll_locked(attendance)
        validators.validate_checkout_after_checkin(attendance.check_in_time, check_out_time)

        break_hours = (
            to_decimal_hours(break_hours)
            if break_hours is not None
            else to_decimal_hours(get_setting('DEFAULT_BREAK_HOURS', 1.0))
        )

        working_hours = AttendanceService.calculate_working_hours(
            attendance.check_in_time, check_out_time, break_hours
        )
        overtime_hours = AttendanceService.calculate_overtime(working_hours)
        early_checkout_minutes = AttendanceService._early_checkout_minutes(today, check_out_time)

        attendance.check_out_time = check_out_time
        attendance.break_hours = break_hours
        attendance.working_hours = working_hours
        attendance.overtime_hours = overtime_hours
        attendance.early_checkout_minutes = early_checkout_minutes

        half_day_threshold = Decimal(str(get_setting('HALF_DAY_THRESHOLD_HOURS', 4.5)))
        if working_hours < half_day_threshold:
            attendance.attendance_status = AttendanceStatus.HALF_DAY

        if remarks:
            attendance.remarks = remarks
        attendance.save()
        return attendance

    # ------------------------------------------------------------------
    # Calculations
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_working_hours(check_in_time, check_out_time, break_hours=Decimal('0')) -> Decimal:
        """Working Hours = Check-Out - Check-In - Break Time."""
        if not check_in_time or not check_out_time:
            return Decimal('0.00')
        gross_hours = timedelta_to_hours(check_out_time - check_in_time)
        net_hours = gross_hours - to_decimal_hours(break_hours)
        return max(net_hours, Decimal('0.00'))

    @staticmethod
    def calculate_overtime(working_hours: Decimal, standard_hours=None) -> Decimal:
        standard_hours = Decimal(str(standard_hours or get_setting('STANDARD_WORKING_HOURS', 9.0)))
        overtime = to_decimal_hours(working_hours) - standard_hours
        return overtime if overtime > 0 else Decimal('0.00')

    @staticmethod
    def _late_arrival_minutes(for_date, check_in_time) -> int:
        grace = get_setting('LATE_GRACE_MINUTES', 15)
        shift_start = shift_start_datetime(for_date) + timedelta(minutes=grace)
        if check_in_time <= shift_start:
            return 0
        return int((check_in_time - shift_start).total_seconds() // 60)

    @staticmethod
    def _early_checkout_minutes(for_date, check_out_time) -> int:
        from .utils import shift_end_datetime

        grace = get_setting('EARLY_CHECKOUT_GRACE_MINUTES', 15)
        shift_end = shift_end_datetime(for_date) - timedelta(minutes=grace)
        if check_out_time >= shift_end:
            return 0
        return int((shift_end - check_out_time).total_seconds() // 60)

    # ------------------------------------------------------------------
    # Summaries / reports
    # ------------------------------------------------------------------
    @staticmethod
    def attendance_summary(employee, month: int, year: int) -> dict:
        """Per-employee monthly summary (used by /my-summary/)."""
        first_day, last_day = month_bounds(year, month)
        qs = Attendance.objects.filter(
            employee=employee,
            attendance_date__gte=first_day,
            attendance_date__lte=last_day,
        )
        return AttendanceService._summarize(qs, employee=employee, year=year, month=month)

    @staticmethod
    def monthly_report(month: int, year: int, department=None, employee=None) -> dict:
        """
        Org-wide (or department/employee scoped) monthly report
        (Module 6 / HR `report/` endpoint).
        """
        first_day, last_day = month_bounds(year, month)
        qs = Attendance.objects.filter(
            attendance_date__gte=first_day, attendance_date__lte=last_day
        )
        if department:
            qs = qs.filter(employee__department=department)
        if employee:
            qs = qs.filter(employee=employee)

        return AttendanceService._summarize(qs, employee=employee, year=year, month=month, department=department)

    @staticmethod
    def _summarize(qs, employee=None, year=None, month=None, department=None) -> dict:
        total_working_days = days_in_month(year, month) if (year and month) else None

        aggregates = qs.aggregate(
            total_hours=Sum('working_hours'),
            total_overtime=Sum('overtime_hours'),
            present_days=Count('id', filter=Q(attendance_status=AttendanceStatus.PRESENT)),
            half_days=Count('id', filter=Q(attendance_status=AttendanceStatus.HALF_DAY)),
            absent_days=Count('id', filter=Q(attendance_status=AttendanceStatus.ABSENT)),
            leave_days=Count('id', filter=Q(attendance_status=AttendanceStatus.ON_LEAVE)),
            wfh_days=Count('id', filter=Q(attendance_status=AttendanceStatus.WORK_FROM_HOME)),
            holiday_days=Count('id', filter=Q(attendance_status=AttendanceStatus.HOLIDAY)),
            weekend_days=Count('id', filter=Q(attendance_status=AttendanceStatus.WEEKEND)),
        )

        result = {
            'year': year,
            'month': month,
            'total_working_days': total_working_days,
            'present_days': aggregates['present_days'] or 0,
            'half_days': aggregates['half_days'] or 0,
            'absent_days': aggregates['absent_days'] or 0,
            'leave_days': aggregates['leave_days'] or 0,
            'wfh_days': aggregates['wfh_days'] or 0,
            'holiday_days': aggregates['holiday_days'] or 0,
            'weekend_days': aggregates['weekend_days'] or 0,
            'total_working_hours': aggregates['total_hours'] or Decimal('0.00'),
            'total_overtime_hours': aggregates['total_overtime'] or Decimal('0.00'),
        }
        if employee is not None:
            result['employee'] = employee.employee_id
        if department is not None:
            result['department'] = department.name
        return result

    # ------------------------------------------------------------------
    # Dashboard (Module 7)
    # ------------------------------------------------------------------
    @staticmethod
    def dashboard_summary(today=None) -> dict:
        today = today or timezone.localdate()
        qs = Attendance.objects.filter(attendance_date=today)

        present_count = qs.filter(
            attendance_status__in=[AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY, AttendanceStatus.WORK_FROM_HOME]
        ).count()
        absent_count = qs.filter(attendance_status=AttendanceStatus.ABSENT).count()
        late_employees = qs.filter(late_arrival_minutes__gt=0).select_related('employee')
        not_checked_out = qs.filter(check_in_time__isnull=False, check_out_time__isnull=True).select_related('employee')
        avg_working_hours = qs.aggregate(avg=Avg('working_hours'))['avg'] or Decimal('0.00')

        return {
            'date': today,
            'todays_attendance_count': qs.count(),
            'present_count': present_count,
            'absent_count': absent_count,
            'late_employees': [a.employee.employee_id for a in late_employees],
            'employees_not_checked_out': [a.employee.employee_id for a in not_checked_out],
            'average_working_hours': to_decimal_hours(avg_working_hours),
        }

    # ------------------------------------------------------------------
    # Analytics (Module 8)
    # ------------------------------------------------------------------
    @staticmethod
    def department_wise_attendance(month: int, year: int):
        from employees.models import Department

        first_day, last_day = month_bounds(year, month)
        results = []
        for department in Department.objects.filter(is_active=True):
            qs = Attendance.objects.filter(
                employee__department=department,
                attendance_date__gte=first_day,
                attendance_date__lte=last_day,
            )
            present = qs.filter(
                attendance_status__in=[AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY, AttendanceStatus.WORK_FROM_HOME]
            ).count()
            absent = qs.filter(attendance_status=AttendanceStatus.ABSENT).count()
            total = present + absent
            results.append({
                'department': department.name,
                'present': present,
                'absent': absent,
                'percentage': percentage(present, total),
            })
        return results

    @staticmethod
    def employee_performance(employee, month: int, year: int) -> dict:
        first_day, last_day = month_bounds(year, month)
        qs = Attendance.objects.filter(
            employee=employee,
            attendance_date__gte=first_day,
            attendance_date__lte=last_day,
        )
        total_days = days_in_month(year, month)
        present = qs.filter(
            attendance_status__in=[AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY, AttendanceStatus.WORK_FROM_HOME]
        ).count()
        aggregates = qs.aggregate(
            avg_hours=Avg('working_hours'),
            total_overtime=Sum('overtime_hours'),
            late_count=Count('id', filter=Q(late_arrival_minutes__gt=0)),
        )
        return {
            'employee': employee.employee_id,
            'attendance_percentage': percentage(present, total_days),
            'average_working_hours': to_decimal_hours(aggregates['avg_hours'] or 0),
            'total_overtime_hours': aggregates['total_overtime'] or Decimal('0.00'),
            'late_arrivals': aggregates['late_count'] or 0,
        }
