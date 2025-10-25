from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from tenancy.models import Branch, Company, UserBranch

User = get_user_model()


class TenantSetupWizardTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Corp")
        self.admin = User.objects.create_user(
            username="tenantadmin",
            email="tenantadmin@example.com",
            password="pass1234",
            role=User.ADMIN,
            company=self.company,
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_access_requires_admin_role(self):
        response = self.client.get(reverse("tenant_setup_wizard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tenant Setup Wizard")

        self.admin.role = User.USER
        self.admin.save(update_fields=["role"])
        response = self.client.get(reverse("tenant_setup_wizard"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_company_step_updates_profile(self):
        payload = {
            "step": "company",
            "name": "Acme Corp",
            "address": "123 Street",
            "contact_person": "Jane Doe",
            "phone": "+123456",
            "email": "ops@acme.test",
            "timezone": "UTC",
        }
        response = self.client.post(reverse("tenant_setup_wizard"), payload)
        self.assertRedirects(response, reverse("tenant_setup_wizard") + "?step=branch")
        self.company.refresh_from_db()
        self.assertEqual(self.company.contact_person, "Jane Doe")

    def test_branch_step_creates_branch_and_primary_membership(self):
        payload = {
            "step": "branch",
            "name": "HQ",
            "code": "HQ",
            "is_head_office": "on",
            "set_as_primary": "on",
        }
        response = self.client.post(reverse("tenant_setup_wizard") + "?step=branch", payload)
        self.assertRedirects(response, reverse("tenant_setup_wizard") + "?step=summary")
        branch = Branch.objects.get(company=self.company, code="HQ")
        membership = UserBranch.objects.get(user=self.admin, branch=branch, company=self.company)
        self.assertTrue(membership.is_primary)

    def test_summary_requires_branch(self):
        response = self.client.get(reverse("tenant_setup_wizard") + "?step=summary")
        self.assertRedirects(response, reverse("tenant_setup_wizard") + "?step=branch")
