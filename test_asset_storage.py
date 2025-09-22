#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from assets.models import Asset
from assetms.storage_backends import MultiStorageBackend

def test_asset_storage():
    print("Testing Asset model storage configuration...")
    
    # Check Asset model field storage
    asset = Asset()
    images_field = asset._meta.get_field('images')
    
    print(f"Images field storage: {images_field.storage}")
    print(f"Storage type: {type(images_field.storage)}")
    
    # Check if it's using MultiStorageBackend
    if isinstance(images_field.storage, MultiStorageBackend):
        print("SUCCESS: Asset images using MultiStorageBackend")
        storage = images_field.storage
        print(f"Cloudinary enabled: {storage.use_cloudinary}")
    else:
        print("ERROR: Asset images NOT using MultiStorageBackend")

if __name__ == "__main__":
    test_asset_storage()