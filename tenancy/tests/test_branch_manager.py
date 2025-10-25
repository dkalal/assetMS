"""
Comprehensive test suite for Branch Manager functionality.

Tests cover:
- Branch model validation
- Manager assignment service
- Admin interface
- Permissions and access control
- Audit logging
- Notifications
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from tenancy.models import Alert, Branch, Company
from tenancy.services import BranchManagerService
from audit.models import AuditLog

User = get_user_model()


class BranchManagerModelTests(TestCase):
    """Test Branch model with manager fields."""

    def setUp(self):
        """Set up test data."""
        self.company = Company.objects.create(name="Test Company")
        
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role=User.ADMIN,
            company=self.company
        )
        
        self.manager = User.objects.create_user(
            username="manager",
            email="manager@test.com",
            password="testpass123",
            role=User.MANAGER,
            company=self.company
        )
        
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
            role=User.USER,
            company=self.company
        )
        
        self.branch = Branch.objects.create(
            company=self.company,
            name="Main Branch",
            code="MAIN",
            is_active=True
        )

    def test_branch_can_have_manager(self):
        """Test that a branch can be assigned a manager."""
        self.branch.manager = self.manager
        self.branch.manager_assigned_at = timezone.now()
        self.branch.manager_assigned_by = self.admin
        self.branch.save()
        
        self.branch.refresh_from_db()
        self.assertEqual(self.branch.manager, self.manager)
        self.assertIsNotNone(self.branch.manager_assigned_at)
        self.assertEqual(self.branch.manager_assigned_by, self.admin)

    def test_branch_manager_must_belong_to_same_company(self):
        """Test that manager must belong to the same company as branch."""
        other_company = Company.objects.create(name="Other Company")
        other_manager = User.objects.create_user(
            username="other_manager",
            email="other@test.com",
            password="testpass123",
            role=User.MANAGER,
            company=other_company
        )
        
        self.branch.manager = other_manager
        
        with self.assertRaises(ValidationError) as context:
            self.branch.full_clean()
        
        self.assertIn("same company", str(context.exception).lower())

    def test_branch_manager_must_have_appropriate_role(self):
        """Test that only managers and admins can be assigned as branch managers."""
        self.branch.manager = self.regular_user
        
        with self.assertRaises(ValidationError) as context:
            self.branch.full_clean()
        
        self.assertIn("role", str(context.exception).lower())

    def test_admin_can_be_branch_manager(self):
        """Test that admin users can be assigned as branch managers."""
        self.branch.manager = self.admin
        self.branch.full_clean()  # Should not raise
        self.branch.save()
        
        self.assertEqual(self.branch.manager, self.admin)


class BranchManagerServiceTests(TestCase):
    """Test BranchManagerService business logic."""

    def setUp(self):
        """Set up test data."""
        self.company = Company.objects.create(name="Test Company")
        
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role=User.ADMIN,
            company=self.company
        )
        
        self.manager1 = User.objects.create_user(
            username="manager1",
            email="manager1@test.com",
            password="testpass123",
            role=User.MANAGER,
            company=self.company
        )
        
        self.manager2 = User.objects.create_user(
            username="manager2",
            email="manager2@test.com",
            password="testpass123",
            role=User.MANAGER,
            company=self.company
        )
        
        self.branch = Branch.objects.create(
            company=self.company,
            name="Main Branch",
            code="MAIN",
            is_active=True
        )

    def test_assign_manager_success(self):
        """Test successful manager assignment."""
        branch = BranchManagerService.assign_manager(
            branch=self.branch,
            new_manager=self.manager1,
            assigned_by=self.admin,
            notes="Initial assignment"
        )
        
        self.assertEqual(branch.manager, self.manager1)
        self.assertIsNotNone(branch.manager_assigned_at)
        self.assertEqual(branch.manager_assigned_by, self.admin)

    def test_assign_manager_creates_audit_log(self):
        """Test that manager assignment creates audit log."""
        initial_count = AuditLog.objects.count()
        
        BranchManagerService.assign_manager(
            branch=self.branch,
            new_manager=self.manager1,
            assigned_by=self.admin
        )
        
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        
        log = AuditLog.objects.latest("timestamp")
        self.assertEqual(log.action, "branch_manager_assigned")
        self.assertEqual(log.user, self.admin)
        self.assertEqual(log.related_user, self.manager1)
        self.assertEqual(log.branch, self.branch)

    def test_assign_manager_creates_notification(self):
        """Test that manager assignment creates notification."""
        initial_count = Alert.objects.count()
        
        BranchManagerService.assign_manager(
            branch=self.branch,
            new_manager=self.manager1,
            assigned_by=self.admin,
            notify_users=True
        )
        
        # Should create one alert for the new manager
        self.assertEqual(Alert.objects.count(), initial_count + 1)
        
        alert = Alert.objects.latest("id")
        self.assertEqual(alert.recipient, self.manager1)
        self.assertEqual(alert.level, Alert.LEVEL_INFO)
        self.assertIn(self.branch.name, alert.message)

    def test_replace_manager_notifies_both(self):
        """Test that replacing a manager notifies both old and new managers."""
        # Assign initial manager
        self.branch.manager = self.manager1
        self.branch.save()
        
        initial_count = Alert.objects.count()
        
        # Replace with new manager
        BranchManagerService.assign_manager(
            branch=self.branch,
            new_manager=self.manager2,
            assigned_by=self.admin,
            notify_users=True
        )
        
        # Should create two alerts: one for old manager, one for new
        self.assertEqual(Alert.objects.count(), initial_count + 2)

    def test_assign_manager_stores_history(self):
        """Test that manager assignments are stored in metadata history."""
        BranchManagerService.assign_manager(
            branch=self.branch,
            new_manager=self.manager1,
            assigned_by=self.admin,
            notes="Initial assignment"
        )
        
        self.branch.refresh_from_db()
        self.assertIn('manager_history', self.branch.metadata)
        self.assertEqual(len(self.branch.metadata['manager_history']), 1)
        
        history = self.branch.metadata['manager_history'][0]
        self.assertEqual(history['to_manager_username'], self.manager1.username)
        self.assertEqual(history['notes'], "Initial assignment")

    def test_remove_manager_success(self):
        """Test successful manager removal."""
        self.branch.manager = self.manager1
        self.branch.save()
        
        branch = BranchManagerService.remove_manager(
            branch=self.branch,
            removed_by=self.admin,
            reason="Restructuring"
        )
        
        self.assertIsNone(branch.manager)
        self.assertIsNone(branch.manager_assigned_at)

    def test_remove_manager_creates_audit_log(self):
        """Test that manager removal creates audit log."""
        self.branch.manager = self.manager1
        self.branch.save()
        
        initial_count = AuditLog.objects.count()
        
        BranchManagerService.remove_manager(
            branch=self.branch,
            removed_by=self.admin,
            reason="Restructuring"
        )
        
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        
        log = AuditLog.objects.latest("timestamp")
        self.assertEqual(log.action, "branch_manager_removed")

    def test_remove_manager_when_none_assigned_raises_error(self):
        """Test that removing manager when none assigned raises error."""
        with self.assertRaises(ValidationError):
            BranchManagerService.remove_manager(
                branch=self.branch,
                removed_by=self.admin
            )

    def test_get_manager_statistics(self):
        """Test getting manager statistics."""
        # Assign manager to branch
        self.branch.manager = self.manager1
        self.branch.manager_assigned_at = timezone.now()
        self.branch.save()
        
        stats = BranchManagerService.get_manager_statistics(
            self.manager1,
            self.company
        )
        
        self.assertEqual(stats['manager'], self.manager1)
        self.assertEqual(stats['branch_count'], 1)
        self.assertIn(self.branch, stats['branches'])


class BranchManagerManagementViewTests(TestCase):
    """Test BranchManagerManagementView."""

    def setUp(self):
        """Set up test data."""
        self.company = Company.objects.create(name="Test Company")
        
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role=User.ADMIN,
            company=self.company
        )
        
        self.manager = User.objects.create_user(
            username="manager",
            email="manager@test.com",
            password="testpass123",
            role=User.MANAGER,
            company=self.company
        )
        
        self.user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
            role=User.USER,
            company=self.company
        )
        
        self.branch = Branch.objects.create(
            company=self.company,
            name="Main Branch",
            code="MAIN",
            is_active=True
        )
        
        self.client = Client()

    def test_access_requires_admin_role(self):
        """Test that only admins can access the view."""
        url = reverse("branch_manager_management")
        
        # Unauthenticated
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # Regular user
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertRedirects(response, reverse("dashboard"))
        
        # Manager (should be denied)
        self.client.force_login(self.manager)
        response = self.client.get(url)
        self.assertRedirects(response, reverse("dashboard"))
        
        # Admin (should succeed)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_displays_branches(self):
        """Test that view displays all company branches."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("branch_manager_management"))
        
        self.assertContains(response, self.branch.name)
        self.assertContains(response, self.branch.code)

    def test_successful_manager_assignment(self):
        """Test successful manager assignment via form."""
        self.client.force_login(self.admin)
        
        response = self.client.post(
            reverse("branch_manager_management"),
            {
                "branch": self.branch.pk,
                "manager": self.manager.pk,
                "notes": "Test assignment",
                "notify_users": True,
            }
        )
        
        self.assertRedirects(response, reverse("branch_manager_management"))
        
        self.branch.refresh_from_db()
        self.assertEqual(self.branch.manager, self.manager)

    def test_manager_removal_via_form(self):
        """Test manager removal by submitting empty manager."""
        self.branch.manager = self.manager
        self.branch.save()
        
        self.client.force_login(self.admin)
        
        response = self.client.post(
            reverse("branch_manager_management"),
            {
                "branch": self.branch.pk,
                "manager": "",  # Empty = remove
                "notes": "Removing manager",
                "notify_users": True,
            }
        )
        
        self.assertRedirects(response, reverse("branch_manager_management"))
        
        self.branch.refresh_from_db()
        self.assertIsNone(self.branch.manager)


