#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Django application..."

# --- Database readiness check (Railway optimized) ---
echo "⏳ Waiting for database..."
python - <<'EOF'
import os, time
import sys

if 'DATABASE_URL' in os.environ:
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        url = urlparse(os.environ['DATABASE_URL'])
        for i in range(60):  # Increased timeout for Railway
            try:
                conn = psycopg2.connect(
                    host=url.hostname,
                    port=url.port or 5432,
                    user=url.username,
                    password=url.password,
                    database=url.path[1:]
                )
                conn.close()
                print("✅ Database is ready!")
                break
            except psycopg2.OperationalError as e:
                print(f"Database not ready, waiting... ({i+1}/60) - {str(e)[:100]}")
                time.sleep(3)  # Slightly longer wait
        else:
            print("❌ Database connection timeout after 3 minutes")
            sys.exit(1)
    except ImportError:
        print("⚠️  psycopg2 not available, skipping database check")
else:
    print("⚠️  No DATABASE_URL found, using SQLite")
EOF

# --- Django migrations ---
echo "⚙️ Running database migrations..."
python manage.py migrate --noinput

# --- Ensure media directories exist ---
echo "📁 Creating media directories..."
mkdir -p media/qr_codes media/profile_images media/asset_images media/asset_docs media/reports

# --- Collect static files ---
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear

# --- Copy media to staticfiles for WhiteNoise ---
echo "📋 Copying media files to static..."
cp -r media/* staticfiles/media/ 2>/dev/null || true

# --- Create superuser (if env vars provided) ---
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "👤 Ensuring superuser exists..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser(
        '$DJANGO_SUPERUSER_USERNAME',
        '$DJANGO_SUPERUSER_EMAIL',
        '$DJANGO_SUPERUSER_PASSWORD'
    )
    print('✅ Superuser created')
else:
    print('ℹ️  Superuser already exists')
"
fi

# --- Gunicorn start ---
PORT=${PORT:-8000}

# OOM-SAFE: Default to 2 workers, 4 threads unless overridden
WORKERS=${GUNICORN_WORKERS:-2}
THREADS=${GUNICORN_THREADS:-4}

echo "🚦 Starting Gunicorn with $WORKERS workers × $THREADS threads on port $PORT..."

exec gunicorn assetms.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers $WORKERS \
    --threads $THREADS \
    --worker-class gthread \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 60 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output
