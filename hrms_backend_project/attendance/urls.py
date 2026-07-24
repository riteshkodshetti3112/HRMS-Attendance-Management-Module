from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'', views.AttendanceViewSet, basename='attendance')

urlpatterns = [
    # Employee APIs
    path('check-in/', views.CheckInView.as_view(), name='attendance-check-in'),
    path('check-out/', views.CheckOutView.as_view(), name='attendance-check-out'),
    path('my-attendance/', views.MyAttendanceListView.as_view(), name='attendance-my-attendance'),
    path('my-summary/', views.MySummaryView.as_view(), name='attendance-my-summary'),

    # HR / Admin APIs
    path('report/', views.AttendanceReportView.as_view(), name='attendance-report'),

    # Dashboard
    path('dashboard/', views.DashboardSummaryView.as_view(), name='attendance-dashboard'),

    # Analytics
    path('analytics/department/', views.DepartmentWiseAttendanceView.as_view(), name='attendance-analytics-department'),
    path(
        'analytics/employee-performance/',
        views.EmployeePerformanceView.as_view(),
        name='attendance-analytics-employee-performance',
    ),

    # Exports
    path('export/excel/daily/', views.ExportDailyAttendanceExcelView.as_view(), name='attendance-export-excel-daily'),
    path(
        'export/excel/monthly/',
        views.ExportMonthlyAttendanceExcelView.as_view(),
        name='attendance-export-excel-monthly',
    ),
    path(
        'export/pdf/employee/',
        views.ExportEmployeeAttendancePDFView.as_view(),
        name='attendance-export-pdf-employee',
    ),
    path(
        'export/pdf/department/',
        views.ExportDepartmentAttendancePDFView.as_view(),
        name='attendance-export-pdf-department',
    ),
    path(
        'export/csv/register/',
        views.ExportAttendanceRegisterCSVView.as_view(),
        name='attendance-export-csv-register',
    ),

    # HR/Admin CRUD (ViewSet) -- must come last so it doesn't swallow the
    # named routes above (router registers /, /{id}/)
    path('', include(router.urls)),
]
