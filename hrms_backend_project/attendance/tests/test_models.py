from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from attendance.models import Attendance, AttendanceStatus
from attendance.services import AttendanceService
from .factories import create_department, create_employee


class AttendanceModelTests(TestCase):
    def setUp(self):
        self.department = create_department()
        self.employee = create_employee(department=self.department)

    def test_attendance_creation(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            attendance_date=date.today(),
            attendance_status=AttendanceStatus.PRESENT,
        )
        self.assertEqual(attendance.employee, self.employee)
        self.assertEqual(attendance.attendance_status, AttendanceStatus.PRESENT)
        self.assertEqual(attendance.working_hours, 0)

    def test_duplicate_attendance_per_day_rejected(self):
        today = date.today()
        Attendance.objects.create(employee=self.employee, attendance_date=today)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(employee=self.employee, attendance_date=today)

    def test_future_date_rejected(self):
        future_date = date.today() + timedelta(days=1)
        attendance = Attendance(employee=self.employee, attendance_date=future_date)
        with self.assertRaises(ValidationError):
            attendance.save()

    def test_checkout_before_checkin_rejected(self):
        now = timezone.now()
        attendance = Attendance(
            employee=self.employee,
            attendance_date=date.today(),
            check_in_time=now,
            check_out_time=now - timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            attendance.save()

    def test_negative_working_hours_rejected(self):
        attendance = Attendance(
            employee=self.employee,
            attendance_date=date.today(),
            working_hours=Decimal('-1.00'),
        )
        with self.assertRaises(ValidationError):
            attendance.save()

    def test_payroll_locked_record_cannot_be_saved(self):
        attendance = Attendance.objects.create(employee=self.employee, attendance_date=date.today())
        # Simulate payroll having been generated for this record (this
        # update bypasses model validation on purpose, the same way a
        # payroll job would flip the flag directly).
        Attendance.objects.filter(pk=attendance.pk).update(is_payroll_locked=True)
        attendance.refresh_from_db()

        attendance.remarks = 'trying to edit after payroll'
        with self.assertRaises(ValidationError):
            attendance.save()


class WorkingHoursCalculationTests(TestCase):
    def test_calculate_working_hours_subtracts_break(self):
        check_in = timezone.now().replace(hour=9, minute=30, second=0, microsecond=0)
        check_out = check_in + timedelta(hours=9)
        working_hours = AttendanceService.calculate_working_hours(check_in, check_out, Decimal('1.00'))
        self.assertEqual(working_hours, Decimal('8.00'))

    def test_calculate_working_hours_never_negative(self):
        check_in = timezone.now()
        check_out = check_in + timedelta(hours=1)
        working_hours = AttendanceService.calculate_working_hours(check_in, check_out, Decimal('5.00'))
        self.assertEqual(working_hours, Decimal('0.00'))

    def test_calculate_overtime_above_standard(self):
        overtime = AttendanceService.calculate_overtime(Decimal('10.50'), standard_hours=9)
        self.assertEqual(overtime, Decimal('1.50'))

    def test_calculate_overtime_zero_when_under_standard(self):
        overtime = AttendanceService.calculate_overtime(Decimal('7.00'), standard_hours=9)
        self.assertEqual(overtime, Decimal('0.00'))
