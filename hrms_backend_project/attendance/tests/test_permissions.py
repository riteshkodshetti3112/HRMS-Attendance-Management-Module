from datetime import date
from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory

from attendance.models import Attendance
from attendance.permissions import (
    IsAdminOnly,
    IsSelfOrHRorAdmin,
    ReadOnlyOrHRorAdmin,
    get_role,
)
from employees.models import Employee
from .factories import create_department, create_employee


class PermissionHelperUnitTests(APITestCase):
    """Direct, HTTP-free tests for the permission helpers/classes."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.department = create_department()
        self.admin_employee = create_employee(role=Employee.ROLE_ADMIN, department=self.department)
        self.hr_employee = create_employee(role=Employee.ROLE_HR, department=self.department)
        self.plain_employee = create_employee(department=self.department)

    def test_get_role_for_superuser_is_admin(self):
        superuser = User.objects.create_superuser(username='root', password='x')
        self.assertEqual(get_role(superuser), 'ADMIN')

    def test_get_role_for_staff_without_profile_is_hr(self):
        staff_user = User.objects.create_user(username='staffer', password='x', is_staff=True)
        self.assertEqual(get_role(staff_user), 'HR')

    def test_get_role_for_plain_user_without_profile_is_employee(self):
        plain_user = User.objects.create_user(username='plain', password='x')
        self.assertEqual(get_role(plain_user), 'EMPLOYEE')

    def test_is_admin_only_permission(self):
        permission = IsAdminOnly()
        admin_request = self.factory.get('/')
        admin_request.user = self.admin_employee.user
        self.assertTrue(permission.has_permission(admin_request, None))

        hr_request = self.factory.get('/')
        hr_request.user = self.hr_employee.user
        self.assertFalse(permission.has_permission(hr_request, None))

    def test_is_self_or_hr_or_admin_object_permission(self):
        permission = IsSelfOrHRorAdmin()
        attendance = Attendance.objects.create(employee=self.plain_employee, attendance_date=date.today())

        owner_request = self.factory.get('/')
        owner_request.user = self.plain_employee.user
        self.assertTrue(permission.has_object_permission(owner_request, None, attendance))

        other_employee = create_employee(department=self.department)
        other_request = self.factory.get('/')
        other_request.user = other_employee.user
        self.assertFalse(permission.has_object_permission(other_request, None, attendance))

        hr_request = self.factory.get('/')
        hr_request.user = self.hr_employee.user
        self.assertTrue(permission.has_object_permission(hr_request, None, attendance))

    def test_read_only_or_hr_or_admin_permission(self):
        permission = ReadOnlyOrHRorAdmin()

        anon_request = self.factory.get('/')
        anon_request.user = AnonymousUser()
        self.assertFalse(permission.has_permission(anon_request, None))

        employee_get = self.factory.get('/')
        employee_get.user = self.plain_employee.user
        self.assertTrue(permission.has_permission(employee_get, None))

        employee_post = self.factory.post('/')
        employee_post.user = self.plain_employee.user
        self.assertFalse(permission.has_permission(employee_post, None))

        hr_post = self.factory.post('/')
        hr_post.user = self.hr_employee.user
        self.assertTrue(permission.has_permission(hr_post, None))


class EmployeeAccessTests(APITestCase):
    def setUp(self):
        self.employee = create_employee()
        self.client.force_authenticate(user=self.employee.user)

    def test_employee_can_use_own_endpoints(self):
        response = self.client.get(reverse('attendance-my-attendance'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_cannot_access_hr_list(self):
        response = self.client.get(reverse('attendance-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_access_dashboard(self):
        response = self.client.get(reverse('attendance-dashboard'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HRAccessTests(APITestCase):
    def setUp(self):
        self.department = create_department()
        self.hr_employee = create_employee(role=Employee.ROLE_HR, department=self.department)
        self.client.force_authenticate(user=self.hr_employee.user)
        self.subject = create_employee(department=self.department)
        self.attendance = Attendance.objects.create(
            employee=self.subject, attendance_date=date.today()
        )

    def test_hr_can_list_all_attendance(self):
        response = self.client.get(reverse('attendance-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hr_can_view_dashboard(self):
        response = self.client.get(reverse('attendance-dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hr_can_update_unlocked_record(self):
        url = reverse('attendance-detail', args=[self.attendance.pk])
        response = self.client.patch(url, {'remarks': 'Updated by HR'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hr_cannot_update_payroll_locked_record(self):
        Attendance.objects.filter(pk=self.attendance.pk).update(is_payroll_locked=True)
        url = reverse('attendance-detail', args=[self.attendance.pk])
        response = self.client.patch(url, {'remarks': 'Should fail'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminAccessTests(APITestCase):
    def setUp(self):
        self.department = create_department()
        self.admin_employee = create_employee(role=Employee.ROLE_ADMIN, department=self.department)
        self.client.force_authenticate(user=self.admin_employee.user)
        self.subject = create_employee(department=self.department)
        self.attendance = Attendance.objects.create(
            employee=self.subject, attendance_date=date.today()
        )

    def test_admin_can_delete_unlocked_record(self):
        url = reverse('attendance-detail', args=[self.attendance.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_can_access_analytics(self):
        today = date.today()
        response = self.client.get(
            reverse('attendance-analytics-department'), {'month': today.month, 'year': today.year}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
