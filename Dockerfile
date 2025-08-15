# Multi-stage build for smaller image size
FROM python:3.13-slim@sha256:f2fdaec50160418e0c2867ba3e254755edd067171725886d5d303fd7057bbf81 AS builder

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

# Translation stage - extracts strings and manages translations
FROM python:3.13-slim@sha256:f2fdaec50160418e0c2867ba3e254755edd067171725886d5d303fd7057bbf81 AS translator

WORKDIR /app

# Install translation tools and Crowdin CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  unzip \
  openjdk-25-jre-headless \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --no-cache-dir babel flask-babel \
  && curl -L https://github.com/crowdin/crowdin-cli/releases/download/4.9.1/crowdin-cli.zip -o crowdin-cli.zip \
  && unzip crowdin-cli.zip -d /opt/ \
  && rm crowdin-cli.zip \
  && CROWDIN_DIR=$(ls -d /opt/*/ | head -n1) \
  && chmod +x ${CROWDIN_DIR}crowdin \
  && ln -s ${CROWDIN_DIR}crowdin-cli.jar /opt/crowdin-cli.jar \
  && ln -s ${CROWDIN_DIR}crowdin /opt/crowdin

# Add Crowdin CLI to PATH
ENV PATH="/opt:${PATH}"

# Copy application code for string extraction
COPY app/ ./app/
COPY babel.cfg ./
COPY translations/ ./translations/
COPY crowdin.yml ./

# Set Crowdin API token and project ID as build arguments (pass during build)
ARG CROWDIN_API_TOKEN
ENV CROWDIN_API_TOKEN=${CROWDIN_API_TOKEN}
ARG CROWDIN_PROJECT_ID
ENV CROWDIN_PROJECT_ID=${CROWDIN_PROJECT_ID}

# Cache busting argument - changes on each build to force refresh
ARG CACHE_BUST=1
RUN echo "Cache bust: ${CACHE_BUST}"

# Extract strings from source code
RUN cd app && pybabel extract -F ../babel.cfg -k _l -k _ -k _n:1,2 -o ../translations/messages.pot . \
  --add-comments="TRANSLATORS:" --sort-by-file && cd ..

# Upload source files and download translations from Crowdin
RUN if [ -n "${CROWDIN_API_TOKEN}" ] && [ -n "${CROWDIN_PROJECT_ID}" ]; then \
  crowdin upload sources --no-progress && \
  crowdin download --no-progress ; \
  else \
  echo "Crowdin sync skipped - missing credentials" ; \
  fi

# Update existing translations with new strings
RUN pybabel update -i translations/messages.pot -d translations || true

# Compile all translations
RUN pybabel compile -d translations

# Final stage with minimal dependencies
FROM python:3.13-slim@sha256:f2fdaec50160418e0c2867ba3e254755edd067171725886d5d303fd7057bbf81

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
COPY app/ ./

# Copy migration files
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Copy babel config
COPY babel.cfg ./

# Copy compiled translations from translator stage
COPY --from=translator /app/translations/ ./translations/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV LOG_LEVEL=INFO

# Make VERSION available in the final layer
ARG VERSION
ENV VERSION=${VERSION}

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

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