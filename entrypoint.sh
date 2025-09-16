#!/bin/bash

# Exit on any error
set -e

echo "Starting Django application..."

# Wait for database to be ready (optional, useful for docker-compose)
echo "Waiting for database..."
python -c "
import os
import time
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
            print('Database is ready!')
            break
        except psycopg2.OperationalError:
            print(f'Database not ready, waiting... ({i+1}/30)')
            time.sleep(2)
    else:
        print('Database connection timeout')
        exit(1)
else:
    print('No DATABASE_URL found, skipping database check')
"

# Run Django migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if specified (optional, for initial setup)
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
fi

# Calculate number of workers: (2 x CPU cores) + 1, with minimum of 3
WORKERS=${GUNICORN_WORKERS:-$(python -c "import multiprocessing; print(max(3, (2 * multiprocessing.cpu_count()) + 1))")}

echo "Starting Gunicorn with $WORKERS workers on port $PORT..."

# Start Gunicorn with proper signal handling (exec ensures proper signal forwarding)
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