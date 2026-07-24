Enterprise HRMS Backend System

Overview
The Attendance Management module enables employee check-in/check-out, attendance tracking, HR management, reporting, analytics, and exports using a service-layer architecture.
Technology Stack
Python 3.12+, Django, Django REST Framework, PostgreSQL, JWT Authentication, Django ORM
Features
Employee: Check-In, Check-Out, My Attendance, Summary.
HR/Admin: Manage attendance, reports, analytics, dashboard, exports.
Database Design
Attendance fields: id, employee, attendance_date, check_in_time, check_out_time, working_hours, break_hours, overtime_hours, attendance_status, remarks, created_at, updated_at.
Statuses: Present, Absent, Half Day, Work From Home, On Leave, Holiday, Weekend.
Constraints: One record/day, checkout>checkin, no future dates, non-negative working hours.
API Endpoints
Employee: POST /check-in, POST /check-out, GET /my-attendance, GET /my-summary.
HR/Admin: GET/PUT/DELETE attendance, GET report.
Business Rules
One check-in/day, checkout only after check-in, auto-calculate working hours and overtime, attendance used in payroll.
Service Layer
attendance_service.py methods: check_in, check_out, calculate_working_hours, calculate_overtime, attendance_summary, monthly_report.
Search & Filters
Employee, Department, Date, Month, Year, Attendance Status.
Reports
Monthly report: working days, present, absent, leave, WFH, hours, overtime.
Dashboard APIs
Today's attendance, present/absent counts, late employees, not checked out, average working hours.
Analytics
Department-wise attendance and employee performance metrics.
Validations
No duplicates, valid sequence, no future dates, lock edits after payroll generation.
Export
Excel, PDF, CSV reports.
Testing
Models, Services, APIs, Permissions with 90%+ code coverage target.
Folder Structure
attendance/
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── services.py
├── permissions.py
├── filters.py
├── validators.py
├── reports.py
├── utils.py
└── tests/
