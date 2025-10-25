from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assets.models import AssetCategory, AssetCategoryField
from tenancy.models import Company

User = get_user_model()


class AssetCategoryTenancyTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="Alpha Corp")
        self.company_b = Company.objects.create(name="Beta Corp")

        self.admin_a = User.objects.create_user(
            username="admin_a",
            password="pass",
            role=User.ADMIN,
            company=self.company_a,
        )
        self.admin_b = User.objects.create_user(
            username="admin_b",
            password="pass",
            role=User.ADMIN,
            company=self.company_b,
        )

        self.category_a = AssetCategory.objects.create(company=self.company_a, name="Laptops")
        self.category_b = AssetCategory.objects.create(company=self.company_b, name="Printers")

        self.field_a = AssetCategoryField.objects.create(
            company=self.company_a,
            category=self.category_a,
            key="serial_number",
            label="Serial Number",
            type="text",
            required=True,
        )

    def login(self, user):
        self.client.logout()
        logged_in = self.client.login(username=user.username, password="pass")
        self.assertTrue(logged_in, "Failed to authenticate test user")

    def test_api_categories_scoped_to_company(self):
        self.login(self.admin_a)
        response = self.client.get(reverse("api_categories"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        category_names = {item["name"] for item in payload.get("categories", [])}
        self.assertIn(self.category_a.name, category_names)
        self.assertNotIn(self.category_b.name, category_names)

    def test_create_category_assigns_company(self):
        self.login(self.admin_a)
        response = self.client.post(
            reverse("api_create_category"),
            data={"name": "Monitors", "description": "Display units"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("success"))
        new_category = AssetCategory.objects.get(pk=payload["category"]["id"])
        self.assertEqual(new_category.company, self.company_a)

    def test_admin_cannot_access_other_company_category_fields(self):
        self.login(self.admin_a)
        response = self.client.get(reverse("api_category_fields", args=[self.category_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_create_field_inherits_company(self):
        self.login(self.admin_a)
        response = self.client.post(
            reverse("api_create_field", args=[self.category_a.id]),
            data={
                "key": "asset_tag",
                "label": "Asset Tag",
                "type": "text",
                "required": "true",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("success"))
        field = AssetCategoryField.objects.get(pk=payload["field"]["id"])
        self.assertEqual(field.company, self.company_a)
        self.assertEqual(field.category, self.category_a)

    def test_update_field_enforces_company_scope(self):
        self.login(self.admin_a)
        response = self.client.post(
            reverse("api_update_field", args=[self.field_a.id]),
            data={
                "label": "Serial",
                "type": "text",
                "required": "false",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.field_a.refresh_from_db()
        self.assertEqual(self.field_a.label, "Serial")
        self.assertFalse(self.field_a.required)

    def test_delete_field_blocked_for_other_company(self):
        self.login(self.admin_b)
        response = self.client.post(
            reverse("api_delete_field", args=[self.field_a.id]),
            data={},
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(AssetCategoryField.objects.filter(pk=self.field_a.id).exists())
