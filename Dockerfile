# syntax=docker/dockerfile:1.18@sha256:dabfc0969b935b2080555ace70ee69a5261af8a8f1b4df97b9e7fbcf6722eddf

###############################
# 1) Builder: Python dependencies
###############################
FROM python:3.13-slim@sha256:8ebd0ea12eea7d353861db137baa7be7bac116537f85e50bd84a52633e302265 AS builder

WORKDIR /app

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Tools for pip
RUN pip install --no-cache-dir pip-tools wheel

# Copy requirements
COPY requirements.txt /app/requirements.txt

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt


###############################
# 2) Frontend builder: Node.js for webpack bundling
###############################
FROM node:22-slim@sha256:0ae9e80c8c7e7a8fea5bc8e8762e4fd09a7a68c251abf8cf44ea0863efda2bc5 AS frontend-builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies (using npm install without lock file to avoid auth issues)
RUN npm install --no-save

# Copy webpack config and source files
COPY webpack.config.js ./
COPY app/static/ /app/app/static/

# Build frontend assets
RUN npm run build

###############################
# 3) Translator: Babel + Crowdin
###############################
FROM python:3.13-slim@sha256:8ebd0ea12eea7d353861db137baa7be7bac116537f85e50bd84a52633e302265 AS translator

# Install tools for Crowdin CLI and Babel
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  unzip \
  openjdk-21-jre-headless \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --no-cache-dir babel flask-babel \
  && curl -L https://github.com/crowdin/crowdin-cli/releases/download/4.11.0/crowdin-cli.zip -o /tmp/crowdin-cli.zip \
  && unzip /tmp/crowdin-cli.zip -d /opt/ \
  && rm /tmp/crowdin-cli.zip \
  && CROWDIN_DIR=$(ls -d /opt/*/ | head -n1) \
  && chmod +x ${CROWDIN_DIR}crowdin \
  && ln -s ${CROWDIN_DIR}crowdin-cli.jar /opt/crowdin-cli.jar \
  && ln -s ${CROWDIN_DIR}crowdin /opt/crowdin

ENV PATH="/opt:${PATH}"

# --- Cache bust (optional) ---
ARG CACHE_BUST=1
RUN echo "Cache bust: ${CACHE_BUST}"

# Copy sources with absolute paths
WORKDIR /
COPY app/ /app/
COPY babel.cfg /babel.cfg
COPY translations/ /app/translations/
COPY crowdin.yml /app/crowdin.yml

WORKDIR /app

# Crowdin credentials (ok for dev; use secrets in production)
ARG CROWDIN_API_TOKEN
ENV CROWDIN_API_TOKEN=${CROWDIN_API_TOKEN}
ARG CROWDIN_PROJECT_ID
ENV CROWDIN_PROJECT_ID=${CROWDIN_PROJECT_ID}

# 2.1: Extract strings
RUN pybabel extract \
  -F /babel.cfg \
  -k _l -k _ -k _n:1,2 \
  -o /app/translations/messages.pot \
  /app \
  --add-comments="TRANSLATORS:" --sort-by-file

# 2.1a: Normalize POT file to prevent false "new string" detections in Crowdin
# Remove POT-Creation-Date which changes on every build
RUN sed -i '/^"POT-Creation-Date:/d' /app/translations/messages.pot

# 2.2: Sync with Crowdin
RUN if [ -n "${CROWDIN_API_TOKEN}" ] && [ -n "${CROWDIN_PROJECT_ID}" ]; then \
  crowdin upload sources --no-progress --config /app/crowdin.yml --base-path /app && \
  crowdin download       --no-progress --config /app/crowdin.yml --base-path /app ; \
  else \
  echo "Crowdin sync skipped - missing credentials" ; \
  fi

# 2.3: Update and compile translations
RUN pybabel update -i /app/translations/messages.pot -d /app/translations || true
RUN pybabel compile -d /app/translations || echo "Translation compilation had errors but continuing"

# 2.4: Assert we actually have something
RUN ls -R /app/translations && \
  find /app/translations -type f \( -name "*.po" -o -name "*.mo" -o -name "messages.pot" \) | head -n 20

###############################
# 4) Runtime: minimal image
###############################
FROM python:3.13-slim@sha256:8ebd0ea12eea7d353861db137baa7be7bac116537f85e50bd84a52633e302265 AS runtime

# 4.1: Metadata
ARG VERSION=0.0.0
LABEL org.opencontainers.image.authors="Jan Großheim (medication-tracker@skjall.de)"
LABEL org.opencontainers.image.title="Medication Tracker"
LABEL org.opencontainers.image.description="A web application to track medications, inventory, and prepare for physician visits"
LABEL org.opencontainers.image.source="https://github.com/skjall/medication-tracker"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="${VERSION}"

WORKDIR /app

# 4.2: Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 4.3: Minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  wget \
  sqlite3 \
  && rm -rf /var/lib/apt/lists/*

# 4.4: Application code and config
COPY app/ /app/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini
COPY babel.cfg /app/babel.cfg

# 4.5: Compiled translations from translator stage
COPY --from=translator /app/translations/ /app/translations/

# 4.6: Built frontend assets from frontend-builder stage
COPY --from=frontend-builder /app/app/static/dist/ /app/static/dist/

# 4.7: Assert we have translations and assets
RUN ls -R /app/translations || (echo "translations missing in runtime image" && exit 1)
RUN ls /app/static/dist || (echo "frontend assets missing in runtime image" && exit 1)

# 4.8: Runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  FLASK_ENV=production \
  LOG_LEVEL=INFO \
  VERSION=${VERSION}

# 3.8: Entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 3.9: Volumes
VOLUME /app/data
VOLUME /app/logs

# 3.10: Port
EXPOSE 8087

# 3.11: Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8087/ || exit 1

# 3.12: Start command
CMD ["/app/entrypoint.sh"]
