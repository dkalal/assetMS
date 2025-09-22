#!/usr/bin/env python
import os
import sys
import django
from PIL import Image
import io

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.core.files.base import ContentFile
from assetms.storage_backends import CloudinaryStorage

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return img_io.getvalue()

def test_real_image_upload():
    print("Testing real image upload to Cloudinary...")
    
    # Create test image
    image_data = create_test_image()
    test_file = ContentFile(image_data, name="test_profile.jpg")
    
    storage = CloudinaryStorage()
    
    try:
        result = storage.save("profile_images/test_profile.jpg", test_file)
        print(f"✓ Upload successful: {result}")
        
        url = storage.url(result)
        print(f"✓ Generated URL: {url}")
        
        # Verify URL is accessible
        if url and "res.cloudinary.com" in url:
            print("✓ URL format is correct")
            print(f"\nTest this URL in browser: {url}")
        else:
            print("✗ URL format is incorrect")
            
    except Exception as e:
        print(f"✗ Upload failed: {e}")

if __name__ == "__main__":
    test_real_image_upload()