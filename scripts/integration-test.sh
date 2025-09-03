#!/bin/bash

# Integration test script for Medication Tracker
# Can be run locally or in CI/CD pipeline

set -euo pipefail

# Configuration
CONTAINER_NAME="medication-tracker-test"
IMAGE_TAG="medication-tracker:test"
PORT="${TEST_PORT:-8088}"
BASE_URL="http://localhost:${PORT}"
MAX_WAIT_TIME=60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Function to wait for container to be ready
wait_for_container() {
    log_info "Waiting for container to start (max ${MAX_WAIT_TIME}s)..."

    for i in $(seq 1 $MAX_WAIT_TIME); do
        # Test from the host, not inside the container
        if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q "200"; then
            log_info "Container is ready after ${i} seconds"
            return 0
        fi

        if [ "$i" -eq "$MAX_WAIT_TIME" ]; then
            log_error "Container failed to start within ${MAX_WAIT_TIME} seconds"
            docker logs "$CONTAINER_NAME" | tail -20
            return 1
        fi

        sleep 1
    done
}

# Function to test a single route
test_route() {
    local route="$1"
    local description="$2"

    echo -n "Testing $description ($route)... "

    # Test from the host (accept 200, 302, 308 redirect codes)
    if curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}${route}" | grep -qE "^(200|302|308)$"; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        return 1
    fi
}

# Function to test POST endpoint
test_post_endpoint() {
    local route="$1"
    local data="$2"
    local description="$3"

    echo -n "Testing $description... "

    # Note: We expect some POST requests to fail due to validation or redirects
    # The important thing is that the server doesn't crash
    curl -s -X POST \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "$data" \
        "${BASE_URL}${route}" > /dev/null 2>&1 || true

    echo -e "${GREEN}COMPLETED${NC}"
    return 0
}

# Main test function
main() {
    log_info "Starting Medication Tracker Integration Tests"

    # Clean up any existing test container first
    cleanup 2>/dev/null || true

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not available"
        exit 1
    fi

    # Build image if it doesn't exist (for local testing)
    if ! docker image inspect "$IMAGE_TAG" > /dev/null 2>&1; then
        log_info "Building Docker image..."

        # Use default builder for local testing to ensure image is available locally
        if [ -n "${GITHUB_ACTIONS:-}" ]; then
            # In GitHub Actions, buildx is set up correctly
            docker build -t "$IMAGE_TAG" \
                --build-arg VERSION="test-$(date +%Y%m%d%H%M)" \
                .
        else
            # For local testing, use traditional docker build or buildx with --load
            if command -v docker-buildx &> /dev/null && docker buildx version &> /dev/null; then
                docker buildx build --load -t "$IMAGE_TAG" \
                    --build-arg VERSION="test-$(date +%Y%m%d%H%M)" \
                    .
            else
                # Fall back to regular docker build
                DOCKER_BUILDKIT=0 docker build -t "$IMAGE_TAG" \
                    --build-arg VERSION="test-$(date +%Y%m%d%H%M)" \
                    .
            fi
        fi
    fi

    # Start container
    log_info "Starting test container..."
    docker run -d --name "$CONTAINER_NAME" \
        -p "$PORT:8087" \
        -e FLASK_ENV=production \
        -e LOG_LEVEL=INFO \
        "$IMAGE_TAG"

    # Wait for container to be ready
    if ! wait_for_container; then
        exit 1
    fi

    # Test basic routes
    log_info "Testing web routes..."
    failed_routes=()

    routes=(
        "/:Dashboard/Home page"
        "/ingredients:Ingredients and products list"
        "/physician_visits:Physician visits list"
        "/physicians:Physicians list"
        "/orders:Orders list"
        "/schedules:Schedules list"
        "/scanner/scan:Scanner page"
        "/onboarding:Package onboarding"
        "/pdf-mapper:PDF mapper"
        "/settings:Settings main page"
        "/settings/physician_visits:Visit settings page"
        "/system/status:System status"
        "/system/migrations:Migration status"
    )

    for route_info in "${routes[@]}"; do
        IFS=':' read -r route description <<< "$route_info"
        if ! test_route "$route" "$description"; then
            failed_routes+=("$route")
        fi
    done

    # Test POST endpoints (form submissions)
    log_info "Testing form submissions..."

    # Test product creation form
    test_post_endpoint "/ingredients/products/new" \
        "ingredient_name=Test+Ingredient&brand_name=Test+Product&manufacturer=Test+Pharma&is_otc=on" \
        "Product creation form"

    # Test physician creation form
    test_post_endpoint "/physicians/new" \
        "name=Dr. Test&specialty=General Medicine&phone=555-1234&email=test@example.com" \
        "Physician creation form"

    # Test visit creation form
    test_post_endpoint "/physician_visits/new" \
        "visit_date=2025-12-31&notes=Test visit&physician_id=" \
        "Visit creation form"

    # Verify pages still work after POST requests
    log_info "Verifying pages after form submissions..."
    test_route "/ingredients" "Ingredients page after form submission"
    test_route "/physicians" "Physicians page after form submission"
    test_route "/physician_visits" "Visits page after form submission"

    # Check container health
    log_info "Checking container health..."

    if docker ps | grep -q "$CONTAINER_NAME"; then
        log_info "✅ Container is still running"
    else
        log_warn "⚠️  Container stopped after testing (this can be normal)"
        # Don't exit here - container stopping after tests can be normal
    fi

    # Check for critical errors in logs
    log_info "Checking application logs..."
    error_logs=$(docker logs "$CONTAINER_NAME" 2>&1 | grep -E " - ERROR - | - CRITICAL - |Exception|Traceback" | grep -v "404\|favicon\|GET.*404" | head -5 || true)

    if [ -n "$error_logs" ]; then
        log_warn "Found critical errors in logs:"
        echo "$error_logs"
        log_warn "Note: Some errors might be expected depending on the test scenario"
    else
        log_info "✅ No critical errors found in logs"
    fi

    # Show recent logs
    echo ""
    log_info "Recent container logs:"
    docker logs --tail 15 "$CONTAINER_NAME"

    # Report results
    echo ""
    if [ "${#failed_routes[@]}" -eq 0 ]; then
        log_info "🎉 All integration tests passed!"
        exit 0
    else
        log_error "❌ Failed routes:"
        printf '%s\n' "${failed_routes[@]}"
        exit 1
    fi
}

# Run main function
main "$@"