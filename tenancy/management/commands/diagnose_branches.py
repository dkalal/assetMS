"""
Management command to diagnose branch assignment issues.

Usage:
    python manage.py diagnose_branches
    python manage.py diagnose_branches --user <username>
    python manage.py diagnose_branches --company <company_id>
    python manage.py diagnose_branches --fix-orphaned
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from tenancy.models import Company, Branch, UserBranch

User = get_user_model()


class Command(BaseCommand):
    help = 'Diagnose and fix branch assignment issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Diagnose specific user by username',
        )
        parser.add_argument(
            '--company',
            type=int,
            help='Diagnose specific company by ID',
        )
        parser.add_argument(
            '--fix-orphaned',
            action='store_true',
            help='Automatically fix users without branch assignments',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Branch Assignment Diagnostic Tool'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

        # Filter by user if specified
        if options['user']:
            self.diagnose_user(options['user'], options['verbose'])
            return

        # Filter by company if specified
        if options['company']:
            self.diagnose_company(options['company'], options['verbose'])
            return

        # Full system diagnosis
        self.diagnose_system(options['verbose'], options['fix_orphaned'])

    def diagnose_system(self, verbose=False, fix_orphaned=False):
        """Run full system diagnosis"""
        
        # 1. Company Statistics
        self.stdout.write(self.style.WARNING('\n📊 COMPANY STATISTICS'))
        self.stdout.write('-' * 70)
        
        companies = Company.objects.annotate(
            branch_count=Count('branches', filter=Q(branches__is_active=True), distinct=True),
            user_count=Count('users', filter=Q(users__is_active=True), distinct=True)
        )
        
        for company in companies:
            self.stdout.write(f'\n🏢 {company.name} (ID: {company.id})')
            self.stdout.write(f'   Active Branches: {company.branch_count}')
            self.stdout.write(f'   Active Users: {company.user_count}')
            
            if company.branch_count == 0:
                self.stdout.write(self.style.ERROR('   ⚠️  WARNING: No active branches!'))

        # 2. Branch Statistics
        self.stdout.write(self.style.WARNING('\n\n🏢 BRANCH STATISTICS'))
        self.stdout.write('-' * 70)
        
        branches = Branch.objects.filter(is_active=True).select_related('company', 'manager').annotate(
            member_count=Count('memberships', distinct=True)
        )
        
        for branch in branches:
            self.stdout.write(f'\n📍 {branch.name} ({branch.company.name})')
            self.stdout.write(f'   Code: {branch.code}')
            self.stdout.write(f'   HQ: {"Yes" if branch.is_head_office else "No"}')
            self.stdout.write(f'   Members: {branch.member_count}')
            self.stdout.write(f'   Manager: {branch.manager or "None"}')
            
            if branch.member_count == 0:
                self.stdout.write(self.style.WARNING('   ⚠️  No users assigned'))

        # 3. User Assignment Issues
        self.stdout.write(self.style.WARNING('\n\n👥 USER ASSIGNMENT ANALYSIS'))
        self.stdout.write('-' * 70)
        
        # Users without any branch assignments
        users_without_branches = User.objects.filter(
            is_active=True,
            company__isnull=False
        ).annotate(
            branch_count=Count('user_branches', distinct=True)
        ).filter(branch_count=0)
        
        if users_without_branches.exists():
            self.stdout.write(self.style.ERROR(f'\n⚠️  {users_without_branches.count()} users without branch assignments:'))
            for user in users_without_branches:
                self.stdout.write(f'   - {user.username} ({user.get_full_name()}) - {user.company.name}')
                
                if fix_orphaned:
                    self.fix_user_branch_assignment(user)
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ All users have branch assignments'))

        # Users without primary branch
        users_without_primary = User.objects.filter(
            is_active=True,
            company__isnull=False
        ).exclude(
            user_branches__is_primary=True
        )
        
        if users_without_primary.exists():
            self.stdout.write(self.style.WARNING(f'\n⚠️  {users_without_primary.count()} users without primary branch:'))
            for user in users_without_primary[:10]:  # Show first 10
                self.stdout.write(f'   - {user.username} ({user.company.name})')

        # 4. UserBranch Statistics
        self.stdout.write(self.style.WARNING('\n\n🔗 USERBRANCH RELATIONSHIPS'))
        self.stdout.write('-' * 70)
        
        total_memberships = UserBranch.objects.filter(branch__is_active=True).count()
        primary_memberships = UserBranch.objects.filter(is_primary=True, branch__is_active=True).count()
        
        self.stdout.write(f'\nTotal Active Memberships: {total_memberships}')
        self.stdout.write(f'Primary Memberships: {primary_memberships}')
        
        # Check for duplicate primaries
        duplicate_primaries = User.objects.annotate(
            primary_count=Count('user_branches', filter=Q(user_branches__is_primary=True), distinct=True)
        ).filter(primary_count__gt=1)
        
        if duplicate_primaries.exists():
            self.stdout.write(self.style.ERROR(f'\n⚠️  {duplicate_primaries.count()} users with multiple primary branches:'))
            for user in duplicate_primaries:
                primaries = UserBranch.objects.filter(user=user, is_primary=True)
                self.stdout.write(f'   - {user.username}: {[p.branch.name for p in primaries]}')

        # 5. Summary
        self.stdout.write(self.style.SUCCESS('\n\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('DIAGNOSIS COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

    def diagnose_user(self, username, verbose=False):
        """Diagnose specific user"""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
            return

        self.stdout.write(self.style.WARNING(f'\n👤 USER: {user.username}'))
        self.stdout.write('-' * 70)
        self.stdout.write(f'Name: {user.get_full_name()}')
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'Role: {user.role}')
        self.stdout.write(f'Company: {user.company.name if user.company else "None"}')
        self.stdout.write(f'Active: {user.is_active}')

        if not user.company:
            self.stdout.write(self.style.ERROR('\n⚠️  User has no company assigned!'))
            return

        # Branch assignments
        memberships = UserBranch.objects.filter(user=user).select_related('branch')
        
        self.stdout.write(f'\n🏢 BRANCH ASSIGNMENTS ({memberships.count()}):')
        for membership in memberships:
            primary = '⭐ PRIMARY' if membership.is_primary else ''
            active = '✅' if membership.branch.is_active else '❌ INACTIVE'
            self.stdout.write(f'   {active} {membership.branch.name} {primary}')

        if memberships.count() == 0:
            self.stdout.write(self.style.ERROR('   ⚠️  No branch assignments!'))

        # Primary branch
        primary_branch = user.primary_branch
        self.stdout.write(f'\nPrimary Branch: {primary_branch.name if primary_branch else "None"}')

    def diagnose_company(self, company_id, verbose=False):
        """Diagnose specific company"""
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Company ID {company_id} not found'))
            return

        self.stdout.write(self.style.WARNING(f'\n🏢 COMPANY: {company.name}'))
        self.stdout.write('-' * 70)

        # Branches
        branches = Branch.objects.filter(company=company, is_active=True)
        self.stdout.write(f'\nActive Branches: {branches.count()}')
        for branch in branches:
            member_count = UserBranch.objects.filter(branch=branch).count()
            self.stdout.write(f'   📍 {branch.name} ({member_count} members)')

        # Users
        users = User.objects.filter(company=company, is_active=True)
        self.stdout.write(f'\nActive Users: {users.count()}')
        
        users_without_branches = users.annotate(
            branch_count=Count('user_branches')
        ).filter(branch_count=0)
        
        if users_without_branches.exists():
            self.stdout.write(self.style.ERROR(f'\n⚠️  {users_without_branches.count()} users without branches:'))
            for user in users_without_branches:
                self.stdout.write(f'   - {user.username}')

    def fix_user_branch_assignment(self, user):
        """Automatically assign user to a branch"""
        if not user.company:
            self.stdout.write(self.style.ERROR(f'   ❌ Cannot fix {user.username}: No company'))
            return

        # Find a suitable branch (prefer HQ)
        branch = Branch.objects.filter(
            company=user.company,
            is_active=True,
            is_head_office=True
        ).first()

        if not branch:
            # Fallback to any active branch
            branch = Branch.objects.filter(
                company=user.company,
                is_active=True
            ).first()

        if not branch:
            self.stdout.write(self.style.ERROR(f'   ❌ Cannot fix {user.username}: No active branches'))
            return

        # Create membership
        UserBranch.ensure_primary(user=user, company=user.company, branch=branch)
        self.stdout.write(self.style.SUCCESS(f'   ✅ Assigned {user.username} to {branch.name}'))
