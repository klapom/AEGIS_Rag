#!/bin/bash
# Monitor RAGAS Phase 1 upload progress
# Usage: ./scripts/check_upload_progress.sh

LOG_FILE="upload_phase1.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Upload log file not found: $LOG_FILE"
    exit 1
fi

# Extract current progress
CURRENT=$(grep -E "^\[[0-9]+/[0-9]+\]" "$LOG_FILE" | tail -1)
UPLOADED=$(grep -c "✓ Success" "$LOG_FILE")
FAILED=$(grep -c "✗ Failed" "$LOG_FILE")

echo "=== RAGAS Phase 1 Upload Progress ==="
echo "Current: $CURRENT"
echo "Uploaded: $UPLOADED"
echo "Failed: $FAILED"
echo ""
echo "Last 5 uploads:"
grep -E "^\[[0-9]+/[0-9]+\]|✓ Success|✗ Failed" "$LOG_FILE" | tail -10
echo ""
echo "To follow live: tail -f $LOG_FILE"
