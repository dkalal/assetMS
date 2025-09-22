#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')

# Set test credentials - replace with your actual ones
os.environ.setdefault('USE_CLOUDINARY', 'true')
os.environ.setdefault('CLOUDINARY_CLOUD_NAME', 'ds0ekfqye')
os.environ.setdefault('CLOUDINARY_API_KEY', 'your_api_key')
os.environ.setdefault('CLOUDINARY_API_SECRET', 'your_api_secret')

django.setup()

import cloudinary
from django.core.files.base import ContentFile
from assetms.storage_backends import CloudinaryStorage

def test_cloudinary_direct():
    """Test direct Cloudinary upload following documentation"""
    print("Testing direct Cloudinary upload...")
    
    # Test configuration
    config = cloudinary.config()
    print(f"Cloud name: {config.cloud_name}")
    
    if not config.api_key or config.api_key == 'your_api_key':
        print("ERROR: Set actual CLOUDINARY_API_KEY")
        return
    
    # Test direct upload (following documentation)
    try:
        test_content = b"Test image content"
        result = cloudinary.uploader.upload(
            test_content,
            public_id="test_direct_upload",
            use_filename=True,
            unique_filename=True,
            resource_type="auto"
        )
        
        print(f"Direct upload successful!")
        print(f"Public ID: {result['public_id']}")
        print(f"Secure URL: {result['secure_url']}")
        
        # Test URL generation
        url = cloudinary.CloudinaryImage(result['public_id']).build_url(secure=True)
        print(f"Generated URL: {url}")
        
        return result['public_id']
        
    except Exception as e:
        print(f"Direct upload failed: {e}")
        return None

def test_storage_backend():
    """Test our storage backend"""
    print("\nTesting storage backend...")
    
    storage = CloudinaryStorage()
    test_file = ContentFile(b"Test content", name="test_storage.txt")
    
    try:
        result = storage.save("test_storage.txt", test_file)
        print(f"Storage upload successful: {result}")
        
        url = storage.url(result)
        print(f"Storage URL: {url}")
        
    except Exception as e:
        print(f"Storage upload failed: {e}")

if __name__ == "__main__":
    test_cloudinary_direct()
    test_storage_backend()