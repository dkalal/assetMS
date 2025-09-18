# ImageKit + Backblaze B2 Multi-Storage Setup

## Professional Multi-Storage Architecture

**Priority Order:**
1. **ImageKit** (Primary) - Image optimization, CDN, transformations
2. **Backblaze B2** (Fallback) - Cost-effective storage
3. **Local Storage** (Final fallback) - Development/emergency

## ImageKit Setup (Primary)

### 1. Create ImageKit Account
1. Go to [imagekit.io](https://imagekit.io)
2. Sign up for free account (20GB free)
3. Get your credentials from dashboard

### 2. Get ImageKit Credentials
- **URL Endpoint**: `https://ik.imagekit.io/your_imagekit_id`
- **Public Key**: Found in Developer Options
- **Private Key**: Found in Developer Options (keep secure)

### 3. Railway Environment Variables
```bash
# ImageKit (Primary)
USE_IMAGEKIT=True
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_imagekit_id
IMAGEKIT_PUBLIC_KEY=public_your_public_key
IMAGEKIT_PRIVATE_KEY=private_your_private_key

# Backblaze B2 (Fallback)
USE_B2=True
B2_APPLICATION_KEY_ID=your_b2_key_id
B2_APPLICATION_KEY=your_b2_key
B2_BUCKET_NAME=assetms-media
B2_BUCKET_REGION=us-east-005
```

## Benefits of This Architecture

### ImageKit Advantages:
- **Real-time image optimization**
- **Global CDN** (faster loading)
- **Image transformations** (resize, crop, format conversion)
- **WebP/AVIF support**
- **Automatic optimization**

### Fallback Strategy:
- **High availability** (99.9% uptime)
- **Cost optimization** (ImageKit free tier + B2 backup)
- **Zero downtime** (automatic failover)
- **Data redundancy**

## Cost Analysis
- **ImageKit**: Free 20GB + transformations
- **Backblaze B2**: $0.005/GB/month (backup only)
- **Total**: ~$0.05/month for 10GB

## Testing Checklist
1. Upload profile image → Should use ImageKit
2. Check image URL → Should contain `imagekit.io`
3. Disable ImageKit → Should fallback to B2
4. Check logs → Should show fallback messages
5. Image transformations → Should work automatically

## Production Deployment
```bash
git add .
git commit -m "Add ImageKit primary storage with B2 fallback"
git push origin main
```

Your images will now be:
- **Optimized automatically**
- **Served from global CDN**
- **Highly available** (multi-storage)
- **Cost-effective**