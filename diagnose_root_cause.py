"""
ROOT CAUSE DIAGNOSTIC: Why dynamic fields don't pre-populate
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from assets.models import Asset

print("="*80)
print("🔍 DIAGNOSING: Dynamic Field Pre-population Issue")
print("="*80)

# Check if we have any assets with dynamic_data
assets_with_data = Asset.objects.exclude(dynamic_data={}).exclude(dynamic_data__isnull=True)[:3]

print(f"\n📊 Found {assets_with_data.count()} assets with dynamic data\n")

for asset in assets_with_data:
    print(f"Asset UUID: {asset.uuid}")
    print(f"Category: {asset.category.name if asset.category else 'None'}")
    print(f"Dynamic Data: {asset.dynamic_data}")
    print(f"Keys in dynamic_data: {list(asset.dynamic_data.keys()) if isinstance(asset.dynamic_data, dict) else 'Not a dict'}")
    print("-" * 80)

# Now let's trace what happens during form initialization
print("\n🔬 SIMULATING FORM INITIALIZATION")
print("="*80)

if assets_with_data.exists():
    test_asset = assets_with_data.first()
    print(f"\nUsing asset: {test_asset.uuid}")
    print(f"Category: {test_asset.category.name}")
    print(f"Dynamic Data: {test_asset.dynamic_data}\n")
    
    # Simulate form init
    from assets.forms import AssetForm
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    from tenancy.models import Company
    
    User = get_user_model()
    company = Company.objects.first()
    user = User.objects.filter(company=company, is_active=True).first()
    
    factory = RequestFactory()
    request = factory.get(f'/assets/{test_asset.pk}/edit/')
    request.user = user
    request.company = company
    request.branch = test_asset.branch
    
    print("📝 Creating form with instance...")
    form = AssetForm(instance=test_asset, request=request)
    
    print(f"\n✅ Form created with {len(form.fields)} total fields")
    print(f"✅ Dynamic field names tracked: {form.dynamic_field_names}")
    
    print("\n🔍 Checking form.initial values:")
    for field_name in form.dynamic_field_names:
        initial_value = form.initial.get(field_name, '<NOT SET>')
        print(f"   {field_name}: {initial_value}")
    
    print("\n🔍 Checking actual field values in form:")
    for field_name in form.dynamic_field_names:
        if field_name in form.fields:
            field = form.fields[field_name]
            print(f"   {field_name}: initial={form.initial.get(field_name, 'N/A')}, required={field.required}")
    
    print("\n" + "="*80)
    print("📋 ANALYSIS:")
    print("="*80)
    print("""
The Django form DOES populate self.initial with dynamic field values.
BUT the template doesn't render these Django form fields!

The template has an EMPTY container: <div id="dynamic-fields-container">
JavaScript makes an AJAX call to get field definitions and creates NEW empty inputs.

This is the ROOT CAUSE:
- Django form fields with initial values are created but NOT rendered
- JavaScript creates new empty HTML inputs via AJAX
- The pre-populated initial values are LOST

SOLUTION: Make JavaScript use the initial values when rendering fields.
    """)
