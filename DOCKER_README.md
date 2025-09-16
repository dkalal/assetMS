# Docker Setup for AssetMS

This directory contains a production-ready Docker setup for the AssetMS Django application.

## Files Overview

- `Dockerfile` - Multi-stage production Docker image with WeasyPrint support
- `entrypoint.sh` - POSIX-compliant startup script handling migrations and static files
- `docker-compose.yml` - Local development setup with PostgreSQL
- `.dockerignore` - Excludes unnecessary files from Docker build context
- `health_check.py` - Simple health check endpoint for container monitoring

## Quick Start

### Local Development with Docker Compose

1. **Build and start services:**
   ```bash
   docker compose up --build
   ```

2. **Access the application:**
   - Web app: http://localhost:8000
   - PostgreSQL: localhost:5432

3. **Create a superuser (optional):**
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

### Production Docker Build

1. **Build the image:**
   ```bash
   docker build -t assetms:latest .
   ```

2. **Run with environment file:**
   ```bash
   docker run --env-file .env -p 8000:8000 assetms:latest
   ```

## Environment Variables

### Required for Production

```bash
# Database
DATABASE_URL=postgres://user:password@host:port/database

# Django
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Application
PORT=8000
```

### Optional Environment Variables

```bash
# Superuser creation (first run only)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=secure-password

# Gunicorn configuration
GUNICORN_WORKERS=3

# S3 Storage (optional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
USE_S3=True
```

## Platform Deployment

### Railway

1. Connect your repository to Railway
2. Set environment variables in Railway dashboard
3. Railway will automatically detect and build the Dockerfile

### Fly.io

1. Install Fly CLI and login
2. Initialize Fly app:
   ```bash
   fly launch
   ```
3. Set secrets:
   ```bash
   fly secrets set SECRET_KEY=your-secret-key
   fly secrets set DATABASE_URL=your-database-url
   ```
4. Deploy:
   ```bash
   fly deploy
   ```

### Generic Docker Platform

Any platform supporting Docker can use this setup:
1. Build: `docker build -t assetms .`
2. Push to registry: `docker push your-registry/assetms`
3. Deploy with proper environment variables

## Security Features

- **Non-root user**: Application runs as `appuser` (UID/GID 1000)
- **No secrets in image**: All sensitive data via environment variables
- **Minimal attack surface**: Slim base image with only required packages
- **Health checks**: Built-in endpoint for container orchestration
- **Signal handling**: Proper shutdown handling via exec in entrypoint

## Development Tips

### Live Code Reloading

Uncomment the volumes section in `docker-compose.yml`:
```yaml
volumes:
  - .:/app
  - /app/staticfiles
```

### Database Access

Connect to PostgreSQL directly:
```bash
docker compose exec db psql -U postgres -d assetms
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web
```

### Reset Database

```bash
docker compose down -v
docker compose up --build
```

## Troubleshooting

### WeasyPrint Issues
If PDF generation fails, ensure all system dependencies are installed. The Dockerfile includes all required libraries.

### Database Connection Issues
- Verify DATABASE_URL format: `postgres://user:password@host:port/database`
- Check if database server is accessible from container
- Ensure database exists before first run

### Static Files Not Loading
- Verify `STATIC_URL` and `STATIC_ROOT` in Django settings
- Check if `collectstatic` runs successfully in container logs
- For S3: verify AWS credentials and bucket permissions

### Health Check Failing
The health check endpoint is at `/health/`. If it fails:
- Check database connectivity
- Verify Django application is responding
- Review container logs for errors

## Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Set `DEBUG=False`
- [ ] Use external database (not SQLite)
- [ ] Configure static file serving (S3 or CDN)
- [ ] Set up proper logging
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerts
- [ ] Use HTTPS in production
- [ ] Regular security updates

## Image Size Optimization

The Dockerfile is optimized for size:
- Uses Python slim base image
- Removes apt caches after installation
- Uses `--no-cache-dir` for pip installs
- Multi-stage build pattern ready for further optimization

Current image size: ~200-300MB (depending on dependencies)