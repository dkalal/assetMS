# Settings System Documentation

## Overview

The Settings System is a comprehensive, enterprise-level configuration management solution for the Asset Management System. It provides users with granular control over their preferences, security settings, and system-wide configurations while maintaining enterprise-grade security and scalability.

## Architecture

### Core Components

1. **Settings App** (`settings/`)
   - Models for theme and backup management
   - Views for different settings categories
   - URL routing with namespace isolation
   - Admin interface integration

2. **Template Structure**
   - Main settings page with tabbed interface
   - Modular partial templates for each section
   - Responsive design with Bootstrap 5
   - Accessibility-compliant components

3. **JavaScript Framework**
   - AJAX-based settings management
   - Real-time validation and feedback
   - Theme preview functionality
   - Confirmation dialogs for destructive actions

## Features

### 1. Profile Settings
- **Personal Information Management**
  - First name, last name, email address
  - Phone number and profile image upload
  - Account information display
  - Password change integration

- **Account Security**
  - Password strength indicators
  - Last login tracking
  - Account creation date
  - Role-based access display

- **Data Management**
  - GDPR-compliant data export
  - Account deletion with confirmation
  - Profile visibility controls

### 2. Security & Privacy Settings
- **Password Security**
  - Password change functionality
  - Last password change tracking
  - Security recommendations

- **Two-Factor Authentication**
  - Toggle for 2FA (coming soon)
  - Security status indicators
  - Setup guidance

- **Session Management**
  - Current session information
  - Terminate other sessions
  - Session timeout configuration

- **Privacy Controls**
  - Profile visibility settings
  - Activity visibility controls
  - Email notification preferences

### 3. Notification Settings
- **Email Notifications**
  - Asset update notifications
  - Maintenance reminders
  - Report generation alerts
  - Security alerts
  - System update notifications

- **In-App Notifications**
  - Asset activity notifications
  - Task reminders
  - System messages
  - Sound notification controls

- **Notification Frequency**
  - Email digest frequency (immediate, hourly, daily, weekly)
  - Quiet hours configuration
  - Urgent notification overrides

### 4. System Settings (Admin Only)
- **Theme Customization**
  - Primary color selection
  - Secondary color configuration
  - Accent color management
  - Background color settings
  - Company logo upload

- **System Configuration**
  - Session timeout settings
  - Maximum login attempts
  - Backup frequency configuration
  - Data retention policies
  - Maintenance mode toggle
  - Debug mode controls

- **Data Management**
  - System backup creation
  - Backup restoration
  - Complete data export
  - Old data cleanup

## Technical Implementation

### Models

```python
# settings/models.py

class ThemeSetting(models.Model):
    primary_color = models.CharField(max_length=7, default="#00A6EB")
    secondary_color = models.CharField(max_length=7, default="#176B87")
    accent_color = models.CharField(max_length=7, default="#04364A")
    background_color = models.CharField(max_length=7, default="#B4E9FC")
    logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

class BackupRestore(models.Model):
    backup_file = models.FileField(upload_to='backups/')
    created_at = models.DateTimeField(auto_now_add=True)
    restored = models.BooleanField()
```

### Views

```python
# settings/views.py

class SettingsView(LoginRequiredMixin, TemplateView):
    """Main settings page with tabbed interface"""
    
class ProfileSettingsView(LoginRequiredMixin, UpdateView):
    """User profile settings update"""
    
class SecuritySettingsView(LoginRequiredMixin, TemplateView):
    """Security and privacy settings"""
    
class SystemSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """System-wide settings (admin only)"""
```

### URL Structure

```python
# settings/urls.py

urlpatterns = [
    path('', views.SettingsView.as_view(), name='settings'),
    path('profile/', views.ProfileSettingsView.as_view(), name='profile_settings'),
    path('security/', views.SecuritySettingsView.as_view(), name='security_settings'),
    path('notifications/', views.NotificationSettingsView.as_view(), name='notification_settings'),
    path('system/', views.SystemSettingsView.as_view(), name='system_settings'),
    
    # API endpoints
    path('api/notifications/', views.update_notification_preferences, name='update_notifications'),
    path('api/theme/', views.update_theme_settings, name='update_theme'),
    path('api/export-data/', views.export_user_data, name='export_data'),
    path('api/delete-account/', views.delete_user_account, name='delete_account'),
]
```

## Security Features

### 1. Authentication & Authorization
- **Login Required**: All settings views require authentication
- **Role-Based Access**: System settings restricted to admin users
- **CSRF Protection**: All forms and AJAX requests protected
- **Permission Checks**: Granular permission validation

