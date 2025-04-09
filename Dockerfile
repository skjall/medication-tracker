# Multi-stage build for smaller image size
FROM python:3.13-slim@sha256:21e39cf1815802d4c6f89a0d3a166cc67ce58f95b6d1639e68a394c99310d2e5 AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Install pip tools
RUN pip install --no-cache-dir pip-tools wheel

# Copy requirements file
COPY requirements.txt .

# Create and use virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Final stage with minimal dependencies
FROM python:3.13-slim@sha256:21e39cf1815802d4c6f89a0d3a166cc67ce58f95b6d1639e68a394c99310d2e5

# Define VERSION as a build argument
ARG VERSION=0.0.0

LABEL org.opencontainers.image.authors="Jan Großheim (medication-tracker@skjall.de)"
LABEL org.opencontainers.image.title="Medication Tracker"
LABEL org.opencontainers.image.description="A web application to track medications, inventory, and prepare for physician visits"
LABEL org.opencontainers.image.source="https://github.com/skjall/medication-tracker"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="${VERSION}"

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Make sure we use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Add minimal runtime dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
  wget \
  && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY app/ .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV LOG_LEVEL=INFO

# Make VERSION available in the final layer
ARG VERSION
ENV VERSION=${VERSION}

# Create entrypoint script to handle permissions - Fixed the syntax error with parentheses
RUN echo '#!/bin/bash\n\
  mkdir -p /app/data /app/logs\n\
  chmod -R 777 /app/data /app/logs\n\
  exec gunicorn --bind 0.0.0.0:8087 --workers 4 --threads 2 --timeout 120 "main:create_app()"\n'\
  > /app/entrypoint.sh && \
  chmod +x /app/entrypoint.sh

# Create volumes for data and logs persistence
VOLUME /app/data
VOLUME /app/logs

# Expose the port the app runs on
EXPOSE 8087

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8087/ || exit 1

# Command to run the application
CMD ["/app/entrypoint.sh"]