class BranchManagerPermissionTests(TestCase):
    """Test permission decorators for branch managers."""

    def setUp(self):
        """Set up test data."""
        self.company = Company.objects.create(name="Test Company")
        
        self.manager = User.objects.create_user(
            username="manager",
            email="manager@test.com",
            password="testpass123",
            role=User.MANAGER,
            company=self.company
        )
        
        self.user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
            role=User.USER,
            company=self.company
        )
        
        self.branch = Branch.objects.create(
            company=self.company,
            name="Main Branch",
            code="MAIN",
            is_active=True,
            manager=self.manager
        )

    def test_branch_manager_required_decorator(self):
        """Test branch_manager_required decorator."""
        from tenancy.decorators import branch_manager_required
        from django.http import HttpResponse
        
        @branch_manager_required
        def test_view(request):
            return HttpResponse("Success")
        
        # Create mock request
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Test with manager
        request = factory.get('/')
        request.user = self.manager
        response = test_view(request)
        self.assertEqual(response.status_code, 200)

    def test_manager_or_admin_required_decorator(self):
        """Test manager_or_admin_required decorator."""
        from tenancy.decorators import manager_or_admin_required
        from django.http import HttpResponse
        
        @manager_or_admin_required
        def test_view(request):
            return HttpResponse("Success")
        
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Test with manager
        request = factory.get('/')
        request.user = self.manager
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
