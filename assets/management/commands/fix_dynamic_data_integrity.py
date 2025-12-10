"""
Management command to fix dynamic_data integrity for all assets.

This command ensures all assets have complete dynamic_data with all category fields.

Usage:
    python manage.py fix_dynamic_data_integrity
    python manage.py fix_dynamic_data_integrity --dry-run
    python manage.py fix_dynamic_data_integrity --company-id=1
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from assets.models import Asset
from tenancy.models import Company


class Command(BaseCommand):
    help = 'Fix dynamic_data integrity for all assets by ensuring all category fields exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Fix assets for specific company only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        company_id = options.get('company_id')

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Dynamic Data Integrity Fix'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Get assets to fix
        assets = Asset.objects.select_related('category', 'company')
        
        if company_id:
            try:
                company = Company.objects.get(id=company_id)
                assets = assets.filter(company=company)
                self.stdout.write(f'📊 Filtering by company: {company.name}')
            except Company.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Company with ID {company_id} not found'))
                return
        
        total_assets = assets.count()
        self.stdout.write(f'📊 Total assets to check: {total_assets}')
        self.stdout.write('')
        
        # Process assets
        fixed_count = 0
        skipped_count = 0
        error_count = 0
        
        for asset in assets:
            try:
                # Check if fix is needed
                needs_fix = asset.ensure_dynamic_data_integrity()
                
                if needs_fix:
                    fixed_count += 1
                    category_name = asset.category.name if asset.category else 'No Category'
                    
                    self.stdout.write(
                        f'  ✅ Fixed: Asset {asset.uuid} ({category_name})'
                    )
                    
                    if not dry_run:
                        # Save with transaction
                        with transaction.atomic():
                            asset.save(update_fields=['dynamic_data'])
                else:
                    skipped_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error fixing asset {asset.uuid}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'📊 Total assets checked: {total_assets}')
        self.stdout.write(f'✅ Assets fixed: {fixed_count}')
        self.stdout.write(f'⏭️  Assets skipped (already correct): {skipped_count}')
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes were made'))
            self.stdout.write(self.style.WARNING('   Run without --dry-run to apply fixes'))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ All fixes applied successfully!'))
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
