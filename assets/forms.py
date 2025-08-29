from django import forms
from .models import Asset, AssetCategory, AssetCategoryField
from django.core.exceptions import ValidationError
from django.apps import apps
import json

class AssetForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        # Get category from POST, GET, or initial
        category_id = None
        if 'data' in kwargs and kwargs['data']:
            category_id = kwargs['data'].get('category')
        if not category_id and 'initial' in kwargs and kwargs['initial']:
            category_id = kwargs['initial'].get('category')
        super().__init__(*args, **kwargs)
        # Add dynamic fields from category
        self.dynamic_field_names = []
        AssetCategoryModel = apps.get_model('assets', 'AssetCategory')
        AssetCategoryFieldModel = apps.get_model('assets', 'AssetCategoryField')
        if category_id:
            try:
                category = AssetCategoryModel.objects.get(pk=category_id)
                for f in AssetCategoryFieldModel.objects.filter(category=category):
                    fname = f"dyn_{f.key}"
                    # Force all dynamic fields to be optional
                    self.fields[fname] = self._make_field({'key': f.key, 'label': f.label, 'type': f.type, 'required': False})
                    self.dynamic_field_names.append(fname)
            except AssetCategoryModel.DoesNotExist:
                pass

    def _make_field(self, field):
        label = field['label']
        required = False  # Force all dynamic fields to be optional
        if field['type'] == 'text':
            return forms.CharField(label=label, required=required, widget=forms.TextInput(attrs={'class': 'form-control'}))
        elif field['type'] == 'number':
            return forms.DecimalField(label=label, required=required, widget=forms.NumberInput(attrs={'class': 'form-control'}))
        elif field['type'] == 'date':
            return forms.DateField(label=label, required=required, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
        else:
            return forms.CharField(label=label, required=required, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Asset
        fields = [
            'category', 'status', 'assigned_to', 'description',
            'purchase_value', 'purchase_date', 'depreciation_method', 'useful_life_years',
            'qr_code', 'images', 'documents'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
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
        # Depreciation validation
        purchase_value = cleaned_data.get('purchase_value')
        purchase_date = cleaned_data.get('purchase_date')
        useful_life_years = cleaned_data.get('useful_life_years')
        depreciation_method = cleaned_data.get('depreciation_method')
        if purchase_value or purchase_date or useful_life_years:
            if not (purchase_value and purchase_date and useful_life_years and depreciation_method):
                raise forms.ValidationError('All depreciation fields (value, date, method, useful life) are required for depreciable assets.')
            if purchase_value <= 0:
                raise forms.ValidationError('Purchase value must be positive.')
            if useful_life_years <= 0:
                raise forms.ValidationError('Useful life must be positive.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.dynamic_data = self.cleaned_data.get('dynamic_data', {})
        if commit:
            instance.save()
            self.save_m2m()
        return instance 