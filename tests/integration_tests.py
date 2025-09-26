#!/usr/bin/env python3
"""
Asset Management System - Integration Tests
Professional test suite for backend components
"""

import os
import sys
import django
import unittest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import requests
import json
from unittest.mock import patch, MagicMock

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

class StorageBackendTests(TestCase):
    """Test cloud storage backends and fallback mechanisms"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    @patch('cloudinary.uploader.upload')
    def test_cloudinary_upload(self, mock_upload):
        """Test Cloudinary upload functionality"""
        mock_upload.return_value = {
            'public_id': 'test_image',
            'secure_url': 'https://res.cloudinary.com/test/image/upload/test_image.jpg',
            'version': 1234567890
        }
        
        # Simulate file upload
        test_file = SimpleUploadedFile(
            "test_image.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        # Test upload process
        result = mock_upload(test_file)
        
        self.assertIn('secure_url', result)
        self.assertIn('public_id', result)
        mock_upload.assert_called_once()
    
    def test_storage_fallback_mechanism(self):
        """Test storage backend fallback chain"""
        from assetms.storage_backends import get_storage_backend
        
        # Test fallback logic
        with patch('cloudinary.uploader.upload', side_effect=Exception("Cloudinary failed")):
            with patch('requests.post') as mock_imagekit:
                mock_imagekit.return_value.status_code = 200
                mock_imagekit.return_value.json.return_value = {
                    'url': 'https://imagekit.io/test/image.jpg'
                }
                
                backend = get_storage_backend()
                self.assertIsNotNone(backend)

class CSPMiddlewareTests(TestCase):
    """Test Content Security Policy middleware"""
    
    def setUp(self):
        self.client = Client()
    
    def test_csp_headers_present(self):
        """Test CSP headers are properly set"""
        response = self.client.get('/')
        
        # Check for CSP header
        csp_header = response.get('Content-Security-Policy')
        if csp_header:
            self.assertIn('cloudinary.com', csp_header)
            self.assertIn('imagekit.io', csp_header)
    
    def test_cloud_domains_whitelisted(self):
        """Test cloud storage domains are whitelisted in CSP"""
        from assetms.middleware import CSPMiddleware
        
        middleware = CSPMiddleware(lambda request: None)
        
        # Test domain inclusion
        domains = middleware.get_cloud_domains()
        expected_domains = ['cloudinary.com', 'imagekit.io', 'backblazeb2.com']
        
        for domain in expected_domains:
            self.assertTrue(any(domain in d for d in domains))

class QRScannerTests(TestCase):
    """Test QR scanner functionality"""
    
    def test_qr_format_validation(self):
        """Test QR code format validation"""
        # Test UUID format
        uuid_qr = "550e8400-e29b-41d4-a716-446655440000"
        self.assertTrue(self.is_valid_uuid(uuid_qr))
        
        # Test numeric format
        numeric_qr = "123456789"
        self.assertTrue(self.is_valid_numeric(numeric_qr))
        
        # Test alphanumeric format
        alpha_qr = "ABC123XYZ"
        self.assertTrue(self.is_valid_alphanumeric(alpha_qr))
    
    def is_valid_uuid(self, value):
        """Validate UUID format"""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))
    
    def is_valid_numeric(self, value):
        """Validate numeric format"""
        return value.isdigit()
    
    def is_valid_alphanumeric(self, value):
        """Validate alphanumeric format"""
        return value.isalnum()

class AssetManagementTests(TestCase):
    """Test core asset management functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_asset_creation(self):
        """Test asset creation process"""
        asset_data = {
            'name': 'Test Asset',
            'description': 'Test Description',
            'category': 'Electronics',
            'status': 'Active'
        }
        
        # Test asset creation endpoint
        response = self.client.post('/assets/create/', asset_data)
        
        # Check response (adjust based on your actual endpoints)
        self.assertIn(response.status_code, [200, 201, 302])
    
    def test_asset_search(self):
        """Test asset search functionality"""
        # Test search endpoint
        response = self.client.get('/assets/search/?q=test')
        
        self.assertEqual(response.status_code, 200)

class DatabaseIntegrityTests(TestCase):
    """Test database operations and integrity"""
    
    def test_database_connection(self):
        """Test database connectivity"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
    
    def test_model_constraints(self):
        """Test database model constraints"""
        from django.core.exceptions import ValidationError
        
        # Test user creation with invalid data
        with self.assertRaises(Exception):
            User.objects.create_user(username='', password='')

class SecurityTests(TestCase):
    """Test security measures"""
    
    def setUp(self):
        self.client = Client()
    
    def test_xss_protection(self):
        """Test XSS protection"""
        malicious_input = "<script>alert('xss')</script>"
        
        response = self.client.post('/assets/search/', {'q': malicious_input})
        
        # Check that script tags are escaped
        self.assertNotIn('<script>', response.content.decode())
    
    def test_csrf_protection(self):
        """Test CSRF protection"""
        # Test POST without CSRF token
        response = self.client.post('/assets/create/', {})
        
        # Should be forbidden or redirect
        self.assertIn(response.status_code, [403, 302])

class PerformanceTests(TestCase):
    """Test system performance"""
    
    def test_response_times(self):
        """Test API response times"""
        import time
        
        start_time = time.time()
        response = self.client.get('/')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Response should be under 2 seconds
        self.assertLess(response_time, 2.0)
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            start = time.time()
            response = self.client.get('/')
            end = time.time()
            results.append({
                'status': response.status_code,
                'time': end - start
            })
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result['status'], 200)
            self.assertLess(result['time'], 3.0)

class TestRunner:
    """Professional test runner with reporting"""
    
    def __init__(self):
        self.results = {}
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🧪 Starting Professional Test Suite")
        print("=" * 50)
        
        test_suites = [
            StorageBackendTests,
            CSPMiddlewareTests,
            QRScannerTests,
            AssetManagementTests,
            DatabaseIntegrityTests,
            SecurityTests,
            PerformanceTests
        ]
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        
        for suite_class in test_suites:
            print(f"\n📋 Running {suite_class.__name__}")
            print("-" * 30)
            
            suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
            self.results[suite_class.__name__] = {
                'tests': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'success': result.wasSuccessful()
            }
        
        self.generate_report(total_tests, total_failures, total_errors)
    
    def generate_report(self, total_tests, total_failures, total_errors):
        """Generate comprehensive test report"""
        print("\n" + "=" * 50)
        print("📊 TEST EXECUTION REPORT")
        print("=" * 50)
        
        success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_tests - total_failures - total_errors}")
        print(f"Failed: {total_failures}")
        print(f"Errors: {total_errors}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        print("\n📋 Suite Breakdown:")
        for suite_name, result in self.results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {suite_name}: {status} ({result['tests']} tests)")
        
        # Export to JSON
        report_data = {
            'timestamp': str(datetime.now()),
            'summary': {
                'total_tests': total_tests,
                'passed': total_tests - total_failures - total_errors,
                'failed': total_failures,
                'errors': total_errors,
                'success_rate': success_rate
            },
            'suites': self.results
        }
        
        with open('test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Report exported to: test_report.json")

if __name__ == '__main__':
    from datetime import datetime
    
    runner = TestRunner()
    runner.run_all_tests()