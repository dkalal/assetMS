#!/usr/bin/env python
import os
import sys
import time
import subprocess
from urllib.parse import urlparse
import psycopg2

def wait_for_db():
    if 'DATABASE_URL' not in os.environ:
        print("⚠️  No DATABASE_URL, skipping database check")
        return

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
            return
        except psycopg2.OperationalError:
            print(f"Database not ready, waiting... ({i+1}/30)")
            time.sleep(2)
    
    print("❌ Database connection timeout")
    sys.exit(1)

def run_migrations():
    subprocess.run(['python', 'manage.py', 'migrate', '--noinput'], check=False)

def collect_static():
    subprocess.run(['python', 'manage.py', 'collectstatic', '--noinput', '--clear'], check=False)

def main():
    print("🚀 Starting Django application...")
    wait_for_db()
    print("⚙️ Running migrations...")
    run_migrations()
    print("📦 Collecting static files...")
    collect_static()
    
    port = os.environ.get('PORT', '8001')
    workers = os.environ.get('GUNICORN_WORKERS', '2')
    threads = os.environ.get('GUNICORN_THREADS', '4')
    
    print(f"🚦 Starting Gunicorn with {workers} workers × {threads} threads on port {port}...")
    
    subprocess.run([
        'gunicorn', 'assetms.wsgi:application',
        '--bind', f'0.0.0.0:{port}',
        '--workers', workers,
        '--threads', threads,
        '--worker-class', 'gthread',
        '--max-requests', '1000',
        '--max-requests-jitter', '100',
        '--timeout', '60',
        '--keep-alive', '5',
        '--log-level', 'info',
        '--access-logfile', '-',
        '--error-logfile', '-'
    ])

if __name__ == '__main__':
    main()
