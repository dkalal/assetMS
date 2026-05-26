from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tenancy.models import Company

from .models import CustomerSyncRun, ExternalCustomerReference, ExternalCustomerSyncConfig
from .services import CustomerSyncService, SourceCustomerApiError


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
