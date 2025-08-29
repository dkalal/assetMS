from django.contrib import admin, messages
from .models import AssetCategory, Asset, AssetCategoryField
from django.forms.models import BaseInlineFormSet
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from audit.utils import log_audit, ASSIGN_ACTION, MAINTENANCE_ACTION
from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
import json

class AssetCategoryFieldInline(admin.TabularInline):
    model = AssetCategoryField
    extra = 1
    min_num = 1
    fields = ('key', 'label', 'type', 'required')

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = [AssetCategoryFieldInline]
    exclude = ('dynamic_fields',)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        # Only update dynamic_fields JSON, do not auto-add any fields
        category = form.instance
        fields = category.fields.all()
        schema = {}
        for f in fields:
            schema[f.key] = {
                'type': f.type,
                'label': f.label,
                'required': f.required,
            }
        category.dynamic_fields = schema
        category.save()

class AssetResource(resources.ModelResource):
    class Meta:
        model = Asset
        fields = ('id', 'category__name', 'status', 'assigned_to__username', 'created_at', 'updated_at')
        export_order = fields

    def dehydrate(self, asset):
        # Flatten dynamic_data for export
        data = {}
        for k, v in asset.dynamic_data.items():
            data[f'dyn_{k}'] = v
        return data

class AssetAdminForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = '__all__'

    class Media:
        js = (
            'admin/js/asset_dynamic_fields.js',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing, get the category from the instance
        category = self.initial.get('category') or (self.instance.category.pk if self.instance and self.instance.category_id else None)
        if category:
            fields = AssetCategoryField.objects.filter(category_id=category)
            for f in fields:
                fname = f"dyn_{f.key}"
                self.fields[fname] = forms.CharField(
                    label=f.label,
                    required=f.required,
                    widget=forms.TextInput(attrs={'class': 'vTextField'})
                )
                # Prepopulate if editing
                if self.instance and self.instance.dynamic_data:
                    self.fields[fname].initial = self.instance.dynamic_data.get(f.key, '')

    def clean(self):
        cleaned_data = super().clean()
        # Collect dynamic fields
        dynamic_data = {}
        for name in self.fields:
            if name.startswith('dyn_'):
                key = name.replace('dyn_', '')
                dynamic_data[key] = cleaned_data.get(name)
        cleaned_data['dynamic_data'] = dynamic_data
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.dynamic_data = self.cleaned_data.get('dynamic_data', {})
        if commit:
            instance.save()
            self.save_m2m()
        return instance

@admin.register(Asset)
class AssetAdmin(ImportExportModelAdmin):
    form = AssetAdminForm
    resource_class = AssetResource
    list_display = ('pk', 'category', 'status', 'assigned_to', 'created_at', 'purchase_value', 'purchase_date', 'depreciation_method', 'useful_life_years')
    list_filter = ('status', 'category', 'depreciation_method')
    search_fields = ('description',)
    actions = ['export_as_pdf']
    fieldsets = (
        (None, {
            'fields': ('category', 'status', 'assigned_to', 'description', 'purchase_value', 'purchase_date', 'depreciation_method', 'useful_life_years', 'qr_code', 'images', 'documents', 'dynamic_data')
        }),
    )
    def export_as_pdf(self, request, queryset):
        # TODO: Implement PDF export with branding
        self.message_user(request, 'PDF export coming soon!')
    export_as_pdf.short_description = 'Export selected as PDF'

    def save_model(self, request, obj, form, change):
        old_obj = None
        if change:
            old_obj = Asset.objects.get(pk=obj.pk)
        super().save_model(request, obj, form, change)
        # Assignment logging
        if change and old_obj and old_obj.assigned_to != obj.assigned_to and obj.assigned_to:
            log_audit(request.user, ASSIGN_ACTION, obj, f'Asset assigned to {obj.assigned_to.username} via admin', related_user=obj.assigned_to)
        # Maintenance logging
        if change and old_obj and old_obj.status != obj.status and obj.status == 'maintenance':
            log_audit(request.user, MAINTENANCE_ACTION, obj, 'Asset marked as under maintenance via admin')

    def has_change_permission(self, request, obj=None):
        # Only admin and manager can change
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ('admin', 'manager')

@admin.register(AssetCategoryField)
class AssetCategoryFieldAdmin(admin.ModelAdmin):
    list_display = ('category', 'key', 'label', 'type', 'required')
    actions = ['delete_selected_fields']

    def delete_selected_fields(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Successfully deleted {count} field(s).", messages.SUCCESS)
    delete_selected_fields.short_description = "Delete selected fields (no related objects)"
