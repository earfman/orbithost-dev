# Dockerfile for OrbitHost
# Multi-stage build for optimized production image

# Stage 1: Backend build
FROM python:3.9-slim as backend-build

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Frontend build
FROM node:18-alpine as frontend-build
WORKDIR /app

# Install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Output is in the .next directory
RUN mkdir -p build
RUN cp -r .next build/
RUN cp -r public build/

# Stage 3: Production image
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including Playwright requirements and NGINX
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    nginx \
    git \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend from build stage
COPY --from=backend-build /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY backend/ /app/backend/

# Copy frontend build from frontend-build stage
COPY --from=frontend-build /app/build/.next /app/frontend/.next
COPY --from=frontend-build /app/build/public /app/frontend/public
COPY frontend/package.json /app/frontend/
# Copy configuration files individually to avoid errors
COPY frontend/package.json /app/frontend/
# Create a shell script to handle optional files
RUN echo '#!/bin/sh' > /tmp/copy_optional.sh && \
    echo 'if [ -f /tmp/frontend/next.config.js ]; then cp /tmp/frontend/next.config.js /app/frontend/; fi' >> /tmp/copy_optional.sh && \
    echo 'if [ -f /tmp/frontend/package-lock.json ]; then cp /tmp/frontend/package-lock.json /app/frontend/; fi' >> /tmp/copy_optional.sh && \
    chmod +x /tmp/copy_optional.sh
# Create temp directory and copy files there first
RUN mkdir -p /tmp/frontend
COPY frontend/ /tmp/frontend/
# Run the script to handle optional files
RUN /tmp/copy_optional.sh

# Install Playwright browsers
RUN pip install playwright && \
    python -m playwright install chromium && \
    python -m playwright install-deps chromium

# Create hosting directories
RUN mkdir -p /var/www/orbithost/sites \
    && mkdir -p /var/www/orbithost/templates \
    && mkdir -p /etc/nginx/sites-available \
    && mkdir -p /etc/nginx/sites-enabled

# Copy NGINX templates
COPY templates/nginx.conf /var/www/orbithost/templates/
COPY templates/nginx-site.conf /etc/nginx/sites-available/orbithost.conf

# Enable the NGINX site
RUN ln -sf /etc/nginx/sites-available/orbithost.conf /etc/nginx/sites-enabled/

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000

# Create necessary directories with proper permissions
RUN mkdir -p /var/log/nginx && \
    mkdir -p /var/www/orbithost/logs && \
    chown -R www-data:www-data /var/www/orbithost && \
    chmod -R 755 /var/www/orbithost

# Copy startup script
COPY scripts/start-services.sh /app/start-services.sh
RUN chmod +x /app/start-services.sh

# Expose ports
EXPOSE 8000 80 443

# Command to run both NGINX and the FastAPI application
CMD ["/app/start-services.sh"]
