#!/usr/bin/env python
"""Check maintenance data in the database."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from assets.models import MaintenanceRecord, Asset
from tenancy.models import Company, Branch
from django.utils import timezone
from datetime import timedelta

print("=" * 80)
print("MAINTENANCE DATA ANALYSIS")
print("=" * 80)

# Check total counts
total_maintenance = MaintenanceRecord.objects.count()
total_assets = Asset.objects.count()
maintenance_enabled_assets = Asset.objects.filter(maintenance_enabled=True).count()

print(f"\n📊 OVERALL STATISTICS:")
print(f"   Total MaintenanceRecords: {total_maintenance}")
print(f"   Total Assets: {total_assets}")
print(f"   Assets with maintenance_enabled=True: {maintenance_enabled_assets}")

# Check by company
companies = Company.objects.all()
print(f"\n🏢 COMPANY BREAKDOWN:")
for company in companies:
    company_maintenance = MaintenanceRecord.objects.filter(company=company).count()
    company_assets = Asset.objects.filter(company=company).count()
    company_enabled = Asset.objects.filter(company=company, maintenance_enabled=True).count()
    print(f"   {company.name}:")
    print(f"      - Maintenance Records: {company_maintenance}")
    print(f"      - Total Assets: {company_assets}")
    print(f"      - Maintenance Enabled: {company_enabled}")

# Check maintenance status breakdown
if total_maintenance > 0:
    print(f"\n📋 MAINTENANCE STATUS BREAKDOWN:")
    for status in MaintenanceRecord.Status:
        count = MaintenanceRecord.objects.filter(status=status.value).count()
        print(f"   {status.label}: {count}")
    
    # Check date ranges
    today = timezone.localdate()
    upcoming = MaintenanceRecord.objects.filter(
        status=MaintenanceRecord.Status.SCHEDULED,
        scheduled_for__gte=today
    ).count()
    overdue = MaintenanceRecord.objects.filter(
        status=MaintenanceRecord.Status.SCHEDULED,
        scheduled_for__lt=today
    ).count()
    recent = MaintenanceRecord.objects.filter(
        status=MaintenanceRecord.Status.COMPLETED,
        completed_at__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    print(f"\n📅 DATE-BASED BREAKDOWN:")
    print(f"   Upcoming (scheduled >= today): {upcoming}")
    print(f"   Overdue (scheduled < today): {overdue}")
    print(f"   Recently Completed (last 30 days): {recent}")
    
    # Show sample records
    print(f"\n📝 SAMPLE MAINTENANCE RECORDS (first 5):")
    for record in MaintenanceRecord.objects.all()[:5]:
        print(f"   - {record}")
else:
    print(f"\n⚠️  NO MAINTENANCE RECORDS FOUND IN DATABASE")
    print(f"   This explains why the maintenance page shows no data.")

# Check if any assets have maintenance_enabled but no records
if maintenance_enabled_assets > 0 and total_maintenance == 0:
    print(f"\n💡 RECOMMENDATION:")
    print(f"   You have {maintenance_enabled_assets} assets with maintenance enabled,")
    print(f"   but no maintenance records scheduled.")
    print(f"   Create some maintenance records to see data on the page.")

print("\n" + "=" * 80)