### 2. Data Protection
- **Input Validation**: Server-side validation for all inputs
- **XSS Prevention**: Proper escaping and sanitization
- **SQL Injection Protection**: Django ORM protection
- **File Upload Security**: Restricted file types and sizes

### 3. Privacy Compliance
- **GDPR Compliance**: Data export and deletion capabilities
- **Audit Logging**: All settings changes logged
- **Data Minimization**: Only necessary data collected
- **User Consent**: Explicit consent for data processing

## User Experience

### 1. Interface Design
- **Tabbed Navigation**: Organized settings categories
- **Responsive Layout**: Mobile-friendly design
- **Visual Feedback**: Success/error messages
- **Loading States**: Progress indicators for actions

### 2. Accessibility
- **ARIA Labels**: Screen reader support
- **Keyboard Navigation**: Full keyboard accessibility
- **Color Contrast**: WCAG 2.1 AA compliance
- **Focus Management**: Proper focus indicators

### 3. Performance
- **Lazy Loading**: Settings loaded on demand
- **Caching**: Theme settings cached
- **Optimized Queries**: Efficient database queries
- **Minimal JavaScript**: Lightweight client-side code

## API Endpoints

### 1. Notification Preferences
```http
POST /settings/api/notifications/
Content-Type: application/json
X-CSRFToken: <token>

{
    "emailAssetUpdates": true,
    "emailMaintenance": true,
    "emailReports": false,
    "emailFrequency": "daily",
    "quietStart": "22:00",
    "quietEnd": "08:00"
}
```

### 2. Theme Settings
```http
POST /settings/api/theme/
Content-Type: application/json
X-CSRFToken: <token>

{
    "primary_color": "#00A6EB",
    "secondary_color": "#176B87",
    "accent_color": "#04364A",
    "background_color": "#B4E9FC"
}
```

### 3. Data Export
```http
POST /settings/api/export-data/
Content-Type: application/json
X-CSRFToken: <token>

Response: {
    "status": "success",
    "message": "Data export initiated. You will receive an email when ready.",
    "download_url": null
}
```

## Configuration

### 1. Environment Variables
```bash
# Settings app configuration
SETTINGS_BACKUP_DIR=/path/to/backups
SETTINGS_MAX_FILE_SIZE=2097152  # 2MB
SETTINGS_ALLOWED_EXTENSIONS=png,jpg,jpeg,gif
```

### 2. Django Settings
```python
# settings.py

INSTALLED_APPS = [
    # ...
    'settings',
]

# File upload settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Session settings
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

## Usage Examples

### 1. Accessing Settings
```python
# In templates
<a href="{% url 'settings:settings' %}">Settings</a>

# In views
from django.urls import reverse
settings_url = reverse('settings:settings')
```

### 2. Theme Customization
```python
# Get current theme settings
from settings.models import ThemeSetting

theme = ThemeSetting.objects.first()
primary_color = theme.primary_color if theme else '#00A6EB'
```

### 3. User Preferences
```python
# Check user notification preferences
user = request.user
# Implementation would check user preferences from database
```

## Best Practices

### 1. Security
- Always validate user permissions before allowing access
- Use Django's built-in security features
- Implement proper error handling
- Log all sensitive operations

### 2. Performance
- Cache frequently accessed settings
- Use database indexes for queries
- Implement pagination for large datasets
- Optimize file uploads

### 3. User Experience
- Provide clear feedback for all actions
- Use progressive disclosure for complex settings
- Implement undo/redo functionality where possible
- Maintain consistency across all settings pages

### 4. Maintenance
- Regular backup of settings data
- Monitor system performance
- Update dependencies regularly
- Document all changes

## Troubleshooting

### Common Issues

1. **Settings Not Saving**
   - Check CSRF token
   - Verify user permissions
   - Check form validation errors

2. **Theme Not Applying**
   - Clear browser cache
   - Check CSS variable definitions
   - Verify color format (hex codes)

3. **File Upload Failures**
   - Check file size limits
   - Verify allowed file types
   - Ensure directory permissions

### Debug Mode

Enable debug mode for detailed error information:
```python
DEBUG = True
```

## Future Enhancements

### 1. Planned Features
- Two-factor authentication implementation
- Advanced notification scheduling
- Bulk settings import/export
- Settings templates for different user roles

### 2. Performance Improvements
- Redis caching for settings
- Database query optimization
- CDN integration for assets
- Progressive web app features

### 3. Security Enhancements
- Advanced audit logging
- IP-based access controls
- Rate limiting for API endpoints
- Enhanced encryption for sensitive data

## Support

For technical support or feature requests:
- Check the help documentation
- Review system logs
- Contact system administrator
- Submit bug reports through the issue tracker

---

**Version**: 1.0.0  
**Last Updated**: August 15, 2025  
**Status**: Production Ready


