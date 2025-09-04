from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from assets.models import Asset, AssetCategory
from audit.models import AuditLog

User = get_user_model()


class NotificationsApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create users with roles
        self.admin = User.objects.create_user(username='admin', password='pass', role='admin')
        self.manager = User.objects.create_user(username='manager', password='pass', role='manager')
        self.user1 = User.objects.create_user(username='user1', password='pass', role='user')
        self.user2 = User.objects.create_user(username='user2', password='pass', role='user')
        # Minimal category required to create assets
        self.cat = AssetCategory.objects.create(name='Laptops')
        # Assets
        self.asset1 = Asset.objects.create(category=self.cat, status='active', description='A1', assigned_to=self.user1, dynamic_data={})
        self.asset2 = Asset.objects.create(category=self.cat, status='active', description='A2', assigned_to=None, dynamic_data={})

        # Logs for visibility rules
        now = timezone.now()
        # user1's own action
        AuditLog.objects.create(user=self.user1, action='view', asset=self.asset1, timestamp=now, details='u1 view a1')
        # action on asset assigned to user1 by someone else
        AuditLog.objects.create(user=self.manager, action='edit', asset=self.asset1, timestamp=now, details='mgr edit a1')
        # unrelated asset action by user2
        AuditLog.objects.create(user=self.user2, action='create', asset=self.asset2, timestamp=now, details='u2 create a2')

    def login(self, user):
        self.client.logout()
        self.client.login(username=user.username, password='pass')

    def test_admin_sees_all_logs(self):
        self.login(self.admin)
        resp = self.client.get('/notifications-api/?limit=10')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('items', data)
        titles = [it.get('title', '') for it in data['items']]
        # All three created above should be present when limit allows
        self.assertTrue(any('View' in t or 'view' in t for t in titles))
        self.assertTrue(any('Edit' in t or 'edit' in t for t in titles))
        self.assertTrue(any('Create' in t or 'create' in t for t in titles))

    def test_user_sees_own_and_assigned_asset_logs_only(self):
        self.login(self.user1)
        resp = self.client.get('/notifications-api/?limit=10')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data['items']
        # Should NOT include user2 on asset2 (unrelated)
        bodies = '\n'.join([str(i) for i in items])
        self.assertIn('a1', bodies.lower())  # has logs for asset1
        self.assertNotIn('a2', bodies.lower())  # should not include asset2 log

    def test_limit_default_and_cap(self):
        # Create many logs
        self.login(self.admin)
        for i in range(40):
            AuditLog.objects.create(user=self.admin, action='view', asset=self.asset1, timestamp=timezone.now(), details=f'x{i}')
        # No limit -> default 5
        resp_default = self.client.get('/notifications-api/')
        self.assertEqual(resp_default.status_code, 200)
        self.assertEqual(len(resp_default.json().get('items', [])), 5)
        # Over-limit -> cap 20
        resp_cap = self.client.get('/notifications-api/?limit=9999')
        self.assertEqual(resp_cap.status_code, 200)
        self.assertEqual(len(resp_cap.json().get('items', [])), 20)

    def test_manager_restricted_like_user(self):
        # Manager should not see unrelated user2 on asset2
        self.login(self.manager)
        resp = self.client.get('/notifications-api/?limit=10')
        self.assertEqual(resp.status_code, 200)
        items = resp.json().get('items', [])
        bodies = '\n'.join([str(i) for i in items])
        self.assertIn('a1', bodies.lower())  # should include logs related to asset1 via user1 assignment
        self.assertNotIn('a2', bodies.lower())  # should NOT include unrelated asset2 log
