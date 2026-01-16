#!/bin/bash
# =============================================================================
# AEGIS-RAG Nightly Cleanup Script
# Sprint 105: Automated cleanup to prevent disk full issues
#
# Runs via cron at 3:00 AM daily
# =============================================================================

set -e
LOG_FILE="/home/admin/logs/aegis-cleanup.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

log() {
    echo "[$DATE] $1" | tee -a "$LOG_FILE"
}

log "=== Starting AEGIS nightly cleanup ==="

# 1. Docker Build Cache (older than 7 days)
log "Cleaning Docker build cache..."
docker builder prune -f --filter "until=168h" 2>/dev/null || log "Docker builder prune skipped"

# 2. Unused Docker Images (dangling)
log "Removing dangling Docker images..."
docker image prune -f 2>/dev/null || log "Docker image prune skipped"

# 3. Unused Docker Volumes (WARNING: only dangling, not named volumes)
log "Removing dangling Docker volumes..."
docker volume prune -f 2>/dev/null || log "Docker volume prune skipped"

# 4. Docker System Cleanup (conservative: only build cache + dangling)
log "Docker system cleanup (conservative)..."
docker system prune -f --filter "until=168h" 2>/dev/null || log "Docker system prune skipped"

# 5. Pip Cache (older than 30 days)
log "Cleaning pip cache..."
if [ -d ~/.cache/pip ]; then
    find ~/.cache/pip -type f -mtime +30 -delete 2>/dev/null || true
    log "Pip cache cleaned (files older than 30 days)"
fi

# 6. HuggingFace Hub Cache (only locks and temp files)
log "Cleaning HuggingFace cache locks..."
if [ -d /data/models ]; then
    find /data/models -name "*.lock" -delete 2>/dev/null || true
    find /data/models -name "*.incomplete" -delete 2>/dev/null || true
    log "HuggingFace locks cleaned"
fi

# 7. Python __pycache__ directories (older than 7 days)
log "Cleaning Python cache..."
find /home/admin/projects/aegisrag/AEGIS_Rag -type d -name "__pycache__" -mtime +7 -exec rm -rf {} + 2>/dev/null || true

# 8. Pytest Cache (older than 7 days)
log "Cleaning pytest cache..."
find /home/admin/projects/aegisrag/AEGIS_Rag -type d -name ".pytest_cache" -mtime +7 -exec rm -rf {} + 2>/dev/null || true

# 9. Log rotation (keep last 7 days of cleanup logs)
log "Rotating cleanup logs..."
if [ -f "$LOG_FILE" ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

# 10. Report disk usage
log "Current disk usage:"
df -h / | tail -1 | tee -a "$LOG_FILE"

log "=== AEGIS nightly cleanup complete ==="

# Calculate space freed (approximate)
SPACE_AFTER=$(df / | tail -1 | awk '{print $4}')
log "Available space: ${SPACE_AFTER}K"
