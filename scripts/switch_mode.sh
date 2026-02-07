#!/bin/bash
# ============================================================================
# scripts/switch_mode.sh - Switch between CHAT and INGESTION modes
# ============================================================================
# Sprint 125 Feature 125.3: Strict Docker profile separation for vLLM vs Ollama
#
# PROBLEM: vLLM and Ollama both need GPU access on DGX Spark, but they CONFLICT:
#   - vLLM does GPU memory profiling during startup
#   - Ollama unloads models when vLLM allocates GPU memory
#   RESULT: vLLM fails with "Error in memory profiling" (AssertionError)
#
# SOLUTION: Run only ONE at a time:
#   - CHAT MODE (default): Ollama only → LLM chat/query
#   - INGESTION MODE: vLLM only → High-concurrency extraction (256+), no chat
#
# Usage:
#   ./scripts/switch_mode.sh chat       # Start CHAT mode (Ollama)
#   ./scripts/switch_mode.sh ingestion  # Start INGESTION mode (vLLM + Docling)
#
# Implementation:
#   - Profiles: ollama in "chat" profile, vllm/docling in "ingestion" profile
#   - Health checks: Wait for service readiness before returning
#   - GPU memory cleanup: 5s pause to ensure GPU memory is fully released
#   - Idempotent: Safe to call multiple times (won't error if already running)
# ============================================================================

set -e

COMPOSE_FILE="docker-compose.dgx-spark.yml"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DOCKER_COMPOSE_CMD="docker compose -f $COMPOSE_FILE"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for service health
wait_for_health() {
    local service=$1
    local url=$2
    local timeout=${3:-60}
    local elapsed=0

    log_info "Waiting for $service to be healthy..."

    while [ $elapsed -lt $timeout ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            log_info "$service is healthy after ${elapsed}s"
            return 0
        fi
        sleep 10
        elapsed=$((elapsed + 10))
    done

    log_warn "$service health check timed out after ${timeout}s (this is OK if service is starting)"
    return 1
}

# Function to check if service is running
is_running() {
    local container=$1
    docker ps --format '{{.Names}}' | grep -q "^${container}$" 2>/dev/null
    return $?
}

# Function to stop and remove Ollama
stop_ollama() {
    if is_running "aegis-ollama"; then
        log_info "Stopping Ollama container..."
        docker compose -f "$COMPOSE_FILE" stop ollama
        log_info "Ollama stopped ✓"
    else
        log_warn "Ollama is not running (skipped)"
    fi
}

# Function to start Ollama
start_ollama() {
    log_info "Starting Ollama in CHAT mode..."
    docker compose -f "$COMPOSE_FILE" up -d ollama

    # Wait for Ollama to be ready
    wait_for_health "Ollama" "http://localhost:11434/api/tags" 120
}

# Function to stop vLLM and Docling
stop_vllm() {
    if is_running "aegis-vllm"; then
        log_info "Stopping vLLM container..."
        docker compose -f "$COMPOSE_FILE" stop vllm
        log_info "vLLM stopped ✓"
    else
        log_warn "vLLM is not running (skipped)"
    fi

    if is_running "aegis-docling"; then
        log_info "Stopping Docling container..."
        docker compose -f "$COMPOSE_FILE" stop docling
        log_info "Docling stopped ✓"
    else
        log_warn "Docling is not running (skipped)"
    fi
}

# Function to start vLLM and Docling
start_vllm() {
    log_info "Switching to INGESTION mode..."
    log_info "  This will stop Ollama and start vLLM + Docling"

    # Wait for GPU memory to be released
    log_info "Pausing 5s for GPU memory cleanup..."
    sleep 5

    # Start vLLM and Docling with ingestion profile
    log_info "Starting vLLM and Docling with --profile ingestion..."
    docker compose -f "$COMPOSE_FILE" --profile ingestion up -d vllm docling

    # Wait for vLLM to be ready (takes 2-7 minutes for model download/initialization)
    log_info "Waiting for vLLM to initialize (this may take 2-7 minutes)..."
    wait_for_health "vLLM" "http://localhost:8001/health" 600
}

# Main command handler
case "$1" in
    chat)
        log_info "=========================================="
        log_info "SWITCHING TO CHAT MODE (Ollama only)"
        log_info "=========================================="
        stop_vllm
        log_info "Pausing 5s for GPU memory cleanup..."
        sleep 5
        start_ollama
        log_info "=========================================="
        log_info "CHAT MODE ACTIVE ✓"
        log_info "  Ollama: http://localhost:11434"
        log_info "  API: http://localhost:8000"
        log_info "=========================================="
        ;;

    ingestion)
        log_info "=========================================="
        log_info "SWITCHING TO INGESTION MODE (vLLM + Docling only)"
        log_info "=========================================="
        stop_ollama
        start_vllm
        log_info "=========================================="
        log_info "INGESTION MODE ACTIVE ✓"
        log_info "  vLLM: http://localhost:8001 (supports 256+ concurrent requests)"
        log_info "  Docling: http://localhost:8080 (GPU-accelerated OCR)"
        log_info "  API: http://localhost:8000"
        log_info "=========================================="
        ;;

    status)
        log_info "Checking current mode..."
        ollama_running=false
        vllm_running=false

        if is_running "aegis-ollama"; then
            ollama_running=true
            log_info "  Ollama: RUNNING ✓"
        else
            log_info "  Ollama: STOPPED"
        fi

        if is_running "aegis-vllm"; then
            vllm_running=true
            log_info "  vLLM: RUNNING ✓"
        else
            log_info "  vLLM: STOPPED"
        fi

        if [ "$ollama_running" = true ] && [ "$vllm_running" = false ]; then
            log_info "Current mode: CHAT ✓"
        elif [ "$ollama_running" = false ] && [ "$vllm_running" = true ]; then
            log_info "Current mode: INGESTION ✓"
        elif [ "$ollama_running" = true ] && [ "$vllm_running" = true ]; then
            log_warn "WARNING: Both Ollama and vLLM are running!"
            log_warn "This will cause GPU memory conflicts. Switch to one mode:"
            log_warn "  ./scripts/switch_mode.sh chat     # Use Ollama"
            log_warn "  ./scripts/switch_mode.sh ingestion # Use vLLM"
        else
            log_warn "Both services are stopped (no LLM available)"
        fi
        ;;

    *)
        log_error "Invalid mode: $1"
        echo ""
        echo "Usage: $0 [chat|ingestion|status]"
        echo ""
        echo "Commands:"
        echo "  chat       - Switch to CHAT mode (Ollama only, for chat/query)"
        echo "  ingestion  - Switch to INGESTION mode (vLLM + Docling, for extraction)"
        echo "  status     - Show current mode"
        echo ""
        echo "Examples:"
        echo "  $0 chat       # Start Ollama for chat"
        echo "  $0 ingestion  # Start vLLM for ingestion (takes 2-7 minutes)"
        echo "  $0 status     # Show which mode is active"
        exit 1
        ;;
esac
