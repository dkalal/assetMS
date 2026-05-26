#!/bin/bash

# Production deployment script for AssetMS
# Usage: bash deploy.sh

set -e

echo "🚀 Starting AssetMS production deployment..."

# 1. Load environment variables
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production not found!"
    echo "Please copy .env.production and update with your production values."
    exit 1
fi

echo "✅ Environment variables loaded from .env.production"

# 2. Pull latest images
echo "📦 Pulling latest images..."
docker compose -f docker-compose.production.yml pull

# 3. Build/rebuild application image
echo "🔨 Building application image..."
docker compose -f docker-compose.production.yml build --no-cache

# 4. Run migrations in a temporary container
echo "🗄️  Running database migrations..."
docker compose -f docker-compose.production.yml run --rm web python manage.py migrate --noinput

# 5. Collect static files
echo "📦 Collecting static files..."
docker compose -f docker-compose.production.yml run --rm web python manage.py collectstatic --noinput --clear

# 6. Create superuser if not exists (optional)
# Uncomment and set DJANGO_SUPERUSER_* env vars if you want auto-creation
# echo "👤 Creating superuser..."
# docker compose -f docker-compose.production.yml run --rm web python manage.py createsuperuser --noinput

# 7. Start all services
echo "▶️  Starting services..."
docker compose -f docker-compose.production.yml up -d

# 8. Wait for services to be healthy
echo "⏳ Waiting for services to become healthy..."
sleep 5

# 9. Check service status
echo "🔍 Checking service status..."
docker compose -f docker-compose.production.yml ps

# 10. Display access information
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Access Information:"
echo "  Web UI: https://your-domain.com"
echo "  Admin: https://your-domain.com/admin"
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose.production.yml ps --format "table {{.Service}}\t{{.Status}}"

echo ""
echo "📝 Useful Commands:"
echo "  View logs:        docker compose -f docker-compose.production.yml logs -f"
echo "  View web logs:    docker compose -f docker-compose.production.yml logs -f web"
echo "  Shell access:     docker compose -f docker-compose.production.yml exec web bash"
echo "  Database shell:   docker compose -f docker-compose.production.yml exec db psql -U \$DB_USER -d \$DB_NAME"
echo "  Stop services:    docker compose -f docker-compose.production.yml down"
echo "  Full cleanup:     docker compose -f docker-compose.production.yml down -v"
