from datetime import date

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from employees.models import Department, Employee

from . import reports
from .filters import AttendanceFilter
from .models import Attendance
from .permissions import (
    IsEmployeeProfileOwner,
    IsHRorAdmin,
    ReadOnlyOrHRorAdmin,
)
from .serializers import (
    AttendanceSerializer,
    CheckInSerializer,
    CheckOutSerializer,
    DashboardSummarySerializer,
    DepartmentAnalyticsSerializer,
    EmployeePerformanceSerializer,
    MonthlySummarySerializer,
    MyAttendanceSerializer,
)
from .services import AttendanceService


def _employee_profile(request):
    return getattr(request.user, 'employee_profile', None)


def _month_year_from_query(request):
    today = timezone.localdate()
    month = int(request.query_params.get('month', today.month))
    year = int(request.query_params.get('year', today.year))
    return month, year


# ---------------------------------------------------------------------------
# Employee-facing APIs
# ---------------------------------------------------------------------------
class CheckInView(APIView):
    """POST /api/v1/attendance/check-in/"""

    permission_classes = [IsEmployeeProfileOwner]

    def post(self, request):
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = _employee_profile(request)
        attendance = AttendanceService.check_in(
            employee=employee, remarks=serializer.validated_data.get('remarks', '')
        )
        return Response(MyAttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)


class CheckOutView(APIView):
    """POST /api/v1/attendance/check-out/"""

    permission_classes = [IsEmployeeProfileOwner]

    def post(self, request):
        serializer = CheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = _employee_profile(request)
        attendance = AttendanceService.check_out(
            employee=employee,
            remarks=serializer.validated_data.get('remarks', ''),
            break_hours=serializer.validated_data.get('break_hours'),
        )
        return Response(MyAttendanceSerializer(attendance).data, status=status.HTTP_200_OK)


class MyAttendanceListView(generics.ListAPIView):
    """GET /api/v1/attendance/my-attendance/"""

    serializer_class = MyAttendanceSerializer
    permission_classes = [IsEmployeeProfileOwner]
    filterset_class = AttendanceFilter

    def get_queryset(self):
        employee = _employee_profile(self.request)
        return Attendance.objects.filter(employee=employee).order_by('-attendance_date')


class MySummaryView(APIView):
    """GET /api/v1/attendance/my-summary/?month=&year="""

    permission_classes = [IsEmployeeProfileOwner]

    def get(self, request):
        employee = _employee_profile(request)
        month, year = _month_year_from_query(request)
        summary = AttendanceService.attendance_summary(employee, month, year)
        return Response(MonthlySummarySerializer(summary).data)


