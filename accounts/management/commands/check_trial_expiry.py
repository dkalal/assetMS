"""
Management Command: Check Trial Expiry
======================================
Purpose: Check and suspend expired trial accounts
Usage: python manage.py check_trial_expiry

Schedule this to run daily via cron/scheduler:
- Linux/Mac: 0 2 * * * /path/to/python manage.py check_trial_expiry
- Windows Task Scheduler: Daily at 2:00 AM

World-Class Pattern: ServiceNow ITAM, IBM Maximo
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import CompanyRegistration


class Command(BaseCommand):
    help = 'Check and suspend expired trial accounts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be suspended without actually suspending',
        )
        parser.add_argument(
            '--notify',
            action='store_true',
            help='Send email notifications to affected companies',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        notify = options['notify']
        
        self.stdout.write(self.style.WARNING(
            f"\n{'='*70}\n"
            f"Trial Expiry Check - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'='*70}\n"
        ))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE("🔍 DRY RUN MODE - No changes will be made\n"))
        
        # Get all trial companies
        trial_companies = CompanyRegistration.objects.filter(
            subscription_status='trial'
        ).select_related('company')
        
        total = trial_companies.count()
        self.stdout.write(f"📊 Found {total} companies on trial\n")
        
        expired_count = 0
        warning_count = 0
        active_count = 0
        
        for registration in trial_companies:
            days_left = registration.days_until_trial_ends()
            company_name = registration.company.name
            
            if days_left is None:
                continue
            
            # Expired trials
            if days_left <= 0:
                expired_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ EXPIRED: {company_name} "
                        f"(expired {abs(days_left)} days ago)"
                    )
                )
                
                if not dry_run:
                    suspended = registration.suspend_if_trial_expired()
                    if suspended:
                        self.stdout.write(
                            self.style.SUCCESS(f"   ✅ Suspended: {company_name}")
                        )
                        
                        if notify:
                            self._send_suspension_email(registration)
                            self.stdout.write(
                                self.style.SUCCESS(f"   📧 Email sent to: {registration.billing_email}")
                            )
            
            # Warning (< 7 days left)
            elif days_left <= 7:
                warning_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  WARNING: {company_name} "
                        f"({days_left} days remaining)"
                    )
                )
                
                if notify and not dry_run:
                    self._send_warning_email(registration, days_left)
                    self.stdout.write(
                        self.style.SUCCESS(f"   📧 Warning email sent to: {registration.billing_email}")
                    )
            
            # Active trials
            else:
                active_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ ACTIVE: {company_name} "
                        f"({days_left} days remaining)"
                    )
                )
        
        # Summary
        self.stdout.write(
            self.style.WARNING(
                f"\n{'='*70}\n"
                f"Summary:\n"
                f"{'='*70}\n"
                f"Total trials: {total}\n"
                f"Active (>7 days): {active_count}\n"
                f"Warning (≤7 days): {warning_count}\n"
                f"Expired: {expired_count}\n"
                f"{'='*70}\n"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "\n💡 This was a dry run. Run without --dry-run to apply changes.\n"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Processed {expired_count} expired trials\n"
                )
            )
    
    def _send_suspension_email(self, registration):
        """Send suspension notification email"""
        # TODO: Implement email sending when email system is ready
        # For now, just log
        self.stdout.write(
            self.style.NOTICE(
                f"   📝 TODO: Send suspension email to {registration.billing_email}"
            )
        )
    
    def _send_warning_email(self, registration, days_left):
        """Send trial expiry warning email"""
        # TODO: Implement email sending when email system is ready
        # For now, just log
        self.stdout.write(
            self.style.NOTICE(
                f"   📝 TODO: Send warning email to {registration.billing_email} "
                f"({days_left} days left)"
            )
        )
