from django.conf import settings
from django.db import models


class Department(models.Model):
    """Minimal Department model — attendance analytics groups by this."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    """
    Minimal Employee model — stands in for the real HRMS employee master
    so the Attendance module can be developed/tested independently.

    `role` drives the permission layer (employee / hr / admin) used
    throughout the attendance module instead of relying on a full-blown
    RBAC system.
    """

    ROLE_EMPLOYEE = 'EMPLOYEE'
    ROLE_HR = 'HR'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CHOICES = [
        (ROLE_EMPLOYEE, 'Employee'),
        (ROLE_HR, 'HR'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile',
    )
    employee_id = models.CharField(max_length=20, unique=True)  # e.g. EMP001
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employees',
    )
    designation = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
    date_joined = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee_id']

    def __str__(self):
        return f'{self.employee_id} - {self.first_name} {self.last_name}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def is_hr(self):
        return self.role == self.ROLE_HR

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN
