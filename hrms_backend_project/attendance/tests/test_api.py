from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from employees.models import Employee
from .factories import create_department, create_employee


class CheckInApiTests(APITestCase):
    def setUp(self):
        self.employee = create_employee()
        self.client.force_authenticate(user=self.employee.user)
        self.url = reverse('attendance-check-in')

    def test_check_in_success(self):
        response = self.client.post(self.url, {'remarks': 'On time'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['check_in_time'])

    def test_check_in_twice_fails(self):
        self.client.post(self.url, {})
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_in_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {})
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class CheckOutApiTests(APITestCase):
    def setUp(self):
        self.employee = create_employee()
        self.client.force_authenticate(user=self.employee.user)
        self.checkin_url = reverse('attendance-check-in')
        self.checkout_url = reverse('attendance-check-out')

    def test_check_out_without_check_in_fails(self):
        response = self.client.post(self.checkout_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_out_success(self):
        self.client.post(self.checkin_url, {})
        response = self.client.post(self.checkout_url, {'break_hours': '1.00'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['check_out_time'])


class MyAttendanceApiTests(APITestCase):
    def setUp(self):
        self.employee = create_employee()
        self.client.force_authenticate(user=self.employee.user)

    def test_my_attendance_list_only_shows_own_records(self):
        other_employee = create_employee()
        self.client.post(reverse('attendance-check-in'))

        other_client_url = reverse('attendance-my-attendance')
        response = self.client.get(other_client_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_my_summary_returns_current_month_totals(self):
        from attendance.services import AttendanceService

        # Build a full working day directly through the service layer so
        # the record lands as PRESENT (not a HALF_DAY from a near-zero gap).
        check_in_time = timezone.now().replace(hour=9, minute=30, second=0, microsecond=0)
        AttendanceService.check_in(self.employee, check_in_time=check_in_time)
        AttendanceService.check_out(self.employee, check_out_time=check_in_time + timedelta(hours=9))

        today = date.today()
        response = self.client.get(
            reverse('attendance-my-summary'), {'month': today.month, 'year': today.year}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['present_days'], 1)


class AttendanceReportApiTests(APITestCase):
    def setUp(self):
        self.department = create_department()
        self.hr_user = create_employee(role=Employee.ROLE_HR, department=self.department)
        self.employee = create_employee(department=self.department)
        self.client.force_authenticate(user=self.hr_user.user)

    def test_report_requires_hr_or_admin(self):
        employee_client_user = create_employee()
        self.client.force_authenticate(user=employee_client_user.user)
        response = self.client.get(reverse('attendance-report'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_accessible_to_hr(self):
        response = self.client.get(reverse('attendance-report'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_working_hours', response.data)
