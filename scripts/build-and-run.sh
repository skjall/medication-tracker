#!/bin/bash
set -e

echo "=== Medication Tracker Deployment ==="

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
mkdir -p $(pwd)/data $(pwd)/logs
chmod -R 777 $(pwd)/data $(pwd)/logs

# Run the container with proper configuration and host-mounted volumes
echo "Starting container..."
docker run -d \
  --name medication-tracker \
  -p 8087:8087 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -e SECRET_KEY=your_secure_secret_key \
  medication-tracker

# Check if container is running
echo "Container status:"
if docker ps | grep -q medication-tracker; then
  echo "Container successfully started!"
  echo "Access the application at: http://localhost:8087"
  docker ps | grep medication-tracker
else
  echo "Container failed to start! Checking logs:"
  docker logs medication-tracker
  exit 1
fi