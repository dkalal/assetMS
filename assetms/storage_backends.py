"""
Professional multi-storage backend with ImageKit primary and Backblaze B2 fallback
"""
import os
import logging
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from imagekitio import ImageKit
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)

class ImageKitStorage:
    """ImageKit storage backend"""
    
    def __init__(self):
        self.imagekit = ImageKit(
            private_key=os.environ.get('IMAGEKIT_PRIVATE_KEY'),
            public_key=os.environ.get('IMAGEKIT_PUBLIC_KEY'),
            url_endpoint=os.environ.get('IMAGEKIT_URL_ENDPOINT')
        )
    
    def save(self, name, content):
        try:
            result = self.imagekit.upload_file(
                file=content.read(),
                file_name=name,
                options={
                    'folder': '/media/',
                    'is_private_file': False,
                    'use_unique_file_name': True,
                    'response_fields': ['name', 'size', 'file_path', 'url', 'file_id']
                }
            )
            return result.response_metadata.raw['file_path']
        except Exception as e:
            logger.error(f"ImageKit upload failed: {e}")
            raise
    
    def url(self, name):
        return f"{os.environ.get('IMAGEKIT_URL_ENDPOINT')}{name}"
    
    def exists(self, name):
        return False  # Always allow new uploads
    
    def delete(self, name):
        try:
            file_id = name.split('/')[-1].split('.')[0]
            self.imagekit.delete_file(file_id)
        except Exception as e:
            logger.error(f"ImageKit delete failed: {e}")

class BackblazeB2Storage(S3Boto3Storage):
    """Backblaze B2 storage backend"""
    
    def __init__(self):
        super().__init__()
        self.access_key = os.environ.get('B2_APPLICATION_KEY_ID')
        self.secret_key = os.environ.get('B2_APPLICATION_KEY')
        self.bucket_name = os.environ.get('B2_BUCKET_NAME')
        self.region_name = os.environ.get('B2_BUCKET_REGION', 'us-east-005')
        self.endpoint_url = f"https://s3.{self.region_name}.backblazeb2.com"
        self.default_acl = 'public-read'
        self.querystring_auth = False

class MultiStorageBackend:
    """
    Professional multi-storage backend with ImageKit primary and B2 fallback
    """
    
    def __init__(self):
        self.use_imagekit = os.environ.get('USE_IMAGEKIT', 'False').lower() == 'true'
        self.use_b2 = os.environ.get('USE_B2', 'False').lower() == 'true'
        
        # Initialize storage backends
        self.imagekit_storage = ImageKitStorage() if self.use_imagekit else None
        self.b2_storage = BackblazeB2Storage() if self.use_b2 else None
        self.local_storage = FileSystemStorage()
    
    def save(self, name, content):
        """Save file with fallback strategy"""
        # Primary: ImageKit
        if self.use_imagekit and self.imagekit_storage:
            try:
                return self.imagekit_storage.save(name, content)
            except Exception as e:
                logger.warning(f"ImageKit failed, falling back to B2: {e}")
        
        # Fallback: Backblaze B2
        if self.use_b2 and self.b2_storage:
            try:
                return self.b2_storage.save(name, content)
            except Exception as e:
                logger.warning(f"B2 failed, falling back to local: {e}")
        
        # Final fallback: Local storage
        return self.local_storage.save(name, content)
    
    def url(self, name):
        """Get URL with priority order"""
        if self.use_imagekit and self.imagekit_storage and name.startswith('/media/'):
            return self.imagekit_storage.url(name)
        
        if self.use_b2 and self.b2_storage:
            return f"https://f002.backblazeb2.com/file/{os.environ.get('B2_BUCKET_NAME')}/{name}"
        
        return self.local_storage.url(name)
    
    def exists(self, name):
        return False  # Always allow uploads
    
    def delete(self, name):
        """Delete from all storages"""
        if self.use_imagekit and self.imagekit_storage:
            try:
                self.imagekit_storage.delete(name)
            except Exception as e:
                logger.error(f"ImageKit delete failed: {e}")
        
        if self.use_b2 and self.b2_storage:
            try:
                self.b2_storage.delete(name)
            except Exception as e:
                logger.error(f"B2 delete failed: {e}")
        
        try:
            self.local_storage.delete(name)
        except Exception as e:
            logger.error(f"Local delete failed: {e}")