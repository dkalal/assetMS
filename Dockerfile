# Use Python 3.12 slim base for production
FROM python:3.12-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by WeasyPrint and Python builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint runtime deps
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgobject-2.0-0 \
    libgdk-pixbuf-2.0-0 \
    libfreetype6 \
    libfontconfig1 \
    libharfbuzz0b \
    # Build deps
    libffi-dev \
    pkg-config \
    gcc \
    g++ \
    # Extra utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create logs and media dirs with correct permissions
RUN mkdir -p logs media /home/appuser/.cache/fontconfig && \
    chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Railway injects PORT dynamically → expose default for local dev
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
