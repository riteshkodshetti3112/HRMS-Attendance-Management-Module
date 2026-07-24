# HRMS Backend — Sprint 1: Attendance Management

Django + DRF implementation of the Attendance module (check-in/out, daily
& monthly attendance, status tracking, reports, analytics, dashboard,
exports). Built as a standalone app so it can be dropped into the real
HRMS backend later — only the `employees` app is a stand-in for the real
employee master.

## Setup (VS Code / terminal)

```bash
# 1. Create & activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Create a superuser (role=ADMIN via is_superuser)
python manage.py createsuperuser

# 5. Run the dev server
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` to create Departments/Employees, or
use the DRF browsable API at `http://127.0.0.1:8000/api/v1/attendance/`.

Each `User` needs a linked `employees.Employee` row (with `role` =
`EMPLOYEE` / `HR` / `ADMIN`) to use the attendance endpoints — create one
per user via the admin site or a data migration/fixture.

## Running tests

```bash
python manage.py test attendance -v 2

# with coverage
coverage run --source='attendance' manage.py test attendance
coverage report -m
```

Current run: **64 tests passing, 99% coverage** on the `attendance` app
(target was 90%).

## API summary

**Employee**
- `POST /api/v1/attendance/check-in/`
- `POST /api/v1/attendance/check-out/`
- `GET  /api/v1/attendance/my-attendance/` (supports the same filters as below)
- `GET  /api/v1/attendance/my-summary/?month=&year=`

**HR / Admin**
- `GET/PUT/PATCH/DELETE /api/v1/attendance/` and `/api/v1/attendance/{id}/`
- `GET /api/v1/attendance/report/?month=&year=&employee=&department=`
- `GET /api/v1/attendance/dashboard/`
- `GET /api/v1/attendance/analytics/department/?month=&year=`
- `GET /api/v1/attendance/analytics/employee-performance/?employee=EMP001&month=&year=`
- `GET /api/v1/attendance/export/excel/daily/?date=YYYY-MM-DD`
- `GET /api/v1/attendance/export/excel/monthly/?month=&year=`
- `GET /api/v1/attendance/export/pdf/employee/?employee=EMP001&month=&year=`
- `GET /api/v1/attendance/export/pdf/department/?department=ENG&month=&year=`
- `GET /api/v1/attendance/export/csv/register/?month=&year=`

Filtering on list/report endpoints: `employee`, `department`, `date`,
`date_from`, `date_to`, `month`, `year`, `status`.

## Design notes

- **Service layer**: all business logic lives in `attendance/services.py`
  (`AttendanceService`). Views never touch the ORM directly or apply
  rules themselves — this is what Module 4 asked for and it's what makes
  `test_services.py` possible without spinning up HTTP requests.
- **Permissions**: role comes from `Employee.role` (`EMPLOYEE`/`HR`/`ADMIN`),
  with `is_superuser`/`is_staff` fallbacks so it still behaves for plain
  Django accounts. See `attendance/permissions.py`.
- **Payroll lock**: `Attendance.is_payroll_locked` simulates a payroll run
  having closed the period; HR/Admin updates and deletes are blocked
  (403) once it's set, and the model-level `clean()` blocks it too as a
  second line of defense.
- **Standard shift / thresholds** (late grace, half-day cutoff, standard
  working hours, default break) are configurable in one place:
  `ATTENDANCE_SETTINGS` in `hrms_backend/settings.py`.
