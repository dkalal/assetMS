#!/usr/bin/env python
import os
import sys
import django
import qrcode
from io import BytesIO
import base64

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from assets.models import Asset

def generate_test_qr_codes():
    """Generate test QR codes for existing assets"""
    
    # Get first few assets
    assets = Asset.objects.all()[:5]
    
    if not assets:
        print("No assets found. Create some assets first.")
        return
    
    print("Generating test QR codes...")
    
    for asset in assets:
        # Generate QR code with asset UUID
        qr_data = str(asset.uuid)
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save as file
        filename = f"test_qr_asset_{asset.id}_{asset.uuid}.png"
        img.save(filename)
        
        print(f"Generated QR code for Asset #{asset.id}: {filename}")
        print(f"  UUID: {asset.uuid}")
        print(f"  Category: {asset.category.name}")
        print(f"  QR Data: {qr_data}")
        print()

def generate_simple_test_qr():
    """Generate simple test QR codes with different formats"""
    
    test_codes = [
        "12345",  # Simple numeric
        "ASSET001",  # Alphanumeric
        "test-asset-uuid-123",  # Hyphenated
        f"http://127.0.0.1:8000/assets/1/",  # URL format
    ]
    
    print("Generating simple test QR codes...")
    
    for i, code in enumerate(test_codes, 1):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(code)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        filename = f"test_qr_simple_{i}.png"
        img.save(filename)
        
        print(f"Generated simple QR code {i}: {filename}")
        print(f"  Data: {code}")
        print()

if __name__ == "__main__":
    try:
        import qrcode
    except ImportError:
        print("QR code library not installed. Install with: pip install qrcode[pil]")
        sys.exit(1)
    
    print("QR Code Generator for Asset Management System")
    print("=" * 50)
    
    generate_test_qr_codes()
    generate_simple_test_qr()
    
    print("QR codes generated successfully!")
    print("Test these QR codes with your scanner to verify detection.")