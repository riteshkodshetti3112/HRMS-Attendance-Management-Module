import django_filters

from .models import Attendance, AttendanceStatus


class AttendanceFilter(django_filters.FilterSet):
    employee = django_filters.CharFilter(field_name='employee__employee_id', lookup_expr='iexact')
    department = django_filters.CharFilter(field_name='employee__department__code', lookup_expr='iexact')
    date = django_filters.DateFilter(field_name='attendance_date', lookup_expr='exact')
    date_from = django_filters.DateFilter(field_name='attendance_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='attendance_date', lookup_expr='lte')
    month = django_filters.NumberFilter(field_name='attendance_date', lookup_expr='month')
    year = django_filters.NumberFilter(field_name='attendance_date', lookup_expr='year')
    status = django_filters.ChoiceFilter(field_name='attendance_status', choices=AttendanceStatus.choices)

    class Meta:
        model = Attendance
        fields = ['employee', 'department', 'date', 'date_from', 'date_to', 'month', 'year', 'status']
