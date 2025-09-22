from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from assetms.storage_backends import ImageKitStorage
import os

class Command(BaseCommand):
    help = 'Test ImageKit upload functionality'

    def handle(self, *args, **options):
        if not os.environ.get('USE_IMAGEKIT', 'False').lower() == 'true':
            self.stdout.write(self.style.ERROR('ImageKit not enabled. Set USE_IMAGEKIT=true'))
            return

        # Test ImageKit configuration
        storage = ImageKitStorage()
        
        # Create a test file
        test_content = b"Test file content for ImageKit upload"
        test_file = ContentFile(test_content, name="test_upload.txt")
        
        try:
            # Test upload
            result = storage.save("test_upload.txt", test_file)
            self.stdout.write(self.style.SUCCESS(f'Upload successful: {result}'))
            
            # Test URL generation
            url = storage.url(result)
            self.stdout.write(self.style.SUCCESS(f'Generated URL: {url}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Upload failed: {e}'))