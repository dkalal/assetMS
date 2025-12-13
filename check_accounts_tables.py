import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' 
        AND table_name LIKE '%invitation%' 
        OR table_name LIKE '%registration%' 
        OR table_name LIKE '%onboarding%'
        ORDER BY table_name;
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    print("Existing accounts tables:")
    for table in tables:
        print(f"  ✓ {table}")
    
    print("\nExpected tables:")
    expected = [
        'user_invitations',
        'company_registrations',
        'onboarding_progress'
    ]
    
    for table in expected:
        if table in tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} (MISSING)")
