from django.core.management.base import BaseCommand
from settings.models import SystemSetting

class Command(BaseCommand):
    help = 'Setup default system settings'

    def handle(self, *args, **options):
        default_settings = [
            {
                'key': 'site_name',
                'value': 'Asset Management System',
                'setting_type': 'string',
                'description': 'Name of the application',
                'category': 'general',
                'is_public': True
            },
            {
                'key': 'max_file_upload_size',
                'value': '10485760',
                'setting_type': 'integer',
                'description': 'Maximum file upload size in bytes (10MB)',
                'category': 'system',
                'is_public': False
            },
            {
                'key': 'enable_notifications',
                'value': 'true',
                'setting_type': 'boolean',
                'description': 'Enable system notifications',
                'category': 'notifications',
                'is_public': False
            },
            {
                'key': 'backup_retention_days',
                'value': '30',
                'setting_type': 'integer',
                'description': 'Number of days to retain backups',
                'category': 'backup',
                'is_public': False
            }
        ]

        created_count = 0
        for setting_data in default_settings:
            setting, created = SystemSetting.objects.get_or_create(
                key=setting_data['key'],
                defaults=setting_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created setting: {setting.key}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Setup complete. Created {created_count} new settings.')
        )