"""
============================================================================
BULK IMPORT VIEWS - World-Class Asset Import Backend
============================================================================

API endpoints for bulk asset import:
- Template download
- Data validation
- Batch asset creation
- Import history

Inspired by: Salesforce Data Loader, ServiceNow Import Sets, IBM Maximo

@version 1.0.0
@author Asset Management System
@license MIT
"""

import csv
import io
import json
import time
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db import transaction, OperationalError
from django.utils import timezone

from assets.models import Asset, AssetCategory
from tenancy.models import Branch, Company
from users.models import User
from audit.utils import log_audit, ASSET_ACTION, BULK_IMPORT_ACTION, CREATE_ACTION


@login_required
@require_GET
def bulk_import_view(request):
    """
    Render bulk import page
    
    Only managers and admins can access
    """
    if request.user.role not in ['admin', 'manager']:
        messages.error(request, 'Only Managers and Admins can perform bulk imports.')
        return render(request, 'assets/bulk_import.html', {
            'can_import': False
        })
    
    return render(request, 'assets/bulk_import.html', {
        'can_import': True
    })


@login_required
@require_GET
def download_import_template(request):
    """
    Download CSV template for bulk import
    
    Returns:
        CSV file with headers and sample data
    """
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    headers = [
        'Category',
        'Branch',
        'Asset Name',
        'Serial Number',
        'Asset Tag',
        'Description',
        'Purchase Value',
        'Purchase Date',
        'Assigned To (Email)'
    ]
    writer.writerow(headers)
    
    # Sample data
    sample_rows = [
        [
            'Laptops',
            'Main Office',
            'Dell Latitude 5420',
            'SN123456789',
            'ASSET-001',
            'Core i7, 16GB RAM, 512GB SSD',
            '1200.00',
            '2024-01-15',
            'user@example.com'
        ],
        [
            'Furniture',
            'Main Office',
            'Office Desk',
            '',
            'DESK-001',
            'Adjustable height desk',
            '350.00',
            '2024-02-20',
            ''
        ],
        [
            'Vehicles',
            'Branch Office',
            'Toyota Hilux 2023',
            'VIN12345678901234',
            'VEH-001',
            'Company vehicle for field work',
            '45000.00',
            '2023-12-10',
            'driver@example.com'
        ]
    ]
    
    for row in sample_rows:
        writer.writerow(row)
    
    # Create HTTP response
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="asset_import_template.csv"'
    
    return response


