"""
Account Management Forms
========================
Purpose: Forms for registration, email verification, invitations, onboarding
"""

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserInvitation, CompanyRegistration, OnboardingProgress
from .utils import validate_password_strength, validate_email_format
from tenancy.models import Company, Branch

User = get_user_model()


class RegistrationForm(forms.Form):
    """
    Self-service registration form.
    
    Fields:
    - Company name
    - First name, last name
    - Email
    - Password (with strength validation)
    - Plan selection
    - Terms acceptance
    """
    
    company_name = forms.CharField(
        max_length=255,
        label='Company Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your company name',
            'required': True,
        }),
        help_text='The name of your organization'
    )
    
    first_name = forms.CharField(
        max_length=150,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John',
            'required': True,
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Doe',
            'required': True,
        })
    )
    
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'john@example.com',
            'required': True,
        }),
        help_text="We'll use this to verify your account"
    )
    
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password',
            'required': True,
            'id': 'id_password',
        }),
        help_text='Minimum 8 characters with uppercase, lowercase, and numbers'
    )
    
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'required': True,
        })
    )
    
    plan = forms.ChoiceField(
        choices=CompanyRegistration.PLAN_CHOICES,
        initial='free',
        label='Plan',
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text='Start with a free trial'
    )
    
    terms_accepted = forms.BooleanField(
        label='I agree to the Terms of Service and Privacy Policy',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True,
        }),
        required=True
    )
    
    def clean_email(self):
        """Validate email uniqueness."""
        email = self.cleaned_data.get('email')
        
        if not validate_email_format(email):
            raise ValidationError('Please enter a valid email address.')
        
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                'An account with this email already exists. Try logging in instead.'
            )
        
        return email
    
    def clean_password(self):
        """Validate password strength."""
        password = self.cleaned_data.get('password')
        
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            raise ValidationError(errors)
        
        return password
    
    def clean(self):
        """Validate password confirmation."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError({
                    'password_confirm': 'Passwords do not match.'
                })
        
        return cleaned_data


class EmailVerificationForm(forms.Form):
    """
    Form for resending verification email.
    """
    
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
        })
    )
    
    def clean_email(self):
        """Validate email exists and is unverified."""
        email = self.cleaned_data.get('email')
        
        try:
            user = User.objects.get(email=email)
            if user.email_verified:
                raise ValidationError('This email is already verified.')
        except User.DoesNotExist:
            raise ValidationError('No account found with this email address.')
        
        return email


class InvitationForm(forms.ModelForm):
    """
    Form for sending user invitations.
    
    Supports single and bulk invitations.
    """
    
    class Meta:
        model = UserInvitation
        fields = ['email', 'first_name', 'last_name', 'role', 'branch']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'colleague@example.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Jane',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Smith',
            }),
            'role': forms.Select(attrs={
                'class': 'form-select',
            }),
            'branch': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        self.invited_by = kwargs.pop('invited_by', None)
        super().__init__(*args, **kwargs)
        
        # Filter branches by company
        if self.company:
            self.fields['branch'].queryset = Branch.objects.filter(
                company=self.company,
                is_active=True
            )
            self.fields['branch'].required = False
            self.fields['branch'].empty_label = 'Select branch (optional)'
    
    def clean_email(self):
        """Validate email doesn't already exist in company."""
        email = self.cleaned_data.get('email')
        
        if self.company and email:
            if User.objects.filter(email=email, company=self.company).exists():
                raise ValidationError(
                    f'A user with this email already exists in {self.company.name}.'
                )
        
        return email
    
    def clean_branch(self):
        """Validate branch belongs to company."""
        branch = self.cleaned_data.get('branch')
        
        if branch and self.company:
            if branch.company != self.company:
                raise ValidationError('Branch must belong to your company.')
        
        return branch


