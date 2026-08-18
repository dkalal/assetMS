from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from assets.models import Asset, AssetCategory, AssetCategoryField
from tenancy.models import Company

from .models import CustomerSyncRun, ExternalCustomerReference, ExternalCustomerSyncConfig
from .services import (
    CustomerAssetProjectionService,
    CustomerSyncService,
    SourceCustomerApiClient,
    SourceCustomerApiError,
    normalize_source_base_url,
)


User = get_user_model()


class CustomerSyncServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Acme')
        self.user = User.objects.create_user(
            username='admin',
            password='pass',
            company=self.company,
            role=User.ADMIN,
        )
        self.config = ExternalCustomerSyncConfig.objects.create(
            company=self.company,
            source_base_url='https://internet.example.com',
            source_tenant_slug='acme',
            api_token='secret-token',
            is_enabled=True,
        )

    @mock.patch('integrations.services.SourceCustomerApiClient.fetch_customer_pages')
    def test_sync_creates_and_updates_references(self, fetch_pages):
        created_at = timezone.now().isoformat()
        fetch_pages.return_value = [[
            {
                'uuid': '11111111-1111-1111-1111-111111111111',
                'full_name': 'John Doe',
                'phone': '+255712345678',
                'email': 'john@example.com',
                'address': 'Mikocheni',
                'customer_status': 'active',
                'customer_type': 'internet',
                'created_at': created_at,
            }
        ]]

        first = CustomerSyncService.sync_company_customers(company=self.company, initiated_by=self.user)
        self.assertEqual(first.status, CustomerSyncRun.Status.SUCCESS)
        self.assertEqual(first.created, 1)
        self.assertEqual(ExternalCustomerReference.objects.filter(company=self.company).count(), 1)

        fetch_pages.return_value = [[
            {
                'uuid': '11111111-1111-1111-1111-111111111111',
                'full_name': 'John Doe Updated',
                'phone': '+255712345678',
                'email': 'john@example.com',
                'address': 'Mikocheni',
                'customer_status': 'active',
                'customer_type': 'internet',
                'created_at': created_at,
            }
        ]]
        second = CustomerSyncService.sync_company_customers(company=self.company, initiated_by=self.user)
        self.assertEqual(second.updated, 1)
        reference = ExternalCustomerReference.objects.get(company=self.company)
        self.assertEqual(reference.full_name, 'John Doe Updated')

    @mock.patch('integrations.services.SourceCustomerApiClient.fetch_customer_pages')
    def test_sync_is_partial_when_one_record_fails(self, fetch_pages):
        fetch_pages.return_value = [[
            {
                'uuid': '11111111-1111-1111-1111-111111111111',
                'full_name': 'Valid Customer',
                'phone': '',
                'email': '',
                'address': '',
                'customer_status': 'active',
                'customer_type': 'internet',
                'created_at': timezone.now().isoformat(),
            },
            {
                'uuid': '',
                'full_name': 'Broken Customer',
                'phone': '',
                'email': '',
                'address': '',
                'customer_status': 'active',
                'customer_type': 'internet',
                'created_at': '',
            },
        ]]

        outcome = CustomerSyncService.sync_company_customers(company=self.company, initiated_by=self.user)
        self.assertEqual(outcome.status, CustomerSyncRun.Status.PARTIAL)
        self.assertEqual(outcome.created, 1)
        self.assertEqual(outcome.failed, 1)

    @mock.patch('integrations.services.SourceCustomerApiClient.fetch_customer_pages')
    def test_sync_raises_when_not_configured(self, fetch_pages):
        self.config.delete()
        with self.assertRaises(SourceCustomerApiError):
            CustomerSyncService.sync_company_customers(company=self.company, initiated_by=self.user)

    def test_normalize_source_base_url_strips_ui_path(self):
        self.assertEqual(
            normalize_source_base_url('http://127.0.0.1:8000/customers'),
            'http://127.0.0.1:8000',
        )
        self.assertEqual(
            normalize_source_base_url('https://example.com/customers/'),
            'https://example.com',
        )

    @mock.patch('integrations.services.SourceCustomerApiClient.replace_customer_assets')
    def test_asset_projection_publishes_authoritative_asset_snapshot(self, replace_customer_assets):
        replace_customer_assets.return_value = {'total': 1}
        customer = ExternalCustomerReference.objects.create(
            company=self.company,
            external_uuid='11111111-1111-1111-1111-111111111111',
            full_name='John Doe',
            customer_status='active',
            customer_type='internet',
            source_created_at=timezone.now(),
            last_synced_at=timezone.now(),
        )
        category = AssetCategory.objects.create(company=self.company, name='Customer Premises Equipment')
        AssetCategoryField.objects.create(
            company=self.company, category=category, key='model', label='Model', type='text', required=False,
        )
        AssetCategoryField.objects.create(
            company=self.company, category=category, key='api_token', label='API token', type='text', required=False,
        )
        asset = Asset.objects.create(
            company=self.company,
            category=category,
            customer_reference=customer,
            asset_tag='ONT-001',
            serial_number='ZX-001',
            status=Asset.STATUS_ACTIVE,
            description='Installed ONT',
            dynamic_data={'name': 'Cudy C-111', 'model': 'C-111', 'api_token': 'must-not-leave-assetms'},
        )

        result = CustomerAssetProjectionService.sync_reference(reference_id=customer.id)

        self.assertEqual(result, {'total': 1})
        replace_customer_assets.assert_called_once()
        call = replace_customer_assets.call_args.kwargs
        self.assertEqual(str(call['customer_uuid']), str(customer.external_uuid))
        self.assertEqual(call['assets'][0]['external_uuid'], str(asset.uuid))
        self.assertEqual(call['assets'][0]['asset_tag'], 'ONT-001')
        self.assertEqual(call['assets'][0]['display_name'], 'Cudy C-111')
        self.assertEqual(call['assets'][0]['category_name'], 'Customer Premises Equipment')
        self.assertEqual(call['assets'][0]['custom_attributes'], [{'label': 'Model', 'value': 'C-111'}])
        self.assertNotIn('must-not-leave-assetms', str(call['assets'][0]))

    @mock.patch('integrations.services.request.urlopen')
    def test_asset_projection_client_uses_authenticated_put(self, urlopen):
        response = mock.MagicMock()
        response.read.return_value = b'{"total": 0}'
        urlopen.return_value.__enter__.return_value = response
        client = SourceCustomerApiClient(base_url='https://internet.example.com', api_token='secret-token')

        result = client.replace_customer_assets(
            customer_uuid='11111111-1111-1111-1111-111111111111',
            assets=[],
        )

        self.assertEqual(result, {'total': 0})
        outgoing = urlopen.call_args.args[0]
        self.assertEqual(outgoing.get_method(), 'PUT')
        self.assertEqual(outgoing.get_header('Authorization'), 'Token secret-token')
        self.assertEqual(outgoing.data, b'{"assets": []}')


class AssetCustomerProjectionSignalTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Projection Co')
        self.category = AssetCategory.objects.create(company=self.company, name='Routers')
        common = {
            'company': self.company,
            'customer_status': 'active',
            'customer_type': 'internet',
            'source_created_at': timezone.now(),
            'last_synced_at': timezone.now(),
        }
        self.customer_a = ExternalCustomerReference.objects.create(full_name='Customer A', **common)
        self.customer_b = ExternalCustomerReference.objects.create(full_name='Customer B', **common)

    @mock.patch('integrations.tasks.sync_customer_asset_projection.delay')
    def test_relinking_queues_old_and_new_customer_snapshots_after_commit(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            asset = Asset.objects.create(
                company=self.company,
                category=self.category,
                customer_reference=self.customer_a,
                status=Asset.STATUS_ACTIVE,
            )
        delay.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            asset.customer_reference = self.customer_b
            asset.save()

        self.assertEqual(
            {call.args[0] for call in delay.call_args_list},
            {self.customer_a.id, self.customer_b.id},
        )


class CustomerSyncApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Beta')
        self.user = User.objects.create_user(
            username='beta-admin',
            password='pass',
            company=self.company,
            role=User.ADMIN,
        )
        self.client.force_login(self.user)

    def test_config_update_and_fetch(self):
        response = self.client.post(
            '/integrations/api/customer-sync-config/update/',
            data='{"source_base_url":"https://internet.example.com","source_tenant_slug":"beta","api_token":"secret","is_enabled":true}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ExternalCustomerSyncConfig.objects.filter(company=self.company).exists())

        fetch = self.client.get('/integrations/api/customer-sync-config/')
        self.assertEqual(fetch.status_code, 200)
        self.assertTrue(fetch.json()['success'])

    @mock.patch('integrations.views.CustomerSyncService.sync_company_customers')
    def test_run_sync_endpoint(self, sync_company_customers):
        sync_company_customers.return_value = mock.Mock(
            status=CustomerSyncRun.Status.SUCCESS,
            created=3,
            updated=1,
            skipped=2,
            failed=0,
            error_summary='',
            run=mock.Mock(finished_at=timezone.now()),
        )
        response = self.client.post('/integrations/api/customer-sync/run/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['sync']['created'], 3)


class SyncedCustomerPageTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Gamma')
        self.user = User.objects.create_user(
            username='gamma-admin',
            password='pass',
            company=self.company,
            role=User.ADMIN,
        )
        self.client.force_login(self.user)
        self.category = AssetCategory.objects.create(company=self.company, name='Laptops')
        self.customer = ExternalCustomerReference.objects.create(
            company=self.company,
            full_name='PETER',
            phone='+255700111222',
            email='peter@example.com',
            address='Dar es Salaam',
            customer_status='active',
            customer_type='internet',
            source_created_at=timezone.now(),
            last_synced_at=timezone.now(),
            sync_status=ExternalCustomerReference.SyncStatus.SYNCED,
        )
        self.asset = Asset.objects.create(
            company=self.company,
            category=self.category,
            customer_reference=self.customer,
            status=Asset.STATUS_ACTIVE,
            description='Linked test asset',
        )

    def test_customer_string_is_human_friendly(self):
        self.assertEqual(str(self.customer), 'PETER (+255700111222, peter@example.com)')

    def test_synced_customer_list_page_renders(self):
        response = self.client.get('/integrations/customers/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Synced Customers')
        self.assertContains(response, 'PETER')
        self.assertContains(response, '+255700111222')
        self.assertContains(response, 'peter@example.com')

    def test_synced_customer_detail_page_shows_linked_asset(self):
        response = self.client.get(f'/integrations/customers/{self.customer.external_uuid}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Linked Assets')
        self.assertContains(response, str(self.asset))
