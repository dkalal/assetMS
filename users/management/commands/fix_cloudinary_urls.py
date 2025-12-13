from django.core.management.base import BaseCommand
from users.models import User
import cloudinary

class Command(BaseCommand):
    help = 'Fix existing Cloudinary URLs to include version parameters'

    def handle(self, *args, **options):
        users_with_images = User.objects.exclude(profile_image='')
        
        for user in users_with_images:
            old_path = str(user.profile_image)
            
            # Skip if already in new format
            if '|' in old_path:
                continue
                
            # Clear old format URLs that won't work
            if 'cloudinary.com' in old_path or old_path.startswith('profile_images/'):
                user.profile_image = ''
                user.save()
                self.stdout.write(f'Cleared invalid URL for user: {user.username}')
        
        self.stdout.write(self.style.SUCCESS('Fixed Cloudinary URLs. Users need to re-upload profile images.'))