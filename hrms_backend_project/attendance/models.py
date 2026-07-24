from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F


class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', 'Present'
    ABSENT = 'ABSENT', 'Absent'
    HALF_DAY = 'HALF_DAY', 'Half Day'
    WORK_FROM_HOME = 'WFH', 'Work From Home'
    ON_LEAVE = 'ON_LEAVE', 'On Leave'
    HOLIDAY = 'HOLIDAY', 'Holiday'
    WEEKEND = 'WEEKEND', 'Weekend'


class Attendance(models.Model):
    """
    One row per employee per calendar day.

    Working/overtime/late/early figures are derived by the service layer
    (see `attendance/services.py`) and persisted here so reports and
    analytics never need to recompute them from raw timestamps.
    """

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    attendance_date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    late_arrival_minutes = models.PositiveIntegerField(default=0)
    early_checkout_minutes = models.PositiveIntegerField(default=0)

    attendance_status = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.ABSENT,
    )
    remarks = models.TextField(blank=True, default='')

    # Simulates payroll lock: once payroll has been run for the period
    # covering this record, it becomes read-only (Module 9).
    is_payroll_locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-attendance_date', 'employee__employee_id']
        constraints = [
            # One attendance record per employee per day
            models.UniqueConstraint(
                fields=['employee', 'attendance_date'],
                name='unique_attendance_per_employee_per_day',
            ),
            # Working hours cannot be negative
            models.CheckConstraint(
                condition=Q(working_hours__gte=0),
                name='working_hours_non_negative',
            ),
            models.CheckConstraint(
                condition=Q(break_hours__gte=0),
                name='break_hours_non_negative',
            ),
            models.CheckConstraint(
                condition=Q(overtime_hours__gte=0),
                name='overtime_hours_non_negative',
            ),
            # Check-out must be strictly after check-in (only enforced
            # once both are set)
            models.CheckConstraint(
                condition=Q(check_out_time__isnull=True)
                | Q(check_in_time__isnull=True)
                | Q(check_out_time__gt=F('check_in_time')),
                name='checkout_after_checkin',
            ),
        ]
        indexes = [
            models.Index(fields=['attendance_date']),
            models.Index(fields=['attendance_status']),
            models.Index(fields=['employee', 'attendance_date']),
        ]

    def __str__(self):
        return f'{self.employee.employee_id} - {self.attendance_date} - {self.attendance_status}'

    # ------------------------------------------------------------------
    # Validation (mirrors the DB constraints so we fail fast with a
    # friendly DRF/ValidationError message before hitting the database).
    # ------------------------------------------------------------------
    def clean(self):
        errors = {}

        if self.attendance_date and self.attendance_date > date.today():
            errors['attendance_date'] = 'Attendance date cannot be in the future.'

        if self.check_in_time and self.check_out_time:
            if self.check_out_time <= self.check_in_time:
                errors['check_out_time'] = 'Check-out time must be greater than check-in time.'

        if self.working_hours is not None and self.working_hours < 0:
            errors['working_hours'] = 'Working hours cannot be negative.'

        if self.pk and self.is_payroll_locked:
            errors['__all__'] = 'This attendance record is locked because payroll has been generated.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_checked_in(self):
        return self.check_in_time is not None

    @property
    def is_checked_out(self):
        return self.check_out_time is not None
