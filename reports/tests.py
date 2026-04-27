import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import timezone

from assets.models import Asset, AssetCategory, MaintenanceRecord
from reports.models import Report
from reports.preview_service import ExportPreviewService
from reports.services import (
    ReportFilters,
    attach_report_branch_labels,
    fetch_individual_report_data,
    get_available_individual_report_users,
    render_individual_assets_dataframe,
    validate_report_filters,
)
from tenancy.models import Branch, Company, UserBranch


class IndividualReportServiceTests(TestCase):
    def test_available_individual_report_users_include_branch_labels(self):
        User = get_user_model()
        company = Company.objects.create(name="Alpha Transport")
        admin = User.objects.create_user(username="admin", password="x", company=company, role="admin")
        subject = User.objects.create_user(
            username="amina",
            first_name="Amina",
            last_name="Hassan",
            password="x",
            company=company,
        )
        hq = Branch.objects.create(company=company, name="HQ", code="HQ", is_head_office=True)
        zanzibar = Branch.objects.create(company=company, name="Zanzibar", code="ZNZ")
        UserBranch.objects.create(user=subject, company=company, branch=zanzibar)
        UserBranch.objects.create(user=subject, company=company, branch=hq, is_primary=True)

        users = attach_report_branch_labels(
            get_available_individual_report_users(company, admin).filter(pk=subject.pk),
            company,
        )

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].report_branch_label, "HQ, Zanzibar")
        self.assertEqual(users[0].report_branch_ids, f"{hq.pk},{zanzibar.pk}")

    def test_report_filter_validation_rejects_bad_date_ranges(self):
        self.assertIsNone(validate_report_filters(ReportFilters(date_from="2026-04-01", date_to="2026-04-30")))
        self.assertEqual(
            validate_report_filters(ReportFilters(date_from="2026-05-01", date_to="2026-04-30")),
            "Start date cannot be after end date.",
        )
        self.assertEqual(
            validate_report_filters(ReportFilters(date_from="not-a-date")),
            "Invalid start date. Please use a valid date.",
        )

    def test_report_subject_label_only_for_individual_reports(self):
        User = get_user_model()
        company = Company.objects.create(name="Alpha Transport")
        admin = User.objects.create_user(username="admin", password="x", company=company, role="admin")

        individual = Report.objects.create(
            company=company,
            report_type="pdf",
            created_by=admin,
            metadata={"report_type": "individual", "subject_user_name": "Amina Hassan"},
        )
        summary = Report.objects.create(
            company=company,
            report_type="pdf",
            created_by=admin,
            metadata={"report_type": "asset_summary", "subject_user_name": "Amina Hassan"},
        )

        self.assertEqual(individual.subject_label, "Amina Hassan")
        self.assertEqual(summary.subject_label, "")

    def test_individual_report_is_scoped_to_subject_and_company(self):
        User = get_user_model()
        company = Company.objects.create(name="Alpha Transport")
        other_company = Company.objects.create(name="Other Company")
        subject = User.objects.create_user(username="amina", password="x", company=company)
        other_user = User.objects.create_user(username="juma", password="x", company=company)
        external_user = User.objects.create_user(username="external", password="x", company=other_company)

        category = AssetCategory.objects.create(company=company, name="Vehicle")
        other_category = AssetCategory.objects.create(company=other_company, name="Vehicle")

        included = Asset.objects.create(
            company=company,
            category=category,
            assigned_to=subject,
            asset_tag="CAR-001",
            status=Asset.STATUS_ACTIVE,
            dynamic_data={"name": "Toyota Hilux", "purchase_value": "12000"},
        )
        Asset.objects.create(
            company=company,
            category=category,
            assigned_to=other_user,
            asset_tag="CAR-002",
            status=Asset.STATUS_ACTIVE,
        )
        Asset.objects.create(
            company=other_company,
            category=other_category,
            assigned_to=external_user,
            asset_tag="CAR-003",
            status=Asset.STATUS_ACTIVE,
        )

        data = fetch_individual_report_data(company, subject, ReportFilters())
        self.assertEqual(data["assets"], [included])
        self.assertEqual(data["summary"]["total_assets"], 1)

        df = render_individual_assets_dataframe(data)
        self.assertEqual(list(df["Asset"]), ["Toyota Hilux"])
        self.assertEqual(list(df["Asset Tag"]), ["CAR-001"])

        html = render_to_string(
            "reports/individual_report_pdf.html",
            {
                "report_data": data,
                "metadata": {
                    "company": company.name,
                    "branch": "All Branches",
                    "generated_at": "2026-04-27 12:00",
                    "generated_by": "admin",
                    "base_url": "http://testserver",
                },
            },
        )
        self.assertIn("Individual Report", html)
        self.assertIn("Toyota Hilux", html)

    def test_preview_individual_report_uses_selected_person(self):
        cache.clear()
        User = get_user_model()
        company = Company.objects.create(name="Alpha Transport")
        admin = User.objects.create_user(username="admin", password="x", company=company, role="admin")
        subject = User.objects.create_user(username="amina", password="x", company=company)
        category = AssetCategory.objects.create(company=company, name="Vehicle")
        Asset.objects.create(
            company=company,
            category=category,
            assigned_to=subject,
            asset_tag="CAR-010",
            status=Asset.STATUS_ACTIVE,
            dynamic_data={"name": "Land Cruiser"},
        )

        result = ExportPreviewService().generate_preview(
            company=company,
            report_type="individual",
            export_format="pdf",
            filters=ReportFilters(user_id=subject.pk),
            user=admin,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.metrics.total_rows, 1)
        self.assertEqual(result.filters_applied["Person"], "amina")
        self.assertEqual(result.preview_data[0]["Asset"], "Land Cruiser")

        json.dumps(result.to_dict(), cls=DjangoJSONEncoder)

        cached_result = ExportPreviewService().generate_preview(
            company=company,
            report_type="individual",
            export_format="pdf",
            filters=ReportFilters(user_id=subject.pk),
            user=admin,
        )

        self.assertTrue(cached_result.success)
        self.assertEqual(cached_result.metrics.total_rows, 1)
        json.dumps(cached_result.to_dict(), cls=DjangoJSONEncoder)

    def test_maintenance_preview_uses_actual_model_fields(self):
        User = get_user_model()
        company = Company.objects.create(name="Alpha Transport")
        admin = User.objects.create_user(username="admin", password="x", company=company, role="admin")
        branch = Branch.objects.create(company=company, name="HQ", code="HQ", is_head_office=True)
        category = AssetCategory.objects.create(company=company, name="Vehicle")
        asset = Asset.objects.create(
            company=company,
            branch=branch,
            category=category,
            assigned_to=admin,
            asset_tag="CAR-020",
            status=Asset.STATUS_ACTIVE,
            dynamic_data={"name": "Service Van"},
        )
        MaintenanceRecord.objects.create(
            company=company,
            branch=branch,
            asset=asset,
            status=MaintenanceRecord.Status.SCHEDULED,
            scheduled_for=timezone.now().date(),
            description="Oil service",
            created_by=admin,
            updated_by=admin,
        )

        result = ExportPreviewService().generate_preview(
            company=company,
            report_type="maintenance",
            export_format="excel",
            filters=ReportFilters(),
            branch=branch,
            user=admin,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.metrics.total_rows, 1)
        self.assertEqual(result.preview_data[0]["Asset"], "Service Van")
        self.assertEqual(result.preview_data[0]["Description"], "Oil service")
