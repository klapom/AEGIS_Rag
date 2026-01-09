#!/bin/bash
# Upload RAGAS Phase 1 contexts to AegisRAG via Frontend API
# Sprint 82: Phase 1 - Text-Only Benchmark
#
# CRITICAL: This script uses the Frontend API to ensure:
# 1. Namespace is correctly set in ALL databases (Qdrant, Neo4j, BM25, LightRAG)
# 2. Full ingestion pipeline runs (chunking -> embedding -> graph extraction)
# 3. All metadata is properly attached
#
# Usage:
#   ./scripts/upload_ragas_phase1.sh                    # Upload all 500 samples
#   ./scripts/upload_ragas_phase1.sh --max 10           # Upload first 10 samples (testing)
#   ./scripts/upload_ragas_phase1.sh --resume 100       # Resume from sample 100
#   ./scripts/upload_ragas_phase1.sh --dry-run          # Show what would be uploaded

set -e

# Configuration
API="http://localhost:8000"
LOGIN_ENDPOINT="$API/api/v1/auth/login"
UPLOAD_ENDPOINT="$API/api/v1/retrieval/upload"
NAMESPACE="ragas_phase1"
CONTEXTS_DIR="data/ragas_phase1_contexts"

# Parse arguments
MAX_SAMPLES=-1
RESUME_FROM=0
DRY_RUN=false
DELAY=2  # Seconds between uploads

while [[ $# -gt 0 ]]; do
    case $1 in
        --max)
            MAX_SAMPLES="$2"
            shift 2
            ;;
        --resume)
            RESUME_FROM="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "================================================================"
echo "RAGAS Phase 1 Upload (Frontend API)"
echo "================================================================"
echo "Namespace: ${NAMESPACE}"
echo "Contexts directory: ${CONTEXTS_DIR}"
echo "API Base: ${API}"
echo "Max samples: ${MAX_SAMPLES} (-1 = all)"
echo "Resume from: ${RESUME_FROM}"
echo "Delay between uploads: ${DELAY}s"
echo "Dry run: ${DRY_RUN}"
echo "================================================================"

# Check if contexts directory exists
if [ ! -d "$CONTEXTS_DIR" ]; then
    echo ""
    echo "ERROR: Contexts directory not found: ${CONTEXTS_DIR}"
    echo ""
    echo "Please run the preparation script first:"
    echo "  poetry run python scripts/ragas_benchmark/prepare_phase1_ingestion.py"
    exit 1
fi

