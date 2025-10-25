"""
Management command to seed maintenance data for testing and demonstration.
Follows world-class AMS patterns from ServiceNow, IBM Maximo, and SAP EAM.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from assets.models import Asset, MaintenanceRecord
from tenancy.models import Company, Branch
from users.models import User


class Command(BaseCommand):
    help = 'Seed maintenance data for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=str,
            help='Company name to seed data for (default: first company)',
        )
        parser.add_argument(
            '--assets',
            type=int,
            default=10,
            help='Number of assets to enable maintenance for (default: 10)',
        )
        parser.add_argument(
            '--records',
            type=int,
            default=15,
            help='Number of maintenance records to create (default: 15)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )

    def handle(self, *args, **options):
        company_name = options.get('company')
        num_assets = options['assets']
        num_records = options['records']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('MAINTENANCE DATA SEEDER'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Get company
        if company_name:
            try:
                company = Company.objects.get(name=company_name)
            except Company.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Company "{company_name}" not found'))
                return
        else:
            company = Company.objects.first()
            if not company:
                self.stdout.write(self.style.ERROR('No companies found in database'))
                return

        self.stdout.write(f'\n📍 Target Company: {company.name}')

        # Get admin user for created_by
        admin_user = User.objects.filter(
            company=company,
            role='admin'
        ).first()

        if not admin_user:
            admin_user = User.objects.filter(company=company).first()

        if not admin_user:
            self.stdout.write(self.style.ERROR('No users found for this company'))
            return

        self.stdout.write(f'👤 Using user: {admin_user.username} ({admin_user.get_full_name()})')

        # Get assets
        assets = list(Asset.objects.filter(
            company=company,
            status='active'
        ).select_related('branch', 'category')[:num_assets])

        if not assets:
            self.stdout.write(self.style.ERROR('No active assets found for this company'))
            return

        self.stdout.write(f'\n📦 Found {len(assets)} active assets')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))

        # Enable maintenance for assets
        self.stdout.write(f'\n✅ Enabling maintenance for {len(assets)} assets...')
        if not dry_run:
            Asset.objects.filter(id__in=[a.id for a in assets]).update(maintenance_enabled=True)
        
        for asset in assets:
            self.stdout.write(f'   - {asset.description or asset.category.name} ({asset.uuid})')

        # Create maintenance records
        self.stdout.write(f'\n📋 Creating {num_records} maintenance records...')
        
        today = timezone.localdate()
        records_created = 0
        
        # Distribution: 30% overdue, 40% upcoming, 20% completed, 10% in progress
        overdue_count = int(num_records * 0.3)
        upcoming_count = int(num_records * 0.4)
        completed_count = int(num_records * 0.2)
        in_progress_count = num_records - overdue_count - upcoming_count - completed_count

        descriptions = [
            "Routine preventive maintenance",
            "Quarterly inspection and service",
            "Annual comprehensive check",
            "Software update and optimization",
            "Hardware component replacement",
            "Calibration and testing",
            "Safety inspection",
            "Performance optimization",
            "Firmware upgrade",
            "Cleaning and lubrication",
        ]

        outcome_notes = [
            "All systems functioning normally. No issues detected.",
            "Minor adjustments made. Equipment running optimally.",
            "Replaced worn components. Performance improved significantly.",
            "Software updated successfully. All tests passed.",
            "Routine maintenance completed as scheduled.",
            "Calibration completed within acceptable tolerances.",
            "Safety checks passed. Equipment certified for continued use.",
            "Performance benchmarks exceeded expectations.",
            "Preventive measures applied. Next service scheduled.",
            "Comprehensive inspection completed. Asset in excellent condition.",
        ]

        # Create overdue records
        for i in range(overdue_count):
            asset = random.choice(assets)
            days_overdue = random.randint(1, 30)
            scheduled_date = today - timedelta(days=days_overdue)
            
            if not dry_run:
                MaintenanceRecord.objects.create(
                    asset=asset,
                    company=company,
                    branch=asset.branch,
                    status=MaintenanceRecord.Status.SCHEDULED,
                    scheduled_for=scheduled_date,
                    description=random.choice(descriptions),
                    created_by=admin_user,
                    updated_by=admin_user,
                )
            
            records_created += 1
            self.stdout.write(f'   ⚠️  Overdue: {asset.description or asset.category.name} '
                            f'(scheduled {days_overdue} days ago)')

        # Create upcoming records
        for i in range(upcoming_count):
            asset = random.choice(assets)
            days_ahead = random.randint(1, 30)
            scheduled_date = today + timedelta(days=days_ahead)
            
            if not dry_run:
                MaintenanceRecord.objects.create(
                    asset=asset,
                    company=company,
                    branch=asset.branch,
                    status=MaintenanceRecord.Status.SCHEDULED,
                    scheduled_for=scheduled_date,
                    description=random.choice(descriptions),
                    supervisor=admin_user if random.random() > 0.5 else None,
                    created_by=admin_user,
                    updated_by=admin_user,
                )
            
            records_created += 1
            self.stdout.write(f'   📅 Upcoming: {asset.description or asset.category.name} '
                            f'(in {days_ahead} days)')

        # Create completed records
        for i in range(completed_count):
            asset = random.choice(assets)
            days_ago = random.randint(1, 30)
            scheduled_date = today - timedelta(days=days_ago + 5)
            completed_date = timezone.now() - timedelta(days=days_ago)
            started_date = completed_date - timedelta(hours=random.randint(1, 8))
            
            if not dry_run:
                MaintenanceRecord.objects.create(
                    asset=asset,
                    company=company,
                    branch=asset.branch,
                    status=MaintenanceRecord.Status.COMPLETED,
                    scheduled_for=scheduled_date,
                    started_at=started_date,
                    completed_at=completed_date,
                    description=random.choice(descriptions),
                    outcome_notes=random.choice(outcome_notes),
                    cost=Decimal(str(random.uniform(50, 500))).quantize(Decimal('0.01')),
                    performed_by=admin_user,
                    supervisor=admin_user if random.random() > 0.5 else None,
                    created_by=admin_user,
                    updated_by=admin_user,
                )
            
            records_created += 1
            self.stdout.write(f'   ✅ Completed: {asset.description or asset.category.name} '
                            f'({days_ago} days ago)')

        # Create in-progress records
        for i in range(in_progress_count):
            asset = random.choice(assets)
            scheduled_date = today - timedelta(days=random.randint(0, 3))
            started_date = timezone.now() - timedelta(hours=random.randint(1, 24))
            
            if not dry_run:
                MaintenanceRecord.objects.create(
                    asset=asset,
                    company=company,
                    branch=asset.branch,
                    status=MaintenanceRecord.Status.IN_PROGRESS,
                    scheduled_for=scheduled_date,
                    started_at=started_date,
                    description=random.choice(descriptions),
                    performed_by=admin_user,
                    supervisor=admin_user if random.random() > 0.5 else None,
                    created_by=admin_user,
                    updated_by=admin_user,
                )
            
            records_created += 1
            self.stdout.write(f'   🔄 In Progress: {asset.description or asset.category.name}')

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 80}'))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'✅ Assets with maintenance enabled: {len(assets)}')
        self.stdout.write(f'📋 Maintenance records created: {records_created}')
        self.stdout.write(f'   - ⚠️  Overdue: {overdue_count}')
        self.stdout.write(f'   - 📅 Upcoming: {upcoming_count}')
        self.stdout.write(f'   - ✅ Completed: {completed_count}')
        self.stdout.write(f'   - 🔄 In Progress: {in_progress_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 This was a DRY RUN - no data was created'))
            self.stdout.write('Run without --dry-run to actually create the data')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Data seeding completed successfully!'))
            self.stdout.write('Visit http://127.0.0.1:8000/maintenance/ to see the results')
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
