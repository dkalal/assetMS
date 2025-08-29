#!/usr/bin/env python
"""
Enterprise Asset Management System - Test Runner
Run comprehensive tests to verify system functionality
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line

def run_tests():
    """Run the enterprise test suite"""
    
    print("🚀 Enterprise Asset Management System - Test Suite")
    print("=" * 60)
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
    django.setup()
    
    # Run migrations first
    print("📋 Running database migrations...")
    execute_from_command_line(['manage.py', 'migrate', '--verbosity=0'])
    
    # Run tests
    print("🧪 Running automated tests...")
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False)
    failures = test_runner.run_tests(['tests.test_enterprise_system'])
    
    # Print results
    print("\n" + "=" * 60)
    if failures:
        print(f"❌ {failures} test(s) failed")
        print("\n📋 MANUAL TESTING REQUIRED:")
        print_manual_tests()
        return False
    else:
        print("✅ All automated tests passed!")
        print("\n📋 MANUAL TESTING CHECKLIST:")
        print_manual_tests()
        return True

def print_manual_tests():
    """Print manual testing checklist"""
    
    manual_tests = [
        "🎨 VISUAL CONSISTENCY:",
        "   • Visit all pages and verify consistent gradient background",
        "   • Test responsive design on mobile/tablet/desktop viewports",
        "   • Verify glass morphism effects on cards and modals",
        "   • Check hover effects and animations work smoothly",
        "",
        "♿ ACCESSIBILITY:",
        "   • Use Tab key to navigate through all interactive elements",
        "   • Test with screen reader (NVDA, JAWS, or VoiceOver)",
        "   • Verify interface works at 200% browser zoom",
        "   • Check color contrast meets WCAG standards",
        "",
        "⚡ PERFORMANCE:",
        "   • Use browser dev tools to check page load times (<3s)",
        "   • Monitor network requests and file sizes",
        "   • Test with throttled network connection",
        "   • Verify smooth scrolling and animations",
        "",
        "🌐 CROSS-BROWSER:",
        "   • Test in Chrome, Firefox, Safari, Edge",
        "   • Verify mobile browsers (iOS Safari, Android Chrome)",
        "   • Check CSS Grid and Flexbox support",
        "   • Test JavaScript functionality across browsers",
        "",
        "🔧 FUNCTIONALITY:",
        "   • Test all forms submit correctly with validation",
        "   • Verify modals open/close with proper focus management",
        "   • Test CRUD operations for assets and settings",
        "   • Check search, filtering, and sorting features",
        "",
        "🔐 SECURITY:",
        "   • Verify role-based access control works",
        "   • Test CSRF protection on forms",
        "   • Check session management and logout",
        "   • Verify unauthorized access is blocked",
        "",
        "📱 URLS TO TEST:",
        "   • http://127.0.0.1:8000/dashboard/",
        "   • http://127.0.0.1:8000/assets/",
        "   • http://127.0.0.1:8000/settings/",
        "   • http://127.0.0.1:8000/settings/security/",
        "   • http://127.0.0.1:8000/settings/organization/",
        "   • http://127.0.0.1:8000/reports/",
        "   • http://127.0.0.1:8000/audit/",
        "   • http://127.0.0.1:8000/scan/",
        "   • http://127.0.0.1:8000/assets/register/",
        "   • http://127.0.0.1:8000/assets/bulk-import/",
    ]
    
    for test in manual_tests:
        print(test)

def check_system_requirements():
    """Check if system meets requirements"""
    
    print("🔍 Checking system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check Django installation
    try:
        import django
        print(f"✅ Django {django.get_version()} installed")
    except ImportError:
        print("❌ Django not installed")
        return False
    
    # Check required packages
    required_packages = ['django', 'pillow']
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            return False
    
    return True

if __name__ == '__main__':
    print("🏢 Enterprise Asset Management System")
    print("🧪 Professional Test Suite")
    print("=" * 60)
    
    # Check requirements
    if not check_system_requirements():
        print("\n❌ System requirements not met")
        sys.exit(1)
    
    # Run tests
    success = run_tests()
    
    if success:
        print("\n🎉 System ready for production!")
        print("📋 Complete manual testing checklist above")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed - review and fix issues")
        sys.exit(1)