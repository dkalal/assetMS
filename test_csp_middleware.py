#!/usr/bin/env python
import os
import sys
import django
from django.test import RequestFactory

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
os.environ.setdefault('CLOUDINARY_CLOUD_NAME', 'ds0ekfqye')
django.setup()

from assetms.middleware import CustomCSPMiddleware

def test_csp_middleware():
    print("Testing CSP Middleware...")
    
    # Create a mock request and response
    factory = RequestFactory()
    request = factory.get('/')
    
    def mock_get_response(request):
        from django.http import HttpResponse
        return HttpResponse("Test")
    
    # Test middleware
    middleware = CustomCSPMiddleware(mock_get_response)
    response = middleware(request)
    
    csp_header = response.get('Content-Security-Policy', '')
    print(f"CSP Header: {csp_header}")
    
    # Check if Cloudinary domains are included
    if 'res.cloudinary.com' in csp_header:
        print("[OK] Cloudinary domains found in CSP")
    else:
        print("[ERROR] Cloudinary domains NOT found in CSP")
    
    if 'cdn.jsdelivr.net' in csp_header:
        print("[OK] CDN domains found in CSP")
    else:
        print("[ERROR] CDN domains NOT found in CSP")

if __name__ == "__main__":
    test_csp_middleware()