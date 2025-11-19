# Class & Exam Management System (CEMS)

## Project Overview
The Class & Exam Management System (CEMS) is a Django-based platform for coordinating classrooms, enrollment, and exam delivery. The goal of this project is to strengthen core Django skills (authentication, authorization, ORM workflows, template rendering) while persisting academic data in a relational database. This document captures the current state of the codebase so new contributors can get productive quickly.

## Current Progress
- Bootstrapped a Django 5.2.8 project (`cems`) with a PostgreSQL-backed configuration and per-app folders for academics, accounts, and exams.
- Added placeholder Django apps to organize future domain modules (user profiles & roles, class scheduling, exam management).
- Wired default static/media directories and template discovery to support upcoming UI work.
- Created a workspace virtual environment (`env/`) locally for development convenience (not committed to version control).

## Repository Layout
```
cems_project/
+-- cems/            # Global project config, settings, URLs, ASGI/WSGI entrypoints
+-- academics/       # Placeholder for class/course entities
+-- accounts/        # Placeholder for user and role management
+-- exams/           # Placeholder for assessments, question sets, and results
+-- templates/       # Shared Django templates (not yet populated)
+-- media/           # User-uploaded files during development
+-- manage.py        # Django management entrypoint
+-- README.MD        # You are here
```

## Getting Started
### Prerequisites
- Python 3.11+ (the local virtual environment in `env/` targets this range)
- PostgreSQL 14+ running locally with a database user that can create/manage `cems_db`
- `pip`, `virtualenv` (or `python -m venv`)

### Local Environment Setup
1. **Create & activate a virtual environment**
   ```powershell
   python -m venv env
   .\env\Scripts\activate
   ```
2. **Install Django and supporting packages** (temporary list until `requirements.txt` is added):
   ```powershell
   pip install django==5.2.8 psycopg2-binary python-dotenv
   ```
3. **Configure environment variables**: create a `.env` file (or edit `cems/settings.py`) with your secret key and database credentials if they differ from the defaults checked into settings.

### Database Configuration
Update `cems/settings.py` if your PostgreSQL instance uses different credentials/host/port. Example override via `.env`:
```env
DATABASE_URL=postgres://<user>:<password>@127.0.0.1:5432/cems_db
SECRET_KEY=<your-secret>
``` 
(You will need to add code that reads `.env` later in development.)

### Running the Server
1. Run migrations: `python manage.py migrate`
2. Create an admin user: `python manage.py createsuperuser`
3. Start the dev server: `python manage.py runserver`

## Next Steps
- Flesh out data models for classes, enrollments, grading, and exam sessions inside the placeholder apps.
- Implement authentication/authorization flows (custom user model, role-based access control).
- Build templates and static assets for dashboards, enrollment forms, and exam modules.

## Resources
- Django docs: https://docs.djangoproject.com/
- PostgreSQL docs: https://www.postgresql.org/docs/

