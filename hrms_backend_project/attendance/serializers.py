from rest_framework import serializers

from employees.models import Employee
from .models import Attendance, AttendanceStatus


class AttendanceSerializer(serializers.ModelSerializer):
    """Full read/write representation used by the HR/Admin ModelViewSet."""

    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    department = serializers.CharField(source='employee.department.name', read_only=True, default=None)

    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_id', 'employee_name', 'department',
            'attendance_date', 'check_in_time', 'check_out_time',
            'working_hours', 'break_hours', 'overtime_hours',
            'late_arrival_minutes', 'early_checkout_minutes',
            'attendance_status', 'remarks', 'is_payroll_locked',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'working_hours', 'overtime_hours', 'late_arrival_minutes',
            'early_checkout_minutes', 'created_at', 'updated_at',
        ]


class MyAttendanceSerializer(serializers.ModelSerializer):
    """Slimmer read-only view for an employee looking at their own history."""

    class Meta:
        model = Attendance
        fields = [
            'id', 'attendance_date', 'check_in_time', 'check_out_time',
            'working_hours', 'break_hours', 'overtime_hours',
            'late_arrival_minutes', 'early_checkout_minutes',
            'attendance_status', 'remarks',
        ]
        read_only_fields = fields


class CheckInSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class CheckOutSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default='')
    break_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None
    )


class MonthYearQuerySerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class MonthlySummarySerializer(serializers.Serializer):
    employee = serializers.CharField(required=False)
    department = serializers.CharField(required=False)
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    total_working_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    half_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    leave_days = serializers.IntegerField()
    wfh_days = serializers.IntegerField()
    holiday_days = serializers.IntegerField()
    weekend_days = serializers.IntegerField()
    total_working_hours = serializers.DecimalField(max_digits=7, decimal_places=2)
    total_overtime_hours = serializers.DecimalField(max_digits=7, decimal_places=2)


class DashboardSummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    todays_attendance_count = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    late_employees = serializers.ListField(child=serializers.CharField())
    employees_not_checked_out = serializers.ListField(child=serializers.CharField())
    average_working_hours = serializers.DecimalField(max_digits=5, decimal_places=2)


class DepartmentAnalyticsSerializer(serializers.Serializer):
    department = serializers.CharField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    percentage = serializers.FloatField()


class EmployeePerformanceSerializer(serializers.Serializer):
    employee = serializers.CharField()
    attendance_percentage = serializers.FloatField()
    average_working_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_overtime_hours = serializers.DecimalField(max_digits=7, decimal_places=2)
    late_arrivals = serializers.IntegerField()
