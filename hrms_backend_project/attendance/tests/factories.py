"""Lightweight test-data helpers (no factory_boy dependency required)."""
from django.contrib.auth.models import User

from employees.models import Department, Employee

_counter = {'n': 0}


def _next_n():
    _counter['n'] += 1
    return _counter['n']


def create_department(name=None, code=None):
    n = _next_n()
    return Department.objects.create(
        name=name or f'Engineering-{n}',
        code=code or f'ENG{n}',
    )


def create_employee(username=None, role=Employee.ROLE_EMPLOYEE, department=None, is_active=True):
    n = _next_n()
    username = username or f'user{n}'
    user = User.objects.create_user(username=username, password='pass1234')
    return Employee.objects.create(
        user=user,
        employee_id=f'EMP{n:03d}',
        first_name='Test',
        last_name=f'User{n}',
        department=department,
        role=role,
        date_joined='2024-01-01',
        is_active=is_active,
    )
