from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from assets.models import Asset, AssetCategory, MaintenanceRecord
from assets.services.maintenance import MaintenanceService
from tenancy.models import Alert, Branch, Company


class MaintenanceServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Corp")
        self.branch = Branch.objects.create(
            company=self.company,
            name="Head Office",
            code="HQ",
            is_head_office=True,
        )
        self.category = AssetCategory.objects.create(company=self.company, name="IT Equipment")
        User = get_user_model()
        self.manager = User.objects.create_user(
            username="manager",
            password="pass12345",
            role=User.MANAGER,
            company=self.company,
        )
        self.asset = Asset.objects.create(
            company=self.company,
            branch=self.branch,
            category=self.category,
            maintenance_enabled=True,
            maintenance_interval_days=30,
        )

    def test_schedule_creates_record_and_alert(self):
        scheduled_for = timezone.localdate() + timedelta(days=5)

        record = MaintenanceService.schedule(
            asset=self.asset,
            scheduled_for=scheduled_for,
            created_by=self.manager,
            supervisor=None,
            description="Quarterly check",
        )

        self.assertEqual(record.status, MaintenanceRecord.Status.SCHEDULED)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.next_maintenance_date, scheduled_for)
        self.assertIsNone(self.asset.last_maintenance_date)
        alerts = Alert.objects.filter(recipient=self.manager)
        self.assertTrue(alerts.exists())

    def test_complete_updates_asset_dates_and_status(self):
        scheduled_for = timezone.localdate() + timedelta(days=3)
        record = MaintenanceService.schedule(
            asset=self.asset,
            scheduled_for=scheduled_for,
            created_by=self.manager,
            supervisor=None,
        )
        MaintenanceService.start(record=record, started_by=self.manager)

        self.asset.status = Asset.STATUS_IN_MAINTENANCE
        self.asset.save(update_fields=["status"])

        completed_record = MaintenanceService.complete(
            record=record,
            completed_by=self.manager,
            outcome_notes="All systems optimal",
            cost=150.00,
        )

        self.assertEqual(completed_record.status, MaintenanceRecord.Status.COMPLETED)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.STATUS_ACTIVE)
        self.assertEqual(self.asset.last_maintenance_date, timezone.localdate())
        self.assertEqual(
            self.asset.next_maintenance_date,
            timezone.localdate() + timedelta(days=self.asset.maintenance_interval_days),
        )

    def test_cancel_clears_next_maintenance(self):
        scheduled_for = timezone.localdate() + timedelta(days=10)
        record = MaintenanceService.schedule(
            asset=self.asset,
            scheduled_for=scheduled_for,
            created_by=self.manager,
            supervisor=None,
        )

        cancelled_record = MaintenanceService.cancel(
            record=record,
            cancelled_by=self.manager,
            reason="Vendor unavailable",
        )

        self.assertEqual(cancelled_record.status, MaintenanceRecord.Status.CANCELLED)
        self.asset.refresh_from_db()
        self.assertIsNone(self.asset.next_maintenance_date)

    def test_send_overdue_alerts_creates_notifications(self):
        scheduled_for = timezone.localdate() - timedelta(days=2)
        record = MaintenanceRecord.objects.create(
            asset=self.asset,
            company=self.company,
            branch=self.branch,
            status=MaintenanceRecord.Status.SCHEDULED,
            scheduled_for=scheduled_for,
            created_by=self.manager,
            updated_by=self.manager,
        )

        MaintenanceService.send_overdue_alerts(company_id=self.company.id)

        self.assertTrue(
            Alert.objects.filter(
                company=self.company,
                context__maintenance_uuid=str(record.uuid),
            ).exists()
        )
