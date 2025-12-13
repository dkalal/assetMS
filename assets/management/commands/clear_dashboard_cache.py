"""
Management command to clear dashboard cache.

Usage:
    python manage.py clear_dashboard_cache
    
This is useful when dashboard metrics are stale or incorrect.
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Clear dashboard cache to refresh metrics'

    def handle(self, *args, **options):
        """Clear the dashboard cache."""
        self.stdout.write('Clearing dashboard cache...')
        
        try:
            # Clear all cache
            cache.clear()
            
            self.stdout.write(self.style.SUCCESS(
                '✅ Dashboard cache cleared successfully!'
            ))
            self.stdout.write(
                'Dashboard metrics will now refresh on next page load.'
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'❌ Failed to clear cache: {e}'
            ))
            return
        
        self.stdout.write(
            '\nNote: In production, consider using Redis with '
            'selective cache invalidation for better performance.'
        )
