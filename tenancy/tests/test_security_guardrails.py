from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import checks
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views.generic import ListView

from assets.models import Asset, AssetCategory
from tenancy.access import accessible_branch_ids
from tenancy.decorators import branch_manager_required, manages_branch
from tenancy.mixins import CompanyScopedQuerysetMixin
from tenancy.models import Branch, Company, UserBranch


User = get_user_model()


class ScopedAssetList(CompanyScopedQuerysetMixin, ListView):
    model = Asset


class TenantSecurityGuardrailTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.company_a = Company.objects.create(name="Tenant A")
        self.company_b = Company.objects.create(name="Tenant B")
        self.branch_a1 = Branch.objects.create(
            company=self.company_a, name="A1", code="A1"
        )
        self.branch_a2 = Branch.objects.create(
            company=self.company_a, name="A2", code="A2"
        )
        self.branch_b = Branch.objects.create(
            company=self.company_b, name="B1", code="B1"
        )
        self.admin_a = User.objects.create_user(
            username="admin-a", password="pass", role="admin", company=self.company_a
        )
        self.manager_a = User.objects.create_user(
            username="manager-a",
            password="pass",
            role="manager",
            company=self.company_a,
        )
        self.unassigned_manager_a = User.objects.create_user(
            username="unassigned-manager-a",
            password="pass",
            role="manager",
            company=self.company_a,
        )
        self.branch_a1.manager = self.manager_a
        self.branch_a1.save(update_fields=["manager"])

        self.category_a = AssetCategory.objects.create(
            company=self.company_a, name="Equipment"
        )
        self.category_b = AssetCategory.objects.create(
            company=self.company_b, name="Equipment"
        )
        self.asset_a1 = Asset.objects.create(
            company=self.company_a,
            branch=self.branch_a1,
            category=self.category_a,
            description="tenant-a-branch-1",
        )
        self.asset_a2 = Asset.objects.create(
            company=self.company_a,
            branch=self.branch_a2,
            category=self.category_a,
            description="tenant-a-branch-2",
        )
        self.asset_b = Asset.objects.create(
            company=self.company_b,
            branch=self.branch_b,
            category=self.category_b,
            description="tenant-b",
        )

    def request_for(self, user, company, branch=None):
        request = self.factory.get("/")
        request.user = user
        request.company = company
        request.branch = branch
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def scoped_asset_ids(self, user, company, branch=None):
        view = ScopedAssetList()
        view.request = self.request_for(user, company, branch)
        return set(view.get_queryset().values_list("id", flat=True))

    def test_manager_scope_is_managed_and_explicit_branches_only(self):
        self.assertEqual(
            accessible_branch_ids(self.manager_a, self.company_a),
            frozenset({self.branch_a1.id}),
        )
        UserBranch.objects.create(
            user=self.manager_a,
            company=self.company_a,
            branch=self.branch_a2,
        )
        self.assertEqual(
            accessible_branch_ids(self.manager_a, self.company_a),
            frozenset({self.branch_a1.id, self.branch_a2.id}),
        )

    def test_manager_without_assignment_never_gets_tenant_fallback(self):
        self.assertEqual(
            accessible_branch_ids(self.unassigned_manager_a, self.company_a),
            frozenset(),
        )
        self.assertEqual(
            self.scoped_asset_ids(self.unassigned_manager_a, self.company_a), set()
        )

    def test_queryset_scope_excludes_other_branches_and_tenants(self):
        self.assertEqual(
            self.scoped_asset_ids(self.manager_a, self.company_a),
            {self.asset_a1.id},
        )
        self.assertEqual(
            self.scoped_asset_ids(self.manager_a, self.company_a, self.branch_a2),
            set(),
        )
        self.assertNotIn(
            self.asset_b.id,
            self.scoped_asset_ids(self.admin_a, self.company_a),
        )

    def test_tenant_mismatch_returns_no_branches_even_for_admin(self):
        self.assertEqual(
            accessible_branch_ids(self.admin_a, self.company_b), frozenset()
        )

    def test_tenant_admin_cannot_use_manages_branch_on_other_tenant(self):
        called = False

        @manages_branch()
        def protected_view(request, branch_id):
            nonlocal called
            called = True
            return HttpResponse("ok")

        response = protected_view(
            self.request_for(self.admin_a, self.company_a),
            branch_id=self.branch_b.id,
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(called)

    def test_branch_manager_decorator_ignores_cross_tenant_assignment(self):
        self.branch_b.manager = self.unassigned_manager_a
        self.branch_b.save(update_fields=["manager"])
        called = False

        @branch_manager_required
        def protected_view(request):
            nonlocal called
            called = True
            return HttpResponse("ok")

        response = protected_view(
            self.request_for(self.unassigned_manager_a, self.company_a)
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(called)

    def test_registered_security_structure_checks_pass(self):
        assetms_errors = [
            issue
            for issue in checks.run_checks(tags=[checks.Tags.security])
            if issue.id.startswith("assetms_security.")
        ]
        self.assertEqual(assetms_errors, [])
