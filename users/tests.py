import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tenancy.models import Branch, Company, UserBranch
from users.models import UserRetirement


User = get_user_model()


class RetirementAPIWorkflowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Retirement Workflow Company')
        self.branch = Branch.objects.create(
            company=self.company,
            name='Head Office',
            code='HO',
            is_head_office=True,
        )
        self.employee = User.objects.create_user(
            username='retirement-employee',
            password='pass',
            role=User.USER,
            company=self.company,
        )
        self.manager = User.objects.create_user(
            username='retirement-manager',
            password='pass',
            role=User.MANAGER,
            company=self.company,
        )
        for user in (self.employee, self.manager):
            UserBranch.objects.create(
                user=user,
                company=self.company,
                branch=self.branch,
                is_primary=True,
            )
        self.branch.manager = self.manager
        self.branch.save(update_fields=['manager'])

    def create_request(self):
        return UserRetirement.objects.create(
            user=self.employee,
            company=self.company,
            requested_by=self.employee,
            effective_date=date.today() + timedelta(days=30),
            reason_category=UserRetirement.REASON_RETIREMENT,
            reason='Planned retirement with a documented asset handover.',
        )

    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_employee_status_payload_and_cancel_contract(self):
        retirement = self.create_request()
        self.client.force_login(self.employee)

        status = self.client.get(reverse('api_retirement_my_request'))
        self.assertEqual(status.status_code, 200)
        payload = status.json()
        self.assertTrue(payload['has_request'])
        self.assertIn('timeline', payload['retirement'])
        self.assertIn('assets', payload['retirement'])

        cancelled = self.post_json(
            reverse('api_retirement_cancel_mine'),
            {'retirement_id': str(retirement.id), 'reason': 'The effective date and transition plan have changed.'},
        )
        self.assertEqual(cancelled.status_code, 200)
        retirement.refresh_from_db()
        self.assertEqual(retirement.status, UserRetirement.STATUS_CANCELLED)

    def test_manager_can_approve_but_employee_cannot(self):
        retirement = self.create_request()
        approve_url = reverse('api_retirement_approve', args=[retirement.id])

        self.client.force_login(self.employee)
        denied = self.post_json(approve_url, {'comments': 'Self approval attempt'})
        self.assertEqual(denied.status_code, 403)
        retirement.refresh_from_db()
        self.assertEqual(retirement.status, UserRetirement.STATUS_REQUESTED)

        self.client.force_login(self.manager)
        approved = self.post_json(approve_url, {'comments': 'Handover plan reviewed and accepted.'})
        self.assertEqual(approved.status_code, 200)
        retirement.refresh_from_db()
        self.assertEqual(retirement.status, UserRetirement.STATUS_APPROVED)
        self.assertEqual(retirement.reviewed_by, self.manager)

    def test_rejection_requires_auditable_reason(self):
        retirement = self.create_request()
        self.client.force_login(self.manager)
        reject_url = reverse('api_retirement_reject', args=[retirement.id])

        invalid = self.post_json(reject_url, {'rejection_reason': 'Too short'})
        self.assertEqual(invalid.status_code, 400)
        retirement.refresh_from_db()
        self.assertEqual(retirement.status, UserRetirement.STATUS_REQUESTED)

        rejected = self.post_json(
            reject_url,
            {'rejection_reason': 'The transition plan needs an updated asset return schedule.'},
        )
        self.assertEqual(rejected.status_code, 200)
        retirement.refresh_from_db()
        self.assertEqual(retirement.status, UserRetirement.STATUS_REJECTED)
