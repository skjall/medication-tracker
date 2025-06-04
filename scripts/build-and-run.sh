#!/bin/bash
set -e

echo "=== Medication Tracker Deployment ==="

# Cleanup function to stop and remove container
cleanup() {
  echo ""
  echo "Shutting down container..."
  docker stop medication-tracker 2>/dev/null || true
  docker rm medication-tracker 2>/dev/null || true
  echo "Container stopped and removed."
  exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM EXIT

# Force remove the container if it exists
echo "Stopping and removing existing container..."
docker rm -f medication-tracker 2>/dev/null || true

# Check if version.txt exists
if [ ! -f version.txt ]; then
  echo "Error: version.txt not found!"
  echo "Creating default version.txt with 1.0.0"
  echo "1.0.0" > version.txt
fi

VERSION=$(cat version.txt)
echo "Building version: $VERSION"

# Build the image with proper load flag and version
echo "Building Docker image..."
docker build --load -t medication-tracker --build-arg VERSION="$VERSION" .

# Check image size
echo "Image size:"
docker images medication-tracker --format "{{.Size}}"

# Create the data and logs directories on the host with proper permissions
echo "Ensuring volume directories exist with proper permissions..."
mkdir -p "$(pwd)/data" "$(pwd)/logs"
chmod -R 777 "$(pwd)/data" "$(pwd)/logs"

# Run the container in foreground with proper configuration and host-mounted volumes
echo "Starting container in foreground..."
echo "Access the application at: http://localhost:8087"
echo "Press Ctrl+C to stop the container and exit"
echo "==============================================="

# Run container in foreground with --rm flag for auto-cleanup and signal handling
docker run --rm \
  --name medication-tracker \
  -p 8087:8087 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -e SECRET_KEY=your_secure_secret_key \
  medication-tracker