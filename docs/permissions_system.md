# Asset Management System - Permissions System Documentation

## Overview
The permissions system in the Asset Management System is designed to be enterprise-grade, providing both role-based and granular permission management capabilities. It supports multiple levels of permission control:

1. Role-based permissions (admin, manager, user)
2. Permission groups (collections of related permissions)
3. Explicit permissions (individual permissions)

## Models

### User Model
- `role`: Role of the user (admin, manager, user)
- `can_manage_users`: Manage users and their permissions
- `can_manage_assets`: Manage assets
- `can_manage_categories`: Manage asset categories
- `can_manage_reports`: Generate and manage reports
- `can_view_audit_logs`: View audit logs and activity history

### PermissionGroup Model
- `name`: Name of the permission group
- `description`: Description of what the group grants access to
- `permissions`: Many-to-many relationship with Django's built-in Permission model

### UserPermission Model
- `user`: User assigned the permission
- `permission_group`: Permission group assigned to the user
- `granted_by`: User who granted the permission
- `granted_at`: Timestamp when permission was granted
- `is_active`: Boolean indicating if the permission is currently active

## Views

### Profile Management
- `profile/`: User profile page showing permissions
- `assign/permission-group/<user_id>/<group_id>/`: Assign a permission group to a user
- `remove/permission-group/<user_id>/<group_id>/`: Remove a permission group from a user
- `assign/explicit-permission/`: Assign an explicit permission to a user
- `remove/explicit-permission/`: Remove an explicit permission from a user

### Permission Management
- `permissions/`: List all users and their permissions
- `permissions/<user_id>/`: Get permissions for a specific user
- `permissions/<user_id>/export/`: Export user's permissions to CSV
- `permission-group/<group_id>/details/`: Get detailed information about a permission group

## Security Features

### Role Hierarchy
1. Admin (highest)
   - Can do everything
   - Can override any permission
2. Manager
   - Can manage assets, categories, and reports
   - Cannot manage users or view audit logs
3. User (lowest)
   - Basic access
   - Permissions defined by assigned groups and explicit permissions

### Audit Logging
- All permission changes are logged
- Logs include:
  - Action (assign/remove)
  - User affected
  - Permission/Group changed
  - Who made the change
  - When the change was made

## Best Practices

### Permission Assignment
1. Use permission groups for common permission sets
2. Use explicit permissions for special cases
3. Always audit permission changes
4. Regularly review user permissions

### Security Considerations
1. Never grant admin privileges unless absolutely necessary
2. Use permission groups to control access to sensitive areas
3. Regularly review and audit permission assignments
4. Ensure proper separation of duties

## Implementation Notes

### Permission Checking
- Uses both role-based and explicit permission checks
- Admins have implicit access to all permissions
- Managers have implicit access to asset-related permissions
- Users must have explicit permissions assigned

### Performance Optimization
- Uses prefetch_related and select_related for efficient queries
- Caches permission data where appropriate
- Minimizes database queries through careful query design

## Future Enhancements
1. Permission inheritance between groups
2. Time-based permissions
3. Resource-specific permissions
4. Permission delegation
5. Advanced permission reporting
