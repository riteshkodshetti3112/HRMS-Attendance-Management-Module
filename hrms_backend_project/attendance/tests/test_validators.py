from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from attendance import validators
from attendance.models import Attendance
from .factories import create_employee


class ValidatorUnitTests(TestCase):
    def setUp(self):
        self.employee = create_employee()

    def test_validate_not_future_date_raises(self):
        with self.assertRaises(ValidationError):
            validators.validate_not_future_date(date.today() + timedelta(days=1))

    def test_validate_not_future_date_passes_for_today(self):
        validators.validate_not_future_date(date.today())  # should not raise

    def test_validate_checkout_after_checkin_raises(self):
        now = timezone.now()
        with self.assertRaises(ValidationError):
            validators.validate_checkout_after_checkin(now, now - timedelta(hours=1))

    def test_validate_working_hours_non_negative_raises(self):
        with self.assertRaises(ValidationError):
            validators.validate_working_hours_non_negative(-1)

    def test_validate_employee_active_raises_for_inactive(self):
        self.employee.is_active = False
        self.employee.save()
        with self.assertRaises(ValidationError):
            validators.validate_employee_active(self.employee)

    def test_validate_not_already_checked_out_raises(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            attendance_date=date.today(),
            check_in_time=timezone.now(),
            check_out_time=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            validators.validate_not_already_checked_out(attendance)

    def test_validate_no_duplicate_attendance_raises(self):
        Attendance.objects.create(employee=self.employee, attendance_date=date.today())
        with self.assertRaises(ValidationError):
            validators.validate_no_duplicate_attendance(self.employee, date.today())

    def test_validate_no_duplicate_attendance_excludes_self(self):
        attendance = Attendance.objects.create(employee=self.employee, attendance_date=date.today())
        # Should not raise: we're excluding the record's own pk (an update case)
        validators.validate_no_duplicate_attendance(self.employee, date.today(), existing_pk=attendance.pk)
