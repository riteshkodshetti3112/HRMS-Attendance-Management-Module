from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from attendance.models import Attendance, AttendanceStatus
from attendance.services import AttendanceService
from .factories import create_department, create_employee


class CheckInServiceTests(TestCase):
    def setUp(self):
        self.employee = create_employee()

    def test_check_in_creates_attendance_record(self):
        attendance = AttendanceService.check_in(self.employee)
        self.assertEqual(attendance.employee, self.employee)
        self.assertEqual(attendance.attendance_date, timezone.localdate())
        self.assertIsNotNone(attendance.check_in_time)
        self.assertEqual(attendance.attendance_status, AttendanceStatus.PRESENT)

    def test_double_check_in_rejected(self):
        AttendanceService.check_in(self.employee)
        with self.assertRaises(ValidationError):
            AttendanceService.check_in(self.employee)

    def test_inactive_employee_cannot_check_in(self):
        self.employee.is_active = False
        self.employee.save()
        with self.assertRaises(ValidationError):
            AttendanceService.check_in(self.employee)


class CheckOutServiceTests(TestCase):
    def setUp(self):
        self.employee = create_employee()

    def test_check_out_without_check_in_rejected(self):
        with self.assertRaises(ValidationError):
            AttendanceService.check_out(self.employee)

    def test_check_out_calculates_working_hours(self):
        today = timezone.localdate()
        check_in_time = timezone.now().replace(hour=9, minute=30, second=0, microsecond=0)
        AttendanceService.check_in(self.employee, check_in_time=check_in_time)

        check_out_time = check_in_time + timedelta(hours=9)
        attendance = AttendanceService.check_out(
            self.employee, check_out_time=check_out_time, break_hours=Decimal('1.00')
        )
        self.assertEqual(attendance.attendance_date, today)
        self.assertEqual(attendance.working_hours, Decimal('8.00'))
        self.assertEqual(attendance.overtime_hours, Decimal('0.00'))

    def test_double_check_out_rejected(self):
        check_in_time = timezone.now()
        AttendanceService.check_in(self.employee, check_in_time=check_in_time)
        AttendanceService.check_out(self.employee, check_out_time=check_in_time + timedelta(hours=9))
        with self.assertRaises(ValidationError):
            AttendanceService.check_out(self.employee, check_out_time=check_in_time + timedelta(hours=10))

    def test_checkout_before_checkin_rejected(self):
        check_in_time = timezone.now()
        AttendanceService.check_in(self.employee, check_in_time=check_in_time)
        with self.assertRaises(ValidationError):
            AttendanceService.check_out(self.employee, check_out_time=check_in_time - timedelta(hours=1))

    def test_short_day_marked_half_day(self):
        check_in_time = timezone.now().replace(hour=9, minute=30, second=0, microsecond=0)
        AttendanceService.check_in(self.employee, check_in_time=check_in_time)
        attendance = AttendanceService.check_out(
            self.employee, check_out_time=check_in_time + timedelta(hours=3), break_hours=Decimal('0')
        )
        self.assertEqual(attendance.attendance_status, AttendanceStatus.HALF_DAY)


class SummaryAndReportTests(TestCase):
    def setUp(self):
        self.department = create_department()
        self.employee = create_employee(department=self.department)
        today = date.today()
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=today,
            attendance_status=AttendanceStatus.PRESENT,
            working_hours=Decimal('8.00'),
            overtime_hours=Decimal('0.00'),
        )
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=today - timedelta(days=1),
            attendance_status=AttendanceStatus.ABSENT,
        )

    def test_attendance_summary_counts_days(self):
        today = date.today()
        summary = AttendanceService.attendance_summary(self.employee, today.month, today.year)
        self.assertEqual(summary['present_days'], 1)
        self.assertEqual(summary['absent_days'], 1)
        self.assertEqual(summary['total_working_hours'], Decimal('8.00'))

    def test_monthly_report_scoped_by_department(self):
        today = date.today()
        report = AttendanceService.monthly_report(today.month, today.year, department=self.department)
        self.assertEqual(report['present_days'], 1)
        self.assertEqual(report['department'], self.department.name)

    def test_department_wise_attendance_percentage(self):
        today = date.today()
        results = AttendanceService.department_wise_attendance(today.month, today.year)
        row = next(r for r in results if r['department'] == self.department.name)
        self.assertEqual(row['present'], 1)
        self.assertEqual(row['absent'], 1)
        self.assertEqual(row['percentage'], 50.0)

    def test_dashboard_summary_reflects_today(self):
        summary = AttendanceService.dashboard_summary()
        self.assertEqual(summary['present_count'], 1)
        self.assertEqual(summary['todays_attendance_count'], 1)
