# Deployment Guide - v2.1.0

## 🚀 Quick Deployment Steps

### 1. Environment Configuration
```bash
# Required Cloudinary Variables
USE_CLOUDINARY=true
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Optional Fallback Storage
USE_IMAGEKIT=false
USE_B2=false
```

### 2. Server Deployment
```bash
# Pull latest changes
git pull origin main

# Install dependencies
pip install -r requirements.txt

# Apply migrations (if any)
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart server
python manage.py runserver
```

### 3. Post-Deployment Tasks
```bash
# Clear existing profile images (one-time)
python manage.py clear_profile_images

# Fix any existing Cloudinary URLs (one-time)
python manage.py fix_cloudinary_urls
```

## 🔧 Configuration Details

### Storage Priority
1. **Cloudinary** (Primary) - Cloud storage with CDN
2. **ImageKit** (Fallback) - Alternative cloud storage
3. **Backblaze B2** (Fallback) - Cost-effective cloud storage
4. **Local Storage** (Final fallback) - File system storage

### CSP Configuration
- **Dynamic CSP**: Automatically includes enabled storage domains
- **Cache Control**: Aggressive cache-busting for immediate updates
- **CDN Support**: Includes jsdelivr and cdnjs domains

### Scanner System
- **Primary**: Quagga library from CDN
- **Fallback**: Local Quagga implementation
- **Manual**: Always-available manual input

## 🛡️ Security Considerations

### Content Security Policy
- CSP handled by custom middleware
- Dynamic policy based on enabled storage
- Automatic cache invalidation

### File Upload Security
- File type validation
- Size limits enforced
- Secure cloud storage with versioning

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Test storage backends
python test_asset_storage.py

# Test CSP configuration
python test_csp_middleware.py

# Test Cloudinary integration
python test_cloudinary_proper.py
```

### Log Monitoring
- Storage backend failures
- CSP policy violations
- Upload errors
- Scanner initialization issues

## 🔄 Rollback Procedure

### Emergency Rollback
```bash
# Revert to previous commit
git revert HEAD

# Disable cloud storage
USE_CLOUDINARY=false
USE_IMAGEKIT=false
USE_B2=false

# Restart server
python manage.py runserver
```

### Gradual Rollback
1. Disable Cloudinary: `USE_CLOUDINARY=false`
2. Test with ImageKit fallback
3. If issues persist, disable all cloud storage
4. Use local storage as final fallback

## 📈 Performance Optimization

### Cloudinary Settings
- **Auto-optimization**: Enabled by default
- **Format conversion**: Automatic WebP/AVIF
- **Responsive images**: Dynamic sizing
- **CDN delivery**: Global edge locations

### Caching Strategy
- **Browser cache**: Disabled for CSP headers
- **CDN cache**: Leveraged for static assets
- **Version parameters**: Automatic cache-busting

## 🐛 Troubleshooting

### Common Issues

**Images not loading:**
1. Check Cloudinary credentials
2. Verify CSP includes cloud domains
3. Clear browser cache completely
4. Check network connectivity

**Scanner not working:**
1. Verify HTTPS or localhost
2. Check camera permissions
3. Use manual input as fallback
4. Check browser compatibility

**Upload failures:**
1. Check file size limits
2. Verify storage credentials
3. Test network connectivity
4. Check server logs

### Debug Commands
```bash
# Test storage configuration
python debug_profile_upload.py

# Test CSP headers
python test_final_csp.py

# Test image upload flow
python test_profile_upload_flow.py
```

## 📞 Support

### Log Locations
- **Django logs**: `logs/django.log` (development)
- **Console output**: Server terminal
- **Browser console**: F12 Developer Tools

### Key Metrics
- Upload success rate
- Storage failover frequency
- CSP violation count
- Scanner usage statistics

---

**Version**: v2.1.0  
**Last Updated**: 2025-01-22  
**Compatibility**: Django 5.2+, Python 3.8+