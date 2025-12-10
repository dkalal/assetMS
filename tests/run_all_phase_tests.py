"""
Comprehensive Test Runner for All Phases

This script runs all phase tests and generates a detailed report.
Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM testing standards

Usage:
    python tests/run_all_phase_tests.py
    python tests/run_all_phase_tests.py --phase 1
    python tests/run_all_phase_tests.py --verbose
"""

import sys
import os
import time
from io import StringIO

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')

import django
django.setup()

from django.test.runner import DiscoverRunner
from django.conf import settings


class PhaseTestRunner:
    """
    Custom test runner for phase-based testing
    """
    
    PHASES = {
        1: {
            'name': 'System Awareness & Initial Setup',
            'module': 'tests.test_phase1_system_setup',
            'description': 'Database, migrations, static files, security configuration'
        },
        2: {
            'name': 'User Onboarding & Authentication',
            'module': 'tests.test_phase2_authentication',
            'description': 'Login, logout, sessions, CSRF, account security'
        },
        3: {
            'name': 'Company & Branch Setup',
            'module': 'tests.test_phase3_company_branch',
            'description': 'Company creation, branch hierarchy, multi-tenancy'
        },
        4: {
            'name': 'User Management',
            'module': 'tests.test_phase4_user_management',
            'description': 'User creation, roles, permissions, RBAC'
        },
        5: {
            'name': 'Asset Categories & Fields',
            'module': 'tests.test_phase5_categories_fields',
            'description': 'Category management, dynamic fields, validation'
        }
    }
    
    def __init__(self, verbose=False, phase=None):
        self.verbose = verbose
        self.phase = phase
        self.results = {}
    
    def print_header(self):
        """Print test suite header"""
        print("\n" + "="*80)
        print("ASSET MANAGEMENT SYSTEM - COMPREHENSIVE TEST SUITE")
        print("="*80)
        print("World-Class Testing Standards")
        print("Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM")
        print("="*80 + "\n")
    
    def print_phase_header(self, phase_num):
        """Print phase header"""
        phase = self.PHASES[phase_num]
        print("\n" + "-"*80)
        print(f"PHASE {phase_num}: {phase['name']}")
        print("-"*80)
        print(f"Description: {phase['description']}")
        print(f"Module: {phase['module']}")
        print("-"*80 + "\n")
    
    def run_phase(self, phase_num):
        """Run tests for a specific phase"""
        phase = self.PHASES[phase_num]
        
        self.print_phase_header(phase_num)
        
        # Run tests
        runner = DiscoverRunner(verbosity=2 if self.verbose else 1)
        
        start_time = time.time()
        
        # Capture test output
        old_config = runner.setup_test_environment()
        old_db = runner.setup_databases()
        
        try:
            suite = runner.test_loader.loadTestsFromName(phase['module'])
            test_runner = runner.test_runner(
                verbosity=2 if self.verbose else 1
            )
            result = test_runner.run(suite)
            
            elapsed_time = time.time() - start_time
            
            # Store results
            self.results[phase_num] = {
                'name': phase['name'],
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped),
                'success': result.wasSuccessful(),
                'time': elapsed_time
            }
            
            # Print phase summary
            self.print_phase_summary(phase_num)
            
        finally:
            runner.teardown_databases(old_db)
            runner.teardown_test_environment()
        
        return result.wasSuccessful()
    
    def print_phase_summary(self, phase_num):
        """Print summary for a phase"""
        result = self.results[phase_num]
        
        print("\n" + "-"*80)
        print(f"PHASE {phase_num} SUMMARY")
        print("-"*80)
        print(f"Tests Run: {result['tests_run']}")
        print(f"Failures: {result['failures']}")
        print(f"Errors: {result['errors']}")
        print(f"Skipped: {result['skipped']}")
        print(f"Time: {result['time']:.2f}s")
        print(f"Status: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
        print("-"*80 + "\n")
    
    def print_final_summary(self):
        """Print final summary of all phases"""
        print("\n" + "="*80)
        print("FINAL TEST SUMMARY")
        print("="*80 + "\n")
        
        total_tests = sum(r['tests_run'] for r in self.results.values())
        total_failures = sum(r['failures'] for r in self.results.values())
        total_errors = sum(r['errors'] for r in self.results.values())
        total_skipped = sum(r['skipped'] for r in self.results.values())
        total_time = sum(r['time'] for r in self.results.values())
        
        # Phase-by-phase results
        for phase_num, result in sorted(self.results.items()):
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            print(f"Phase {phase_num}: {result['name']:<40} {status}")
            print(f"  Tests: {result['tests_run']}, "
                  f"Failures: {result['failures']}, "
                  f"Errors: {result['errors']}, "
                  f"Time: {result['time']:.2f}s")
        
        print("\n" + "-"*80)
        print(f"Total Tests Run: {total_tests}")
        print(f"Total Failures: {total_failures}")
        print(f"Total Errors: {total_errors}")
        print(f"Total Skipped: {total_skipped}")
        print(f"Total Time: {total_time:.2f}s")
        
        # Overall status
        all_passed = all(r['success'] for r in self.results.values())
        print("\n" + "="*80)
        if all_passed:
            print("✅ ALL PHASES PASSED - SYSTEM READY FOR PRODUCTION")
        else:
            print("❌ SOME PHASES FAILED - REVIEW ERRORS ABOVE")
        print("="*80 + "\n")
        
        # Coverage report
        self.print_coverage_report()
    
    def print_coverage_report(self):
        """Print test coverage report"""
        print("\n" + "="*80)
        print("TEST COVERAGE REPORT")
        print("="*80 + "\n")
        
        coverage_areas = {
            'System Setup': '✅' if 1 in self.results and self.results[1]['success'] else '❌',
            'Authentication': '✅' if 2 in self.results and self.results[2]['success'] else '❌',
            'Multi-Tenancy': '✅' if 3 in self.results and self.results[3]['success'] else '❌',
            'User Management': '✅' if 4 in self.results and self.results[4]['success'] else '❌',
            'Category Management': '✅' if 5 in self.results and self.results[5]['success'] else '❌',
        }
        
        for area, status in coverage_areas.items():
            print(f"{status} {area}")
        
        print("\n" + "="*80 + "\n")
    
    def run(self):
        """Run all tests or specific phase"""
        self.print_header()
        
        if self.phase:
            # Run specific phase
            if self.phase not in self.PHASES:
                print(f"❌ Error: Phase {self.phase} does not exist")
                print(f"Available phases: {list(self.PHASES.keys())}")
                return False
            
            success = self.run_phase(self.phase)
            return success
        else:
            # Run all phases
            all_success = True
            for phase_num in sorted(self.PHASES.keys()):
                success = self.run_phase(phase_num)
                if not success:
                    all_success = False
            
            self.print_final_summary()
            return all_success


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run comprehensive phase tests for Asset Management System'
    )
    parser.add_argument(
        '--phase',
        type=int,
        choices=[1, 2, 3, 4, 5],
        help='Run specific phase (1-5)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    runner = PhaseTestRunner(verbose=args.verbose, phase=args.phase)
    success = runner.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
