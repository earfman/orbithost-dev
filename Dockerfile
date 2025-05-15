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

# Stage 2: Frontend build - temporarily disabled until frontend is implemented
# Placeholder stage for now
FROM alpine:latest as frontend-build
WORKDIR /app
RUN mkdir -p build

# Stage 3: Production image
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
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
COPY --from=frontend-build /app/build /app/frontend/build

# Install Playwright browsers
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000

# Create a non-root user to run the application
RUN useradd -m orbituser
USER orbituser

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["python", "backend/main.py"]
