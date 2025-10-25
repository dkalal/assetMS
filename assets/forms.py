from datetime import date

from django import forms
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Asset, AssetCategory, AssetCategoryField, MaintenanceRecord
from users.fields import UserWithBranchChoiceField
import json

class AssetForm(forms.ModelForm):
    # Company as hidden field (set from request context)
    company = forms.ModelChoiceField(
        queryset=None,
        widget=forms.HiddenInput(),
        required=True
    )
    
    # Override assigned_to field with custom field that shows branch info
    assigned_to = UserWithBranchChoiceField(
        queryset=None,
        required=False,
        empty_label="-- Not Assigned --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.company = getattr(self.request, 'company', None) if self.request else None
        # Get category from POST, GET, or initial
        category_id = None
        if 'data' in kwargs and kwargs['data']:
            category_id = kwargs['data'].get('category')
        if not category_id and 'initial' in kwargs and kwargs['initial']:
            category_id = kwargs['initial'].get('category')
        super().__init__(*args, **kwargs)
        
        # Set company field (CRITICAL: Must be set before any validation)
        if 'company' in self.fields:
            from tenancy.models import Company
            if self.company:
                self.fields['company'].queryset = Company.objects.filter(id=self.company.id)
                self.fields['company'].initial = self.company
                # Pre-populate company in cleaned_data to ensure it's available
                if not self.is_bound:
                    self.initial['company'] = self.company
            else:
                self.fields['company'].queryset = Company.objects.none()
        
        # Limit category choices to company scope
        if 'category' in self.fields:
            category_qs = AssetCategory.objects.for_company(self.company) if self.company else AssetCategory.objects.none()
            self.fields['category'].queryset = category_qs
        
        # Scope branch choices by company and user permissions (MULTI-TENANCY)
        if 'branch' in self.fields:
            from tenancy.models import Branch
            from tenancy.policy_service import PolicyService
            
            if self.company:
                request_user = getattr(self.request, 'user', None)
                
                # Get accessible branches based on policy
                if request_user:
                    accessible_branch_ids = PolicyService.get_accessible_branches(request_user, self.company)
                    branch_qs = Branch.objects.filter(
                        id__in=accessible_branch_ids,
                        is_active=True
                    ).order_by('name')
                else:
                    branch_qs = Branch.objects.filter(
                        company=self.company,
                        is_active=True
                    ).order_by('name')
                
                self.fields['branch'].queryset = branch_qs
                self.fields['branch'].required = True  # Branch is mandatory
                self.fields['branch'].empty_label = "-- Select Branch --"
            else:
                self.fields['branch'].queryset = Branch.objects.none()
        # Scope assigned_to choices by company with branch information (ENHANCED)
        UserModel = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1]) if settings.AUTH_USER_MODEL else None
        assigned_field = self.fields.get('assigned_to')
        if assigned_field:
            if self.company:
                # Optimize query with prefetch_related to avoid N+1 queries
                assigned_qs = UserModel.objects.filter(
                    company=self.company,
                    is_active=True
                ).select_related('company').prefetch_related(
                    'user_branches__branch'  # Prefetch branches for display
                ).order_by('username') if UserModel else assigned_field.queryset
                
                request_user = getattr(self.request, 'user', None)
                request_branch = getattr(self.request, 'branch', None)
                
                # Filter by manager's branches if applicable
                if request_user and getattr(request_user, 'role', None) == 'manager':
                    from tenancy.models import UserBranch
                    branch_ids = list(
                        UserBranch.objects.filter(
                            user=request_user,
                            company=self.company,
                            branch__is_active=True,
                        ).values_list('branch_id', flat=True)
                    )
                    branch_ids = [*branch_ids]
                    if request_branch and request_branch.id not in branch_ids:
                        branch_ids.append(request_branch.id)
                    if branch_ids:
                        assigned_qs = assigned_qs.filter(user_branches__branch_id__in=branch_ids).distinct()
                    else:
                        assigned_qs = assigned_qs.none()
                
                assigned_field.queryset = assigned_qs
            else:
                assigned_field.queryset = assigned_field.queryset.none()
        # Ensure depreciation fields are not required at the form level
        for fname in ['purchase_value', 'purchase_date', 'depreciation_method', 'useful_life_years']:
            if fname in self.fields:
                self.fields[fname].required = False
        # Add dynamic fields from category (ENHANCED to support all wizard field types)
        self.dynamic_field_names = []
        AssetCategoryModel = apps.get_model('assets', 'AssetCategory')
        AssetCategoryFieldModel = apps.get_model('assets', 'AssetCategoryField')
        if category_id:
            try:
                category = AssetCategoryModel.objects.for_company(self.company).get(pk=category_id)
                for f in AssetCategoryFieldModel.objects.for_company(self.company).filter(category=category):
                    fname = f"dyn_{f.key}"
                    
                    # Build complete field metadata for enhanced rendering (DEFENSIVE)
                    field_data = {
                        'key': f.key,
                        'label': f.label,
                        'type': f.type,
                        'required': getattr(f, 'required', False),
                        'help_text': getattr(f, 'help_text', ''),
                    }
                    
                    # Add type-specific metadata (safely check attributes)
                    if f.type == 'select':
                        field_data['options'] = getattr(f, 'options', [])
                    
                    if f.type == 'number':
                        field_data['min_value'] = getattr(f, 'min_value', None)
                        field_data['max_value'] = getattr(f, 'max_value', None)
                    
                    if f.type in ['text', 'textarea']:
                        default_max = 255 if f.type == 'text' else 1000
                        field_data['max_length'] = getattr(f, 'max_length', default_max)
                    
                    self.fields[fname] = self._make_field(field_data)
                    self.dynamic_field_names.append(fname)
            except AssetCategoryModel.DoesNotExist:
                pass
        # Always add optional warranty fields to support enterprise warranty tracking
        if 'dyn_warranty_expiry' not in self.fields:
            self.fields['dyn_warranty_expiry'] = forms.DateField(
                label='Warranty Expiry (Optional)', required=False,
                widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
            )
            self.dynamic_field_names.append('dyn_warranty_expiry')
        if 'dyn_warranty_provider' not in self.fields:
            self.fields['dyn_warranty_provider'] = forms.CharField(
                label='Warranty Provider (Optional)', required=False,
                widget=forms.TextInput(attrs={'class': 'form-control'})
            )
            self.dynamic_field_names.append('dyn_warranty_provider')

    def _make_field(self, field):
        """
        Enhanced field creation supporting ALL wizard field types:
        text, number, date, select, textarea, file
        """
        label = field.get('label', 'Field')
        required = field.get('required', False)
        field_type = field.get('type', 'text')
        help_text = field.get('help_text', '')
        
        base_attrs = {'class': 'form-control'}
        if help_text:
            base_attrs['title'] = help_text
        
        # TEXT FIELD
        if field_type == 'text':
            max_length = field.get('max_length', 255)
            return forms.CharField(
                label=label,
                required=required,
                max_length=max_length,
                help_text=help_text,
                widget=forms.TextInput(attrs=base_attrs)
            )
        
        # TEXTAREA FIELD (NEW!)
        elif field_type == 'textarea':
            max_length = field.get('max_length', 1000)
            return forms.CharField(
                label=label,
                required=required,
                max_length=max_length,
                help_text=help_text,
                widget=forms.Textarea(attrs={**base_attrs, 'rows': 3})
            )
        
        # NUMBER FIELD
        elif field_type == 'number':
            min_val = field.get('min_value')
            max_val = field.get('max_value')
            return forms.DecimalField(
                label=label,
                required=required,
                min_value=min_val,
                max_value=max_val,
                help_text=help_text,
                widget=forms.NumberInput(attrs=base_attrs)
            )
        
        # DATE FIELD
        elif field_type == 'date':
            return forms.DateField(
                label=label,
                required=required,
                help_text=help_text,
                widget=forms.DateInput(attrs={**base_attrs, 'type': 'date'})
            )
        
        # SELECT FIELD (NEW!)
        elif field_type == 'select':
            options = field.get('options', [])
            if not options:
                options = []
            
            choices = [('', '-- Select --')]
            if isinstance(options, list):
                choices.extend([(opt, opt) for opt in options])
            elif isinstance(options, dict):
                choices.extend(options.items())
            
            return forms.ChoiceField(
                label=label,
                required=required,
                choices=choices,
                help_text=help_text,
                widget=forms.Select(attrs={'class': 'form-select'})
            )
        
        # FILE FIELD (NEW!)
        elif field_type == 'file':
            return forms.FileField(
                label=label,
                required=required,
                help_text=help_text or 'Max size: 5MB',
                widget=forms.FileInput(attrs={'class': 'form-control'})
            )
        
        # FALLBACK (for unknown types)
        else:
            return forms.CharField(
                label=label,
                required=required,
                help_text=help_text,
                widget=forms.TextInput(attrs=base_attrs)
            )

    # Status change conditional fields (shown/hidden via JavaScript)
    status_change_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Explain why you are changing the status (min 10 characters)'
        }),
        help_text="Required for status changes to: In Maintenance, Retired, Lost, Deleted"
    )
    
    # Retirement-specific fields
    disposal_method = forms.ChoiceField(
        required=False,
        choices=[
            ('', '-- Select Disposal Method --'),
            ('sell', 'Sell'),
            ('donate', 'Donate'),
            ('scrap', 'Scrap'),
            ('recycle', 'Recycle'),
            ('transfer', 'Transfer to another entity'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="How will this asset be disposed of?"
    )
    
    salvage_value = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        help_text="Estimated resale or salvage value"
    )
    
    # Loss-specific fields
    loss_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Date when asset was lost/stolen"
    )
    
    loss_reason = forms.ChoiceField(
        required=False,
        choices=[
            ('', '-- Select Loss Reason --'),
            ('lost', 'Lost/Misplaced'),
            ('stolen', 'Stolen'),
            ('damaged_beyond_repair', 'Damaged Beyond Repair'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    loss_details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Provide detailed description of circumstances (min 20 characters)'
        }),
        help_text="Detailed description of loss circumstances"
    )
    
    last_known_location = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Building A, Floor 3, Room 301'
        }),
        help_text="Last known location of asset"
    )
    
    police_report_number = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., PR-2025-001234'
        }),
        help_text="Police report number (required if stolen)"
    )
    
    # Maintenance-specific fields
    maintenance_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', '-- Select Maintenance Type --'),
            ('preventive', 'Preventive Maintenance'),
            ('corrective', 'Corrective Maintenance'),
            ('emergency', 'Emergency Maintenance'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Asset
        fields = [
            'company', 'category', 'branch', 'status', 'assigned_to', 'description',
            'purchase_value', 'purchase_date', 'depreciation_method', 'useful_life_years',
            'maintenance_enabled', 'maintenance_interval_days', 'maintenance_notes',
            'qr_code', 'images', 'documents'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'maintenance_notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_status',
                'data-original-status': ''  # Will be set via JavaScript
            }),
        }

    def clean_images(self):
        image = self.cleaned_data.get('images')
        if image:
            # Only validate if this is a new upload (InMemoryUploadedFile or TemporaryUploadedFile)
            from django.core.files.uploadedfile import UploadedFile
            if isinstance(image, UploadedFile):
                if image.size > 2*1024*1024:
                    raise ValidationError('Image file too large (max 2MB).')
                if not hasattr(image, 'content_type') or not image.content_type.startswith('image/'):
                    raise ValidationError('File is not an image.')
            # If it's an existing file (ImageFieldFile), skip content_type/size checks
        return image

    def clean_documents(self):
        doc = self.cleaned_data.get('documents')
        if doc:
            from django.core.files.uploadedfile import UploadedFile
            if isinstance(doc, UploadedFile):
                if doc.size > 5*1024*1024:
                    raise ValidationError('Document file too large (max 5MB).')
                allowed_types = [
                    'application/pdf',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                ]
                if not hasattr(doc, 'content_type') or doc.content_type not in allowed_types:
                    raise ValidationError('Only PDF or Word documents are allowed.')
            # If it's an existing file (FileFieldFile), skip content_type/size checks
        return doc

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get('company')
        category = cleaned_data.get('category')
        branch = cleaned_data.get('branch')
        assigned_to = cleaned_data.get('assigned_to')
        
        # WORLD-CLASS: Detect status change FIRST
        # If status is changing, skip validation of unrelated fields
        is_status_change = False
        if self.instance and self.instance.pk:
            old_status = self.instance.status
            new_status = cleaned_data.get('status')
            
            if old_status != new_status:
                is_status_change = True
                # Store for later use
                cleaned_data['_status_changed'] = True
                cleaned_data['_old_status'] = old_status
                cleaned_data['_new_status'] = new_status
        
        # CRITICAL: Ensure company is set (defensive check)
        if not company:
            raise forms.ValidationError('Company context is required. Please try again.')
        
        # WORLD-CLASS: Skip non-status validations during status changes
        # This prevents "branch required" errors when only changing status
        if is_status_change:
            # Only validate status-specific fields
            # Skip branch, category, and dynamic field validation
            # The service layer will handle the status transition
            
            # Preserve existing values for fields not being changed
            if not branch and self.instance:
                cleaned_data['branch'] = self.instance.branch
            if not category and self.instance:
                cleaned_data['category'] = self.instance.category
            
            # Skip to status change validation
            # (handled below in the status change section)
        else:
            # NORMAL ASSET UPDATE: Validate all fields
            
            # WORLD-CLASS FIX: Validate maintenance configuration
            # Enforce maintenance interval when maintenance is enabled
            maintenance_enabled = cleaned_data.get('maintenance_enabled', False)
            maintenance_interval = cleaned_data.get('maintenance_interval_days')
            
            if maintenance_enabled:
                if not maintenance_interval or maintenance_interval <= 0:
                    raise forms.ValidationError({
                        'maintenance_interval_days': [
                            'Maintenance interval must be a positive number (in days) when maintenance tracking is enabled. '
                            'Example: 90 for quarterly maintenance, 180 for semi-annual, 365 for annual.'
                        ]
                    })
            else:
                # If maintenance is disabled, clear interval to avoid validation issues
                cleaned_data['maintenance_interval_days'] = None
            
            # CRITICAL: Validate branch belongs to company and user has access
            if branch:
                # Verify branch belongs to company
                if branch.company_id != company.id:
                    raise forms.ValidationError('Selected branch does not belong to your company.')
                
                # Verify user has access to branch (policy-driven)
                request_user = getattr(self.request, 'user', None)
                if request_user and company:
                    from tenancy.policy_service import PolicyService
                    accessible_branch_ids = PolicyService.get_accessible_branches(request_user, company)
                    
                    if branch.id not in accessible_branch_ids:
                        raise forms.ValidationError(
                            'You do not have permission to create assets in this branch. '
                            'Please contact your administrator.'
                        )
            
            # CRITICAL: Validate branch-user consistency (prevent cross-branch assignments)
            if branch and assigned_to:
                request_user = getattr(self.request, 'user', None)
                
                # For non-admins, enforce strict branch matching
                if request_user and request_user.role != 'admin':
                    user_primary_branch = assigned_to.primary_branch
                    
                    if user_primary_branch and user_primary_branch.id != branch.id:
                        raise forms.ValidationError(
                            f'Cannot assign asset in "{branch.name}" to user "{assigned_to.username}" '
                            f'who belongs to "{user_primary_branch.name}". '
                            f'Please select a user from the same branch or leave unassigned.'
                        )
                
                # For admins, just log the cross-branch assignment (allow but track)
                elif request_user and request_user.role == 'admin':
                    user_primary_branch = assigned_to.primary_branch
                    
                    if user_primary_branch and user_primary_branch.id != branch.id:
                        # Log warning but allow
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(
                            f'Admin {request_user.username} assigned asset in branch {branch.id} ({branch.name}) '
                            f'to user {assigned_to.username} in branch {user_primary_branch.id} ({user_primary_branch.name})'
                        )
        
        # WORLD-CLASS: Status Change Validation
        # Validate status-specific fields when status is changing
        if is_status_change:
            old_status = self.instance.status
            new_status = cleaned_data.get('status')
            
            if old_status != new_status:
                # Status is changing - validate based on transition
                status_change_reason = cleaned_data.get('status_change_reason', '').strip()
                
                # IN_MAINTENANCE: Require reason and maintenance type
                if new_status == 'in_maintenance':
                    if not status_change_reason or len(status_change_reason) < 10:
                        raise forms.ValidationError({
                            'status_change_reason': 'Please provide a detailed reason for maintenance (min 10 characters).'
                        })
                    
                    maintenance_type = cleaned_data.get('maintenance_type')
                    if not maintenance_type:
                        raise forms.ValidationError({
                            'maintenance_type': 'Please select the type of maintenance.'
                        })
                
                # RETIRED: Require reason and disposal method
                elif new_status == 'retired':
                    if not status_change_reason or len(status_change_reason) < 10:
                        raise forms.ValidationError({
                            'status_change_reason': 'Please provide a detailed reason for retirement (min 10 characters).'
                        })
                    
                    disposal_method = cleaned_data.get('disposal_method')
                    if not disposal_method:
                        raise forms.ValidationError({
                            'disposal_method': 'Please select a disposal method.'
                        })
                
                # LOST: Require reason, details, and police report if stolen
                elif new_status == 'lost':
                    if not status_change_reason or len(status_change_reason) < 10:
                        raise forms.ValidationError({
                            'status_change_reason': 'Please provide a detailed reason for reporting loss (min 10 characters).'
                        })
                    
                    loss_reason = cleaned_data.get('loss_reason')
                    if not loss_reason:
                        raise forms.ValidationError({
                            'loss_reason': 'Please select the reason for loss.'
                        })
                    
                    loss_details = cleaned_data.get('loss_details', '').strip()
                    if not loss_details or len(loss_details) < 20:
                        raise forms.ValidationError({
                            'loss_details': 'Please provide detailed circumstances of the loss (min 20 characters).'
                        })
                    
                    # If stolen, require police report
                    if loss_reason == 'stolen':
                        police_report = cleaned_data.get('police_report_number', '').strip()
                        if not police_report:
                            raise forms.ValidationError({
                                'police_report_number': 'Police report number is required for stolen assets.'
                            })
                    
                    # Require loss date
                    loss_date = cleaned_data.get('loss_date')
                    if not loss_date:
                        raise forms.ValidationError({
                            'loss_date': 'Please specify when the asset was lost.'
                        })
                
                # DELETED: Require reason (admin-only, enforced in view)
                elif new_status == 'deleted':
                    if not status_change_reason or len(status_change_reason) < 10:
                        raise forms.ValidationError({
                            'status_change_reason': 'Please provide a detailed reason for deletion (min 10 characters).'
                        })
                
                # Store status change data for view processing
                cleaned_data['_status_changed'] = True
                cleaned_data['_old_status'] = old_status
                cleaned_data['_new_status'] = new_status
        
        # WORLD-CLASS: Skip dynamic field assembly during status changes
        # Dynamic fields are not relevant for status transitions
        if not is_status_change:
            # Assemble dynamic_data from dyn_* fields
            dynamic_data = {}
            for fname in self.dynamic_field_names:
                key = fname.replace('dyn_', '')
                value = self.cleaned_data.get(fname)
                # Convert date objects to ISO string for JSON serialization
                import datetime
                if isinstance(value, (datetime.date, datetime.datetime)):
                    value = value.isoformat()
                dynamic_data[key] = value
            # No required field validation for dynamic fields
            cleaned_data['dynamic_data'] = dynamic_data
        else:
            # Preserve existing dynamic data during status changes
            if self.instance and hasattr(self.instance, 'dynamic_data'):
                cleaned_data['dynamic_data'] = self.instance.dynamic_data or {}
        
        # Depreciation validation
        purchase_value = cleaned_data.get('purchase_value')
        purchase_date = cleaned_data.get('purchase_date')
        useful_life_years = cleaned_data.get('useful_life_years')
        depreciation_method = cleaned_data.get('depreciation_method')
        # If any depreciation values supplied, require complete set & validate
        if purchase_value or purchase_date or useful_life_years:
            if not (purchase_value and purchase_date and useful_life_years and depreciation_method):
                raise forms.ValidationError('All depreciation fields (value, date, method, useful life) are required for depreciable assets.')
            if purchase_value is not None and purchase_value <= 0:
                raise forms.ValidationError('Purchase value must be positive.')
            if useful_life_years is not None and useful_life_years <= 0:
                raise forms.ValidationError('Useful life must be positive.')
        else:
            # No depreciation provided: coerce safe defaults to satisfy model
            cleaned_data['depreciation_method'] = 'straight_line'
            cleaned_data['purchase_value'] = None
            cleaned_data['purchase_date'] = None
            cleaned_data['useful_life_years'] = None
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.dynamic_data = self.cleaned_data.get('dynamic_data', {})
        if commit:
            instance.save()
            self.save_m2m()
        return instance 


