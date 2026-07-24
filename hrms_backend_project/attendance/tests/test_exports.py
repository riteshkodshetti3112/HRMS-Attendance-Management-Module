from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from attendance.models import Attendance
from attendance.services import AttendanceService
from employees.models import Employee
from .factories import create_department, create_employee


class ExportEndpointTests(APITestCase):
    def setUp(self):
        self.department = create_department()
        self.hr_user = create_employee(role=Employee.ROLE_HR, department=self.department)
        self.employee = create_employee(department=self.department)
        self.client.force_authenticate(user=self.hr_user.user)

        check_in_time = timezone.now().replace(hour=9, minute=30, second=0, microsecond=0)
        AttendanceService.check_in(self.employee, check_in_time=check_in_time)
        AttendanceService.check_out(self.employee, check_out_time=check_in_time + timedelta(hours=9))

    def test_export_daily_excel(self):
        response = self.client.get(reverse('attendance-export-excel-daily'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('spreadsheetml', response['Content-Type'])

    def test_export_monthly_excel(self):
        today = date.today()
        response = self.client.get(
            reverse('attendance-export-excel-monthly'), {'month': today.month, 'year': today.year}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_attendance_register_csv(self):
        response = self.client.get(reverse('attendance-export-csv-register'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_employee_pdf(self):
        today = date.today()
        response = self.client.get(
            reverse('attendance-export-pdf-employee'),
            {'employee': self.employee.employee_id, 'month': today.month, 'year': today.year},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_export_employee_pdf_requires_employee_param(self):
        response = self.client.get(reverse('attendance-export-pdf-employee'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_export_department_pdf(self):
        today = date.today()
        response = self.client.get(
            reverse('attendance-export-pdf-department'),
            {'department': self.department.code, 'month': today.month, 'year': today.year},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_export_department_pdf_requires_department_param(self):
        response = self.client.get(reverse('attendance-export-pdf-department'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_performance_analytics(self):
        today = date.today()
        response = self.client.get(
            reverse('attendance-analytics-employee-performance'),
            {'employee': self.employee.employee_id, 'month': today.month, 'year': today.year},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('attendance_percentage', response.data)

    def test_employee_performance_requires_employee_param(self):
        response = self.client.get(reverse('attendance-analytics-employee-performance'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_filters_by_employee(self):
        today = date.today()
        response = self.client.get(
            reverse('attendance-report'),
            {'employee': self.employee.employee_id, 'month': today.month, 'year': today.year},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['employee'], self.employee.employee_id)
