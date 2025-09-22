#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
os.environ.setdefault('USE_CLOUDINARY', 'true')
os.environ.setdefault('CLOUDINARY_CLOUD_NAME', 'ds0ekfqye')
os.environ.setdefault('CLOUDINARY_API_KEY', 'test_key')
os.environ.setdefault('CLOUDINARY_API_SECRET', 'test_secret')
django.setup()

from django.core.files.base import ContentFile
from assetms.storage_backends import CloudinaryStorage

def test_cloudinary():
    print("Testing Cloudinary configuration...")
    
    # Test storage initialization
    try:
        storage = CloudinaryStorage()
        print("[OK] Cloudinary storage initialized")
    except Exception as e:
        print(f"[ERROR] Cloudinary initialization failed: {e}")
        return
    
    # Test URL generation
    test_url = storage.url("media/test_image.jpg")
    print(f"[OK] Generated URL: {test_url}")
    
    # Verify URL format
    if "res.cloudinary.com" in test_url:
        print("[OK] URL format is correct")
    else:
        print("[ERROR] URL format is incorrect")

if __name__ == "__main__":
    test_cloudinary()