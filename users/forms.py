from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import User
from tenancy.models import Company, Branch, UserBranch


class EnterpriseUserCreationForm(DjangoUserCreationForm):
    """
    World-class user creation form with multi-tenancy support.
    
    Features:
    - Company and branch assignment
    - Role-based field visibility
    - Primary branch auto-assignment
    - Comprehensive validation
    - Audit trail integration
    - Email uniqueness check
    """
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        }),
        help_text='User\'s first name'
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        }),
        help_text='User\'s last name'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'user@company.com'
        }),
        help_text='Unique email address for login and notifications'
    )
    
    phone_number = forms.CharField(
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890'
        }),
        help_text='Contact phone number (optional)'
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='User role determines permissions and access level'
    )
    
    primary_branch = forms.ModelChoiceField(
        queryset=None,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Primary branch for this user'
    )
    
    send_invitation = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Send invitation email with login credentials'
    )
    
    force_password_change = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Require password change on first login'
    )

    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 
            'phone_number', 'role', 'primary_branch',
            'password1', 'password2'
        )
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        self.created_by = kwargs.pop('created_by', None)
        super().__init__(*args, **kwargs)
        
        # Make email required
        self.fields['email'].required = True
        
        # Scope branches to company
        if self.company:
            self.fields['primary_branch'].queryset = Branch.objects.filter(
                company=self.company,
                is_active=True
            ).order_by('name')
        else:
            self.fields['primary_branch'].queryset = Branch.objects.none()
        
        # Add help text for passwords
        self.fields['password1'].help_text = 'Minimum 8 characters. Leave blank to auto-generate.'
        self.fields['password2'].help_text = 'Re-enter password for confirmation'
        
        # Make passwords optional (will auto-generate if empty)
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def clean_email(self):
        """Ensure email is unique across the system."""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError(
                'A user with this email already exists. Please use a different email.'
            )
        return email
    
    def clean_username(self):
        """Ensure username is unique and follows naming conventions."""
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise ValidationError(
                'This username is already taken. Please choose a different username.'
            )
        # Additional validation: no spaces, minimum length
        if ' ' in username:
            raise ValidationError('Username cannot contain spaces.')
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters long.')
        return username
    
    def clean_primary_branch(self):
        """Validate branch belongs to the company."""
        branch = self.cleaned_data.get('primary_branch')
        if branch and self.company and branch.company_id != self.company.pk:
            raise ValidationError(
                'Selected branch does not belong to your company.'
            )
        if branch and not branch.is_active:
            raise ValidationError(
                'Cannot assign user to an inactive branch.'
            )
        return branch
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        # If one password is provided, both must be provided
        if password1 or password2:
            if password1 != password2:
                raise ValidationError({
                    'password2': 'Passwords do not match.'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Create user with company and branch assignment."""
        from django.utils.crypto import get_random_string
        
        user = super().save(commit=False)
        
        # Set company
        user.company = self.company
        
        # Auto-generate password if not provided
        password = self.cleaned_data.get('password1')
        if not password:
            password = get_random_string(12)
            user.set_password(password)
            user.force_password_change = True
        
        # Set additional fields
        user.force_password_change = self.cleaned_data.get('force_password_change', True)
        
        # Generate invitation token if needed
        if self.cleaned_data.get('send_invitation', True):
            user.is_invited = True
            user.invitation_token = get_random_string(32)
            from django.utils import timezone
            user.invitation_sent_at = timezone.now()
        
        if commit:
            with transaction.atomic():
                user.save()
                
                # Create primary branch membership
                primary_branch = self.cleaned_data.get('primary_branch')
                if primary_branch:
                    UserBranch.ensure_primary(
                        user=user,
                        company=self.company,
                        branch=primary_branch
                    )
        
        # Store generated password for display
        self.generated_password = password if not self.cleaned_data.get('password1') else None
        
        return user


class UserCreationForm(DjangoUserCreationForm):
    """Legacy form - kept for backward compatibility."""
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True 

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'profile_image', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        # Only admin can edit role
        if user and getattr(user, 'role', User.USER) != User.ADMIN:
            self.fields['role'].disabled = True