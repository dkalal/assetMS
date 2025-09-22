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
from users.models import User

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (200, 200), color='green')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    return img_io.getvalue()

def test_profile_upload_simulation():
    print("Testing profile upload simulation...")
    
    # Get a user
    user = User.objects.first()
    if not user:
        print("No users found. Create a user first.")
        return
    
    print(f"Testing with user: {user.username}")
    
    # Create test image
    image_data = create_test_image()
    test_file = ContentFile(image_data, name="profile_test.jpg")
    
    try:
        # Simulate profile image upload
        user.profile_image.save("profile_test.jpg", test_file, save=True)
        
        print(f"Upload successful!")
        print(f"Stored value: {user.profile_image}")
        print(f"Generated URL: {user.profile_image.url}")
        
        # Check if it's in Cloudinary format
        if '|' in str(user.profile_image):
            print("SUCCESS: Using new Cloudinary format with version")
        else:
            print("WARNING: Not using new Cloudinary format")
            
    except Exception as e:
        print(f"Upload failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_profile_upload_simulation()