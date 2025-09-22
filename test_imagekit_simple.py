#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
os.environ.setdefault('USE_IMAGEKIT', 'true')
os.environ.setdefault('IMAGEKIT_PRIVATE_KEY', 'your_private_key')
os.environ.setdefault('IMAGEKIT_PUBLIC_KEY', 'your_public_key') 
os.environ.setdefault('IMAGEKIT_URL_ENDPOINT', 'https://ik.imagekit.io/dk360')

# Setup Django
django.setup()

from django.core.files.base import ContentFile
from assetms.storage_backends import ImageKitStorage

def test_imagekit():
    print("Testing ImageKit configuration...")
    
    # Check environment variables
    print(f"USE_IMAGEKIT: {os.environ.get('USE_IMAGEKIT')}")
    print(f"IMAGEKIT_URL_ENDPOINT: {os.environ.get('IMAGEKIT_URL_ENDPOINT')}")
    
    # Test storage initialization
    try:
        storage = ImageKitStorage()
        print("[OK] ImageKit storage initialized successfully")
    except Exception as e:
        print(f"[ERROR] ImageKit storage initialization failed: {e}")
        return
    
    # Test URL generation
    test_url = storage.url("test/image.jpg")
    print(f"[OK] Generated URL: {test_url}")
    
    print("\nImageKit configuration test completed!")

if __name__ == "__main__":
    test_imagekit()