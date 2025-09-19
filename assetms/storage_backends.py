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
            # Read file content
            file_content = content.read()
            
            # Upload to ImageKit
            result = self.imagekit.upload_file(
                file=file_content,
                file_name=name,
                options={
                    'folder': '/media/',
                    'is_private_file': False,
                    'use_unique_file_name': False,
                    'response_fields': ['name', 'size', 'file_path', 'url', 'file_id']
                }
            )
            
            # Return the file path for URL generation
            file_path = result.response_metadata.raw.get('file_path', name)
            logger.info(f"ImageKit upload successful: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"ImageKit upload failed: {e}")
            raise
    
    def url(self, name):
        if not name:
            return ''
        endpoint = os.environ.get('IMAGEKIT_URL_ENDPOINT', '').rstrip('/')
        # Ensure name starts with / for proper URL construction
        if not name.startswith('/'):
            name = '/' + name
        return f"{endpoint}{name}"
    
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
    
    def __init__(self, location=None):
        self.use_imagekit = os.environ.get('USE_IMAGEKIT', 'False').lower() == 'true'
        self.use_b2 = os.environ.get('USE_B2', 'False').lower() == 'true'
        
        # Initialize storage backends
        self.imagekit_storage = ImageKitStorage() if self.use_imagekit else None
        self.b2_storage = BackblazeB2Storage() if self.use_b2 else None
        self.local_storage = FileSystemStorage(location=location)
    
    def save(self, name, content, max_length=None):
        """Save file with fallback strategy"""
        # Reset content position for multiple reads
        if hasattr(content, 'seek'):
            content.seek(0)
        
        # Primary: ImageKit
        if self.use_imagekit and self.imagekit_storage:
            try:
                # Create a copy of content for ImageKit
                content_copy = ContentFile(content.read())
                content_copy.name = name
                result = self.imagekit_storage.save(name, content_copy)
                logger.info(f"File uploaded to ImageKit: {result}")
                return result
            except Exception as e:
                logger.warning(f"ImageKit failed, falling back to B2: {e}")
                # Reset content position for fallback
                if hasattr(content, 'seek'):
                    content.seek(0)
        
        # Fallback: Backblaze B2
        if self.use_b2 and self.b2_storage:
            try:
                result = self.b2_storage.save(name, content, max_length)
                logger.info(f"File uploaded to B2: {result}")
                return result
            except Exception as e:
                logger.warning(f"B2 failed, falling back to local: {e}")
        
        # Final fallback: Local storage
        result = self.local_storage.save(name, content, max_length)
        logger.info(f"File saved locally: {result}")
        return result
    
    def url(self, name):
        """Get URL with priority order"""
        if not name:
            return ''
            
        # ImageKit URLs (primary)
        if self.use_imagekit and self.imagekit_storage:
            return self.imagekit_storage.url(name)
        
        # B2 URLs (fallback)
        if self.use_b2 and self.b2_storage:
            return f"https://f002.backblazeb2.com/file/{os.environ.get('B2_BUCKET_NAME')}/{name}"
        
        # Local URLs (final fallback)
        return self.local_storage.url(name)
    
    def exists(self, name):
        """Check if file exists in any storage"""
        if self.use_imagekit and self.imagekit_storage:
            return False  # Always allow new uploads to ImageKit
        
        if self.use_b2 and self.b2_storage:
            try:
                return self.b2_storage.exists(name)
            except:
                return False
        
        return self.local_storage.exists(name)
    
    def size(self, name):
        """Get file size"""
        if self.use_b2 and self.b2_storage:
            try:
                return self.b2_storage.size(name)
            except:
                pass
        return self.local_storage.size(name)
    
    def get_valid_name(self, name):
        """Get valid filename"""
        return self.local_storage.get_valid_name(name)
    
    def get_available_name(self, name, max_length=None):
        """Get available filename"""
        return self.local_storage.get_available_name(name, max_length)
    
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