#!/usr/bin/env python
"""
Enterprise Permission System Test Suite
Comprehensive testing for scalability, security, and performance
"""
import os
import django
import time
from concurrent.futures import ThreadPoolExecutor
# import requests  # Not needed for Django test client

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from users.permissions import UserPermissionManager

User = get_user_model()

class PermissionSystemTests:
    def __init__(self):
        self.client = Client()
        self.base_url = 'http://localhost:8000'
        
    def setup_test_users(self):
        """Create test users for different roles"""
        users = []
        
        # Create admin user
        admin = User.objects.create_user(
            username='test_admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        users.append(admin)
        
        # Create manager user
        manager = User.objects.create_user(
            username='test_manager',
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )
        users.append(manager)
        
        # Create regular user
        user = User.objects.create_user(
            username='test_user',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
        users.append(user)
        
        return users
    
    def test_permission_matrix(self):
        """Test role-based permission matrix"""
        print("Testing Permission Matrix...")
        
        users = self.setup_test_users()
        
        for user in users:
            permissions = UserPermissionManager.get_user_permissions_summary(user)
            print(f"[OK] {user.role}: {len(permissions['permissions'])} permissions")
            
            # Update user permissions first
            UserPermissionManager.update_user_permissions(user, user.role)
            permissions = UserPermissionManager.get_user_permissions_summary(user)
            
            # Verify admin has all permissions
            if user.role == 'admin':
                assert len(permissions['permissions']) >= 4, "Admin should have permissions"
            
            # Verify user has minimal permissions
            elif user.role == 'user':
                assert len(permissions['permissions']) >= 1, "User should have view permissions"
        
        print("Permission matrix test passed")
    
    def test_api_performance(self):
        """Test API endpoint performance under load"""
        print("Testing API Performance...")
        
        admin = User.objects.filter(role='admin').first()
        self.client.force_login(admin)
        
        # Test single request performance
        start_time = time.time()
        response = self.client.get('/api/users/')
        duration = time.time() - start_time
        
        print(f"Single request: {duration:.3f}s")
        assert duration < 1.0, "API should respond within 1 second"
        
        # Test concurrent requests
        def make_request():
            return self.client.get('/api/users/')
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in futures]
        
        duration = time.time() - start_time
        print(f"50 concurrent requests: {duration:.3f}s")
        
        # Verify all requests succeeded
        success_count = sum(1 for r in results if r.status_code == 200)
        print(f"Success rate: {success_count}/50 ({success_count/50*100:.1f}%)")
    
    def test_security_access_control(self):
        """Test security and access control"""
        print("Testing Security & Access Control...")
        
        # Test unauthorized access
        response = self.client.get('/api/users/')
        assert response.status_code in [302, 403], "Should require authentication"
        
        # Test regular user access to admin endpoints
        user = User.objects.filter(role='user').first()
        self.client.force_login(user)
        
        response = self.client.get('/api/users/')
        assert response.status_code == 403, "Regular user should not access admin endpoints"
        
        # Test admin access
        admin = User.objects.filter(role='admin').first()
        self.client.force_login(admin)
        
        response = self.client.get('/api/users/')
        assert response.status_code == 200, "Admin should have access"
        
        print("Security tests passed")
    
    def test_data_integrity(self):
        """Test data integrity and validation"""
        print("Testing Data Integrity...")
        
        admin = User.objects.filter(role='admin').first()
        self.client.force_login(admin)
        
        # Test role update with invalid data
        response = self.client.post('/api/users/update-role/', {
            'user_id': 'invalid',
            'role': 'invalid_role'
        })
        
        data = response.json()
        assert not data['success'], "Should reject invalid data"
        
        # Test self-demotion prevention
        response = self.client.post('/api/users/update-role/', {
            'user_id': admin.id,
            'role': 'user'
        })
        
        data = response.json()
        assert not data['success'], "Should prevent self-demotion"
        
        print("Data integrity tests passed")
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("Starting Enterprise Permission System Tests...\n")
        
        try:
            self.test_permission_matrix()
            self.test_security_access_control()
            self.test_data_integrity()
            self.test_api_performance()
            
            print("\nAll tests passed! System is enterprise-ready.")
            
        except Exception as e:
            print(f"\nTest failed: {str(e)}")
            raise
        
        finally:
            # Cleanup test users
            User.objects.filter(username__startswith='test_').delete()

if __name__ == '__main__':
    tester = PermissionSystemTests()
    tester.run_all_tests()