#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
os.environ.setdefault('USE_CLOUDINARY', 'true')
os.environ.setdefault('CLOUDINARY_CLOUD_NAME', 'ds0ekfqye')

# You need to set these with your actual credentials
if not os.environ.get('CLOUDINARY_API_KEY'):
    print("ERROR: Set CLOUDINARY_API_KEY environment variable")
    sys.exit(1)
if not os.environ.get('CLOUDINARY_API_SECRET'):
    print("ERROR: Set CLOUDINARY_API_SECRET environment variable")
    sys.exit(1)

django.setup()

from django.core.files.base import ContentFile
from assetms.storage_backends import CloudinaryStorage
import cloudinary

def test_cloudinary_real():
    print("Testing Cloudinary with real credentials...")
    
    # Test configuration
    config = cloudinary.config()
    print(f"Cloud name: {config.cloud_name}")
    print(f"API key: {config.api_key[:4]}***")
    
    # Test storage
    storage = CloudinaryStorage()
    
    # Create test file
    test_content = b"Test image content for Cloudinary"
    test_file = ContentFile(test_content, name="test_image.txt")
    
    try:
        # Test upload
        result = storage.save("profile_images/test_upload.txt", test_file)
        print(f"Upload result: {result}")
        
        # Test URL generation
        url = storage.url(result)
        print(f"Generated URL: {url}")
        
        # Verify URL format
        if url and "res.cloudinary.com" in url and "ds0ekfqye" in url:
            print("[OK] URL format is correct")
        else:
            print("[ERROR] URL format is incorrect")
            
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")

if __name__ == "__main__":
    test_cloudinary_real()