# Count files
TOTAL_FILES=$(ls -1 "${CONTEXTS_DIR}"/*.txt 2>/dev/null | wc -l)
echo ""
echo "Found ${TOTAL_FILES} context files"

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "[DRY RUN] Would upload ${TOTAL_FILES} files to namespace '${NAMESPACE}'"
    echo "[DRY RUN] First 5 files:"
    ls -1 "${CONTEXTS_DIR}"/*.txt | head -5 | while read f; do
        echo "  - $(basename "$f")"
    done
    exit 0
fi

# Step 1: Login and get JWT token
echo ""
echo "=== Step 1: Authenticating ==="
LOGIN_RESPONSE=$(curl -s -X POST "$LOGIN_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "  ERROR: Login failed!"
    echo "$LOGIN_RESPONSE" | jq .
    exit 1
fi

echo "  ✓ Authenticated successfully"
echo "  Token: ${TOKEN:0:20}..."

# Function to upload a single file
upload_file() {
    local file=$1
    local namespace=$2
    local index=$3
    local total=$4
    local filename=$(basename "$file")

    echo ""
    echo "[${index}/${total}] Uploading: ${filename}"

    RESPONSE=$(curl -s -X POST "$UPLOAD_ENDPOINT" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$file" \
        -F "namespace_id=$namespace" \
        -w "\n%{http_code}" \
        --max-time 300)  # 5 min timeout per file

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    if [ "$HTTP_CODE" = "200" ]; then
        # Parse response
        STATUS=$(echo "$BODY" | jq -r '.status // "unknown"')
        CHUNKS=$(echo "$BODY" | jq -r '.chunks_created // 0')
        ENTITIES=$(echo "$BODY" | jq -r '.entities_extracted // 0')
        RELATIONS=$(echo "$BODY" | jq -r '.relations_extracted // 0')
        DURATION=$(echo "$BODY" | jq -r '.processing_time_s // 0')

        echo "  ✓ Success (${DURATION}s)"
        echo "    Chunks: ${CHUNKS}, Entities: ${ENTITIES}, Relations: ${RELATIONS}"
        return 0
    else
        echo "  ✗ Failed (HTTP ${HTTP_CODE})"
        echo "    Error: $(echo "$BODY" | jq -r '.detail // .error.message // "Unknown error"' 2>/dev/null || echo "$BODY")"
        return 1
    fi
}

# Step 2: Upload files
echo ""
echo "=== Step 2: Uploading Contexts ==="

UPLOADED=0
FAILED=0
SKIPPED=0
INDEX=0

# Sort files for consistent ordering
FILES=$(ls -1 "${CONTEXTS_DIR}"/*.txt | sort)

for file in $FILES; do
    INDEX=$((INDEX + 1))

    # Skip if before resume point
    if [ $INDEX -le $RESUME_FROM ]; then
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Stop if max reached
    if [ $MAX_SAMPLES -gt 0 ] && [ $UPLOADED -ge $MAX_SAMPLES ]; then
        echo ""
        echo "Reached max samples limit (${MAX_SAMPLES})"
        break
    fi

    # Calculate effective index for display
    EFFECTIVE_INDEX=$((UPLOADED + 1))
    if [ $MAX_SAMPLES -gt 0 ]; then
        DISPLAY_TOTAL=$MAX_SAMPLES
    else
        DISPLAY_TOTAL=$((TOTAL_FILES - RESUME_FROM))
    fi

    if upload_file "$file" "$NAMESPACE" "$EFFECTIVE_INDEX" "$DISPLAY_TOTAL"; then
        UPLOADED=$((UPLOADED + 1))
    else
        FAILED=$((FAILED + 1))
    fi

    # Rate limiting
    sleep $DELAY
done

# Summary
echo ""
echo "================================================================"
echo "UPLOAD SUMMARY"
echo "================================================================"
echo "Total Files:      ${TOTAL_FILES}"
echo "Skipped:          ${SKIPPED}"
echo "Uploaded:         ${UPLOADED}"
echo "Failed:           ${FAILED}"
if [ $UPLOADED -gt 0 ]; then
    SUCCESS_RATE=$((UPLOADED * 100 / (UPLOADED + FAILED)))
    echo "Success Rate:     ${SUCCESS_RATE}%"
fi
echo "================================================================"

# Verification hint
echo ""
echo "### VERIFY INGESTION ###"
echo ""
echo "1. Check Qdrant namespace:"
echo "   curl -s 'http://localhost:6333/collections/documents_v1/points/scroll' \\"
echo "       -d '{\"limit\": 3, \"with_payload\": [\"namespace_id\"], \"filter\": {\"must\": [{\"key\": \"namespace_id\", \"match\": {\"value\": \"${NAMESPACE}\"}}]}}' | jq"
echo ""
echo "2. Check Neo4j entities:"
echo "   MATCH (e:base {namespace_id: '${NAMESPACE}'}) RETURN count(e)"
echo ""
echo "3. Run RAGAS evaluation:"
echo "   poetry run python scripts/run_ragas_evaluation.py \\"
echo "       --dataset data/evaluation/ragas_phase1_questions.jsonl \\"
echo "       --namespace ${NAMESPACE} \\"
echo "       --mode hybrid \\"
echo "       --max-questions 10"
echo ""

exit $FAILED
