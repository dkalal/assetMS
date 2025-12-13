"""
Management command to fix orphaned assets without company or branch.

Usage:
    python manage.py fix_orphaned_assets --dry-run
    python manage.py fix_orphaned_assets --company-id=1
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from assets.models import Asset
from tenancy.models import Company, Branch


class Command(BaseCommand):
    help = 'Fix orphaned assets without company or branch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Assign orphaned assets to specific company ID'
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Automatically fix if only one company exists'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        company_id = options.get('company_id')
        auto = options['auto']
        
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('  ORPHANED ASSETS ANALYSIS & FIX'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))
        
        # Find orphaned assets
        orphaned_no_company = Asset.objects.filter(company__isnull=True)
        orphaned_no_branch = Asset.objects.filter(company__isnull=False, branch__isnull=True)
        
        self.stdout.write(f"📊 Analysis Results:")
        self.stdout.write(f"   • Assets without company: {orphaned_no_company.count()}")
        self.stdout.write(f"   • Assets without branch:  {orphaned_no_branch.count()}")
        self.stdout.write("")
        
        if orphaned_no_company.count() == 0 and orphaned_no_branch.count() == 0:
            self.stdout.write(self.style.SUCCESS("✅ No orphaned assets found. Database is clean!"))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made\n"))
            
            if orphaned_no_company.exists():
                self.stdout.write("Assets without company:")
                for asset in orphaned_no_company[:10]:
                    self.stdout.write(f"   - Asset #{asset.id}: {asset.description[:50]}")
                if orphaned_no_company.count() > 10:
                    self.stdout.write(f"   ... and {orphaned_no_company.count() - 10} more")
            
            if orphaned_no_branch.exists():
                self.stdout.write("\nAssets without branch:")
                for asset in orphaned_no_branch[:10]:
                    self.stdout.write(f"   - Asset #{asset.id}: {asset.description[:50]} (Company: {asset.company.name})")
                if orphaned_no_branch.count() > 10:
                    self.stdout.write(f"   ... and {orphaned_no_branch.count() - 10} more")
            
            self.stdout.write(self.style.WARNING("\nTo fix, run:"))
            self.stdout.write("   python manage.py fix_orphaned_assets --company-id=<ID>")
            self.stdout.write("   python manage.py fix_orphaned_assets --auto")
            return
        
        # Fix orphaned assets
        fixed_count = 0
        
        with transaction.atomic():
            # Fix assets without company
            if orphaned_no_company.exists():
                companies = Company.objects.all()
                
                if company_id:
                    try:
                        company = Company.objects.get(pk=company_id)
                    except Company.DoesNotExist:
                        raise CommandError(f"Company with ID {company_id} does not exist")
                elif auto and companies.count() == 1:
                    company = companies.first()
                    self.stdout.write(f"🤖 Auto mode: Using only company '{company.name}'")
                else:
                    self.stdout.write(self.style.ERROR("\n❌ Multiple companies exist. Specify --company-id or use --auto"))
                    self.stdout.write("\nAvailable companies:")
                    for c in companies:
                        self.stdout.write(f"   • ID {c.id}: {c.name}")
                    return
                
                # Get default branch for company
                default_branch = Branch.objects.filter(company=company, is_active=True).first()
                
                if not default_branch:
                    raise CommandError(f"No active branches found for company '{company.name}'")
                
                # Update orphaned assets
                count = orphaned_no_company.update(
                    company=company,
                    branch=default_branch
                )
                fixed_count += count
                
                self.stdout.write(self.style.SUCCESS(f"\n✅ Fixed {count} assets without company"))
                self.stdout.write(f"   • Assigned to company: {company.name}")
                self.stdout.write(f"   • Assigned to branch:  {default_branch.name}")
            
            # Fix assets without branch
            if orphaned_no_branch.exists():
                branch_fixed = 0
                for asset in orphaned_no_branch:
                    # Assign to company's first active branch
                    default_branch = Branch.objects.filter(
                        company=asset.company,
                        is_active=True
                    ).first()
                    
                    if default_branch:
                        asset.branch = default_branch
                        asset.save(update_fields=['branch'])
                        branch_fixed += 1
                
                fixed_count += branch_fixed
                self.stdout.write(self.style.SUCCESS(f"\n✅ Fixed {branch_fixed} assets without branch"))
        
        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("="*60))
        self.stdout.write(self.style.SUCCESS(f"  TOTAL FIXED: {fixed_count} assets"))
        self.stdout.write(self.style.SUCCESS("="*60))
        self.stdout.write("")
        self.stdout.write("Next steps:")
        self.stdout.write("   1. Clear cache: python manage.py shell")
        self.stdout.write("      >>> from django.core.cache import cache")
        self.stdout.write("      >>> cache.clear()")
        self.stdout.write("   2. Restart server")
        self.stdout.write("   3. Verify dashboard counts")
        self.stdout.write("")
