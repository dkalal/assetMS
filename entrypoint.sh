#!/bin/bash
set -e

echo "🚀 Starting Django application..."

# Wait for database if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
  echo "⏳ Waiting for database..."
  python - <<'PYCODE'
import os, time, psycopg2
from urllib.parse import urlparse

url = urlparse(os.environ["DATABASE_URL"])
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
        print(f"Database not ready, retrying... ({i+1}/30)")
        time.sleep(2)
else:
    print("❌ Database connection timeout")
    exit(1)
PYCODE
else
  echo "⚠️ No DATABASE_URL found, skipping database wait"
fi

# Run migrations
echo "⚙️ Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if env vars provided
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "👤 Creating superuser..."
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
    print('ℹ️ Superuser already exists')
"
fi

# Set PORT (Railway provides it automatically)
PORT=${PORT:-8000}

# Auto-calc Gunicorn workers
WORKERS=${GUNICORN_WORKERS:-$(python -c "import multiprocessing; print(max(3, (2 * multiprocessing.cpu_count()) + 1))")}

echo "🚀 Starting Gunicorn with $WORKERS workers on port $PORT..."

exec gunicorn assetms.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers $WORKERS \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30 \
    --keep-alive 2 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output
