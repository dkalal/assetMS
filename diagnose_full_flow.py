"""
COMPLETE DIAGNOSTIC: Trace ENTIRE flow from DB to rendered HTML
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from assets.models import Asset, AssetCategory
from assets.forms import AssetForm
from django.test import RequestFactory
from django.contrib.auth import get_user_model

print("="*80)
print("🔍 COMPLETE FLOW DIAGNOSTIC: DB → Form → Template → JavaScript")
print("="*80)

# Find an asset with dynamic_data
asset = Asset.objects.exclude(dynamic_data={}).exclude(dynamic_data__isnull=True).first()

if not asset:
    print("❌ No assets with dynamic_data found!")
    exit(1)

print(f"\n📋 ASSET FOUND:")
print(f"   UUID: {asset.uuid}")
print(f"   Category: {asset.category.name if asset.category else 'None'}")
print(f"   Dynamic Data: {asset.dynamic_data}")
print(f"   Keys: {list(asset.dynamic_data.keys()) if isinstance(asset.dynamic_data, dict) else 'Not a dict'}")

# Check if category has fields defined
if asset.category:
    from assets.models import AssetCategoryField
    fields = AssetCategoryField.objects.filter(category=asset.category)
    print(f"\n🔧 CATEGORY FIELDS DEFINED:")
    for f in fields:
        print(f"   - {f.key} ({f.label}) - type: {f.type}, required: {f.required}")

# Simulate form creation
User = get_user_model()
user = User.objects.filter(is_active=True).first()

factory = RequestFactory()
request = factory.get(f'/assets/{asset.pk}/edit/')
request.user = user
request.company = asset.company
request.branch = asset.branch

print(f"\n📝 CREATING FORM...")
form = AssetForm(instance=asset, request=request)

print(f"\n✅ FORM CREATED:")
print(f"   Total fields: {len(form.fields)}")
print(f"   Dynamic field names tracked: {form.dynamic_field_names}")

print(f"\n🔍 CHECKING form.initial:")
for field_name in form.dynamic_field_names:
    initial_value = form.initial.get(field_name, '<NOT SET>')
    print(f"   {field_name}: {initial_value}")

print(f"\n🔍 CHECKING form.fields (actual field objects):")
for field_name in form.dynamic_field_names[:5]:  # First 5 to avoid spam
    if field_name in form.fields:
        field = form.fields[field_name]
        initial = field.initial if hasattr(field, 'initial') else 'N/A'
        print(f"   {field_name}: exists={True}, initial={initial}")

print(f"\n🔍 CHECKING TEMPLATE DATA:")
# Simulate what the template receives
context_dynamic_data = asset.dynamic_data if hasattr(asset, 'dynamic_data') else {}
print(f"   object.dynamic_data would be: {context_dynamic_data}")

print("\n" + "="*80)
print("💡 ANALYSIS:")
print("="*80)

# Check if data is in dynamic_data
if 'serial_number' in asset.dynamic_data:
    print(f"✅ DB has serial_number: {asset.dynamic_data['serial_number']}")
else:
    print(f"❌ DB missing serial_number key!")

# Check if form.initial has it
if 'dyn_serial_number' in form.initial:
    print(f"✅ form.initial has dyn_serial_number: {form.initial['dyn_serial_number']}")
else:
    print(f"❌ form.initial missing dyn_serial_number!")
    
    # Debug why
    if 'dyn_serial_number' not in form.fields:
        print(f"   ⚠️ Field 'dyn_serial_number' was NOT created in form.fields")
        print(f"   ⚠️ This means category doesn't have 'serial_number' field defined")
    else:
        print(f"   ✅ Field 'dyn_serial_number' EXISTS in form.fields")
        print(f"   ❌ But it wasn't populated in form.initial")
        print(f"   🐛 BUG: Pre-population logic failed!")

print("\n" + "="*80)
print("🎯 ROOT CAUSE:")
print("="*80)

# The real issue
if asset.category:
    cat_field = AssetCategoryField.objects.filter(
        category=asset.category,
        key='serial_number'
    ).first()
    
    if not cat_field:
        print(f"""
❌ CATEGORY '{asset.category.name}' DOES NOT HAVE 'serial_number' FIELD DEFINED!

The asset has serial_number in dynamic_data: {asset.dynamic_data.get('serial_number', 'N/A')}
But the category doesn't have a field definition for it!

SOLUTION:
1. Go to /categories/
2. Edit category '{asset.category.name}'
3. Add dynamic field with key='serial_number'
4. Then the form will create dyn_serial_number field
5. Then pre-population will work

This is a DATA CONSISTENCY ISSUE, not a code bug!
""")
    else:
        print(f"""
✅ Category HAS serial_number field defined
   Field key: {cat_field.key}
   Field type: {cat_field.type}
   Required: {cat_field.required}
   
If form.initial doesn't have it, there's a BUG in the pre-population code!
""")
