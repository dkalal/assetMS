from datetime import date

from django import forms
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import QueryDict

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
        # Get category from POST, GET, initial, or instance (for edit forms)
        category_id = None
        data = kwargs.get('data')
        # Support both keyword and positional data (e.g., AssetForm(request.POST, request=request))
        if data is None and args:
            first_arg = args[0]
            if isinstance(first_arg, (dict, QueryDict)):
                data = first_arg
        if data:
            category_id = data.get('category')
        if not category_id and 'initial' in kwargs and kwargs['initial']:
            category_id = kwargs['initial'].get('category')
        # CRITICAL FIX: For edit forms, get category from instance
        if not category_id and 'instance' in kwargs and kwargs['instance']:
            category_id = getattr(kwargs['instance'], 'category_id', None)
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
        
        # WORLD-CLASS FIX: Set default status for new assets
        # This prevents "status is required" error when creating new assets
        if 'status' in self.fields and not self.instance.pk:
            self.fields['status'].initial = Asset.STATUS_ACTIVE
            self.initial['status'] = Asset.STATUS_ACTIVE

        # WORLD-CLASS: Make UI match backend rules for IN_MAINTENANCE
        # Manual status changes to "in_maintenance" are blocked in clean(),
        # so hide that choice in the dropdown for normal edits and treat it
        # as a system-controlled status set by Maintenance Center / services.
        if 'status' in self.fields and self.instance and self.instance.pk:
            status_field = self.fields['status']
            current_status = getattr(self.instance, 'status', None)

            if current_status == Asset.STATUS_IN_MAINTENANCE:
                # While an asset is under maintenance, prevent manual status
                # edits from this form. Maintenance workflows will return it
                # to ACTIVE.
                status_field.disabled = True
            else:
                # Hide the IN_MAINTENANCE option from the manual dropdown to
                # avoid confusing users, since backend validation forbids it.
                filtered_choices = [
                    (value, label)
                    for (value, label) in status_field.choices
                    if value != Asset.STATUS_IN_MAINTENANCE
                ]
                status_field.choices = filtered_choices

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
                # WORLD-CLASS: Branch not required for existing assets (status updates)
                self.fields['branch'].required = not (self.instance and self.instance.pk)
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
        
        # WORLD-CLASS FIX: Detect if this is a status-only update
        # When editing an existing asset and only changing status, skip dynamic field requirements
        is_status_only_update = False
        if self.instance and self.instance.pk and 'data' in kwargs and kwargs['data']:
            # Check if status is being changed
            new_status = kwargs['data'].get('status')
            old_status = self.instance.status
            
            if new_status and new_status != old_status:
                # This is a status change - check if other fields are unchanged
                # If category is not in POST data or matches existing, it's status-only
                posted_category = kwargs['data'].get('category')
                if not posted_category or str(posted_category) == str(self.instance.category_id):
                    is_status_only_update = True
        
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
                        # WORLD-CLASS: Make dynamic fields NOT required during status-only updates
                        'required': getattr(f, 'required', False) and not is_status_only_update,
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
        
        # ============================================================
        # WORLD-CLASS FIX: Pre-populate dynamic fields from instance
        # ============================================================
        # For EDIT forms, pre-populate dynamic fields from asset.dynamic_data
        # This ensures users see all their existing data without re-entering
        if self.instance and self.instance.pk and hasattr(self.instance, 'dynamic_data'):
            try:
                dynamic_data = self.instance.dynamic_data if isinstance(self.instance.dynamic_data, dict) else {}
                
                if dynamic_data:
                    populated_count = 0
                    
                    for key, value in dynamic_data.items():
                        field_name = f'dyn_{key}'
                        
                        # Only populate if field exists in form
                        # Allow None and empty string (user may have intentionally left it empty)
                        if field_name in self.fields:
                            # CRITICAL FIX: Set BOTH form.initial AND field.initial
                            # Django uses form.initial for form-level, but field.initial for widget rendering
                            # We need BOTH to ensure values appear in HTML
                            prepared_value = value if value is not None else ''
                            
                            # Set form-level initial (used by Django form logic)
                            self.initial[field_name] = prepared_value
                            
                            # Set field-level initial (used by widget rendering)
                            self.fields[field_name].initial = prepared_value
                            
                            populated_count += 1
                    
                    if populated_count > 0:
                        print(f"✅ FORM INIT: Pre-populated {populated_count} dynamic fields from instance")
                        
            except Exception as e:
                # Don't fail form initialization if dynamic data has issues
                print(f"⚠️ Warning: Could not pre-populate dynamic fields in form: {e}")

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
            ('', '-- Select Method --'),
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
            # Core fields
            'company', 'category', 'branch', 'status', 'assigned_to', 'description',
            # WORLD-CLASS DUPLICATE DETECTION FIELDS
            'serial_number', 'asset_tag', 'qr_string',
            # Maintenance fields
            'maintenance_enabled', 'maintenance_interval_days', 'maintenance_notes',
            # Media fields
            'qr_code', 'images', 'documents',
            # CRITICAL: Status-specific fields (dynamically shown/hidden by JavaScript)
            # These MUST be in fields list for Django to process them
            'status_change_reason',
            'maintenance_type',
            'disposal_method',
            'loss_date', 'loss_reason', 'loss_details', 'last_known_location', 'police_report_number',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'maintenance_notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'maintenance_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_maintenance_enabled'}),
            'maintenance_interval_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
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
        
        # WORLD-CLASS: Detect ACTUAL status change (not just form submission)
        # Only treat as status change if the value is DIFFERENT from current
        is_status_change = False
        if self.instance and self.instance.pk:
            old_status = self.instance.status
            new_status = cleaned_data.get('status')
            
            # CRITICAL FIX: Only flag as status change if values are ACTUALLY different
            # This prevents false positives when editing other fields
            if new_status and old_status and str(old_status) != str(new_status):
                is_status_change = True
                # Store for later use
                cleaned_data['_status_changed'] = True
                cleaned_data['_old_status'] = old_status
                cleaned_data['_new_status'] = new_status
                
                # WORLD-CLASS FIX: Prevent manual status change TO "in_maintenance"
                # This enforces proper workflow through Maintenance Center
                # Inspired by ServiceNow ITAM, IBM Maximo, SAP EAM best practices
                if old_status != Asset.STATUS_IN_MAINTENANCE and new_status == Asset.STATUS_IN_MAINTENANCE:
                    raise forms.ValidationError({
                        'status': [
                            'Cannot manually set status to "In Maintenance". '
                            'Please use the Maintenance Center (/maintenance/) to properly schedule and start maintenance. '
                            'This ensures complete tracking, audit trail, and proper workflow.'
                        ]
                    })
        
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
        
        # WORLD-CLASS DUPLICATE DETECTION VALIDATION
        # Layer 1: Hard constraint validation (prevents database errors)
        if not is_status_change:  # Skip during status-only changes
            from assets.services.duplicate_detection import DuplicateDetectionService
            
            # Get duplicate detection fields
            serial_number = cleaned_data.get('serial_number', '').strip() if cleaned_data.get('serial_number') else None
            asset_tag = cleaned_data.get('asset_tag', '').strip() if cleaned_data.get('asset_tag') else None
            qr_string = cleaned_data.get('qr_string', '').strip() if cleaned_data.get('qr_string') else None
            
            # Validate hard constraints (database-level uniqueness)
            exclude_id = self.instance.id if self.instance and self.instance.pk else None
            constraint_errors = DuplicateDetectionService.validate_hard_constraints(
                serial_number=serial_number,
                asset_tag=asset_tag,
                qr_string=qr_string,
                company=company,
                exclude_asset_id=exclude_id
            )
            
            # Add any constraint errors to form errors
            for field, error_list in constraint_errors.items():
                if field in cleaned_data:
                    if field not in self._errors:
                        self._errors[field] = self.error_class()
                    self._errors[field].extend(error_list)
            
            # Layer 2: Soft duplicate detection (warnings stored in form for display)
            if not constraint_errors and (serial_number or asset_tag):  # Only if hard constraints pass
                asset_data = {
                    'serial_number': serial_number,
                    'asset_tag': asset_tag,
                }
                
                # Add dynamic field data for similarity comparison
                dynamic_data = {}
                for field_name in self.dynamic_field_names:
                    if field_name in cleaned_data and cleaned_data[field_name]:
                        # Remove 'dyn_' prefix to get actual field key
                        actual_key = field_name[4:] if field_name.startswith('dyn_') else field_name
                        dynamic_data[actual_key] = cleaned_data[field_name]
                
                asset_data.update(dynamic_data)
                
                # Find potential duplicates
                potential_duplicates = DuplicateDetectionService.find_potential_duplicates(
                    asset_data=asset_data,
                    company=company,
                    category=category,
                    exclude_asset_id=exclude_id
                )
                
                # Store warnings in form for template display (non-blocking)
                if potential_duplicates:
                    cleaned_data['_duplicate_warnings'] = potential_duplicates
        
        # WORLD-CLASS: Status Change Validation
        # ONLY validate status-specific fields when status is ACTUALLY changing
        if is_status_change:
            old_status = cleaned_data.get('_old_status')
            new_status = cleaned_data.get('_new_status')
            
            # Double-check that status is actually different
            if old_status and new_status and str(old_status) != str(new_status):
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
                
                # Status change data already stored above
                pass
            else:
                # Status values are the same - NOT a status change
                # Clear the flag to prevent false validation
                is_status_change = False
                cleaned_data.pop('_status_changed', None)
                cleaned_data.pop('_old_status', None)
                cleaned_data.pop('_new_status', None)
        
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
        return cleaned_data

    def save(self, commit=True):
        """
        WORLD-CLASS SAVE: Properly persist dynamic field data to JSONField.
        
        Critical Fix:
        - Extract all dynamic field values from cleaned_data
        - Build dynamic_data dict with proper structure
        - Preserve existing data not in form
        - Handle file uploads and type conversions
        
        Architecture:
        1. Call parent save (creates instance, sets standard fields)
        2. Build dynamic_data dict from all dyn_* fields
        3. Merge with existing data (for partial updates)
        4. Validate at model level
        5. Save to database
        
        Multi-tenancy: All data scoped to company context
        Performance: Single database write with JSONField
        Security: Validated and sanitized data only
        """
        instance = super().save(commit=False)
        
        # ================================================================
        # CRITICAL FIX: Build dynamic_data from individual dynamic fields
        # ================================================================
        # Initialize with existing data (for edit forms) or empty dict
        if instance.pk and hasattr(instance, 'dynamic_data') and isinstance(instance.dynamic_data, dict):
            dynamic_data = instance.dynamic_data.copy()
        else:
            dynamic_data = {}
        
        # Extract all dynamic field values from cleaned_data
        for field_name in self.dynamic_field_names:
            if field_name in self.cleaned_data:
                value = self.cleaned_data[field_name]
                
                # Remove 'dyn_' prefix to get actual key for storage
                # e.g., 'dyn_serial_number' → 'serial_number'
                actual_key = field_name[4:] if field_name.startswith('dyn_') else field_name
                
                # Handle different field types for proper JSON serialization
                if value is None:
                    # Preserve None for optional fields
                    dynamic_data[actual_key] = None
                elif isinstance(value, date):
                    # Convert dates to ISO format strings for JSON
                    dynamic_data[actual_key] = value.isoformat()
                elif isinstance(value, bool):
                    # Preserve boolean type
                    dynamic_data[actual_key] = value
                elif isinstance(value, (int, float)):
                    # Preserve numeric types
                    dynamic_data[actual_key] = value
                elif hasattr(value, 'url'):
                    # File upload - store URL (CloudinaryField, ImageField, FileField)
                    dynamic_data[actual_key] = value.url
                else:
                    # String or other types - convert to string
                    dynamic_data[actual_key] = str(value) if value != '' else ''
        
        # Assign the built dynamic_data dict to instance
        instance.dynamic_data = dynamic_data
        
        # Log for debugging (remove in production)
        if dynamic_data:
            print(f"💾 SAVE: Persisting {len(dynamic_data)} dynamic fields to database")
            for key, val in dynamic_data.items():
                print(f"   - {key}: {val}")
        
        # CRITICAL FIX: Call full_clean() to trigger model-level validation
        # This ensures _validate_unique_fields() is called for duplicate detection
        if commit:
            try:
                instance.full_clean()  # Triggers Asset.clean() which calls _validate_unique_fields()
            except ValidationError as e:
                # Re-raise as form validation error for proper display
                raise forms.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
            
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