"""
Export generators for the attendance module (Module 10).

Each function returns an `HttpResponse` with the correct content-type
and `Content-Disposition` header so views can simply `return` it.
"""
import csv
import io

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

ATTENDANCE_COLUMNS = [
    'Employee ID', 'Employee Name', 'Department', 'Date',
    'Check-In', 'Check-Out', 'Working Hours', 'Break Hours',
    'Overtime Hours', 'Status', 'Remarks',
]


def _row_for(attendance):
    employee = attendance.employee
    return [
        employee.employee_id,
        employee.full_name,
        employee.department.name if employee.department else '',
        attendance.attendance_date.isoformat(),
        attendance.check_in_time.strftime('%Y-%m-%d %H:%M') if attendance.check_in_time else '',
        attendance.check_out_time.strftime('%Y-%m-%d %H:%M') if attendance.check_out_time else '',
        float(attendance.working_hours),
        float(attendance.break_hours),
        float(attendance.overtime_hours),
        attendance.get_attendance_status_display(),
        attendance.remarks,
    ]


# ---------------------------------------------------------------------------
# Excel (Daily / Monthly attendance)
# ---------------------------------------------------------------------------
def generate_attendance_excel(queryset, filename='attendance.xlsx', sheet_title='Attendance'):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title

    sheet.append(ATTENDANCE_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for attendance in queryset.select_related('employee', 'employee__department'):
        sheet.append(_row_for(attendance))

    for column_cells in sheet.columns:
        length = max(len(str(cell.value)) for cell in column_cells if cell.value is not None) if any(
            cell.value is not None for cell in column_cells
        ) else 10
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 40)

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# CSV (Attendance register)
# ---------------------------------------------------------------------------
def generate_attendance_csv(queryset, filename='attendance_register.csv'):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(ATTENDANCE_COLUMNS)
    for attendance in queryset.select_related('employee', 'employee__department'):
        writer.writerow(_row_for(attendance))
    return response


# ---------------------------------------------------------------------------
# PDF (Employee / Department attendance report)
# ---------------------------------------------------------------------------
def generate_attendance_pdf(title, summary_rows, table_rows, filename='attendance_report.pdf'):
    """
    `summary_rows`: list of (label, value) tuples shown above the table.
    `table_rows`: list of lists, first row is the header.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles['Title']), Spacer(1, 12)]

    if summary_rows:
        summary_table = Table([[str(label), str(value)] for label, value in summary_rows])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 16))

    if table_rows:
        data_table = Table(table_rows, repeatRows=1)
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3436')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f6fa')]),
        ]))
        elements.append(data_table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def employee_attendance_pdf(employee, queryset, summary: dict):
    summary_rows = [
        ('Employee', f'{employee.employee_id} - {employee.full_name}'),
        ('Department', employee.department.name if employee.department else '-'),
        ('Period', f"{summary.get('month')}/{summary.get('year')}"),
        ('Present Days', summary.get('present_days')),
        ('Absent Days', summary.get('absent_days')),
        ('Total Working Hours', summary.get('total_working_hours')),
        ('Total Overtime Hours', summary.get('total_overtime_hours')),
    ]
    table_rows = [['Date', 'Check-In', 'Check-Out', 'Working Hrs', 'Status']]
    for attendance in queryset.order_by('attendance_date'):
        table_rows.append([
            attendance.attendance_date.isoformat(),
            attendance.check_in_time.strftime('%H:%M') if attendance.check_in_time else '-',
            attendance.check_out_time.strftime('%H:%M') if attendance.check_out_time else '-',
            str(attendance.working_hours),
            attendance.get_attendance_status_display(),
        ])
    return generate_attendance_pdf(
        f'Attendance Report - {employee.employee_id}',
        summary_rows,
        table_rows,
        filename=f'attendance_{employee.employee_id}.pdf',
    )


def department_attendance_pdf(department, analytics: dict):
    summary_rows = [
        ('Department', analytics.get('department')),
        ('Present', analytics.get('present')),
        ('Absent', analytics.get('absent')),
        ('Attendance %', analytics.get('percentage')),
    ]
    return generate_attendance_pdf(
        f'Department Attendance Report - {department.name}',
        summary_rows,
        table_rows=[],
        filename=f'attendance_{department.code}.pdf',
    )
