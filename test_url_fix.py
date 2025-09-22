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
    img = Image.new('RGB', (100, 100), color='blue')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return img_io.getvalue()

def test_url_generation():
    print("Testing Cloudinary URL generation fix...")
    
    # Create test image
    image_data = create_test_image()
    test_file = ContentFile(image_data, name="url_test.jpg")
    
    storage = CloudinaryStorage()
    
    try:
        # Upload file
        result = storage.save("profile_images/url_test.jpg", test_file)
        print(f"Upload result: {result}")
        
        # Generate URL
        url = storage.url(result)
        print(f"Generated URL: {url}")
        
        # Check URL format
        if url and "res.cloudinary.com" in url and "/v" in url:
            print("SUCCESS: URL contains version parameter")
            print(f"Test this URL: {url}")
        else:
            print("ERROR: URL missing version parameter")
            
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    test_url_generation()