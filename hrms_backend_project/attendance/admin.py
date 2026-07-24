from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'attendance_date', 'check_in_time', 'check_out_time',
        'working_hours', 'overtime_hours', 'attendance_status', 'is_payroll_locked',
    )
    list_filter = ('attendance_status', 'is_payroll_locked', 'attendance_date')
    search_fields = ('employee__employee_id', 'employee__first_name', 'employee__last_name')
    date_hierarchy = 'attendance_date'
    readonly_fields = ('created_at', 'updated_at')