class MaintenanceScheduleForm(forms.Form):
    """Collect scheduling inputs for creating a maintenance record."""

    scheduled_for = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    supervisor = forms.ModelChoiceField(queryset=None, required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        self.asset = kwargs.pop('asset')
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        company = getattr(self.request, 'company', None)
        User = self.request.user.__class__
        supervisor_qs = User.objects.filter(company=company, is_active=True) if company else User.objects.none()
        self.fields['supervisor'].queryset = supervisor_qs

    def clean(self):
        cleaned_data = super().clean()
        company = getattr(self.request, 'company', None)
        if not company:
            raise forms.ValidationError('Company context is required.')
        if self.asset.company_id != company.id:
            raise forms.ValidationError('Asset does not belong to your company.')
        if not self.asset.maintenance_enabled:
            raise forms.ValidationError('Maintenance tracking is not enabled for this asset.')
        scheduled_for = cleaned_data.get('scheduled_for')
        if scheduled_for and scheduled_for < date.today():
            raise forms.ValidationError('Scheduled maintenance date cannot be in the past.')
        supervisor = cleaned_data.get('supervisor')
        if supervisor and getattr(supervisor, 'company_id', None) != company.id:
            raise forms.ValidationError('Supervisor must belong to your company.')
        return cleaned_data


class MaintenanceStartForm(forms.Form):
    """Confirm starting an existing maintenance record."""

    def __init__(self, *args, **kwargs):
        self.record: MaintenanceRecord = kwargs.pop('record')
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        company = getattr(self.request, 'company', None)
        if not company or self.record.company_id != company.id:
            raise forms.ValidationError('Maintenance record does not belong to your company.')
        if self.record.status not in {
            MaintenanceRecord.Status.SCHEDULED,
            MaintenanceRecord.Status.IN_PROGRESS,
        }:
            raise forms.ValidationError('Only scheduled maintenance can be started.')
        return cleaned_data


class MaintenanceCompletionForm(forms.Form):
    """Capture completion details for maintenance records."""

    outcome_notes = forms.CharField(
        required=True,
        min_length=10,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Summarize the work performed, findings, and follow-up actions (min 10 characters).',
            }
        ),
    )
    cost = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'placeholder': 'Leave blank if not applicable'}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.record: MaintenanceRecord = kwargs.pop('record')
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        company = getattr(self.request, 'company', None)
        if not company or self.record.company_id != company.id:
            raise forms.ValidationError('Maintenance record does not belong to your company.')
        if self.record.status not in {
            MaintenanceRecord.Status.SCHEDULED,
            MaintenanceRecord.Status.IN_PROGRESS,
        }:
            raise forms.ValidationError('Only scheduled or in-progress maintenance can be completed.')
        return cleaned_data


class MaintenanceCancellationForm(forms.Form):
    """Provide cancellation reason for maintenance records."""

    reason = forms.CharField(
        required=True,
        min_length=10,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Explain why this maintenance task is being cancelled (min 10 characters).',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.record: MaintenanceRecord = kwargs.pop('record')
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        company = getattr(self.request, 'company', None)
        if not company or self.record.company_id != company.id:
            raise forms.ValidationError('Maintenance record does not belong to your company.')
        if self.record.status == MaintenanceRecord.Status.COMPLETED:
            raise forms.ValidationError('Completed maintenance cannot be cancelled.')
        reason = cleaned_data.get('reason', '').strip()
        if len(reason) < 10:
            raise forms.ValidationError('Please provide a detailed cancellation reason (min 10 characters).')
        return cleaned_data