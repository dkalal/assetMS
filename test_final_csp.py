#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def test_final_csp():
    print("Testing final CSP configuration...")
    
    client = Client()
    User = get_user_model()
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@example.com'}
    )
    
    # Test profile page
    response = client.get('/profile/', follow=True)
    
    print(f"Response status: {response.status_code}")
    csp = response.get('Content-Security-Policy', 'NOT SET')
    
    if 'res.cloudinary.com' in csp:
        print("SUCCESS: Cloudinary domains in CSP")
        print("Images should now load correctly!")
    else:
        print("ERROR: Cloudinary domains missing")
        print(f"CSP: {csp}")

if __name__ == "__main__":
    test_final_csp()