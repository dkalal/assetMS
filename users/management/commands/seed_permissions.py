from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction


class Command(BaseCommand):
    help = "Seed default groups and permissions (Admin, Manager, User) and assign based on user.role"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # Ensure custom permissions exist (created from users.User Meta.permissions during migrate)
        required_perms = [
            ("users", "can_manage_users"),
            ("users", "can_manage_assets"),
            ("users", "can_manage_categories"),
            ("users", "can_manage_reports"),
            ("users", "can_view_audit_logs"),
        ]

        perms = {}
        for app_label, codename in required_perms:
            perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if not perm:
                self.stdout.write(self.style.WARNING(f"Missing permission {app_label}.{codename}. Did you run migrations?"))
            perms[codename] = perm

        # Create or update groups
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        user_group, _ = Group.objects.get_or_create(name="User")

        # Assign permissions to groups (ignore None perms that might be missing)
        def set_group_perms(group, codenames):
            group.permissions.clear()
            for code in codenames:
                if perms.get(code):
                    group.permissions.add(perms[code])
            group.save()

        set_group_perms(admin_group, [
            "can_manage_users",
            "can_manage_assets",
            "can_manage_categories",
            "can_manage_reports",
            "can_view_audit_logs",
        ])

        set_group_perms(manager_group, [
            "can_manage_assets",
            "can_manage_categories",
            "can_manage_reports",
        ])

        set_group_perms(user_group, [])

        # Assign groups based on role field for convenience (idempotent)
        admins = User.objects.filter(role="admin")
        managers = User.objects.filter(role="manager")
        basic_users = User.objects.filter(role="user")

        for u in admins:
            u.groups.add(admin_group)
        for u in managers:
            u.groups.add(manager_group)
        for u in basic_users:
            u.groups.add(user_group)

        self.stdout.write(self.style.SUCCESS("Seeded groups and permissions; assigned groups by user.role"))




