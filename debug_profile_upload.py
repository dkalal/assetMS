#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.conf import settings
from users.models import User
from assetms.storage_backends import MultiStorageBackend

def debug_storage_config():
    print("=== STORAGE CONFIGURATION DEBUG ===")
    print(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    print(f"USE_CLOUDINARY: {os.environ.get('USE_CLOUDINARY')}")
    print(f"USE_IMAGEKIT: {os.environ.get('USE_IMAGEKIT')}")
    print(f"USE_B2: {os.environ.get('USE_B2')}")
    
    # Test storage backend
    storage = MultiStorageBackend()
    print(f"Cloudinary enabled: {storage.use_cloudinary}")
    print(f"ImageKit enabled: {storage.use_imagekit}")
    print(f"B2 enabled: {storage.use_b2}")
    
    # Check User model field
    user = User.objects.first()
    if user:
        print(f"User profile_image field: {user._meta.get_field('profile_image')}")
        print(f"Current profile_image value: {user.profile_image}")
        
        # Check storage backend
        field = user._meta.get_field('profile_image')
        print(f"Field storage: {field.storage}")
        print(f"Field upload_to: {field.upload_to}")

if __name__ == "__main__":
    debug_storage_config()