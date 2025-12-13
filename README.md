# Enterprise Asset Management System (Django)

A production-ready, modular Enterprise Asset Management System built with Django 5.

## Features
- Role-based access control (admin/manager/user)
- Enterprise session management and CSRF hardening
- Comprehensive audit logging and reporting
- Responsive UI (Bootstrap 5), real-time search, optimized queries
- Import/Export, UUID-based assets, dynamic categories
- Maintenance scheduling & history with tenant-aware workflows

## Tech Stack
- Python 3.12+, Django 5
- SQLite (dev) / PostgreSQL (prod-ready)
- Bootstrap 5, modern JS

## Quick Start
```bash
# 1) Create & activate venv (Windows)
python -m venv venv
venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure environment
# Create a .env based on your environment. Do NOT commit secrets.
# Ensure DEBUG, SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS, EMAIL settings as needed.

# 4) Run migrations and start server
python manage.py migrate
python manage.py runserver
```

## Multi-Tenant Categories
- Asset categories and dynamic fields are now scoped per company. `AssetCategory` and `AssetCategoryField` records require a `company` FK and are filtered through tenant-aware querysets.
- Category CRUD APIs and forms automatically bind to `request.company`; ensure middleware (`tenancy/middleware.py`) is active so requests populate `request.company`/`request.branch`.
- Legacy or pre-existing categories are migrated via `assets/migrations/0012_assetcategory_company_assetcategoryfield_company.py`, which backfills company ownership and clones cross-company data where required.
- When creating assets programmatically, always set `company` on the asset and choose categories that belong to the same company to avoid validation errors.

### Branch Selector Expectations
- The top navigation branch selector renders the authenticated user's `UserBranch` memberships supplied by `tenancy/context_processors.py`.
- `TenancyMiddleware` hydrates `request.available_branches` so the selector only lists branches within the active company.
- When no explicit branch is in session, the context processor promotes the user's primary branch (or first membership) to keep the UI consistent.
- `tenancy/views.py::switch_branch()` validates company ownership before persisting the `active_branch_id` in session, ensuring strict multi-tenant isolation.

## Testing & Quality
```bash
python manage.py check
python manage.py test assets.tests.test_maintenance
python manage.py test assets.tests.test_categories_tenancy
pytest -q
```

Tenant regression coverage lives in `assets/tests/test_categories_tenancy.py`; run it whenever category or field logic changes to confirm cross-company isolation.

## Security & Hardening
- Secrets in `.env` (ignored by Git)
- Security headers, XSS/CSRF protections
- Account lockout, failed login tracking
- Strong session controls with audit trail

## Deployment
- Collect static with WhiteNoise or S3
- Use PostgreSQL in production
- See `DEPLOYMENT_GUIDE.md`

## Maintenance Workflow
- Managers and admins schedule and track maintenance from `/maintenance/` (site UI, not Django admin).
- `MaintenanceService` enforces tenant scoping, audit logging, and alert notifications; see `assets/services/maintenance.py`.
- Forms in `assets/forms.py` and views in `tenancy/maintenance_views.py` provide scheduling, start, completion, and cancellation flows with role checks.
- Dashboard and reporting surfaces highlight upcoming, overdue, and completed maintenance for enhanced operational visibility.

## License
Copyright © 2025. All rights reserved.
