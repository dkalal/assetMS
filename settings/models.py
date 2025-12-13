from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class SystemSetting(models.Model):
    """Enterprise system settings model"""
    SETTING_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]
    
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string')
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default='general')
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'system_settings'
        ordering = ['category', 'key']
    
    def __str__(self):
        return f"{self.key}: {self.value}"

class OrganizationProfile(models.Model):
    """Organization/Company profile settings"""
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='organization/', blank=True, null=True)
    website = models.URLField(blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Address fields
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Business details
    tax_id = models.CharField(max_length=50, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    
    # System settings
    timezone = models.CharField(max_length=50, default='UTC')
    date_format = models.CharField(max_length=20, default='YYYY-MM-DD')
    currency = models.CharField(max_length=10, default='USD')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'organization_profile'
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_current(cls):
        """Get or create the organization profile"""
        profile, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'name': 'Your Organization',
                'email': 'admin@yourorg.com'
            }
        )
        return profile