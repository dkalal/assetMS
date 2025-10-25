from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from assets.models import Asset, AssetCategory
from tenancy.approval_models import ApprovalRequest
from tenancy.models import Alert, Branch, Company, UserBranch


User = get_user_model()


class AssetCreationApprovalTests(TestCase):
    """Automated coverage for asset creation approval workflow."""

    def setUp(self):
        self.company = Company.objects.create(name="Acme Corp")

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass123",
            role=User.ADMIN,
            company=self.company,
        )
        self.manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="pass123",
            role=User.MANAGER,
            company=self.company,
        )
        self.other_manager = User.objects.create_user(
            username="manager2",
            email="manager2@example.com",
            password="pass123",
            role=User.MANAGER,
            company=self.company,
        )
        self.regular_user = User.objects.create_user(
            username="employee",
            email="employee@example.com",
            password="pass123",
            role=User.USER,
            company=self.company,
        )

        self.branch = Branch.objects.create(
            company=self.company,
            name="Head Office",
            code="HQ",
            is_head_office=True,
            manager=self.manager,
        )
        self.secondary_branch = Branch.objects.create(
            company=self.company,
            name="Warehouse",
            code="WH",
            manager=self.other_manager,
        )

        self.category = AssetCategory.objects.create(
            company=self.company,
            name="Laptops",
        )
        
        # CRITICAL FIX: Create UserBranch assignments for multi-tenancy
        UserBranch.objects.create(
            user=self.admin,
            company=self.company,
            branch=self.branch,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.manager,
            company=self.company,
            branch=self.branch,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.other_manager,
            company=self.company,
            branch=self.secondary_branch,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.regular_user,
            company=self.company,
            branch=self.branch,
            is_primary=True
        )

    def create_asset_creation_request(self, *, branch, requested_by, assigned_to, title="New Asset"):
        """Helper to provision a pending asset creation approval request."""

        metadata = {
            "category_name": self.category.name,
            "asset_data": {
                "category_id": self.category.id,
                "branch_id": branch.id,
                "description": "MacBook Pro 14",
                "status": Asset.STATUS_ACTIVE,
                "dynamic_data": {
                    "name": f"{title} Unit",
                    "model": "2024",
                },
            },
        }

        return ApprovalRequest.objects.create(
            company=self.company,
            branch=branch,
            request_type=ApprovalRequest.TYPE_ASSET_CREATION,
            title=title,
            description=f"Approval for {title.lower()}",
            priority=ApprovalRequest.PRIORITY_HIGH,
            requested_by=requested_by,
            assigned_to=assigned_to,
            metadata=metadata,
        )

    def test_pending_requests_api_respects_role_and_branch_scoping(self):
        request_primary = self.create_asset_creation_request(
            branch=self.branch,
            requested_by=self.manager,
            assigned_to=self.admin,
            title="Executive Laptop",
        )
        request_secondary = self.create_asset_creation_request(
            branch=self.secondary_branch,
            requested_by=self.other_manager,
            assigned_to=self.admin,
            title="Warehouse Tablet",
        )

        # Admin can see every pending request in company scope
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api_pending_asset_creation_requests"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], 2)
        titles = {item["title"] for item in data["requests"]}
        self.assertSetEqual(titles, {request_primary.title, request_secondary.title})

        # Branch manager only sees requests for branches they manage
        self.client.logout()
        self.client.force_login(self.manager)
        manager_response = self.client.get(reverse("api_pending_asset_creation_requests"))
        self.assertEqual(manager_response.status_code, 200)
        manager_data = manager_response.json()
        self.assertTrue(manager_data["success"])
        self.assertEqual(manager_data["total"], 1)
        self.assertEqual(manager_data["requests"][0]["branch"]["id"], self.branch.id)

        # Regular employee lacks permission
        self.client.logout()
        self.client.force_login(self.regular_user)
        denied_response = self.client.get(reverse("api_pending_asset_creation_requests"))
        self.assertEqual(denied_response.status_code, 403)

    def test_quick_approve_flow_creates_asset_and_logs_audit(self):
        approval_request = self.create_asset_creation_request(
            branch=self.branch,
            requested_by=self.manager,
            assigned_to=self.admin,
            title="Data Science Laptop",
        )

        self.client.force_login(self.admin)
        url = reverse("api_quick_approve_asset_creation", args=[approval_request.id])
        response = self.client.post(url, data={"notes": "Approved instantly"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

        approval_request.refresh_from_db()
        self.assertEqual(approval_request.status, ApprovalRequest.STATUS_APPROVED)
        self.assertEqual(approval_request.approved_by, self.admin)
        self.assertIn("created_asset_id", approval_request.metadata)
        self.assertIn("created_asset_uuid", approval_request.metadata)

        created_asset = Asset.objects.get(pk=approval_request.metadata["created_asset_id"])
        self.assertEqual(created_asset.company, self.company)
        self.assertEqual(created_asset.branch, self.branch)
        self.assertEqual(created_asset.category, self.category)
        self.assertEqual(created_asset.dynamic_data.get("name"), "Data Science Laptop Unit")

        # Requester receives success alert
        self.assertTrue(
            Alert.objects.filter(
                recipient=self.manager,
                message__contains=approval_request.title,
                level=Alert.LEVEL_SUCCESS,
            ).exists()
        )

        # Audit log contains approval and asset creation entries
        approvals = AuditLog.objects.filter(action="approval_request_approved", user=self.admin)
        self.assertTrue(approvals.exists())
        asset_creations = AuditLog.objects.filter(action="asset_created_from_approval", user=self.admin)
        self.assertTrue(asset_creations.exists())

        # API response contains created asset details for follow-up flows
        self.assertEqual(payload["asset"]["id"], created_asset.id)
        self.assertEqual(payload["asset"]["uuid"], str(created_asset.uuid))
