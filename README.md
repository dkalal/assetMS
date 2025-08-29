# Enterprise Asset Management System (Django)

A production-ready, modular Enterprise Asset Management System built with Django 5.

## Features
- Role-based access control (admin/manager/user)
- Enterprise session management and CSRF hardening
- Comprehensive audit logging and reporting
- Responsive UI (Bootstrap 5), real-time search, optimized queries
- Import/Export, UUID-based assets, dynamic categories

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

## Testing & Quality
```bash
python manage.py check
pytest -q
```

## Security & Hardening
- Secrets in `.env` (ignored by Git)
- Security headers, XSS/CSRF protections
- Account lockout, failed login tracking
- Strong session controls with audit trail

## Deployment
- Collect static with WhiteNoise or S3
- Use PostgreSQL in production
- See `DEPLOYMENT_GUIDE.md`

## License
Copyright © 2025. All rights reserved.
