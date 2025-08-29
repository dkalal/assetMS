"""
Enterprise Session Cleanup Management Command
Handles automated cleanup of expired and old sessions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.session_manager import session_manager
from users.models import UserSession, AccessLog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up expired sessions and old session records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--expired-hours',
            type=int,
            default=24,
            help='Mark sessions as expired if inactive for this many hours (default: 24)'
        )
        
        parser.add_argument(
            '--delete-days',
            type=int,
            default=30,
            help='Permanently delete session records older than this many days (default: 30)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without making changes'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation prompts'
        )
    
    def handle(self, *args, **options):
        expired_hours = options['expired_hours']
        delete_days = options['delete_days']
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS(f'🧹 Enterprise Session Cleanup Started')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made')
            )
        
        # Step 1: Mark expired sessions as inactive
        self.stdout.write('\n📊 Analyzing expired sessions...')
        
        cutoff_time = timezone.now() - timedelta(hours=expired_hours)
        expired_sessions = UserSession.objects.filter(
            last_activity__lt=cutoff_time,
            is_active=True
        )
        
        expired_count = expired_sessions.count()
        
        if expired_count > 0:
            self.stdout.write(
                f'Found {expired_count} sessions inactive for more than {expired_hours} hours'
            )
            
            if not dry_run:
                if not force:
                    confirm = input(f'Mark {expired_count} sessions as expired? (y/N): ')
                    if confirm.lower() != 'y':
                        self.stdout.write('❌ Expired session cleanup cancelled')
                        return
                
                # Use the session manager for proper cleanup
                cleaned_count = session_manager.cleanup_expired_sessions(expired_hours)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Marked {cleaned_count} sessions as expired')
                )
            else:
                self.stdout.write(f'Would mark {expired_count} sessions as expired')
        else:
            self.stdout.write('✅ No expired sessions found')
        
        # Step 2: Delete old session records
        self.stdout.write('\n🗑️  Analyzing old session records...')
        
        delete_cutoff = timezone.now() - timedelta(days=delete_days)
        old_sessions = UserSession.objects.filter(
            last_activity__lt=delete_cutoff,
            is_active=False
        )
        
        old_count = old_sessions.count()
        
        if old_count > 0:
            self.stdout.write(
                f'Found {old_count} inactive session records older than {delete_days} days'
            )
            
            if not dry_run:
                if not force:
                    confirm = input(f'Permanently delete {old_count} old session records? (y/N): ')
                    if confirm.lower() != 'y':
                        self.stdout.write('❌ Old session cleanup cancelled')
                        return
                
                deleted_count = session_manager.cleanup_old_session_records(delete_days)
                self.stdout.write(
                    self.style.SUCCESS(f'🗑️  Permanently deleted {deleted_count} old session records')
                )
            else:
                self.stdout.write(f'Would delete {old_count} old session records')
        else:
            self.stdout.write('✅ No old session records found')
        
        # Step 3: Clean up old access logs (optional)
        self.stdout.write('\n📋 Analyzing old access logs...')
        
        old_logs = AccessLog.objects.filter(
            timestamp__lt=delete_cutoff
        )
        
        old_logs_count = old_logs.count()
        
        if old_logs_count > 0:
            self.stdout.write(
                f'Found {old_logs_count} access log entries older than {delete_days} days'
            )
            
            if not dry_run:
                if not force:
                    confirm = input(f'Delete {old_logs_count} old access log entries? (y/N): ')
                    if confirm.lower() == 'y':
                        deleted_logs = old_logs.delete()[0]
                        self.stdout.write(
                            self.style.SUCCESS(f'📋 Deleted {deleted_logs} old access log entries')
                        )
                    else:
                        self.stdout.write('❌ Access log cleanup cancelled')
                else:
                    deleted_logs = old_logs.delete()[0]
                    self.stdout.write(
                        self.style.SUCCESS(f'📋 Deleted {deleted_logs} old access log entries')
                    )
            else:
                self.stdout.write(f'Would delete {old_logs_count} old access log entries')
        else:
            self.stdout.write('✅ No old access logs found')
        
        # Step 4: Generate cleanup summary
        self.stdout.write('\n📈 Generating cleanup summary...')
        
        current_stats = session_manager.get_session_statistics()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎯 CLEANUP SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'Currently Active Sessions: {current_stats["active_sessions_count"]}')
        self.stdout.write(f'Unique Active Users: {current_stats["unique_active_users"]}')
        self.stdout.write(f'Sessions Created Today: {current_stats["sessions_today"]}')
        self.stdout.write(f'Total Registered Users: {current_stats["total_registered_users"]}')
        
        # Context breakdown
        self.stdout.write('\n📊 Active Sessions by Context:')
        for context, count in current_stats['context_breakdown'].items():
            self.stdout.write(f'  {context.title()}: {count}')
        
        # Role breakdown
        self.stdout.write('\n👥 Active Sessions by Role:')
        for role, count in current_stats['role_breakdown'].items():
            self.stdout.write(f'  {role.title()}: {count}')
        
        self.stdout.write('\n' + '='*60)
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('✅ Session cleanup completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('🔍 Dry run completed - no changes made')
            )
        
        # Recommendations
        self.stdout.write('\n💡 RECOMMENDATIONS:')
        
        if current_stats['active_sessions_count'] > current_stats['unique_active_users'] * 2:
            self.stdout.write('⚠️  High concurrent sessions detected - consider reviewing session limits')
        
        if current_stats['users_with_multiple_sessions'] > current_stats['unique_active_users'] * 0.5:
            self.stdout.write('ℹ️  Many users have multiple sessions - this is normal for tab usage')
        
        self.stdout.write(f'📅 Next recommended cleanup: {(timezone.now() + timedelta(days=7)).strftime("%Y-%m-%d")}')
        
        # Usage examples
        self.stdout.write('\n🔧 USAGE EXAMPLES:')
        self.stdout.write('  # Daily cleanup (mark 24h inactive as expired)')
        self.stdout.write('  python manage.py cleanup_sessions')
        self.stdout.write('')
        self.stdout.write('  # Aggressive cleanup (mark 6h inactive as expired)')
        self.stdout.write('  python manage.py cleanup_sessions --expired-hours 6')
        self.stdout.write('')
        self.stdout.write('  # Weekly maintenance (delete 7-day old records)')
        self.stdout.write('  python manage.py cleanup_sessions --delete-days 7 --force')
        self.stdout.write('')
        self.stdout.write('  # Preview changes without making them')
        self.stdout.write('  python manage.py cleanup_sessions --dry-run')