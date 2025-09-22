from django.core.management.base import BaseCommand
from users.models import User

class Command(BaseCommand):
    help = 'Clear cached profile images to force new uploads'

    def handle(self, *args, **options):
        users_with_images = User.objects.exclude(profile_image='')
        count = users_with_images.count()
        
        if count > 0:
            users_with_images.update(profile_image='')
            self.stdout.write(self.style.SUCCESS(f'Cleared {count} profile images'))
        else:
            self.stdout.write(self.style.SUCCESS('No profile images to clear'))