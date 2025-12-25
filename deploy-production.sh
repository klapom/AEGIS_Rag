#!/bin/bash
# =============================================================================
# AEGIS RAG Production Deployment Script for DGX Spark
# =============================================================================
# This script deploys AEGIS RAG for production use on DGX Spark
# After deployment, access via: http://<dgx-spark-ip>
#
# Usage:
#   ./deploy-production.sh         # Full deployment
#   ./deploy-production.sh --rebuild # Rebuild all images
#   ./deploy-production.sh --stop    # Stop all services
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi

    # Check environment file
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "Environment file not found. Creating from template..."
        cp .env.example "$ENV_FILE" 2>/dev/null || true
        log_warning "Please edit $ENV_FILE with your configuration!"
        exit 1
    fi

    log_success "All requirements met"
}

build_frontend() {
    log_info "Building frontend production bundle..."

    cd frontend

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install
    fi

    # Build production bundle
    log_info "Creating production build..."
    npm run build

    cd ..

    log_success "Frontend build complete (dist folder ready)"
}

pull_ollama_models() {
    log_info "Pulling Ollama models (this may take a while)..."

    # Wait for Ollama to be ready
    log_info "Waiting for Ollama to start..."
    sleep 10

    # Pull models
    docker exec aegis-ollama ollama pull nemotron-no-think:latest || log_warning "Failed to pull nemotron-no-think"
    docker exec aegis-ollama ollama pull gpt-oss:20b || log_warning "Failed to pull gpt-oss"
    docker exec aegis-ollama ollama pull qwen3-vl:32b || log_warning "Failed to pull qwen3-vl"

    log_success "Ollama models pulled"
}

deploy() {
    log_info "Starting AEGIS RAG production deployment..."

    # Build frontend
    build_frontend

    # Start services
    log_info "Starting Docker services..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 5

    # Pull Ollama models
    pull_ollama_models

    # Get DGX Spark IP
    DGX_IP=$(hostname -I | awk '{print $1}')

    log_success "Deployment complete!"
    echo ""
    echo "========================================="
    echo "AEGIS RAG is now running!"
    echo "========================================="
    echo ""
    echo "Frontend:    http://$DGX_IP"
    echo "API:         http://$DGX_IP/api"
    echo "Health:      http://$DGX_IP/health"
    echo ""
    echo "Monitoring:"
    echo "  Prometheus: http://$DGX_IP:9090"
    echo "  Grafana:    http://$DGX_IP:3000 (admin/admin)"
    echo ""
    echo "Database Admin (Internal):"
    echo "  Neo4j:      http://$DGX_IP/neo4j"
    echo "  Qdrant:     http://$DGX_IP/qdrant"
    echo ""
    echo "Logs:        docker compose -f $COMPOSE_FILE logs -f"
    echo "Stop:        ./deploy-production.sh --stop"
    echo "========================================="
}

rebuild() {
    log_info "Rebuilding all images..."

    # Stop existing containers
    docker compose -f "$COMPOSE_FILE" down

    # Build frontend
    build_frontend

    # Rebuild Docker images
    docker compose -f "$COMPOSE_FILE" build --no-cache

    # Start services
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

    log_success "Rebuild complete"
}

stop() {
    log_info "Stopping AEGIS RAG services..."
    docker compose -f "$COMPOSE_FILE" down
    log_success "All services stopped"
}

show_logs() {
    docker compose -f "$COMPOSE_FILE" logs -f
}

show_status() {
    log_info "Service Status:"
    docker compose -f "$COMPOSE_FILE" ps
}

# Main script
case "${1:-deploy}" in
    deploy)
        check_requirements
        deploy
        ;;
    --rebuild)
        check_requirements
        rebuild
        ;;
    --stop)
        stop
        ;;
    --logs)
        show_logs
        ;;
    --status)
        show_status
        ;;
    *)
        echo "Usage: $0 [deploy|--rebuild|--stop|--logs|--status]"
        exit 1
        ;;
esac
