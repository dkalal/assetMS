# Backblaze B2 Storage Setup

## Why Backblaze B2?
- **Cost-effective**: $0.005/GB/month (cheaper than AWS S3)
- **No egress fees** for first 1GB daily
- **S3-compatible API**
- **Reliable and fast**

## Setup Steps

### 1. Create Backblaze B2 Account
1. Go to [backblaze.com](https://www.backblaze.com/b2/cloud-storage.html)
2. Sign up for B2 Cloud Storage
3. Create a new bucket for your media files

### 2. Get API Credentials
1. In B2 dashboard, go to "App Keys"
2. Create a new application key with these permissions:
   - `listBuckets`
   - `listFiles`
   - `readFiles`
   - `shareFiles`
   - `writeFiles`
   - `deleteFiles`
3. Note down:
   - **Application Key ID** (keyID)
   - **Application Key** (applicationKey)
   - **Bucket Name**

### 3. Configure Railway Environment Variables
Add these to your Railway project:

```bash
USE_B2=True
B2_APPLICATION_KEY_ID=your_key_id_here
B2_APPLICATION_KEY=your_application_key_here
B2_BUCKET_NAME=your-bucket-name
B2_BUCKET_REGION=us-west-002
```

### 4. Optional: Custom Domain (Recommended)
1. Set up a CNAME record: `media.yourdomain.com` → `f002.backblazeb2.com`
2. Add to Railway: `B2_CUSTOM_DOMAIN=media.yourdomain.com`

## Cost Estimation
- **Storage**: $0.005/GB/month
- **Downloads**: Free for first 1GB/day, then $0.01/GB
- **API calls**: $0.004 per 10,000 calls

**Example**: 10GB storage + 500MB daily downloads = ~$0.05/month

## Testing
1. Deploy to Railway with B2 enabled
2. Upload a profile image
3. Check if image displays correctly
4. Verify files appear in B2 dashboard

## Fallback
If B2 fails, set `USE_B2=False` to use local storage with WhiteNoise.