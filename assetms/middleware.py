"""
Custom middleware for handling CSP headers with Backblaze B2 support
"""
import os

class CustomCSPMiddleware:
    """
    Custom CSP middleware that properly handles Backblaze B2 domains
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.use_b2 = os.environ.get('USE_B2', 'False').lower() == 'true'
        self.b2_custom_domain = os.environ.get('B2_CUSTOM_DOMAIN')
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Build CSP header
        img_src = "'self' data:"
        connect_src = "'self'"
        
        # ImageKit domains
        use_imagekit = os.environ.get('USE_IMAGEKIT', 'False').lower() == 'true'
        if use_imagekit:
            imagekit_endpoint = os.environ.get('IMAGEKIT_URL_ENDPOINT', '')
            if imagekit_endpoint:
                domain = imagekit_endpoint.replace('https://', '').replace('http://', '')
                img_src += f" https://{domain} https://*.imagekit.io"
                connect_src += f" https://{domain} https://*.imagekit.io"
        
        # Backblaze B2 domains
        if self.use_b2:
            img_src += " https://f002.backblazeb2.com https://*.backblazeb2.com"
            connect_src += " https://f002.backblazeb2.com https://*.backblazeb2.com"
            
            if self.b2_custom_domain:
                img_src += f" https://{self.b2_custom_domain}"
                connect_src += f" https://{self.b2_custom_domain}"
        
        # Add CDN domains
        connect_src += " https://cdn.jsdelivr.net https://cdnjs.cloudflare.com"
        
        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"img-src {img_src}; "
            f"font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"connect-src {connect_src}; "
            f"object-src 'none'; "
            f"base-uri 'self';"
        )
        
        response['Content-Security-Policy'] = csp_policy
        return response