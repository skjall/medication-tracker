FROM python:3.13-slim@sha256:8f3aba466a471c0ab903dbd7cb979abd4bda370b04789d25440cc90372b50e04

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs \
  && chmod -R 755 /app/data /app/logs

# Create volumes for data and logs persistence
VOLUME /app/data
VOLUME /app/logs

# Expose the port the app runs on
EXPOSE 8087

# Copy the application code
COPY app/ .

# Command to run the application
CMD ["gunicorn","--bind", "0.0.0.0:8087","--workers", "4","--threads", "2","--timeout", "120","main:create_app()"]