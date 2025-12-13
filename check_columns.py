import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users_user' 
        AND (
            column_name LIKE '%email%' 
            OR column_name LIKE '%system%' 
            OR column_name LIKE '%onboarding%'
        )
        ORDER BY column_name;
    """)
    
    columns = [row[0] for row in cursor.fetchall()]
    
    print("Existing columns:")
    for col in columns:
        print(f"  ✓ {col}")
    
    print("\nExpected columns:")
    expected = [
        'email',
        'email_verified',
        'email_verification_token',
        'email_verification_sent_at',
        'is_system_admin',
        'onboarding_completed'
    ]
    
    for col in expected:
        if col in columns:
            print(f"  ✓ {col}")
        else:
            print(f"  ✗ {col} (MISSING)")
