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

def test_asset_register_csp():
    print("Testing CSP on asset register page...")
    
    client = Client()
    User = get_user_model()
    
    # Get or create admin user
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@example.com', 'role': 'admin'}
    )
    if created:
        user.set_password('admin')
        user.save()
    
    # Login
    client.login(username='admin', password='admin')
    
    # Test asset register page
    response = client.get('/assets/register/', follow=True)
    
    print(f"Response status: {response.status_code}")
    csp = response.get('Content-Security-Policy', 'NOT SET')
    
    if 'res.cloudinary.com' in csp:
        print("SUCCESS: Asset register page has correct CSP")
        print("Cloudinary images should work")
    else:
        print("ERROR: Asset register page missing Cloudinary CSP")
        print(f"CSP: {csp[:100]}...")

if __name__ == "__main__":
    test_asset_register_csp()