from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings

from .models import User
from tenancy.models import Company, Branch, UserBranch
from audit.utils import log_password_reset_requested
from .tasks import send_password_reset_email


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


class PasswordResetEmailOrUsernameForm(PasswordResetForm):
    """
    Password reset form that accepts email or username.
    We keep the field name as 'email' to satisfy Django's view expectations,
    but allow either value and resolve to matching active users.
    """
    email = forms.CharField(
        label='Email or Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email or username',
            'autocomplete': 'email',
        }),
        help_text='We will send a reset link if the account exists.'
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Provide company-aware hint when available
        company = getattr(self.request.user, 'company', None) if self.request and getattr(self.request, 'user', None) else None
        if company:
            self.fields['email'].help_text = (
                f"We'll email the reset link to active {company.name} accounts. "
                "Usernames are also accepted."
            )

    def get_users(self, email_or_username):
        """
        Resolve active users scoped to the requester's company, accepting email or username.
        """
        email_or_username = email_or_username.strip()
        if not email_or_username:
            return []

        base_query = Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username)
        filters = {'is_active': True}

        if self.request and getattr(self.request, 'user', None) and getattr(self.request.user, 'company', None):
            filters['company'] = self.request.user.company

        return User._default_manager.filter(base_query, **filters)

    def save(
        self,
        domain_override=None,
        subject_template_name='registration/password_reset_subject.txt',
        email_template_name='registration/password_reset_email.html',
        html_email_template_name=None,
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        extra_email_context=None,
    ):
        """Send password reset emails via Celery with tenancy-aware logging."""

        request = request or self.request
        identifier = self.cleaned_data.get('email', '').strip()
        users = list(self.get_users(identifier))

        if request is None:
            # Without request context we cannot determine domain; abort safely.
            log_password_reset_requested(
                user=None,
                request=None,
                identifier=identifier,
                success=False,
                target_user=None,
            )
            return

        if domain_override:
            domain = domain_override
            site_name = domain_override
        else:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain

        protocol = 'https' if use_https or request.is_secure() else 'http'
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        request_user = getattr(request, 'user', None)
        authenticated_request_user = request_user if getattr(request_user, 'is_authenticated', False) else None

        emails_sent = False
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            reset_path = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            reset_link = f"{protocol}://{domain}{reset_path}"
            company_name = user.company.name if getattr(user, 'company', None) else 'AssetMS'

            subject_context = {
                'company_name': company_name,
                'site_name': site_name,
            }

            # Compose subject using default template behaviour
            subject = f"[{company_name}] Password Reset Request"
            if subject_template_name:
                try:
                    from django.template.loader import render_to_string

                    subject = render_to_string(subject_template_name, subject_context)
                    subject = ''.join(subject.splitlines())
                except Exception:
                    # Fall back to static subject if template rendering fails
                    subject = f"[{company_name}] Password Reset Request"

            email_context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': uid,
                'user_id': user.id,
                'token': token,
                'protocol': protocol,
                'reset_link': reset_link,
                'company_name': company_name,
            }
            if extra_email_context:
                email_context.update(extra_email_context)

            send_password_reset_email.delay(
                user_id=user.id,
                subject=subject,
                template=email_template_name,
                html_template=html_email_template_name,
                context=email_context,
                from_email=from_email,
            )

            log_password_reset_requested(
                user=authenticated_request_user,
                request=request,
                identifier=identifier,
                success=True,
                target_user=user,
            )
            emails_sent = True

        if not emails_sent:
            log_password_reset_requested(
                user=authenticated_request_user,
                request=request,
                identifier=identifier,
                success=False,
                target_user=None,
            )


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