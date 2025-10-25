from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from tenancy.forms import UserBranchAssignmentForm
from tenancy.models import Alert, Branch, Company, UserBranch
from audit.models import AuditLog

User = get_user_model()


class UserBranchManagementViewTests(TestCase):
    """
    Comprehensive test suite for admin user branch management functionality.
    
    Tests cover:
    - Access control and permissions
    - Company scoping and isolation
    - Form validation
    - Primary branch assignment
    - Audit logging
    - Alert notifications
    """

    def setUp(self):
        """Set up test data for each test method."""
        # Create two companies for isolation testing
        self.company1 = Company.objects.create(name="Company One")
        self.company2 = Company.objects.create(name="Company Two")

        # Create branches for company1
        self.branch1_hq = Branch.objects.create(
            company=self.company1,
            name="HQ",
            code="HQ",
            is_head_office=True,
            is_active=True
        )
        self.branch1_branch_a = Branch.objects.create(
            company=self.company1,
            name="Branch A",
            code="BRA",
            is_active=True
        )
        self.branch1_inactive = Branch.objects.create(
            company=self.company1,
            name="Inactive Branch",
            code="INACT",
            is_active=False
        )

        # Create branch for company2
        self.branch2_hq = Branch.objects.create(
            company=self.company2,
            name="Company 2 HQ",
            code="C2HQ",
            is_head_office=True,
            is_active=True
        )

        # Create users
        self.admin1 = User.objects.create_user(
            username="admin1",
            email="admin1@company1.com",
            password="testpass123",
            role=User.ADMIN,
            company=self.company1
        )
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@company1.com",
            password="testpass123",
            role=User.USER,
            company=self.company1
        )
        self.manager1 = User.objects.create_user(
            username="manager1",
            email="manager1@company1.com",
            password="testpass123",
            role=User.MANAGER,
            company=self.company1
        )
        self.admin2 = User.objects.create_user(
            username="admin2",
            email="admin2@company2.com",
            password="testpass123",
            role=User.ADMIN,
            company=self.company2
        )

        # Create initial memberships
        UserBranch.objects.create(
            user=self.user1,
            company=self.company1,
            branch=self.branch1_hq,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.user1,
            company=self.company1,
            branch=self.branch1_branch_a,
            is_primary=False
        )

        self.client = Client()

    def test_access_requires_admin_role(self):
        """Test that only admins can access the user branch management view."""
        url = reverse("user_branch_management")

        # Test unauthenticated access
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Test regular user access (should be denied)
        self.client.force_login(self.user1)
        response = self.client.get(url)
        self.assertRedirects(response, reverse("dashboard"))

        # Test manager access (should be denied)
        self.client.force_login(self.manager1)
        response = self.client.get(url)
        self.assertRedirects(response, reverse("dashboard"))

        # Test admin access (should succeed)
        self.client.force_login(self.admin1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User Branch Management")

    def test_view_displays_company_users_only(self):
        """Test that view only displays users from the admin's company."""
        self.client.force_login(self.admin1)
        response = self.client.get(reverse("user_branch_management"))
        
        # Should contain company1 users
        self.assertContains(response, self.user1.username)
        self.assertContains(response, self.manager1.username)
        
        # Should NOT contain company2 users
        self.assertNotContains(response, self.admin2.username)

    def test_form_validates_company_scoping(self):
        """Test that form validates users and branches belong to same company."""
        # Try to assign company2 branch to company1 user
        # The form's queryset filtering will prevent this at the field level
        form = UserBranchAssignmentForm(
            data={
                "user": self.user1.pk,
                "primary_branch": self.branch2_hq.pk,
            },
            company=self.company1,
            admin_user=self.admin1
        )
        
        # Form should be invalid because branch2_hq is not in the queryset
        self.assertFalse(form.is_valid())
        # Django's ModelChoiceField validation message
        self.assertIn("valid choice", str(form.errors).lower())

    def test_form_rejects_inactive_branches(self):
        """Test that form rejects inactive branches as primary."""
        # The form's queryset only includes active branches
        # So inactive branch won't be in the available choices
        form = UserBranchAssignmentForm(
            data={
                "user": self.user1.pk,
                "primary_branch": self.branch1_inactive.pk,
            },
            company=self.company1,
            admin_user=self.admin1
        )
        
        # Form should be invalid because inactive branch is not in queryset
        self.assertFalse(form.is_valid())
        # Django's ModelChoiceField validation message
        self.assertIn("valid choice", str(form.errors).lower())

    def test_successful_primary_branch_assignment(self):
        """Test successful primary branch assignment with all side effects."""
        self.client.force_login(self.admin1)
        
        # Verify initial state
        initial_membership = UserBranch.objects.get(
            user=self.user1,
            company=self.company1,
            is_primary=True
        )
        self.assertEqual(initial_membership.branch, self.branch1_hq)
        
        # Submit form to change primary branch
        response = self.client.post(
            reverse("user_branch_management"),
            {
                "user": self.user1.pk,
                "primary_branch": self.branch1_branch_a.pk,
            }
        )
        
        # Should redirect on success
        self.assertRedirects(response, reverse("user_branch_management"))
        
        # Verify primary branch was updated
        new_membership = UserBranch.objects.get(
            user=self.user1,
            company=self.company1,
            is_primary=True
        )
        self.assertEqual(new_membership.branch, self.branch1_branch_a)
        
        # Verify old primary was cleared
        old_membership = UserBranch.objects.get(
            user=self.user1,
            company=self.company1,
            branch=self.branch1_hq
        )
        self.assertFalse(old_membership.is_primary)

    def test_audit_log_created_on_assignment(self):
        """Test that audit log is created when primary branch is assigned."""
        self.client.force_login(self.admin1)
        
        initial_count = AuditLog.objects.count()
        
        self.client.post(
            reverse("user_branch_management"),
            {
                "user": self.user1.pk,
                "primary_branch": self.branch1_branch_a.pk,
            }
        )
        
        # Verify audit log was created
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        
        # AuditLog uses 'timestamp' field, not 'created_at'
        log = AuditLog.objects.latest("timestamp")
        self.assertEqual(log.action, "user_primary_branch_updated")
        self.assertEqual(log.user, self.admin1)
        self.assertEqual(log.related_user, self.user1)
        self.assertEqual(log.branch, self.branch1_branch_a)
        self.assertIn(self.user1.username, log.details)
        self.assertIn(self.branch1_branch_a.name, log.details)

    def test_alert_created_for_affected_user(self):
        """Test that alert notification is created for the affected user."""
        self.client.force_login(self.admin1)
        
        initial_count = Alert.objects.count()
        
        self.client.post(
            reverse("user_branch_management"),
            {
                "user": self.user1.pk,
                "primary_branch": self.branch1_branch_a.pk,
            }
        )
        
        # Verify alert was created
        self.assertEqual(Alert.objects.count(), initial_count + 1)
        
        # Get the latest alert for the user
        alert = Alert.objects.filter(recipient=self.user1).latest("id")
        self.assertEqual(alert.recipient, self.user1)
        self.assertEqual(alert.level, Alert.LEVEL_INFO)
        self.assertIn(self.branch1_branch_a.name, alert.message)
        self.assertIn(self.admin1.username, alert.message)

    def test_form_queryset_scoping(self):
        """Test that form querysets are properly scoped to company."""
        form = UserBranchAssignmentForm(
            company=self.company1,
            admin_user=self.admin1
        )
        
        # User queryset should only contain company1 users
        user_pks = list(form.fields["user"].queryset.values_list("pk", flat=True))
        self.assertIn(self.user1.pk, user_pks)
        self.assertIn(self.manager1.pk, user_pks)
        self.assertNotIn(self.admin2.pk, user_pks)
        
        # Branch queryset should only contain company1 active branches
        branch_pks = list(form.fields["primary_branch"].queryset.values_list("pk", flat=True))
        self.assertIn(self.branch1_hq.pk, branch_pks)
        self.assertIn(self.branch1_branch_a.pk, branch_pks)
        self.assertNotIn(self.branch1_inactive.pk, branch_pks)
        self.assertNotIn(self.branch2_hq.pk, branch_pks)

    def test_context_data_structure(self):
        """Test that view provides correct context data structure."""
        self.client.force_login(self.admin1)
        response = self.client.get(reverse("user_branch_management"))
        
        self.assertIn("users_data", response.context)
        self.assertIn("form", response.context)
        self.assertIn("active_branches", response.context)
        self.assertIn("total_users", response.context)
        
        # Verify users_data structure
        users_data = response.context["users_data"]
        self.assertGreater(len(users_data), 0)
        
        first_user_data = users_data[0]
        self.assertIn("user", first_user_data)
        self.assertIn("primary_branch", first_user_data)
        self.assertIn("all_branches", first_user_data)
        self.assertIn("membership_count", first_user_data)
