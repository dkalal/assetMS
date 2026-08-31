import re
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import CompanyRegistration
from assets.models import Asset, AssetCategory, AssetCategoryField, MaintenanceRecord
from audit.models import AuditLog
from reports.models import Report
from tenancy.approval_models import ApprovalRequest
from tenancy.models import Branch, Company, UserBranch
from users.models import UserRetirement
from users.models import AccessLog, UserSession


User = get_user_model()


class UIFoundationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='A Company With A Deliberately Long Workspace Name')
        self.branch = Branch.objects.create(
            company=self.company,
            name='Head Office With A Long Branch Name',
            code='HQ',
            is_head_office=True,
        )
        self.admin = User.objects.create_user(
            username='ui-admin',
            password='pass',
            role=User.ADMIN,
            company=self.company,
        )
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save(update_fields=['is_superuser', 'is_staff'])
        self.employee = User.objects.create_user(
            username='ui-user',
            password='pass',
            role=User.USER,
            company=self.company,
        )
        self.manager = User.objects.create_user(
            username='ui-manager',
            password='pass',
            role=User.MANAGER,
            company=self.company,
        )
        for user in (self.admin, self.manager, self.employee):
            UserBranch.objects.create(
                user=user,
                company=self.company,
                branch=self.branch,
                is_primary=True,
            )
        self.branch.manager = self.manager
        self.branch.save(update_fields=['manager'])
        self.category = AssetCategory.objects.create(company=self.company, name='Computers')
        self.asset = Asset(
            company=self.company,
            branch=self.branch,
            category=self.category,
            assigned_to=self.employee,
            dynamic_data={'name': 'Long Named Laptop Asset', 'serial_number': 'SN-001'},
        )
        Asset.objects.bulk_create([self.asset])
        self.approval_request = ApprovalRequest.objects.create(
            company=self.company,
            branch=self.branch,
            requested_by=self.employee,
            assigned_to=self.manager,
            request_type=ApprovalRequest.TYPE_CUSTOM,
            title='Replace damaged secure storage cabinet',
            description='The cabinet lock failed and requires a controlled replacement.',
            priority=ApprovalRequest.PRIORITY_HIGH,
        )
        self.retirement_request = UserRetirement.objects.create(
            user=self.employee,
            company=self.company,
            requested_by=self.employee,
            effective_date=date.today() + timedelta(days=30),
            reason_category=UserRetirement.REASON_RETIREMENT,
            reason='Planned retirement after completing the current handover.',
            asset_count=1,
            assets_pending=1,
        )

    def test_authenticated_shell_loads_only_canonical_foundation(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('asset_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'css/ui-foundation.css')
        self.assertContains(response, 'css/app-shell.css')
        self.assertNotContains(response, 'css/global-override.css')
        self.assertNotContains(response, 'css/sidebar-navbar-worldclass.css')
        self.assertContains(response, 'app-sidebar')
        self.assertContains(response, 'sidebar-backdrop')

    def test_dashboard_renders_inside_canonical_shell(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'app-shell')
        self.assertContains(response, 'Dashboard')

    def test_asset_list_renders_desktop_and_mobile_record_patterns(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('asset_list'))

        self.assertContains(response, 'asset-table-wrap')
        self.assertContains(response, 'asset-mobile-list')
        self.assertContains(response, 'Long Named Laptop Asset')
        self.assertContains(response, 'asset-selection-toolbar')
        self.assertContains(response, 'Request disposal')

    def test_regular_user_does_not_receive_management_navigation_or_actions(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('asset_list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Review and control')
        self.assertNotContains(response, 'Administration')
        self.assertNotContains(response, 'Register asset')
        self.assertNotContains(response, 'asset-selection-toolbar')
        self.assertNotContains(response, 'Request disposal')

    def test_manager_receives_review_tools_but_not_administration(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('asset_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Review and control')
        self.assertContains(response, 'Branch oversight')
        self.assertContains(response, 'Register asset')
        self.assertNotContains(response, 'Administration')
        self.assertNotContains(response, 'Users and access')

    def test_filter_state_is_counted_and_rendered_only_when_active(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('asset_list'), {'status': 'active', 'search': 'Laptop'})

        self.assertEqual(response.context['active_filter_count'], 2)
        self.assertTrue(response.context['has_active_filters'])
        self.assertContains(response, 'Search: Laptop')
        self.assertContains(response, 'Active')

    def test_asset_detail_separates_authenticated_and_public_information(self):
        self.client.force_login(self.admin)
        private = self.client.get(reverse('asset_detail_by_uuid', kwargs={'uuid': self.asset.uuid}), {'internal': '1'})

        self.assertEqual(private.status_code, 200)
        self.assertContains(private, 'css/asset-detail.css')
        self.assertContains(private, 'Long Named Laptop Asset')
        self.assertContains(private, 'Edit asset')
        self.assertNotContains(private, 'Delete Asset')
        self.client.logout()

        public = self.client.get(reverse('asset_detail_by_uuid', kwargs={'uuid': self.asset.uuid}))
        self.assertEqual(public.status_code, 200)
        self.assertContains(public, 'Sign in to view details')
        self.assertNotContains(public, self.employee.username)
        self.assertNotContains(public, 'Purchase value')

    def test_regular_user_asset_detail_preserves_role_actions(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('asset_detail_by_uuid', kwargs={'uuid': self.asset.uuid}), {'internal': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Request maintenance')
        self.assertContains(response, 'Transfer')
        self.assertNotContains(response, 'Edit asset')
        self.assertNotContains(response, 'Schedule maintenance')

    def test_transfer_and_maintenance_centers_use_canonical_components(self):
        self.client.force_login(self.manager)
        transfer = self.client.get(reverse('assets:transfer_dashboard'))
        maintenance = self.client.get(reverse('maintenance:list'))

        self.assertEqual(transfer.status_code, 200)
        self.assertContains(transfer, 'css/transfer-center.css')
        self.assertContains(transfer, 'Initiate transfer')
        self.assertNotContains(transfer, 'onclick=')
        self.assertEqual(maintenance.status_code, 200)
        self.assertContains(maintenance, 'css/maintenance-center.css')
        self.assertContains(maintenance, 'Search maintenance records')
        self.assertNotContains(maintenance, 'Generate Sample Data')

        self.client.force_login(self.employee)
        denied = self.client.get(reverse('maintenance:list'))
        self.assertRedirects(denied, reverse('dashboard'))

    def test_approval_center_and_detail_preserve_separation_of_duties(self):
        self.client.force_login(self.manager)
        dashboard = self.client.get(reverse('approval_dashboard'))
        detail = self.client.get(reverse('approval_request_detail', args=[self.approval_request.pk]))

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'css/approval-center.css')
        self.assertContains(dashboard, self.approval_request.title)
        self.assertNotContains(dashboard, 'onsubmit=')
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, 'Record a decision')
        self.assertContains(detail, 'name=\'action\' value=\'approve\'')
        self.assertNotContains(detail, 'onclick=')

        self.client.force_login(self.employee)
        own_detail = self.client.get(reverse('approval_request_detail', args=[self.approval_request.pk]))
        self.assertContains(own_detail, 'Awaiting independent review')
        self.assertNotContains(own_detail, 'Record a decision')

    def test_retirement_surfaces_preserve_rbac_and_named_api_contracts(self):
        self.client.force_login(self.employee)
        mine = self.client.get(reverse('users:my_retirement'))
        self.assertEqual(mine.status_code, 200)
        self.assertContains(mine, 'css/retirement-center.css')
        self.assertContains(mine, reverse('api_retirement_my_request'))
        self.assertContains(mine, reverse('api_retirement_cancel_mine'))
        denied = self.client.get(reverse('users:retirement_approvals'))
        self.assertRedirects(denied, reverse('dashboard'))

        self.client.force_login(self.manager)
        manager_center = self.client.get(reverse('users:retirement_approvals'))
        self.assertEqual(manager_center.status_code, 200)
        self.assertContains(manager_center, 'Retirement approvals')
        self.assertNotContains(manager_center, 'Approved and in progress')

        self.client.force_login(self.admin)
        admin_center = self.client.get(reverse('users:retirement_approvals'))
        self.assertContains(admin_center, 'Approved and in progress')
        self.assertNotContains(admin_center, 'onclick=')

    def test_asset_form_uses_canonical_sections_and_preserves_rbac(self):
        self.client.force_login(self.admin)
        create = self.client.get(reverse('asset_register'))
        edit = self.client.get(reverse('assets:asset_update', kwargs={'uuid': self.asset.uuid}))

        self.assertEqual(create.status_code, 200)
        self.assertContains(create, 'css/asset-form.css')
        self.assertContains(create, 'name="serial_number"')
        self.assertContains(create, 'name="asset_tag"')
        self.assertContains(create, 'category-fields-container')
        self.assertContains(create, 'js/asset_form.js')
        self.assertNotContains(create, 'duplicate-detection.js')
        self.assertNotContains(create, 'asset-status-fields.js')
        self.assertNotContains(create, 'onclick=')
        self.assertEqual(edit.status_code, 200)
        self.assertContains(edit, 'Lifecycle status')
        self.assertContains(edit, 'data-status-panel="lost"')

        self.client.force_login(self.manager)
        manager_create = self.client.get(reverse('asset_register'))
        self.assertEqual(manager_create.status_code, 200)
        self.assertContains(manager_create, 'Business justification')
        self.assertContains(manager_create, 'Submit for approval')
        self.assertNotContains(manager_create, 'name="images"')

        self.client.force_login(self.employee)
        denied = self.client.get(reverse('asset_register'))
        self.assertEqual(denied.status_code, 302)
        self.assertTrue(denied.url.startswith(reverse('users:login')))

    def test_manager_asset_request_preserves_form_data_through_approval(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('asset_register'),
            {
                'company': self.company.pk,
                'category': self.category.pk,
                'branch': self.branch.pk,
                'status': Asset.STATUS_ACTIVE,
                'assigned_to': self.employee.pk,
                'serial_number': 'REQUEST-SERIAL-001',
                'asset_tag': 'REQUEST-TAG-001',
                'maintenance_enabled': 'on',
                'maintenance_interval_days': '90',
                'maintenance_notes': 'Quarterly inspection',
                'description': 'Replacement field laptop',
                'priority': ApprovalRequest.PRIORITY_HIGH,
                'justification': 'Required for field support and secure customer visits.',
            },
        )
        self.assertRedirects(response, reverse('approval_dashboard'))
        approval = ApprovalRequest.objects.filter(
            request_type=ApprovalRequest.TYPE_ASSET_CREATION,
            requested_by=self.manager,
        ).latest('created_at')
        self.assertEqual(approval.metadata['asset_data']['assigned_to_id'], self.employee.pk)
        self.assertEqual(approval.metadata['asset_data']['serial_number'], 'REQUEST-SERIAL-001')
        self.assertEqual(approval.metadata['asset_data']['maintenance_interval_days'], 90)

        approval.approve(self.admin, 'Operational need verified.')
        created = approval.create_asset_from_approval()
        self.assertEqual(created.assigned_to, self.employee)
        self.assertEqual(created.serial_number, 'REQUEST-SERIAL-001')
        self.assertEqual(created.asset_tag, 'REQUEST-TAG-001')
        self.assertTrue(created.maintenance_enabled)
        self.assertEqual(created.maintenance_interval_days, 90)

    def test_dynamic_field_endpoint_is_company_scoped_and_returns_metadata(self):
        dynamic_field = AssetCategoryField.objects.create(
            company=self.company,
            category=self.category,
            key='purchase_date',
            label='Purchase date',
            type='date',
            required=True,
        )
        other_company = Company.objects.create(name='Other Company')
        other_category = AssetCategory.objects.create(company=other_company, name='Restricted')

        self.client.force_login(self.admin)
        response = self.client.get(reverse('get_dynamic_fields'), {'category_id': self.category.pk})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['fields'][dynamic_field.key]['type'], 'date')
        self.assertTrue(payload['fields'][dynamic_field.key]['required'])
        self.assertIn('help_text', payload['fields'][dynamic_field.key])

        restricted = self.client.get(reverse('get_dynamic_fields'), {'category_id': other_category.pk})
        self.assertEqual(restricted.status_code, 200)
        self.assertEqual(restricted.json()['fields'], {})

    def test_related_asset_request_forms_use_shared_form_foundation(self):
        self.client.force_login(self.manager)
        creation = self.client.get(reverse('assets:asset_creation_request'))
        self.assertEqual(creation.status_code, 200)
        self.assertContains(creation, 'css/asset-request-forms.css')
        self.assertContains(creation, 'js/asset-request-forms.js')
        self.assertContains(creation, 'Independent approval required')
        self.assertNotContains(creation, '<style')
        self.assertNotContains(creation, 'console.')

        self.client.force_login(self.employee)
        disposal = self.client.get(
            reverse('assets:asset_disposal_request', kwargs={'asset_uuid': self.asset.uuid}),
            {'from': 'delete'},
        )
        self.assertEqual(disposal.status_code, 200)
        self.assertContains(disposal, 'css/asset-request-forms.css')
        self.assertContains(disposal, 'This is a lifecycle-sensitive request')
        self.assertNotContains(disposal, '<style')
        self.assertNotContains(disposal, 'onclick=')

    def test_historical_asset_routes_resolve_to_canonical_uuid_workflows(self):
        self.client.force_login(self.employee)
        integer_detail = self.client.get(reverse('asset_detail', args=[self.asset.pk]))
        self.assertRedirects(
            integer_detail,
            reverse('asset_detail_by_uuid', kwargs={'uuid': self.asset.uuid}),
            fetch_redirect_response=False,
        )

        wizard = self.client.get(reverse('assets:asset_register_wizard'))
        self.assertRedirects(wizard, reverse('asset_register'), fetch_redirect_response=False)

        self.asset.status = Asset.STATUS_RETIRED
        self.asset.save(update_fields=['status'])
        retired_disposal = self.client.get(
            reverse('assets:asset_disposal_request', kwargs={'asset_uuid': self.asset.uuid}),
        )
        self.assertRedirects(
            retired_disposal,
            reverse('asset_detail_by_uuid', kwargs={'uuid': self.asset.uuid}),
            fetch_redirect_response=False,
        )

    def test_asset_scanner_uses_scoped_assets_and_safe_lookup_contract(self):
        self.client.force_login(self.admin)
        page = self.client.get(reverse('asset_scan'))
        lookup = self.client.get(reverse('asset_by_code'), {'code': str(self.asset.pk)})

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'css/asset-scanner.css')
        self.assertContains(page, 'js/asset-scanner.js')
        self.assertContains(page, reverse('asset_by_code'))
        self.assertNotContains(page, 'css/enterprise.css')
        self.assertNotContains(page, 'scanner-worldclass.css')
        self.assertNotContains(page, 'onclick=')
        self.assertNotContains(page, '<style')
        self.assertNotContains(page, 'console.')
        self.assertEqual(lookup.status_code, 200)
        self.assertTrue(lookup.json()['success'])
        self.assertNotIn('assigned_to', lookup.json()['asset'])

    def test_transfer_request_assets_are_loaded_by_the_canonical_shell(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('users:my_transfer_requests_page'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'js/user-transfer-request.js')
        self.assertContains(response, 'js/my-transfer-requests.js')
        self.assertContains(response, 'Request Branch Transfer')

    def test_system_admin_surfaces_render_and_remain_globally_restricted(self):
        CompanyRegistration.objects.create(
            company=self.company,
            billing_email='billing@example.com',
            subscription_status='active',
        )
        system_admin = User.objects.create_user(
            username='system-operator',
            password='pass',
            role=User.ADMIN,
            company=None,
            is_system_admin=True,
        )

        self.client.force_login(system_admin)
        pages = (
            reverse('system_admin:dashboard'),
            reverse('system_admin:company_list'),
            reverse('system_admin:create_company'),
            reverse('system_admin:company_detail', args=[self.company.pk]),
            reverse('system_admin:impersonate', args=[self.employee.pk]),
            reverse('system_admin:role_permissions'),
        )
        for url in pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertContains(response, 'id=\'main-content\'')

        dashboard = self.client.get(reverse('system_admin:dashboard'))
        companies = self.client.get(reverse('system_admin:company_list'))
        detail = self.client.get(reverse('system_admin:company_detail', args=[self.company.pk]))
        self.assertContains(dashboard, 'Administration scope')
        self.assertNotContains(dashboard, 'Celery:')
        self.assertContains(dashboard, 'system-admin-mobile-records')
        self.assertContains(companies, 'system-admin-mobile-records')
        self.assertContains(detail, 'system-admin-mobile-records')

        confirmation = self.client.get(
            reverse('system_admin:impersonate', args=[self.employee.pk]),
        )
        self.assertContains(confirmation, 'Confirm impersonation')
        self.assertContains(confirmation, 'csrfmiddlewaretoken')

        self.client.force_login(self.admin)
        denied = self.client.get(reverse('system_admin:dashboard'))
        self.assertRedirects(denied, reverse('dashboard'))

    def test_reports_and_audit_use_real_responsive_record_patterns(self):
        Report.objects.create(
            company=self.company,
            branch=self.branch,
            created_by=self.admin,
            report_type='pdf',
            metadata={'report_type': 'asset_summary', 'format': 'pdf'},
        )
        AuditLog.objects.create(
            company=self.company,
            branch=self.branch,
            user=self.admin,
            asset=self.asset,
            action='edit',
            details='Updated identifier REQUEST-TAG for the field support asset.',
        )

        self.client.force_login(self.admin)
        reports = self.client.get(reverse('reports:reports_dashboard'))
        audit = self.client.get(reverse('audit_dashboard'), {'search': 'REQUEST-TAG'})
        self.assertEqual(reports.status_code, 200)
        self.assertContains(reports, 'css/records-center.css')
        self.assertContains(reports, 'records-desktop-table')
        self.assertContains(reports, 'records-mobile-list')
        self.assertContains(reports, 'Generate report')
        self.assertNotContains(reports, 'Scheduled')
        self.assertNotContains(reports, 'onclick=')
        self.assertEqual(audit.status_code, 200)
        self.assertContains(audit, 'Updated identifier REQUEST-TAG')
        self.assertContains(audit, 'Print current view')
        self.assertNotContains(audit, 'console.')
        self.assertNotContains(audit, 'onclick=')

        self.client.force_login(self.employee)
        employee_reports = self.client.get(reverse('reports:reports_dashboard'))
        self.assertEqual(employee_reports.status_code, 200)
        self.assertNotContains(employee_reports, 'Generate report')
        self.assertNotContains(employee_reports, 'Create a report')

    def test_user_access_pages_preserve_roles_and_tenant_boundaries(self):
        other_company = Company.objects.create(name='Restricted Company')
        other_user = User.objects.create_user(
            username='restricted-user',
            password='pass',
            role=User.USER,
            company=other_company,
        )

        self.client.force_login(self.admin)
        directory = self.client.get(reverse('settings:user_management'))
        profile = self.client.get(reverse('settings:staff_detail', args=[self.employee.pk]))
        users_api = self.client.get(reverse('settings:api_users_management'))
        restricted_profile = self.client.get(reverse('settings:staff_detail', args=[other_user.pk]))

        self.assertEqual(directory.status_code, 200)
        self.assertContains(directory, 'css/user-access.css')
        self.assertContains(directory, 'user-record-list')
        self.assertContains(directory, 'Add user')
        self.assertNotContains(directory, 'chart.js')
        self.assertNotContains(directory, 'onclick=')
        self.assertEqual(profile.status_code, 200)
        self.assertContains(profile, 'js/staff-detail.js')
        self.assertContains(profile, 'Transfer assets')
        self.assertNotContains(profile, '<style')
        self.assertNotContains(profile, 'console.')
        self.assertEqual(restricted_profile.status_code, 404)
        self.assertEqual(users_api.status_code, 200)
        self.assertNotContains(users_api, other_user.username)

        self.client.force_login(self.manager)
        manager_directory = self.client.get(reverse('settings:user_management'))
        manager_profile = self.client.get(reverse('settings:staff_detail', args=[self.employee.pk]))
        self.assertEqual(manager_directory.status_code, 200)
        self.assertNotContains(manager_directory, 'Add user')
        self.assertNotContains(manager_profile, 'Edit user')
        self.assertNotContains(manager_profile, 'Transfer assets')

        self.client.force_login(self.employee)
        denied = self.client.get(reverse('settings:user_management'))
        self.assertEqual(denied.status_code, 403)

    def test_settings_surfaces_use_real_company_scoped_workflows(self):
        other_company = Company.objects.create(name='Other Settings Company')
        other_user = User.objects.create_user(
            username='other-session-user',
            password='pass',
            role=User.ADMIN,
            company=other_company,
        )
        UserSession.objects.create(
            user=other_user,
            session_key='other-session',
            ip_address='203.0.113.10',
            user_agent='Other company browser',
            browser_fingerprint='other-company-fingerprint',
        )
        AccessLog.objects.create(
            user=other_user,
            action='failed_login',
            ip_address='203.0.113.11',
            user_agent='Other company browser',
        )

        self.client.force_login(self.admin)
        hub = self.client.get(reverse('settings:settings_dashboard'))
        organization = self.client.get(reverse('settings:organization_settings'))
        sessions = self.client.get(reverse('settings:session_management'))
        security = self.client.get(reverse('settings:security_privacy_settings'))
        session_metrics = self.client.get(reverse('settings:api_session_stats'))
        security_metrics = self.client.get(reverse('settings:api_security_metrics'))

        self.assertEqual(hub.status_code, 200)
        self.assertContains(hub, 'css/settings-center.css')
        self.assertContains(hub, 'Save profile')
        self.assertNotContains(hub, 'Save All Changes')
        self.assertNotContains(hub, 'onclick=')
        self.assertEqual(organization.status_code, 200)
        self.assertContains(organization, 'js/organization-settings.js')
        self.assertNotContains(organization, '<style')
        self.assertNotContains(organization, 'console.')
        self.assertEqual(sessions.status_code, 200)
        self.assertNotContains(sessions, 'Other company browser')
        self.assertNotContains(sessions, 'default:1')
        self.assertNotContains(sessions, 'onclick=')
        self.assertEqual(security.status_code, 200)
        self.assertContains(security, 'Enforced controls')
        self.assertNotContains(security, 'Save All Changes')
        self.assertEqual(security_metrics.json()['metrics']['failed_logins'], 0)

        self.client.force_login(self.manager)
        manager_sessions = self.client.get(reverse('settings:session_management'))
        manager_hub = self.client.get(reverse('settings:settings_dashboard'))
        self.assertEqual(manager_sessions.status_code, 200)
        self.assertNotContains(manager_sessions, 'Clean expired')
        self.assertNotContains(manager_hub, 'Organization settings')

        self.client.force_login(self.employee)
        employee_hub = self.client.get(reverse('settings:settings_dashboard'))
        self.assertEqual(employee_hub.status_code, 200)
        self.assertNotContains(employee_hub, 'Users and access')
        self.assertNotContains(employee_hub, 'Session management')

    def test_category_center_uses_scoped_apis_and_external_components(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('categories:category_list'))
        listing = self.client.get(reverse('api_categories'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'css/category-center.css')
        self.assertContains(response, 'js/category-center.js')
        self.assertContains(response, 'data-category-center')
        self.assertNotContains(response, 'css/dashboard.css')
        self.assertNotContains(response, 'category-wizard-simple.js')
        self.assertNotContains(response, '<style')
        self.assertNotContains(response, 'onclick=')
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            [category['name'] for category in listing.json()['categories']],
            [self.category.name],
        )

        self.client.force_login(self.manager)
        denied = self.client.get(reverse('categories:category_list'))
        self.assertEqual(denied.status_code, 302)
        self.assertIn(reverse('users:login'), denied.url)

    def test_remaining_tenancy_pages_render_inside_canonical_shell(self):
        self.client.force_login(self.admin)
        admin_pages = (
            reverse('tenant_setup_wizard'),
            reverse('user_branch_management'),
            reverse('branch_manager_management'),
        )
        for url in admin_pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'class=\'app-shell\'')
            self.assertContains(response, 'id=\'main-content\'')

        self.client.force_login(self.manager)
        manager_pages = (
            reverse('branch_manager_performance'),
            reverse('approval_request_create'),
        )
        for url in manager_pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'class=\'app-shell\'')

    def test_branch_administration_uses_scoped_components_and_preserves_rbac(self):
        self.client.force_login(self.admin)
        assignments = self.client.get(reverse('user_branch_management'))
        managers = self.client.get(reverse('branch_manager_management'))

        self.assertEqual(assignments.status_code, 200)
        self.assertContains(assignments, 'css/organization-admin.css')
        self.assertContains(assignments, 'name="user"')
        self.assertContains(assignments, 'name="primary_branch"')
        self.assertNotContains(assignments, '<style')
        self.assertEqual(managers.status_code, 200)
        self.assertContains(managers, 'js/organization-admin.js')
        self.assertContains(managers, 'name="branch"')
        self.assertContains(managers, 'name="manager"')
        self.assertNotContains(managers, 'onclick=')

        self.client.force_login(self.employee)
        self.assertRedirects(
            self.client.get(reverse('user_branch_management')),
            reverse('dashboard'),
        )
        self.assertRedirects(
            self.client.get(reverse('branch_manager_management')),
            reverse('dashboard'),
        )

    def test_manager_center_is_scoped_and_invalid_period_is_resilient(self):
        self.client.force_login(self.manager)
        dashboard = self.client.get(reverse('manager_dashboard'))
        report = self.client.get(reverse('branch_manager_performance'), {'period': 'invalid'})

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'css/manager-center.css')
        self.assertContains(dashboard, self.branch.name)
        self.assertNotContains(dashboard, 'dashboard-blue-modern.css')
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.context['period_days'], 30)
        self.assertContains(report, 'js/manager-center.js')
        self.assertNotContains(report, 'onclick=')

        self.client.force_login(self.employee)
        self.assertRedirects(
            self.client.get(reverse('manager_dashboard')),
            reverse('dashboard'),
        )

    def test_public_auth_shell_preserves_login_contract(self):
        response = self.client.get(reverse('users:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'css/auth-foundation.css')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'js/login.js')
        self.assertNotContains(response, 'global-override.css')
        self.assertNotContains(response, 'onclick=')

        reset = self.client.get(reverse('users:password_reset'))
        register = self.client.get(reverse('accounts:register'))
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(register.status_code, 200)
        self.assertContains(reset, 'css/auth-foundation.css')
        self.assertContains(register, 'js/registration.js')
        self.assertNotContains(register, '<style')

        signed_in = self.client.post(
            reverse('users:login'),
            {'username': self.admin.username, 'password': 'pass'},
        )
        self.assertRedirects(signed_in, reverse('dashboard'))

    def test_help_and_resources_use_canonical_truthful_surfaces(self):
        self.client.force_login(self.admin)
        help_center = self.client.get(reverse('help_center'))
        resources = self.client.get(reverse('documents'))

        self.assertEqual(help_center.status_code, 200)
        self.assertContains(help_center, 'css/support-center.css')
        self.assertContains(help_center, 'js/support-center.js')
        self.assertContains(help_center, 'data-support-search')
        self.assertNotContains(help_center, 'help-center-worldclass.css')
        self.assertNotContains(help_center, 'onclick=')
        self.assertEqual(resources.status_code, 200)
        self.assertContains(resources, reverse('asset_bulk_import'))
        self.assertContains(resources, 'Only resources backed by a current application route')
        self.assertNotContains(resources, 'Download All')
        self.assertNotContains(resources, 'v2.1')
        self.assertNotContains(resources, 'onclick=')

        self.client.force_login(self.employee)
        employee_resources = self.client.get(reverse('documents'))
        self.assertEqual(employee_resources.status_code, 200)
        self.assertNotContains(employee_resources, reverse('asset_bulk_import'))

    def test_maintenance_schedule_form_preserves_rbac_and_post_contract(self):
        self.asset.maintenance_enabled = True
        self.asset.save(update_fields=['maintenance_enabled'])
        url = reverse('maintenance:schedule', kwargs={'asset_uuid': self.asset.uuid})

        self.client.force_login(self.manager)
        form_page = self.client.get(url)
        self.assertEqual(form_page.status_code, 200)
        self.assertContains(form_page, 'css/maintenance-center.css')
        self.assertContains(form_page, 'name="scheduled_for"')
        self.assertContains(form_page, 'name="supervisor"')
        self.assertContains(form_page, 'name="description"')
        self.assertNotContains(form_page, 'global-override.css')

        scheduled_for = date.today() + timedelta(days=7)
        created = self.client.post(
            url,
            {
                'scheduled_for': scheduled_for.isoformat(),
                'supervisor': self.manager.pk,
                'description': 'Quarterly preventive inspection.',
            },
        )
        self.assertRedirects(created, reverse('maintenance:list'))
        record = MaintenanceRecord.objects.get(asset=self.asset)
        self.assertEqual(record.scheduled_for, scheduled_for)
        self.assertEqual(record.supervisor, self.manager)

        self.client.force_login(self.employee)
        self.assertRedirects(self.client.get(url), reverse('dashboard'))

    def test_approval_action_preserves_self_approval_guard_and_manager_authority(self):
        action_url = reverse('approval_action', args=[self.approval_request.pk])
        self.client.force_login(self.employee)
        self.client.post(action_url, {'action': 'approve', 'notes': 'Self approval attempt'})
        self.approval_request.refresh_from_db()
        self.assertEqual(self.approval_request.status, ApprovalRequest.STATUS_PENDING)

        self.client.force_login(self.manager)
        response = self.client.post(
            action_url,
            {'action': 'approve', 'notes': 'Replacement need independently verified.'},
        )
        self.assertRedirects(
            response,
            reverse('approval_dashboard'),
        )
        self.approval_request.refresh_from_db()
        self.assertEqual(self.approval_request.status, ApprovalRequest.STATUS_APPROVED)
        self.assertEqual(self.approval_request.approved_by, self.manager)

    def test_headless_viewport_overflow_smoke(self):
        edge = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        if not edge.exists():
            self.skipTest('Microsoft Edge is not installed')

        self.client.force_login(self.admin)
        response = self.client.get(reverse('asset_list'))
        document = response.content.decode()
        static_root = (Path(settings.BASE_DIR) / 'static').as_uri() + '/'
        document = document.replace('/static/', static_root)
        probe = '''<script>
window.addEventListener('load', function () {
  window.setTimeout(function () {
    const root = document.documentElement;
    const main = document.querySelector('.app-main');
    const navbar = document.querySelector('.app-navbar');
    document.body.setAttribute('data-tested-width', String(root.clientWidth));
    document.body.setAttribute('data-page-overflow', String(root.scrollWidth > root.clientWidth));
    const offenders = Array.from(document.querySelectorAll('body *')).filter(function (element) {
      const rect = element.getBoundingClientRect();
      return rect.right > root.clientWidth + 1;
    }).slice(0, 8).map(function (element) {
      return element.tagName.toLowerCase() + (element.id ? '#' + element.id : '') +
        (element.classList.length ? '.' + Array.from(element.classList).join('.') : '') +
        '@' + Math.round(element.getBoundingClientRect().right);
    });
    document.body.setAttribute('data-overflow-offenders', offenders.join('|'));
    document.body.setAttribute('data-main-margin', getComputedStyle(main).marginLeft);
    document.body.setAttribute('data-navbar-contained', String(navbar.getBoundingClientRect().right <= window.innerWidth + 1));
  }, 700);
});
</script>'''
        document = document.replace('</body>', probe + '</body>')
        viewports = [
            (320, 568), (360, 800), (390, 844), (576, 900),
            (768, 1024), (820, 1180), (992, 768), (1024, 768),
            (1280, 800), (1366, 768), (1440, 900), (1920, 1080),
        ]

        with tempfile.TemporaryDirectory(prefix='assetms-ui-') as temp_dir:
            temp_path = Path(temp_dir)
            snapshot = temp_path / 'asset-list.html'
            snapshot.write_text(document, encoding='utf-8')
            profile = temp_path / 'edge-profile'
            for width, height in viewports:
                expected_width = max(width, 477)
                result = subprocess.run(
                    [
                        str(edge), '--headless=new', '--disable-gpu', '--no-first-run',
                        '--allow-file-access-from-files', '--virtual-time-budget=2000',
                        f'--window-size={expected_width + 24},{height}',
                        f'--user-data-dir={profile / f"shell-{width}-{height}"}',
                        '--dump-dom', snapshot.as_uri(),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=20,
                )
                dom = result.stdout
                measured = re.search(r'data-tested-width=.([0-9]+)', dom)
                self.assertIsNotNone(measured, f'Viewport probe did not run at {width}x{height}')
                self.assertEqual(int(measured.group(1)), expected_width)
                self.assertRegex(dom, r'data-page-overflow=.false', f'Page overflow at {width}x{height}')
                self.assertRegex(dom, r'data-navbar-contained=.true', f'Navbar overflow at {width}x{height}')
                margin = re.search(r'data-main-margin=.([0-9.]+px)', dom)
                self.assertIsNotNone(margin)
                if width < 992:
                    self.assertEqual(margin.group(1), '0px')
                else:
                    self.assertNotEqual(margin.group(1), '0px')

            self.client.force_login(self.manager)
            self.asset.maintenance_enabled = True
            self.asset.save(update_fields=['maintenance_enabled'])
            creation_request_response = self.client.get(reverse('assets:asset_creation_request'))
            manager_dashboard_response = self.client.get(reverse('manager_dashboard'))
            manager_performance_response = self.client.get(reverse('branch_manager_performance'))
            maintenance_form_response = self.client.get(
                reverse('maintenance:schedule', kwargs={'asset_uuid': self.asset.uuid}),
            )
            CompanyRegistration.objects.get_or_create(
                company=self.company,
                defaults={
                    'billing_email': 'viewport-billing@example.com',
                    'subscription_status': 'active',
                },
            )
            viewport_operator = User.objects.create_user(
                username='viewport-system-operator',
                password='pass',
                role=User.ADMIN,
                company=None,
                is_system_admin=True,
            )
            self.client.force_login(viewport_operator)
            system_companies_response = self.client.get(reverse('system_admin:company_list'))
            system_company_response = self.client.get(
                reverse('system_admin:company_detail', args=[self.company.pk]),
            )
            self.client.force_login(self.admin)
            migrated_pages = {
                'asset-detail': self.client.get(
                    reverse('asset_detail_by_uuid', kwargs={'uuid': self.asset.uuid}),
                    {'internal': '1'},
                ),
                'transfer-center': self.client.get(reverse('assets:transfer_dashboard')),
                'maintenance-center': self.client.get(reverse('maintenance:list')),
                'approval-center': self.client.get(reverse('approval_dashboard')),
                'approval-detail': self.client.get(
                    reverse('approval_request_detail', args=[self.approval_request.pk]),
                ),
                'retirement-request': self.client.get(reverse('users:my_retirement')),
                'retirement-approvals': self.client.get(reverse('users:retirement_approvals')),
                'asset-form': self.client.get(reverse('asset_register')),
                'asset-creation-request': creation_request_response,
                'asset-disposal-request': self.client.get(
                    reverse('assets:asset_disposal_request', kwargs={'asset_uuid': self.asset.uuid}),
                    {'from': 'delete'},
                ),
                'reports': self.client.get(reverse('reports:reports_dashboard')),
                'audit': self.client.get(reverse('audit_dashboard')),
                'user-directory': self.client.get(reverse('settings:user_management')),
                'staff-profile': self.client.get(
                    reverse('settings:staff_detail', args=[self.employee.pk]),
                ),
                'settings-hub': self.client.get(reverse('settings:settings_dashboard')),
                'organization-settings': self.client.get(
                    reverse('settings:organization_settings'),
                ),
                'session-management': self.client.get(
                    reverse('settings:session_management'),
                ),
                'security-center': self.client.get(
                    reverse('settings:security_privacy_settings'),
                ),
                'category-center': self.client.get(
                    reverse('categories:category_list'),
                ),
                'tenant-setup': self.client.get(reverse('tenant_setup_wizard')),
                'approval-request-form': self.client.get(
                    reverse('approval_request_create'),
                ),
                'user-branch-admin': self.client.get(
                    reverse('user_branch_management'),
                ),
                'branch-manager-admin': self.client.get(
                    reverse('branch_manager_management'),
                ),
                'manager-dashboard': manager_dashboard_response,
                'manager-performance': manager_performance_response,
                'maintenance-form': maintenance_form_response,
                'help-center': self.client.get(reverse('help_center')),
                'resources': self.client.get(reverse('documents')),
                'asset-scanner': self.client.get(reverse('asset_scan')),
                'system-companies': system_companies_response,
                'system-company': system_company_response,
            }
            for page_name, page_response in migrated_pages.items():
                page_document = page_response.content.decode().replace('/static/', static_root)
                page_document = page_document.replace('</body>', probe + '</body>')
                page_snapshot = temp_path / f'{page_name}.html'
                page_snapshot.write_text(page_document, encoding='utf-8')
                for width, height in ((477, 844), (768, 1024), (1024, 768)):
                    result = subprocess.run(
                        [
                            str(edge), '--headless=new', '--disable-gpu', '--no-first-run',
                            '--allow-file-access-from-files', '--virtual-time-budget=2000',
                            f'--window-size={width + 24},{height}',
                            f'--user-data-dir={profile / f"{page_name}-{width}-{height}"}',
                            '--dump-dom', page_snapshot.as_uri(),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=20,
                    )
                    dom = result.stdout or ''
                    self.assertTrue(
                        dom,
                        f'{page_name} produced no DOM at {width}x{height}: {result.stderr}',
                    )
                    offenders = re.search(r'data-overflow-offenders=.([^"]*)', dom)
                    offender_text = offenders.group(1) if offenders else 'not captured'
                    self.assertRegex(dom, r'data-page-overflow=.false', f'{page_name} overflow at {width}x{height}: {offender_text}')
                    self.assertRegex(dom, r'data-navbar-contained=.true', f'{page_name} navbar overflow at {width}x{height}')

    def test_auth_viewport_overflow_smoke(self):
        edge = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        if not edge.exists():
            self.skipTest('Microsoft Edge is not installed')

        static_root = (Path(settings.BASE_DIR) / 'static').as_uri() + '/'
        pages = {
            'login': self.client.get(reverse('users:login')),
            'register': self.client.get(reverse('accounts:register')),
        }
        probe = '''<script>
window.addEventListener('load', function () {
  window.setTimeout(function () {
    const root = document.documentElement;
    document.body.setAttribute('data-auth-overflow', String(root.scrollWidth > root.clientWidth));
  }, 500);
});
</script>'''
        with tempfile.TemporaryDirectory(prefix='assetms-auth-ui-') as temp_dir:
            temp_path = Path(temp_dir)
            for page_name, response in pages.items():
                document = response.content.decode().replace('/static/', static_root)
                document = document.replace('</body>', probe + '</body>')
                snapshot = temp_path / f'{page_name}.html'
                snapshot.write_text(document, encoding='utf-8')
                for width, height in ((477, 844), (768, 1024), (1024, 768)):
                    result = subprocess.run(
                        [
                            str(edge), '--headless=new', '--disable-gpu', '--no-first-run',
                            '--allow-file-access-from-files', '--virtual-time-budget=1500',
                            f'--window-size={width + 24},{height}',
                            f'--user-data-dir={temp_path / f"{page_name}-{width}-{height}"}',
                            '--dump-dom', snapshot.as_uri(),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=20,
                    )
                    self.assertRegex(
                        result.stdout,
                        r'data-auth-overflow=.false',
                        f'{page_name} overflow at {width}x{height}',
                    )
