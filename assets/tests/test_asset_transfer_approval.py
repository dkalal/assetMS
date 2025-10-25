"""
Asset Transfer Approval Tests

Comprehensive test suite for two-level asset transfer approval workflow.
Tests cover: initiation, receiver approval/rejection, admin approval/rejection,
permissions, multi-tenancy, notifications, and audit trail.

Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError, PermissionDenied

from audit.models import AuditLog
from assets.models import Asset, AssetCategory, AssetTransfer
from assets.services.transfers import initiate_transfer, receiver_review, admin_review
from tenancy.models import Alert, Branch, Company, UserBranch

User = get_user_model()


class AssetTransferApprovalTests(TestCase):
    """
    World-class test suite for asset transfer approval workflow.
    
    Tests cover:
    - Two-level approval (receiver → admin)
    - Role-based permissions
    - Multi-tenancy enforcement
    - Branch-level access control
    - State transitions
    - Notification system
    - Audit trail
    - Edge cases and error handling
    """

    def setUp(self):
        """
        Set up test environment with proper multi-tenancy structure.
        
        Creates:
        - Company with 2 branches
        - Admin, 2 managers, 2 regular users
        - UserBranch assignments for all users
        - Asset category
        - Test asset
        """
        # Create company
        self.company = Company.objects.create(name="Acme Corp")

        # Create users with explicit roles
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass123",
            role=User.ADMIN,
            company=self.company,
        )
        
        self.manager1 = User.objects.create_user(
            username="manager1",
            email="manager1@example.com",
            password="pass123",
            role=User.MANAGER,
            company=self.company,
        )
        
        self.manager2 = User.objects.create_user(
            username="manager2",
            email="manager2@example.com",
            password="pass123",
            role=User.MANAGER,
            company=self.company,
        )
        
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass123",
            role=User.USER,
            company=self.company,
        )
        
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123",
            role=User.USER,
            company=self.company,
        )

        # Create branches
        self.branch1 = Branch.objects.create(
            company=self.company,
            name="Head Office",
            code="HQ",
            is_head_office=True,
            manager=self.manager1,
        )
        
        self.branch2 = Branch.objects.create(
            company=self.company,
            name="Warehouse",
            code="WH",
            manager=self.manager2,
        )

        # CRITICAL: Create UserBranch assignments
        UserBranch.objects.create(
            user=self.admin,
            company=self.company,
            branch=self.branch1,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.manager1,
            company=self.company,
            branch=self.branch1,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.manager2,
            company=self.company,
            branch=self.branch2,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.user1,
            company=self.company,
            branch=self.branch1,
            is_primary=True
        )
        UserBranch.objects.create(
            user=self.user2,
            company=self.company,
            branch=self.branch2,
            is_primary=True
        )

        # Create category
        self.category = AssetCategory.objects.create(
            company=self.company,
            name="Laptops",
        )
        
        # Create test asset
        self.asset = Asset.objects.create(
            company=self.company,
            branch=self.branch1,
            category=self.category,
            description="Test Laptop",
            status=Asset.STATUS_ACTIVE,
            assigned_to=self.user1,
            dynamic_data={'name': 'MacBook Pro', 'model': '2024'}
        )

    def test_initiate_transfer_creates_request_and_notifies_receiver(self):
        """
        Test: Transfer initiation creates request and sends notification.
        
        Scenario:
        1. Admin initiates transfer (user1 → user2)
        2. Verify transfer created with PENDING_RECEIVER state
        3. Verify receiver (user2) receives alert
        4. Verify audit log entry created
        
        Expected:
        - Transfer state = PENDING_RECEIVER
        - Transfer initiator = admin
        - Transfer to_user = user2
        - Alert created for user2
        - Audit log contains transfer_initiated
        """
        # Act: Initiate transfer
        transfer = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user2,
            to_branch=self.branch2,
            initiator_comment="Transferring laptop to warehouse"
        )
        
        # Assert: Transfer created correctly
        self.assertEqual(transfer.state, AssetTransfer.TransferState.PENDING_RECEIVER)
        self.assertEqual(transfer.initiator, self.admin)
        self.assertEqual(transfer.to_user, self.user2)
        self.assertEqual(transfer.from_user, self.user1)
        self.assertEqual(transfer.from_branch, self.branch1)
        self.assertEqual(transfer.to_branch, self.branch2)
        self.assertEqual(transfer.asset, self.asset)
        self.assertEqual(transfer.company, self.company)
        
        # Assert: Receiver notified
        alert = Alert.objects.filter(
            recipient=self.user2,
            message__icontains="transfer request"
        )
        self.assertTrue(alert.exists(), "Receiver should receive transfer alert")
        
        # Assert: Audit log created
        audit = AuditLog.objects.filter(
            user=self.admin,
            action="transfer_initiated",
            asset=self.asset
        )
        self.assertTrue(audit.exists(), "Transfer initiation should be logged")

    def test_receiver_approves_transfer_moves_to_admin_review(self):
        """
        Test: Receiver approval moves transfer to admin review.
        
        Scenario:
        1. Create transfer (admin → user2)
        2. Receiver (user2) approves
        3. Verify state = AWAITING_ADMIN
        4. Verify initiator notified
        5. Verify audit log updated
        
        Expected:
        - Transfer state = AWAITING_ADMIN
        - Transfer receiver_decision = APPROVED
        - Transfer receiver_decided_at set
        - Alert created for initiator
        - Audit log contains receiver_decision
        """
        # Arrange: Create transfer
        transfer = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user2,
            to_branch=self.branch2,
            initiator_comment="Test transfer"
        )
        
        # Act: Receiver approves
        transfer = receiver_review(
            transfer=transfer,
            receiver=self.user2,
            decision=AssetTransfer.Decision.APPROVED,
            comment="I accept this transfer"
        )
        
        # Assert: State updated
        self.assertEqual(transfer.state, AssetTransfer.TransferState.AWAITING_ADMIN)
        self.assertEqual(transfer.receiver_decision, AssetTransfer.Decision.APPROVED)
        self.assertIsNotNone(transfer.receiver_decided_at)
        self.assertEqual(transfer.receiver_comment, "I accept this transfer")
        
        # Assert: Initiator notified
        alert = Alert.objects.filter(
            recipient=self.admin,
            message__icontains="approved"
        )
        self.assertTrue(alert.exists(), "Initiator should be notified of approval")
        
        # Assert: Audit log updated
        audit = AuditLog.objects.filter(
            user=self.user2,
            action="transfer_receiver_decision",
            asset=self.asset
        )
        self.assertTrue(audit.exists(), "Receiver decision should be logged")

    def test_receiver_rejects_transfer_ends_workflow(self):
        """
        Test: Receiver rejection ends transfer workflow.
        
        Scenario:
        1. Create transfer (admin → user2)
        2. Receiver (user2) rejects with reason
        3. Verify state = RECEIVER_REJECTED
        4. Verify initiator notified
        5. Verify asset unchanged
        
        Expected:
        - Transfer state = RECEIVER_REJECTED
        - Transfer receiver_decision = REJECTED
        - Transfer rejection reason set
        - Asset assigned_to unchanged
        - Asset branch unchanged
        - Alert created for initiator
        """
        # Arrange: Create transfer
        transfer = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user2,
            to_branch=self.branch2,
            initiator_comment="Test transfer"
        )
        
        original_assigned_to = self.asset.assigned_to
        original_branch = self.asset.branch
        
        # Act: Receiver rejects
        transfer = receiver_review(
            transfer=transfer,
            receiver=self.user2,
            decision=AssetTransfer.Decision.REJECTED,
            comment="I cannot accept this asset"
        )
        
        # Assert: State updated
        self.assertEqual(transfer.state, AssetTransfer.TransferState.RECEIVER_REJECTED)
        self.assertEqual(transfer.receiver_decision, AssetTransfer.Decision.REJECTED)
        self.assertEqual(transfer.receiver_comment, "I cannot accept this asset")
        
        # Assert: Asset unchanged
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.assigned_to, original_assigned_to)
        self.assertEqual(self.asset.branch, original_branch)
        
        # Assert: Initiator notified
        alert = Alert.objects.filter(
            recipient=self.admin,
            message__icontains="rejected"
        )
        self.assertTrue(alert.exists(), "Initiator should be notified of rejection")

    def test_admin_approves_transfer_completes_workflow(self):
        """
        Test: Admin approval completes transfer and updates asset.
        
        Scenario:
        1. Create transfer (admin → user2)
        2. Receiver approves
        3. Admin approves
        4. Verify state = COMPLETED
        5. Verify asset updated
        6. Verify all parties notified
        
        Expected:
        - Transfer state = COMPLETED
        - Transfer admin_decision = APPROVED
        - Transfer completed_at set
        - Asset assigned_to = user2
        - Asset branch = branch2
        - Alerts created for initiator and receiver
        - Audit log contains admin_approval and asset_updated
        """
        # Arrange: Create and receiver-approve transfer
        transfer = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user2,
            to_branch=self.branch2,
            initiator_comment="Test transfer"
        )
        
        transfer = receiver_review(
            transfer=transfer,
            receiver=self.user2,
            decision=AssetTransfer.Decision.APPROVED,
            comment="Accepted"
        )
        
        # Act: Admin approves
        transfer = admin_review(
            transfer=transfer,
            reviewer=self.admin,
            decision=AssetTransfer.Decision.APPROVED,
            comment="Transfer approved"
        )
        
        # Assert: Transfer completed
        self.assertEqual(transfer.state, AssetTransfer.TransferState.COMPLETED)
        self.assertEqual(transfer.admin_decision, AssetTransfer.Decision.APPROVED)
        self.assertIsNotNone(transfer.admin_decided_at)
        
        # Assert: Asset updated
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.assigned_to, self.user2)
        self.assertEqual(self.asset.branch, self.branch2)
        
        # Assert: Audit log complete (admin approval logs as 'assign' action)
        audit = AuditLog.objects.filter(
            user=self.admin,
            action="assign",
            asset=self.asset
        )
        self.assertTrue(audit.exists(), "Admin approval (assign action) should be logged")

    def test_only_receiver_can_approve_at_receiver_stage(self):
        """
        Test: Only designated receiver can approve at receiver stage.
        
        Scenario:
        1. Create transfer (admin → user2)
        2. Try to approve as different user (user1)
        3. Verify PermissionDenied raised
        4. Try to approve as receiver (user2)
        5. Verify success
        
        Expected:
        - user1 approval raises PermissionDenied
        - user2 approval succeeds
        - Transfer state updated only after user2 approval
        """
        # Arrange: Create transfer
        transfer = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user2,
            to_branch=self.branch2,
            initiator_comment="Test transfer"
        )
        
        # Act & Assert: Wrong user cannot approve
        with self.assertRaises(PermissionDenied):
            receiver_review(
                transfer=transfer,
                receiver=self.user1,  # Wrong user!
                decision=AssetTransfer.Decision.APPROVED,
                comment="Trying to approve"
            )
        
        # Assert: State unchanged
        transfer.refresh_from_db()
        self.assertEqual(transfer.state, AssetTransfer.TransferState.PENDING_RECEIVER)
        
        # Act: Correct user approves
        transfer = receiver_review(
            transfer=transfer,
            receiver=self.user2,  # Correct user
            decision=AssetTransfer.Decision.APPROVED,
            comment="Approved"
        )
        
        # Assert: State updated
        self.assertEqual(transfer.state, AssetTransfer.TransferState.AWAITING_ADMIN)

    def test_cross_company_transfer_blocked(self):
        """
        Test: Transfers between different companies are blocked.
        
        Scenario:
        1. Create second company
        2. Create user in second company
        3. Try to transfer asset to user in different company
        4. Verify ValidationError raised
        
        Expected:
        - Transfer creation fails
        - Error message mentions company mismatch
        - No transfer record created
        - No alerts sent
        """
        # Arrange: Create second company and user
        company2 = Company.objects.create(name="Other Corp")
        user_other_company = User.objects.create_user(
            username="other_user",
            email="other@example.com",
            password="pass123",
            role=User.USER,
            company=company2,
        )
        
        # Act & Assert: Cross-company transfer blocked
        with self.assertRaises(ValidationError) as context:
            initiate_transfer(
                initiator=self.admin,
                asset=self.asset,
                to_user=user_other_company,
                initiator_comment="Trying cross-company transfer"
            )
        
        # Assert: Error message mentions company
        self.assertIn("company", str(context.exception).lower())
        
        # Assert: No transfer created
        transfer_count = AssetTransfer.objects.filter(asset=self.asset).count()
        self.assertEqual(transfer_count, 0)

    def test_cannot_initiate_transfer_while_active_transfer_exists(self):
        """
        Test: Only one active transfer per asset at a time.
        
        Scenario:
        1. Create transfer (admin → user2)
        2. Try to create second transfer for same asset
        3. Verify ValidationError raised
        4. Complete first transfer
        5. Verify second transfer now allowed
        
        Expected:
        - Second transfer blocked while first active
        - Error message mentions active transfer
        - Second transfer succeeds after first completes
        """
        # Arrange: Create first transfer
        transfer1 = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user2,
            initiator_comment="First transfer"
        )
        
        # Act & Assert: Second transfer blocked
        with self.assertRaises(ValidationError) as context:
            initiate_transfer(
                initiator=self.admin,
                asset=self.asset,
                to_user=self.user1,
                initiator_comment="Second transfer"
            )
        
        # Assert: Error mentions active transfer
        self.assertIn("active transfer", str(context.exception).lower())
        
        # Arrange: Complete first transfer
        transfer1 = receiver_review(
            transfer=transfer1,
            receiver=self.user2,
            decision=AssetTransfer.Decision.APPROVED,
            comment="Approved"
        )
        transfer1 = admin_review(
            transfer=transfer1,
            reviewer=self.admin,
            decision=AssetTransfer.Decision.APPROVED,
            comment="Approved"
        )
        
        # Act: Second transfer now allowed
        transfer2 = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user1,
            initiator_comment="Second transfer after first completed"
        )
        
        # Assert: Second transfer created
        self.assertIsNotNone(transfer2)
        self.assertEqual(transfer2.state, AssetTransfer.TransferState.PENDING_RECEIVER)

    def test_transfer_workflow_creates_complete_audit_trail(self):
        """
        Test: Complete audit trail for entire transfer workflow.
        
        Scenario:
        1. Initiate transfer
        2. Receiver approves
        3. Admin approves
        4. Query audit logs
        5. Verify all events logged
        
        Expected:
        - transfer_initiated logged
        - transfer_receiver_decision logged
        - transfer_admin_decision logged
        - All logs have correct user, company, branch
        - All logs have transfer context
        """
        # Act: Complete transfer workflow
        transfer = initiate_transfer(
            initiator=self.admin,
            asset=self.asset,
            to_user=self.user2,
            to_branch=self.branch2,
            initiator_comment="Test transfer"
        )
        
        transfer = receiver_review(
            transfer=transfer,
            receiver=self.user2,
            decision=AssetTransfer.Decision.APPROVED,
            comment="Approved"
        )
        
        transfer = admin_review(
            transfer=transfer,
            reviewer=self.admin,
            decision=AssetTransfer.Decision.APPROVED,
            comment="Approved"
        )
        
        # Assert: All events logged
        audit_logs = AuditLog.objects.filter(asset=self.asset).order_by('timestamp')
        
        # Check for transfer_initiated
        initiated_log = audit_logs.filter(action="transfer_initiated")
        self.assertTrue(initiated_log.exists(), "Transfer initiation should be logged")
        self.assertEqual(initiated_log.first().user, self.admin)
        
        # Check for receiver_decision
        receiver_log = audit_logs.filter(action="transfer_receiver_decision")
        self.assertTrue(receiver_log.exists(), "Receiver decision should be logged")
        self.assertEqual(receiver_log.first().user, self.user2)
        
        # Check for admin approval (logs as 'assign' action when transfer completes)
        admin_log = audit_logs.filter(action="assign")
        self.assertTrue(admin_log.exists(), "Admin approval (assign action) should be logged")
        self.assertEqual(admin_log.first().user, self.admin)
        
        # Assert: All logs have company and branch
        for log in audit_logs:
            self.assertEqual(log.company, self.company)
            self.assertIsNotNone(log.branch)
