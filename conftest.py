"""
Pytest configuration and shared fixtures for Asset Management System.

This module provides reusable fixtures for testing with world-class standards:
- Multi-tenancy test data (companies, branches, users)
- Asset management fixtures (categories, assets, transfers)
- Performance testing utilities
- Accessibility testing helpers
- Integration testing setup

Following best practices from ServiceNow ITAM, IBM Maximo, and SAP EAM.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from datetime import timedelta

from tenancy.models import Company, Branch
from assets.models import Asset, AssetCategory, AssetTransfer
from users.models import RolePermissionMatrix

User = get_user_model()


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, database)"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "accessibility: Accessibility and WCAG compliance tests"
    )


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope='function')
def db_access(db):
    """
    Provide database access for tests.
    Scope: function - fresh database state for each test.
    """
    return db


# ============================================================================
# MULTI-TENANCY FIXTURES
# ============================================================================

@pytest.fixture
def company(db):
    """
    Create a test company with proper multi-tenancy setup.
    
    Returns:
        Company: Test company instance
    """
    return Company.objects.create(
        name='Test Company',
        address='123 Test Street',
        tax_id='TAX-12345',
        contact_person='John Doe',
        phone='+1234567890',
        email='contact@testcompany.com',
        timezone='UTC'
    )


@pytest.fixture
def company2(db):
    """
    Create a second test company for multi-tenancy isolation tests.
    
    Returns:
        Company: Second test company instance
    """
    return Company.objects.create(
        name='Test Company 2',
        address='456 Test Avenue',
        tax_id='TAX-67890',
        contact_person='Jane Smith',
        phone='+0987654321',
        email='contact@testcompany2.com',
        timezone='UTC'
    )


@pytest.fixture
def head_office(db, company):
    """
    Create head office branch for test company.
    
    Args:
        company: Test company fixture
        
    Returns:
        Branch: Head office branch instance
    """
    return Branch.objects.create(
        company=company,
        name='Head Office',
        address='123 Test Street',
        code='HQ',
        is_head_office=True
    )


@pytest.fixture
def branch(db, company):
    """
    Create a regular branch for test company.
    
    Args:
        company: Test company fixture
        
    Returns:
        Branch: Regular branch instance
    """
    return Branch.objects.create(
        company=company,
        name='Test Branch',
        address='789 Branch Road',
        code='BR01',
        is_head_office=False
    )


@pytest.fixture
def branch2(db, company):
    """
    Create a second branch for transfer testing.
    
    Args:
        company: Test company fixture
        
    Returns:
        Branch: Second branch instance
    """
    return Branch.objects.create(
        company=company,
        name='Test Branch 2',
        address='321 Branch Avenue',
        code='BR02',
        is_head_office=False
    )


# ============================================================================
# USER FIXTURES
# ============================================================================

@pytest.fixture
def admin_user(db, company, head_office):
    """
    Create admin user with full permissions.
    
    Args:
        company: Test company fixture
        head_office: Head office branch fixture
        
    Returns:
        User: Admin user instance
    """
    user = User.objects.create_user(
        username='admin',
        email='admin@testcompany.com',
        password='AdminPass123!',
        company=company,
        role='admin',
        is_staff=True,
        is_superuser=True
    )
    user.branches.add(head_office)
    return user


@pytest.fixture
def manager_user(db, company, branch):
    """
    Create manager user with branch-level permissions.
    
    Args:
        company: Test company fixture
        branch: Branch fixture
        
    Returns:
        User: Manager user instance
    """
    user = User.objects.create_user(
        username='manager',
        email='manager@testcompany.com',
        password='ManagerPass123!',
        company=company,
        role='manager'
    )
    user.branches.add(branch)
    
    # Set as branch manager
    branch.manager = user
    branch.manager_assigned_at = timezone.now()
    branch.manager_assigned_by = user
    branch.save()
    
    return user


@pytest.fixture
def regular_user(db, company, branch):
    """
    Create regular user with limited permissions.
    
    Args:
        company: Test company fixture
        branch: Branch fixture
        
    Returns:
        User: Regular user instance
    """
    user = User.objects.create_user(
        username='user',
        email='user@testcompany.com',
        password='UserPass123!',
        company=company,
        role='user'
    )
    user.branches.add(branch)
    return user


@pytest.fixture
def user2(db, company, branch2):
    """
    Create second regular user for transfer testing.
    
    Args:
        company: Test company fixture
        branch2: Second branch fixture
        
    Returns:
        User: Second user instance
    """
    user = User.objects.create_user(
        username='user2',
        email='user2@testcompany.com',
        password='UserPass123!',
        company=company,
        role='user'
    )
    user.branches.add(branch2)
    return user


# ============================================================================
# ASSET FIXTURES
# ============================================================================

@pytest.fixture
def category(db, company):
    """
    Create asset category with dynamic fields.
    
    Args:
        company: Test company fixture
        
    Returns:
        AssetCategory: Category instance with dynamic fields
    """
    return AssetCategory.objects.create(
        company=company,
        name='Laptops',
        description='Laptop computers',
        dynamic_fields=[
            {
                'name': 'serial_number',
                'label': 'Serial Number',
                'type': 'text',
                'required': True
            },
            {
                'name': 'model',
                'label': 'Model',
                'type': 'text',
                'required': True
            },
            {
                'name': 'ram',
                'label': 'RAM (GB)',
                'type': 'number',
                'required': False
            }
        ]
    )


@pytest.fixture
def asset(db, company, branch, category, regular_user):
    """
    Create test asset with proper multi-tenancy.
    
    Args:
        company: Test company fixture
        branch: Branch fixture
        category: Category fixture
        regular_user: User fixture
        
    Returns:
        Asset: Test asset instance
    """
    return Asset.objects.create(
        company=company,
        branch=branch,
        category=category,
        name='Test Laptop',
        status=Asset.STATUS_ACTIVE,
        assigned_to=regular_user,
        dynamic_data={
            'serial_number': 'SN123456',
            'model': 'ThinkPad X1',
            'ram': 16
        }
    )


@pytest.fixture
def assets_bulk(db, company, branch, category):
    """
    Create multiple assets for performance testing.
    
    Args:
        company: Test company fixture
        branch: Branch fixture
        category: Category fixture
        
    Returns:
        list: List of 100 asset instances
    """
    assets = []
    for i in range(100):
        asset = Asset.objects.create(
            company=company,
            branch=branch,
            category=category,
            name=f'Asset {i+1}',
            status=Asset.STATUS_ACTIVE,
            dynamic_data={
                'serial_number': f'SN{i+1:06d}',
                'model': f'Model-{i % 10}',
                'ram': 8 + (i % 3) * 8
            }
        )
        assets.append(asset)
    return assets


# ============================================================================
# TRANSFER FIXTURES
# ============================================================================

@pytest.fixture
def transfer(db, company, asset, regular_user, user2):
    """
    Create asset transfer for workflow testing.
    
    Args:
        company: Test company fixture
        asset: Asset fixture
        regular_user: From user fixture
        user2: To user fixture
        
    Returns:
        AssetTransfer: Transfer instance
    """
    return AssetTransfer.objects.create(
        company=company,
        asset=asset,
        initiator=regular_user,
        from_user=regular_user,
        to_user=user2,
        from_branch=regular_user.branches.first(),
        to_branch=user2.branches.first(),
        state=AssetTransfer.TransferState.PENDING_RECEIVER,
        reason='Equipment upgrade'
    )


# ============================================================================
# CLIENT FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """
    Provide Django test client.
    
    Returns:
        Client: Django test client instance
    """
    return Client()


@pytest.fixture
def authenticated_client(client, admin_user):
    """
    Provide authenticated client with admin user.
    
    Args:
        client: Django test client
        admin_user: Admin user fixture
        
    Returns:
        Client: Authenticated client instance
    """
    client.force_login(admin_user)
    return client


@pytest.fixture
def manager_client(client, manager_user):
    """
    Provide authenticated client with manager user.
    
    Args:
        client: Django test client
        manager_user: Manager user fixture
        
    Returns:
        Client: Authenticated manager client
    """
    client.force_login(manager_user)
    return client


@pytest.fixture
def user_client(client, regular_user):
    """
    Provide authenticated client with regular user.
    
    Args:
        client: Django test client
        regular_user: Regular user fixture
        
    Returns:
        Client: Authenticated user client
    """
    client.force_login(regular_user)
    return client


# ============================================================================
# PERMISSION FIXTURES
# ============================================================================

@pytest.fixture
def permission_matrix(db):
    """
    Create role permission matrix for testing.
    
    Returns:
        RolePermissionMatrix: Permission matrix instance
    """
    matrix, created = RolePermissionMatrix.objects.get_or_create(
        role='admin',
        defaults={
            'permissions': {
                'view_assets': True,
                'create_assets': True,
                'edit_assets': True,
                'delete_assets': True,
                'transfer_assets': True,
                'approve_transfers': True,
                'view_reports': True,
                'manage_users': True,
                'manage_branches': True,
                'manage_categories': True,
            }
        }
    )
    return matrix


# ============================================================================
# PERFORMANCE TESTING UTILITIES
# ============================================================================

@pytest.fixture
def query_counter():
    """
    Utility to count database queries for performance testing.
    
    Usage:
        with query_counter() as counter:
            # perform operations
            assert counter.count < 20
    """
    from django.test.utils import CaptureQueriesContext
    from django.db import connection
    
    class QueryCounter:
        def __init__(self):
            self.context = None
            
        def __enter__(self):
            self.context = CaptureQueriesContext(connection)
            self.context.__enter__()
            return self
            
        def __exit__(self, *args):
            self.context.__exit__(*args)
            
        @property
        def count(self):
            return len(self.context.captured_queries) if self.context else 0
            
        @property
        def queries(self):
            return self.context.captured_queries if self.context else []
    
    return QueryCounter


@pytest.fixture
def performance_timer():
    """
    Utility to measure execution time for performance testing.
    
    Usage:
        with performance_timer() as timer:
            # perform operations
            assert timer.elapsed < 1.0  # seconds
    """
    import time
    
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, *args):
            self.end_time = time.time()
            
        @property
        def elapsed(self):
            if self.end_time and self.start_time:
                return self.end_time - self.start_time
            return 0
    
    return PerformanceTimer


# ============================================================================
# CLEANUP HOOKS
# ============================================================================

@pytest.fixture(autouse=True)
def reset_sequences(db):
    """
    Reset database sequences after each test for consistency.
    This ensures predictable IDs in tests.
    """
    yield
    # Cleanup happens after test
    from django.core.management import call_command
    from django.db import connection
    
    if connection.vendor == 'postgresql':
        # Reset PostgreSQL sequences
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT setval(pg_get_serial_sequence('"' || table_name || '"', 'id'), 1, false)
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name NOT LIKE '%_pkey';
            """)