class BulkInvitationForm(forms.Form):
    """
    Form for bulk user invitations.
    
    Accepts multiple email addresses.
    """
    
    emails = forms.CharField(
        label='Email Addresses',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'colleague1@example.com\ncolleague2@example.com\ncolleague3@example.com',
        }),
        help_text='Enter one email address per line'
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        initial=User.USER,
        label='Default Role',
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text='All invited users will have this role'
    )
    
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        required=False,
        label='Default Branch',
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text='All invited users will be assigned to this branch'
    )
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if self.company:
            self.fields['branch'].queryset = Branch.objects.filter(
                company=self.company,
                is_active=True
            )
            self.fields['branch'].empty_label = 'Select branch (optional)'
    
    def clean_emails(self):
        """Parse and validate email addresses."""
        emails_text = self.cleaned_data.get('emails', '')
        emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
        
        if not emails:
            raise ValidationError('Please enter at least one email address.')
        
        if len(emails) > 50:
            raise ValidationError('Maximum 50 invitations per batch.')
        
        # Validate email formats
        invalid_emails = []
        for email in emails:
            if not validate_email_format(email):
                invalid_emails.append(email)
        
        if invalid_emails:
            raise ValidationError(f'Invalid email addresses: {", ".join(invalid_emails)}')
        
        # Check for duplicates
        if len(emails) != len(set(emails)):
            raise ValidationError('Duplicate email addresses found.')
        
        # Check if any emails already exist
        if self.company:
            existing_emails = User.objects.filter(
                email__in=emails,
                company=self.company
            ).values_list('email', flat=True)
            
            if existing_emails:
                raise ValidationError(
                    f'Users with these emails already exist: {", ".join(existing_emails)}'
                )
        
        return emails


class InvitationAcceptanceForm(forms.Form):
    """
    Form for accepting user invitation.
    
    User only needs to set password.
    """
    
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password',
            'required': True,
        }),
        help_text='Minimum 8 characters with uppercase, lowercase, and numbers'
    )
    
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'required': True,
        })
    )
    
    terms_accepted = forms.BooleanField(
        label='I agree to the Terms of Service and Privacy Policy',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True,
        }),
        required=True
    )
    
    def clean_password(self):
        """Validate password strength."""
        password = self.cleaned_data.get('password')
        
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            raise ValidationError(errors)
        
        return password
    
    def clean(self):
        """Validate password confirmation."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError({
                    'password_confirm': 'Passwords do not match.'
                })
        
        return cleaned_data


class OnboardingStep1Form(forms.Form):
    """
    Onboarding Step 1: Company Details
    """
    
    INDUSTRY_CHOICES = [
        ('', 'Select industry'),
        ('technology', 'Technology'),
        ('manufacturing', 'Manufacturing'),
        ('healthcare', 'Healthcare'),
        ('retail', 'Retail'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('government', 'Government'),
        ('other', 'Other'),
    ]
    
    COMPANY_SIZE_CHOICES = [
        ('', 'Select company size'),
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-1000', '201-1000 employees'),
        ('1000+', '1000+ employees'),
    ]
    
    industry = forms.ChoiceField(
        choices=INDUSTRY_CHOICES,
        required=False,
        label='Industry',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    company_size = forms.ChoiceField(
        choices=COMPANY_SIZE_CHOICES,
        required=False,
        label='Company Size',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    timezone = forms.CharField(
        max_length=100,
        required=False,
        label='Timezone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., America/New_York',
        }),
        help_text='Optional: Set your timezone for accurate timestamps'
    )


class OnboardingStep2Form(forms.Form):
    """
    Onboarding Step 2: Team Invitation (Optional)
    
    Uses BulkInvitationForm logic but simplified for onboarding.
    """
    
    invite_team = forms.BooleanField(
        required=False,
        label='Invite team members now',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    emails = forms.CharField(
        required=False,
        label='Email Addresses',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'colleague1@example.com\ncolleague2@example.com',
        }),
        help_text='Enter one email address per line (optional)'
    )
    
    def clean_emails(self):
        """Validate email addresses if provided."""
        emails_text = self.cleaned_data.get('emails', '')
        invite_team = self.cleaned_data.get('invite_team', False)
        
        if invite_team and emails_text:
            emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
            
            if not emails:
                raise ValidationError('Please enter at least one email address.')
            
            # Validate formats
            invalid_emails = []
            for email in emails:
                if not validate_email_format(email):
                    invalid_emails.append(email)
            
            if invalid_emails:
                raise ValidationError(f'Invalid email addresses: {", ".join(invalid_emails)}')
            
            return emails
        
        return []







