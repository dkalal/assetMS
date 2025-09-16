# Use Python 3.12 slim as base image for smaller footprint
FROM python:3.12-slim

# Set environment variables for Python optimization and unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies required by WeasyPrint and build tools
# WeasyPrint needs: cairo, pango, gobject/glib, gdk-pixbuf, freetype, fontconfig, harfbuzz
# Also install build dependencies for Python packages compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint runtime dependencies
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgobject-2.0-0 \
    libgdk-pixbuf-2.0-0 \
    libfreetype6 \
    libfontconfig1 \
    libharfbuzz0b \
    # Build dependencies for Python packages
    libffi-dev \
    pkg-config \
    gcc \
    g++ \
    # Additional utilities
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies without cache to reduce image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create logs, media, and fontconfig cache directories, set proper permissions
RUN mkdir -p logs media /home/appuser/.cache/fontconfig && \
    chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Copy and make entrypoint script executable
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port (Railway will set PORT environment variable)
EXPOSE 8000

# Health check to ensure the application is running
# Note: Ensure your Django project has a /health/ endpoint that returns 200 OK
# If not, add a simple health view in your urls.py and views.py
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health/ || exit 1

# Use entrypoint script to handle migrations, static files, and start gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]