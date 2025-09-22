"""
Professional multi-storage backend with ImageKit primary and Backblaze B2 fallback
"""
import os
import logging
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from imagekitio import ImageKit
from storages.backends.s3boto3 import S3Boto3Storage
import cloudinary
import cloudinary.uploader
from django.core.files.storage import Storage

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
            import base64
            
            # Read and encode file content
            file_content = content.read()
            logger.info(f"Uploading to ImageKit: {name}, size: {len(file_content)} bytes")
            
            # Upload to ImageKit with proper API format
            result = self.imagekit.upload_file(
                file=file_content,  # Use raw bytes, not base64
                file_name=name,
                options={
                    'folder': '/media/',
                    'is_private_file': False,
                    'use_unique_file_name': False
                }
            )
            
            logger.info(f"ImageKit response: {result.__dict__ if hasattr(result, '__dict__') else result}")
            
            # Get the actual file path from response
            if hasattr(result, 'file_path'):
                file_path = result.file_path
            elif hasattr(result, 'response_metadata') and result.response_metadata.raw:
                file_path = result.response_metadata.raw.get('filePath', name)
            else:
                file_path = f"/media/{name}"
            
            logger.info(f"ImageKit upload successful: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"ImageKit upload failed for {name}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def url(self, name):
        if not name:
            return ''
        endpoint = os.environ.get('IMAGEKIT_URL_ENDPOINT', '').rstrip('/')
        # Clean the name path
        clean_name = name.lstrip('/')
        return f"{endpoint}/{clean_name}"
    
    def exists(self, name):
        return False  # Always allow new uploads
    
    def delete(self, name):
        try:
            # Extract file_id from ImageKit response or use name
            file_id = name.split('/')[-1].split('.')[0]
            self.imagekit.delete_file(file_id)
        except Exception as e:
            logger.error(f"ImageKit delete failed: {e}")

class CloudinaryStorage(Storage):
    """Cloudinary storage backend following official documentation"""
    
    def __init__(self):
        cloudinary.config(
            cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
            api_key=os.environ.get('CLOUDINARY_API_KEY'),
            api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
            secure=True
        )
    
    def save(self, name, content):
        try:
            # Extract folder and filename from Django upload path
            folder = os.path.dirname(name) or "uploads"
            filename = os.path.basename(name)
            public_id = os.path.splitext(filename)[0]
            
            logger.info(f"Uploading to Cloudinary - folder: {folder}, filename: {filename}")
            
            # Determine resource type based on file extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                resource_type = "image"
            elif file_ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']:
                resource_type = "video"
            else:
                resource_type = "raw"
            
            result = cloudinary.uploader.upload(
                content,
                public_id=public_id,
                folder=folder,
                use_filename=True,
                unique_filename=True,
                resource_type=resource_type
            )
            
            logger.info(f"Cloudinary upload successful: {result['public_id']}")
            logger.info(f"Secure URL: {result['secure_url']}")
            
            # Store the complete URL for proper access
            # Return format: "public_id|version|resource_type|format"
            return f"{result['public_id']}|{result['version']}|{result['resource_type']}|{result['format']}"
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed for {name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def url(self, name):
        if not name:
            return ''
        try:
            # Handle stored format: "public_id|version|resource_type|format"
            if '|' in name:
                parts = name.split('|')
                public_id = parts[0]
                version = parts[1] if len(parts) > 1 else None
                resource_type = parts[2] if len(parts) > 2 else 'image'
                file_format = parts[3] if len(parts) > 3 else None
                
                # Build URL with version
                url_params = {'secure': True}
                if version:
                    url_params['version'] = version
                if file_format:
                    url_params['format'] = file_format
                    
                return cloudinary.CloudinaryImage(public_id).build_url(**url_params)
            else:
                # Fallback for old format
                return cloudinary.CloudinaryImage(name).build_url(secure=True)
        except Exception as e:
            logger.error(f"Failed to generate URL for {name}: {e}")
            return ''
    
    def exists(self, name):
        return False  # Always allow uploads
    
    def delete(self, name):
        try:
            # Handle stored format: "public_id|version|resource_type|format"
            if '|' in name:
                public_id = name.split('|')[0]
            else:
                public_id = name
            cloudinary.uploader.destroy(public_id)
        except Exception as e:
            logger.error(f"Cloudinary delete failed: {e}")
    
    def size(self, name):
        return 0

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
        self.use_cloudinary = os.environ.get('USE_CLOUDINARY', 'False').lower() == 'true'
        self.use_imagekit = os.environ.get('USE_IMAGEKIT', 'False').lower() == 'true'
        self.use_b2 = os.environ.get('USE_B2', 'False').lower() == 'true'
        
        # Initialize storage backends
        self.cloudinary_storage = CloudinaryStorage() if self.use_cloudinary else None
        self.imagekit_storage = ImageKitStorage() if self.use_imagekit else None
        self.b2_storage = BackblazeB2Storage() if self.use_b2 else None
        self.local_storage = FileSystemStorage(location=location)
    
    def save(self, name, content, max_length=None):
        """Save file with fallback strategy"""
        # Reset content position for multiple reads
        if hasattr(content, 'seek'):
            content.seek(0)
        
        # Primary: Cloudinary
        if self.use_cloudinary and self.cloudinary_storage:
            try:
                content_copy = ContentFile(content.read())
                content_copy.name = name
                result = self.cloudinary_storage.save(name, content_copy)
                logger.info(f"File uploaded to Cloudinary: {result}")
                return result
            except Exception as e:
                logger.warning(f"Cloudinary failed, falling back to ImageKit: {e}")
                if hasattr(content, 'seek'):
                    content.seek(0)
        
        # Fallback: ImageKit
        if self.use_imagekit and self.imagekit_storage:
            try:
                content_copy = ContentFile(content.read())
                content_copy.name = name
                result = self.imagekit_storage.save(name, content_copy)
                logger.info(f"File uploaded to ImageKit: {result}")
                return result
            except Exception as e:
                logger.warning(f"ImageKit failed, falling back to B2: {e}")
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
            
        # Cloudinary URLs (primary)
        if self.use_cloudinary and self.cloudinary_storage:
            return self.cloudinary_storage.url(name)
            
        # ImageKit URLs (fallback)
        if self.use_imagekit and self.imagekit_storage:
            return self.imagekit_storage.url(name)
        
        # B2 URLs (fallback)
        if self.use_b2 and self.b2_storage:
            return f"https://f002.backblazeb2.com/file/{os.environ.get('B2_BUCKET_NAME')}/{name}"
        
        # Local URLs (final fallback)
        return self.local_storage.url(name)
    
    def exists(self, name):
        """Check if file exists in any storage"""
        if self.use_cloudinary and self.cloudinary_storage:
            return False  # Always allow new uploads to Cloudinary
            
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
    
    def generate_filename(self, filename):
        """Generate filename for upload"""
        return self.local_storage.generate_filename(filename)
    
    def path(self, name):
        """Get local path (fallback only)"""
        return self.local_storage.path(name)
    
    def accessed_time(self, name):
        """Get accessed time (fallback only)"""
        return self.local_storage.accessed_time(name)
    
    def created_time(self, name):
        """Get created time (fallback only)"""
        return self.local_storage.created_time(name)
    
    def modified_time(self, name):
        """Get modified time (fallback only)"""
        return self.local_storage.modified_time(name)
    
    def open(self, name, mode='rb'):
        """Open file (fallback only)"""
        return self.local_storage.open(name, mode)
    
    def delete(self, name):
        """Delete from all storages"""
        if self.use_cloudinary and self.cloudinary_storage:
            try:
                self.cloudinary_storage.delete(name)
            except Exception as e:
                logger.error(f"Cloudinary delete failed: {e}")
                
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