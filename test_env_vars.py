#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

import cloudinary
from django.core.files.base import ContentFile
from assetms.storage_backends import CloudinaryStorage

def test_env_and_upload():
    print("Environment Variables:")
    print(f"USE_CLOUDINARY: {os.environ.get('USE_CLOUDINARY')}")
    print(f"CLOUDINARY_CLOUD_NAME: {os.environ.get('CLOUDINARY_CLOUD_NAME')}")
    print(f"CLOUDINARY_API_KEY: {os.environ.get('CLOUDINARY_API_KEY')}")
    print(f"CLOUDINARY_API_SECRET: {'***' if os.environ.get('CLOUDINARY_API_SECRET') else 'Not set'}")
    
    # Test Cloudinary config
    config = cloudinary.config()
    print(f"\nCloudinary Config:")
    print(f"Cloud name: {config.cloud_name}")
    print(f"API key: {config.api_key}")
    
    # Test actual upload
    print("\nTesting upload...")
    storage = CloudinaryStorage()
    test_file = ContentFile(b"Test profile image", name="test_profile.jpg")
    
    try:
        result = storage.save("profile_images/test_profile.jpg", test_file)
        print(f"Upload successful: {result}")
        
        url = storage.url(result)
        print(f"Generated URL: {url}")
        
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    test_env_and_upload()