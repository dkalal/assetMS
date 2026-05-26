#!/bin/bash
set -e
echo "🚀 Starting Django application..."
echo "⏳ Waiting for database..."
python - <<'EOF'
import os, time
import psycopg2
from urllib.parse import urlparse

if 'DATABASE_URL' in os.environ:
    url = urlparse(os.environ['DATABASE_URL'])
    for i in range(30):
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
        except psycopg2.OperationalError:
            print(f"Database not ready, waiting... ({i+1}/30)")
            time.sleep(2)
    else:
        print("❌ Database connection timeout")
        exit(1)
else:
    print("⚠️  No DATABASE_URL found, skipping database check")
EOF
echo "⚙️ Running database migrations..."
python manage.py migrate --noinput
echo "📁 Creating media directories..."
mkdir -p media/qr_codes media/profile_images media/asset_images media/asset_docs media/reports
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "📋 Copying media files to static..."
cp -r media/* staticfiles/media/ 2>/dev/null || true
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
PORT=${PORT:-8001}
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
