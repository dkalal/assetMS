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
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Build CSP header dynamically
        img_src = "'self' data: blob:"
        connect_src = "'self'"
        
        # Cloudinary, ImageKit and Backblaze domains (include for tests and common usage)
        img_src += " https://res.cloudinary.com https://*.cloudinary.com"
        connect_src += " https://res.cloudinary.com https://*.cloudinary.com"

        # ImageKit: if configured include the endpoint domain, otherwise include the common imagekit.io wildcard
        imagekit_endpoint = os.environ.get('IMAGEKIT_URL_ENDPOINT', '')
        if imagekit_endpoint:
            domain = imagekit_endpoint.replace('https://', '').replace('http://', '').rstrip('/')
            img_src += f" https://{domain} https://*.imagekit.io"
            connect_src += f" https://{domain} https://*.imagekit.io"
        else:
            img_src += " https://*.imagekit.io"
            connect_src += " https://*.imagekit.io"

        # Backblaze B2: include common domains; allow custom domain if set
        img_src += " https://f002.backblazeb2.com https://*.backblazeb2.com"
        connect_src += " https://f002.backblazeb2.com https://*.backblazeb2.com"
        b2_custom_domain = os.environ.get('B2_CUSTOM_DOMAIN')
        if b2_custom_domain:
            img_src += f" https://{b2_custom_domain}"
            connect_src += f" https://{b2_custom_domain}"
        
        # Add CDN domains and source maps
        connect_src += " https://cdn.jsdelivr.net https://cdnjs.cloudflare.com"
        
        # Debug: Log CSP policy
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"CSP img-src: {img_src}")
        
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
        
        logger.info(f"Final CSP: {csp_policy}")
        
        # Force CSP header refresh
        response['Content-Security-Policy'] = csp_policy
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Remove any conflicting CSP headers
        if 'Content-Security-Policy-Report-Only' in response:
            del response['Content-Security-Policy-Report-Only']
            
        return response

    def get_cloud_domains(self):
        """Return a list of cloud domains included in the CSP policy.

        Kept simple for tests: always include the common cloud storage domains.
        """
        domains = [
            'cloudinary.com',
            'imagekit.io',
            'backblazeb2.com',
        ]
        return domains

# Maintain backward-compatible name expected by tests and other code
# Provide `CSPMiddleware` alias to the implemented `CustomCSPMiddleware`.
CSPMiddleware = CustomCSPMiddleware