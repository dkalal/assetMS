from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from users.models import User
from users.permissions import UserPermissionManager

class Command(BaseCommand):
    help = 'Setup enterprise-level permissions and groups'

    def handle(self, *args, **options):
        self.stdout.write('Setting up permissions and groups...')
        
        # Create custom permissions
        user_ct = ContentType.objects.get_for_model(User)
        
        custom_permissions = [
            ('view_reports', 'Can view reports'),
            ('export_data', 'Can export data'),
            ('backup_system', 'Can backup system'),
            ('restore_system', 'Can restore system'),
        ]
        
        for codename, name in custom_permissions:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=user_ct,
                defaults={'name': name}
            )
            if created:
                self.stdout.write(f'Created permission: {name}')
        
        # Setup role groups
        for role in ['admin', 'manager', 'user']:
            group, created = Group.objects.get_or_create(name=role.title())
            if created:
                self.stdout.write(f'Created group: {role.title()}')
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add permissions based on role
            permissions = UserPermissionManager.get_role_permissions(role)
            for perm_codename in permissions:
                try:
                    permission = Permission.objects.get(codename=perm_codename)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(f'Warning: Permission {perm_codename} not found')
            
            self.stdout.write(f'Updated permissions for {role} group')
        
        # Update existing users
        for user in User.objects.all():
            UserPermissionManager.update_user_permissions(user, user.role)
            self.stdout.write(f'Updated permissions for user: {user.username}')
        
        self.stdout.write(self.style.SUCCESS('Successfully setup permissions and groups'))