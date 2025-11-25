# CEMS - Class & Exam Management System

A polished Django workspace for managing academic years, classes, subjects, teacher assignments, exams, and results. It ships with role-based dashboards (Super Admin, Teacher, Student), a styled landing page, and PostgreSQL defaults ready for local development.

## Feature Snapshot
- Role-aware routing and auth (login, signup for students, password reset with email validation, fallback 404 to home).
- Academic structure: years, classes with sections, subjects, teacher-to-class-subject assignments, and student enrollments with auto roll numbers.
- Exam lifecycle: teachers create exams only for their mapped class/subject pairs, record marks and attendance, and see stats; results are unique per exam/student.
- Student experience: read-only dashboard showing enrollment, subjects, upcoming exams, published results, attendance, and multi-year history.
- Admin control: complete CRUD in Django Admin plus a showcase admin dashboard template; bulk section creation for classes from comma-separated input.
- Front end: curated templates under `templates/` using global styles in `cems/static/css/style.css`.

## Directory Map
- `manage.py` - Django entrypoint.
- `cems/` - project settings, URLs, static config, WSGI/ASGI.
- `accounts/` - auth views, student signup, password reset validation, role redirects, dashboards, and profile models.
- `academics/` - academic years, classes, subjects, teacher assignments, student enrollments, and teacher dashboards.
- `exams/` - exams, results, and teacher-facing exam create/manage/results flows.
- `templates/` - landing page plus admin/teacher/student dashboards and auth screens.
- `cems/static/` - global styles and scripts referenced by `base.html`.

## Requirements
- Python 3.11+
- Django 5.2.8
- PostgreSQL (configured in `cems/settings.py`)

## Quickstart
1) Install prerequisites  
   - Python 3.11+  
   - PostgreSQL server  
   - `pip install --upgrade pip`

2) Create and activate a virtual environment
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
# source .venv/bin/activate  # macOS/Linux
```

3) Install dependencies
```bash
pip install Django==5.2.8 psycopg2-binary
```

4) Configure the database  
   Ensure these credentials exist in PostgreSQL (edit `cems/settings.py` if needed):
   - NAME: `cems_db`
   - USER: `postgres`
   - PASSWORD: `masumjia`
   - HOST: `127.0.0.1`
   - PORT: `5432`
```bash
psql -U postgres -c "CREATE DATABASE cems_db;"
```

5) Apply migrations and create a superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

6) Run the server
```bash
python manage.py runserver
```
Landing page: `http://localhost:8000/`  
Django Admin: `http://localhost:8000/admin/`

## Role Playbook
- **Authentication**: `accounts.views.CEMSLoginView` and `CEMSPasswordResetView` (console email backend). Students self-register at `/accounts/register/student/`; other roles are provisioned by admins.
- **Super Admin**: manage all models via Django Admin. `ClassLevelAdmin` supports comma-delimited sections to create multiple class entries in one save. A showcase admin dashboard view is at `accounts.views.admin_dashboard` using `templates/admin_dashboard.html`.
- **Teacher**: `academics.views.teacher_dashboard` lists assigned classes/subjects and owned exams. Teachers admit existing students into their classes (auto roll numbers), create exams for assigned pairs, and enter marks/attendance via `exams.views.teacher_exam_manage`.
- **Student**: `accounts.views.student_dashboard` offers read-only visibility into enrollment, subjects, upcoming exams, published results with attendance, and prior-year history.
- **Routing**: `cems/urls.py` mounts `accounts`, `academics`, and `exams`; unknown routes fall back to `accounts.views.fallback_to_home`.

## Data Model Notes
- `StudentProfile` auto-generates immutable `student_id`; roll numbers sync from `StudentEnrollment`.
- `TeacherProfile` auto-generates incremental `employee_code` (EMP### pattern).
- `StudentEnrollment` enforces unique roll numbers per class/year and auto-assigns the next roll on create.
- `ExamResult` is unique per exam/student and stores marks, attendance, and publication status.

## Static and Media
- Static: `cems/static`; `STATIC_ROOT` defaults to `BASE_DIR/static`. Run `python manage.py collectstatic` before production.
- Media: stored under `media/` via `MEDIA_ROOT` and served at `MEDIA_URL=/media/`.

## Handy Commands
- Runserver: `python manage.py runserver`
- Migrations: `python manage.py makemigrations && python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`
- Collect static: `python manage.py collectstatic`

## Security and Deployment
- Replace the dev `SECRET_KEY` in `cems/settings.py`; load secrets and DB credentials from environment variables.
- Set `DEBUG = False` and configure `ALLOWED_HOSTS` for production.
- Use a real email backend for password resets.
- Add SSL, secure cookies, and proper static/media hosting when deploying.

## Testing
- No automated tests are included yet. Add coverage for auth flows, enrollment logic, exam creation/result handling, and admin helpers as you extend the project.
