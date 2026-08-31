import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assets.models import Asset, AssetCategory, AssetTransfer
from tenancy.models import Branch, Company


User = get_user_model()


class AssetTransferApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Corp")
        self.branch = Branch.objects.create(company=self.company, name="HQ", code="HQ", is_head_office=True)
        self.category = AssetCategory.objects.create(company=self.company, name="Laptops")

        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            role=User.ADMIN,
            company=self.company,
        )
        self.holder = User.objects.create_user(
            username="holder",
            password="pass",
            role=User.USER,
            company=self.company,
        )
        self.receiver = User.objects.create_user(
            username="receiver",
            password="pass",
            role=User.USER,
            company=self.company,
        )

        self.asset = Asset.objects.create(
            company=self.company,
            branch=self.branch,
            category=self.category,
            assigned_to=self.holder,
            dynamic_data={"name": "MacBook Pro"},
        )

    def test_transfer_lifecycle_flow(self):
        self.client.force_login(self.admin)
        payload = {
            "asset_id": self.asset.id,
            "to_user_id": self.receiver.id,
            "to_branch_id": self.branch.id,
            "initiator_comment": "Please approve",
        }
        initiate_resp = self.client.post(
            reverse("assets:asset_transfer_initiate"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(initiate_resp.status_code, 201)
        data = initiate_resp.json()
        self.assertTrue(data["success"])
        transfer_id = data["transfer"]["id"]

        transfer = AssetTransfer.objects.get(pk=transfer_id)
        self.assertEqual(transfer.state, AssetTransfer.TransferState.PENDING_RECEIVER)
        self.assertEqual(transfer.initiator, self.admin)
        self.assertEqual(transfer.to_user, self.receiver)

        # Receiver views alerts and approves the transfer
        self.client.logout()
        self.client.force_login(self.receiver)

        alerts_resp = self.client.get(reverse("assets:asset_transfer_alerts"))
        self.assertEqual(alerts_resp.status_code, 200)
        alerts_payload = alerts_resp.json()
        self.assertTrue(alerts_payload["success"])
        alert_ids = [alert["id"] for alert in alerts_payload["alerts"]]
        self.assertGreater(len(alert_ids), 0)

        mark_resp = self.client.post(
            reverse("assets:asset_transfer_alerts"),
            data=json.dumps({"alert_ids": alert_ids, "action": "mark_read"}),
            content_type="application/json",
        )
        self.assertEqual(mark_resp.status_code, 200)
        self.assertTrue(mark_resp.json()["success"])

        receiver_decision_resp = self.client.post(
            reverse("assets:asset_transfer_receiver_decision"),
            data=json.dumps({
                "transfer_id": transfer_id,
                "decision": AssetTransfer.Decision.APPROVED,
            }),
            content_type="application/json",
        )
        self.assertEqual(receiver_decision_resp.status_code, 200)
        transfer.refresh_from_db()
        self.assertEqual(transfer.state, AssetTransfer.TransferState.AWAITING_ADMIN)

        # Admin completes the transfer
        self.client.logout()
        self.client.force_login(self.admin)
        admin_review_resp = self.client.post(
            reverse("assets:asset_transfer_admin_review"),
            data=json.dumps({
                "transfer_id": transfer_id,
                "decision": AssetTransfer.Decision.APPROVED,
                "comment": "Approved",
            }),
            content_type="application/json",
        )
        self.assertEqual(admin_review_resp.status_code, 200)

        transfer.refresh_from_db()
        self.asset.refresh_from_db()
        self.assertEqual(transfer.state, AssetTransfer.TransferState.COMPLETED)
        self.assertEqual(self.asset.assigned_to, self.receiver)
        self.assertEqual(self.asset.status, Asset.STATUS_ACTIVE)

    def test_assigned_holder_can_initiate_transfer(self):
        self.client.force_login(self.holder)
        response = self.client.post(
            reverse("assets:asset_transfer_initiate"),
            data=json.dumps({
                "asset_id": self.asset.id,
                "to_user_id": self.receiver.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AssetTransfer.objects.filter(initiator=self.holder, asset=self.asset).exists())