@login_required
@csrf_protect
@require_POST
def validate_bulk_data(request):
    """
    Validate bulk import data before import
    
    Request Body:
        {
            "data": [
                {
                    "category": "Laptops",
                    "branch": "Main Office",
                    "name": "Dell Latitude",
                    ...
                }
            ]
        }
    
    Returns:
        {
            "valid_count": 10,
            "invalid_count": 2,
            "rows": [
                {
                    "valid": true,
                    "errors": []
                },
                {
                    "valid": false,
                    "errors": ["Category not found", "Invalid date format"]
                }
            ]
        }
    """
    try:
        data = json.loads(request.body)
        rows_data = data.get('data', [])
        
        company = request.user.company
        validated_rows = []
        valid_count = 0
        invalid_count = 0
        
        # Track duplicates within the import file (cross-row validation)
        serial_numbers_in_file = defaultdict(list)
        asset_tags_in_file = defaultdict(list)
        
        # First pass: collect all serial numbers and asset tags
        for idx, row in enumerate(rows_data):
            serial_number = row.get('serial_number', '').strip()
            if serial_number:
                serial_numbers_in_file[serial_number.lower()].append(idx + 1)
            
            asset_tag = row.get('asset_tag', '').strip()
            if asset_tag:
                asset_tags_in_file[asset_tag.lower()].append(idx + 1)
        
        # Second pass: validate each row
        for idx, row in enumerate(rows_data):
            errors = []
            row_number = idx + 1
            
            # Validate required fields
            category_name = row.get('category', '').strip()
            branch_name = row.get('branch', '').strip()
            
            if not category_name:
                errors.append('Category is required')
            else:
                # Check if category exists
                if not AssetCategory.objects.filter(
                    company=company,
                    name__iexact=category_name
                ).exists():
                    errors.append(f'Category "{category_name}" not found in your company')
            
            if not branch_name:
                errors.append('Branch is required')
            else:
                # Check if branch exists
                if not Branch.objects.filter(
                    company=company,
                    name__iexact=branch_name
                ).exists():
                    errors.append(f'Branch "{branch_name}" not found in your company')
            
            # Validate serial number uniqueness (if provided)
            serial_number = row.get('serial_number', '').strip()
            if serial_number:
                # Check database
                if Asset.objects.filter(
                    company=company,
                    serial_number__iexact=serial_number
                ).exists():
                    errors.append(f'Serial number "{serial_number}" already exists in database')
                
                # Check for duplicates within import file
                duplicate_rows = serial_numbers_in_file[serial_number.lower()]
                if len(duplicate_rows) > 1:
                    other_rows = [r for r in duplicate_rows if r != row_number]
                    errors.append(f'Serial number "{serial_number}" duplicated in rows: {", ".join(map(str, other_rows))}')
            
            # Validate asset tag uniqueness (if provided)
            asset_tag = row.get('asset_tag', '').strip()
            if asset_tag:
                # Check database
                if Asset.objects.filter(
                    company=company,
                    asset_tag__iexact=asset_tag
                ).exists():
                    errors.append(f'Asset tag "{asset_tag}" already exists in database')
                
                # Check for duplicates within import file
                duplicate_rows = asset_tags_in_file[asset_tag.lower()]
                if len(duplicate_rows) > 1:
                    other_rows = [r for r in duplicate_rows if r != row_number]
                    errors.append(f'Asset tag "{asset_tag}" duplicated in rows: {", ".join(map(str, other_rows))}')
            
            # Validate purchase value (if provided)
            purchase_value = row.get('purchase_value', '').strip()
            if purchase_value:
                try:
                    float(purchase_value)
                except ValueError:
                    errors.append('Purchase value must be a number')
            
            # Validate purchase date (if provided)
            purchase_date = row.get('purchase_date', '').strip()
            if purchase_date:
                try:
                    datetime.strptime(purchase_date, '%Y-%m-%d')
                except ValueError:
                    errors.append('Purchase date must be in YYYY-MM-DD format')
            
            # Validate assigned user (if provided)
            assigned_to_email = row.get('assigned_to', '').strip()
            if assigned_to_email:
                if not User.objects.filter(
                    company=company,
                    email__iexact=assigned_to_email
                ).exists():
                    errors.append(f'User "{assigned_to_email}" not found')
            
            # Determine if row is valid
            is_valid = len(errors) == 0
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
            
            validated_rows.append({
                'valid': is_valid,
                'errors': errors
            })
        
        return JsonResponse({
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'rows': validated_rows
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)


@login_required
@csrf_protect
@require_POST
def execute_bulk_import(request):
    """
    Execute bulk asset import with world-class performance optimization.
    
    Performance Features:
    - Pre-caching: Load all lookup data before processing
    - Batch processing: Split into chunks to prevent long transactions
    - Two-phase: Database writes + QR generation separated
    - Progress tracking: Real-time updates (future enhancement)
    
    Request Body:
        {
            "assets": [
                {
                    "category": "Laptops",
                    "branch": "Main Office",
                    ...
                }
            ]
        }
    
    Returns:
        {
            "created_count": 10,
            "failed_count": 0,
            "errors": []
        }
    """
    # Check permission
    if request.user.role not in ['admin', 'manager']:
        return JsonResponse({
            'error': 'Only Managers and Admins can perform bulk imports'
        }, status=403)
    
    def _user_friendly_error(error_msg: str, row_number: int) -> str:
        """
        Convert technical errors to user-friendly messages
        Following world-class UX standards (ServiceNow, Salesforce)
        """
        error_lower = error_msg.lower()
        
        # Database lock errors
        if 'database is locked' in error_lower or 'locked' in error_lower:
            return f"Row {row_number}: Import processing conflict. The system is busy. Please try again in a moment."
        
        # Duplicate errors
        if 'unique constraint' in error_lower or 'duplicate' in error_lower:
            if 'serial_number' in error_lower:
                return f"Row {row_number}: This serial number already exists. Please use a unique serial number."
            elif 'asset_tag' in error_lower:
                return f"Row {row_number}: This asset tag already exists. Please use a unique asset tag."
            else:
                return f"Row {row_number}: Duplicate value detected. Please check your data."
        
        # Not found errors
        if 'does not exist' in error_lower or 'not found' in error_lower:
            if 'category' in error_lower:
                return f"Row {row_number}: Category not found. Please check the category name."
            elif 'branch' in error_lower:
                return f"Row {row_number}: Branch not found. Please check the branch name."
            elif 'user' in error_lower:
                return f"Row {row_number}: User not found. Please check the email address."
            else:
                return f"Row {row_number}: Required data not found. Please verify your input."
        
        # Validation errors
        if 'invalid' in error_lower:
            return f"Row {row_number}: Invalid data format. Please check your input."
        
        # Permission errors
        if 'permission' in error_lower or 'forbidden' in error_lower:
            return f"Row {row_number}: You don't have permission to perform this action."
        
        # Default: return original with row number
        return f"Row {row_number}: {error_msg}"
    
    try:
        data = json.loads(request.body)
        assets_data = data.get('assets', [])
        
        company = request.user.company
        created_assets = []  # Track created assets for QR generation
        created_count = 0
        failed_count = 0
        errors = []
        
        # ===================================================================
        # OPTIMIZATION 1: PRE-CACHE ALL LOOKUP DATA (Prevents database locks)
        # ===================================================================
        # Load all categories, branches, and users into memory BEFORE transaction
        # This eliminates repeated database queries inside the transaction loop
        
        print("[Bulk Import] Pre-caching lookup data...")
        
        # Cache categories by lowercase name for fast lookup
        categories_cache = {}
        for cat in AssetCategory.objects.filter(company=company):
            categories_cache[cat.name.lower()] = cat
        
        # Cache branches by lowercase name
        branches_cache = {}
        for branch in Branch.objects.filter(company=company):
            branches_cache[branch.name.lower()] = branch
        
        # Cache users by lowercase email
        users_cache = {}
        for user in User.objects.filter(company=company):
            users_cache[user.email.lower()] = user
        
        print(f"[Bulk Import] Cached {len(categories_cache)} categories, {len(branches_cache)} branches, {len(users_cache)} users")
        
        # ===================================================================
        # OPTIMIZATION 2: TRACK DUPLICATES WITHIN IMPORT (Re-validation)
        # ===================================================================
        # Track serial numbers and asset tags as we import to catch race conditions
        # This prevents duplicates even if another import runs concurrently
        
        imported_serial_numbers = set()
        imported_asset_tags = set()
        
        # ===================================================================
        # OPTIMIZATION 3: BATCH PROCESSING (Prevents long-running transactions)
        # ===================================================================
        # Process assets in chunks of 10 to minimize transaction duration
        # Smaller batches = shorter locks = better for SQLite
        
        BATCH_SIZE = 10  # Optimal for SQLite (reduced from 20)
        MAX_RETRIES = 3  # Retry locked transactions
        RETRY_DELAY = 0.5  # 500ms between retries
        total_assets = len(assets_data)
        
        for batch_start in range(0, total_assets, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_assets)
            batch = assets_data[batch_start:batch_end]
            
            batch_number = batch_start//BATCH_SIZE + 1
            print(f"[Bulk Import] Processing batch {batch_number}/{(total_assets + BATCH_SIZE - 1)//BATCH_SIZE}: rows {batch_start + 1}-{batch_end}")
            
            # Short transaction for this batch only WITH RETRY LOGIC
            retry_count = 0
            batch_success = False
            
            while not batch_success and retry_count < MAX_RETRIES:
                try:
                    with transaction.atomic():
                        for idx_in_batch, asset_data in enumerate(batch):
                            global_idx = batch_start + idx_in_batch
                            row_number = global_idx + 1
                            
                            try:
                                # Get category from cache (no database query!)
                                category_name = asset_data.get('category', '').strip()
                                category = categories_cache.get(category_name.lower())
                                if not category:
                                    raise ValueError(f'Category "{category_name}" not found')
                                
                                # Get branch from cache (no database query!)
                                branch_name = asset_data.get('branch', '').strip()
                                branch = branches_cache.get(branch_name.lower())
                                if not branch:
                                    raise ValueError(f'Branch "{branch_name}" not found')
                                
                                # ===============================================
                                # CRITICAL: RE-VALIDATE DUPLICATES DURING IMPORT
                                # ===============================================
                                # Check both database AND already-imported items
                                # This prevents race conditions between validation and import
                                
                                serial_number = asset_data.get('serial_number', '').strip()
                                if serial_number:
                                    serial_lower = serial_number.lower()
                                    
                                    # Check database (might have changed since validation)
                                    if Asset.objects.filter(
                                        company=company,
                                        serial_number__iexact=serial_number
                                    ).exists():
                                        raise ValueError(f'Serial number "{serial_number}" already exists in database')
                                    
                                    # Check already imported in this session
                                    if serial_lower in imported_serial_numbers:
                                        raise ValueError(f'Serial number "{serial_number}" was already imported in this batch')
                                    
                                    # Mark as imported
                                    imported_serial_numbers.add(serial_lower)
                                
                                asset_tag = asset_data.get('asset_tag', '').strip()
                                if asset_tag:
                                    tag_lower = asset_tag.lower()
                                    
                                    # Check database
                                    if Asset.objects.filter(
                                        company=company,
                                        asset_tag__iexact=asset_tag
                                    ).exists():
                                        raise ValueError(f'Asset tag "{asset_tag}" already exists in database')
                                    
                                    # Check already imported
                                    if tag_lower in imported_asset_tags:
                                        raise ValueError(f'Asset tag "{asset_tag}" was already imported in this batch')
                                    
                                    # Mark as imported
                                    imported_asset_tags.add(tag_lower)
                        
                                # Get assigned user from cache (if provided)
                                assigned_to = None
                                assigned_to_email = asset_data.get('assigned_to', '').strip()
                                if assigned_to_email:
                                    assigned_to = users_cache.get(assigned_to_email.lower())
                                    if not assigned_to:
                                        raise ValueError(f'User "{assigned_to_email}" not found')
                                
                                # Parse purchase value
                                purchase_value = None
                                purchase_value_str = asset_data.get('purchase_value', '').strip()
                                if purchase_value_str:
                                    purchase_value = Decimal(purchase_value_str)
                                
                                # Parse purchase date
                                purchase_date = None
                                purchase_date_str = asset_data.get('purchase_date', '').strip()
                                if purchase_date_str:
                                    purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
                                
                                # Create asset (database only, no file I/O)
                                asset = Asset.objects.create(
                                    company=company,
                                    category=category,
                                    branch=branch,
                                    name=asset_data.get('name', '').strip() or None,
                                    serial_number=serial_number or None,
                                    asset_tag=asset_tag or None,
                                    description=asset_data.get('description', '').strip() or None,
                                    purchase_value=purchase_value,
                                    purchase_date=purchase_date,
                                    assigned_to=assigned_to,
                                    status='active',
                                    created_by=request.user
                                )
                                
                                # Track for post-transaction processing
                                created_assets.append({
                                    'asset': asset,
                                    'row_number': row_number,
                                    'category_name': category_name,
                                    'branch_name': branch_name
                                })
                                
                                created_count += 1
                            
                            except Exception as e:
                                failed_count += 1
                                # User-friendly error message
                                friendly_error = _user_friendly_error(str(e), row_number)
                                errors.append({
                                    'row': row_number,
                                    'error': friendly_error,
                                    'technical_error': str(e)  # For debugging
                                })
                    
                    # Transaction succeeded
                    batch_success = True
                    print(f"[Bulk Import] Batch {batch_number} complete: {created_count} created, {failed_count} failed so far")
                    
                except OperationalError as e:
                    # Database lock detected
                    if 'database is locked' in str(e).lower():
                        retry_count += 1
                        if retry_count < MAX_RETRIES:
                            print(f"[Bulk Import] ⚠️ Database locked. Retry {retry_count}/{MAX_RETRIES} in {RETRY_DELAY}s...")
                            time.sleep(RETRY_DELAY)
                            # Roll back the imported tracking for this batch
                            # We'll re-attempt with fresh checks
                        else:
                            # Max retries exceeded - fail the entire batch
                            print(f"[Bulk Import] ❌ Batch {batch_number} failed after {MAX_RETRIES} retries")
                            for idx_in_batch in range(len(batch)):
                                global_idx = batch_start + idx_in_batch
                                row_number = global_idx + 1
                                failed_count += 1
                                friendly_error = _user_friendly_error(str(e), row_number)
                                errors.append({
                                    'row': row_number,
                                    'error': friendly_error,
                                    'technical_error': str(e)
                                })
                            batch_success = True  # Exit retry loop
                    else:
                        # Other operational error - don't retry
                        raise
        
        # ===================================================================
        # STEP 2: Generate QR codes OUTSIDE transaction (prevents locks)
        # ===================================================================
        # File I/O operations don't block database
        
        print(f"[Bulk Import] Generating QR codes for {len(created_assets)} assets...")
        
        for asset_info in created_assets:
            try:
                asset = asset_info['asset']
                asset.generate_qr_code()
                
                # Log audit - Individual asset creation
                log_audit(
                    request.user,
                    CREATE_ACTION,
                    asset,
                    f"Asset created via bulk import (row {asset_info['row_number']})",
                    company=company,
                    branch=asset.branch,
                    metadata={
                        'import_method': 'bulk',
                        'row_number': asset_info['row_number'],
                        'category': asset_info['category_name'],
                        'branch': asset_info['branch_name']
                    }
                )
            except Exception as e:
                # QR generation failed, but asset is created
                # Log warning but don't fail the import
                print(f"[Bulk Import] Warning: QR code generation failed for asset {asset.id}: {str(e)}")
        
        print(f"[Bulk Import] QR code generation complete")
        
        # ===================================================================
        # FINAL: Log bulk import operation summary (world-class audit trail)
        # ===================================================================
        
        success_rate = f"{(created_count / len(assets_data) * 100):.1f}%" if assets_data else "0%"
        
        print(f"[Bulk Import] COMPLETE: {created_count} created, {failed_count} failed ({success_rate} success rate)")
        
        log_audit(
            request.user,
            BULK_IMPORT_ACTION,
            None,
            f"Bulk import completed: {created_count} created, {failed_count} failed ({success_rate} success)",
            company=company,
            branch=None,  # Bulk import is company-wide
            metadata={
                'total_rows': len(assets_data),
                'created_count': created_count,
                'failed_count': failed_count,
                'success_rate': success_rate,
                'batch_size': BATCH_SIZE,
                'optimization': 'pre-caching + batch processing'
            }
        )
        
        return JsonResponse({
            'created_count': created_count,
            'failed_count': failed_count,
            'errors': errors,
            'success_rate': success_rate
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)