# ---------------------------------------------------------------------------
# HR / Admin APIs
# ---------------------------------------------------------------------------
class AttendanceViewSet(viewsets.ModelViewSet):
    """
    list/retrieve/update/destroy for HR & Admin.

    GET   /api/v1/attendance/
    GET   /api/v1/attendance/{id}/
    PUT   /api/v1/attendance/{id}/
    DELETE /api/v1/attendance/{id}/
    """

    queryset = Attendance.objects.select_related('employee', 'employee__department').all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsHRorAdmin]
    filterset_class = AttendanceFilter
    http_method_names = ['get', 'put', 'patch', 'delete', 'head', 'options']

    def perform_update(self, serializer):
        if serializer.instance.is_payroll_locked:
            raise PermissionDenied('This attendance record is locked because payroll has been generated.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_payroll_locked:
            raise PermissionDenied('This attendance record is locked because payroll has been generated.')
        instance.delete()


class AttendanceReportView(APIView):
    """GET /api/v1/attendance/report/?month=&year=&employee=&department="""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        month, year = _month_year_from_query(request)

        employee = None
        if request.query_params.get('employee'):
            employee = get_object_or_404(Employee, employee_id=request.query_params['employee'])

        department = None
        if request.query_params.get('department'):
            department = get_object_or_404(Department, code=request.query_params['department'])

        summary = AttendanceService.monthly_report(month, year, department=department, employee=employee)
        return Response(MonthlySummarySerializer(summary).data)


# ---------------------------------------------------------------------------
# Dashboard (Module 7)
# ---------------------------------------------------------------------------
class DashboardSummaryView(APIView):
    """
    GET /api/v1/attendance/dashboard/

    Returns today's attendance, present/absent counts, late employees,
    employees who haven't checked out yet, and average working hours —
    all in one call for the HR dashboard.
    """

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        summary = AttendanceService.dashboard_summary()
        return Response(DashboardSummarySerializer(summary).data)


# ---------------------------------------------------------------------------
# Analytics (Module 8)
# ---------------------------------------------------------------------------
class DepartmentWiseAttendanceView(APIView):
    """GET /api/v1/attendance/analytics/department/?month=&year="""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        month, year = _month_year_from_query(request)
        data = AttendanceService.department_wise_attendance(month, year)
        return Response(DepartmentAnalyticsSerializer(data, many=True).data)


class EmployeePerformanceView(APIView):
    """GET /api/v1/attendance/analytics/employee-performance/?employee=EMP001&month=&year="""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        employee_id = request.query_params.get('employee')
        if not employee_id:
            raise ValidationError({'employee': 'This query parameter is required.'})
        employee = get_object_or_404(Employee, employee_id=employee_id)
        month, year = _month_year_from_query(request)
        data = AttendanceService.employee_performance(employee, month, year)
        return Response(EmployeePerformanceSerializer(data).data)


# ---------------------------------------------------------------------------
# Exports (Module 10)
# ---------------------------------------------------------------------------
class ExportDailyAttendanceExcelView(APIView):
    """GET /api/v1/attendance/export/excel/daily/?date=YYYY-MM-DD"""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        day = request.query_params.get('date', timezone.localdate().isoformat())
        queryset = Attendance.objects.filter(attendance_date=day)
        return reports.generate_attendance_excel(
            queryset, filename=f'daily_attendance_{day}.xlsx', sheet_title='Daily Attendance'
        )


class ExportMonthlyAttendanceExcelView(APIView):
    """GET /api/v1/attendance/export/excel/monthly/?month=&year="""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        month, year = _month_year_from_query(request)
        queryset = Attendance.objects.filter(
            attendance_date__month=month, attendance_date__year=year
        )
        return reports.generate_attendance_excel(
            queryset, filename=f'monthly_attendance_{year}_{month:02d}.xlsx', sheet_title='Monthly Attendance'
        )


class ExportEmployeeAttendancePDFView(APIView):
    """GET /api/v1/attendance/export/pdf/employee/?employee=EMP001&month=&year="""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        employee_id = request.query_params.get('employee')
        if not employee_id:
            raise ValidationError({'employee': 'This query parameter is required.'})
        employee = get_object_or_404(Employee, employee_id=employee_id)
        month, year = _month_year_from_query(request)

        summary = AttendanceService.attendance_summary(employee, month, year)
        queryset = Attendance.objects.filter(
            employee=employee, attendance_date__month=month, attendance_date__year=year
        )
        return reports.employee_attendance_pdf(employee, queryset, summary)


class ExportDepartmentAttendancePDFView(APIView):
    """GET /api/v1/attendance/export/pdf/department/?department=ENG&month=&year="""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        code = request.query_params.get('department')
        if not code:
            raise ValidationError({'department': 'This query parameter is required.'})
        department = get_object_or_404(Department, code=code)
        month, year = _month_year_from_query(request)

        analytics_rows = AttendanceService.department_wise_attendance(month, year)
        analytics = next((row for row in analytics_rows if row['department'] == department.name), {
            'department': department.name, 'present': 0, 'absent': 0, 'percentage': 0.0,
        })
        return reports.department_attendance_pdf(department, analytics)


class ExportAttendanceRegisterCSVView(APIView):
    """GET /api/v1/attendance/export/csv/register/?month=&year="""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        queryset = Attendance.objects.all()
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        if month:
            queryset = queryset.filter(attendance_date__month=month)
        if year:
            queryset = queryset.filter(attendance_date__year=year)
        return reports.generate_attendance_csv(queryset, filename='attendance_register.csv')
