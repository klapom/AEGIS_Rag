#!/bin/bash
# Upload Amnesty QA contexts to AegisRAG
# Sprint 76 Feature 76.4: RAGAS Default Evaluation Set

set -e

NAMESPACE="amnesty_qa"
CONTEXTS_DIR="data/amnesty_qa_contexts/contexts"
API_BASE="http://localhost:8000"
LOGIN_ENDPOINT="${API_BASE}/api/v1/auth/login"
UPLOAD_ENDPOINT="${API_BASE}/api/v1/retrieval/upload"

echo "================================================================================"
echo "UPLOADING AMNESTY QA CONTEXTS"
echo "================================================================================"
echo "Namespace: ${NAMESPACE}"
echo "Contexts directory: ${CONTEXTS_DIR}"
echo "API Base: ${API_BASE}"
echo ""

# Login to get JWT token
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$LOGIN_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "✗ Login failed!"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo "✓ Login successful"
echo ""

# Count files
TOTAL_FILES=$(ls -1 "${CONTEXTS_DIR}"/*.txt 2>/dev/null | wc -l)
echo "Found ${TOTAL_FILES} context files"
echo ""

# Upload each context file
UPLOADED=0
FAILED=0

for file in "${CONTEXTS_DIR}"/*.txt; do
    if [ ! -f "$file" ]; then
        continue
    fi

    filename=$(basename "$file")
    echo -n "Uploading ${filename}... "

    RESPONSE=$(curl -s -X POST "$UPLOAD_ENDPOINT" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@${file}" \
        -F "namespace_id=${NAMESPACE}")

    STATUS=$(echo "$RESPONSE" | jq -r '.status // "error"')

    if [ "$STATUS" = "success" ]; then
        echo "✓"
        ((UPLOADED++))
    else
        echo "✗"
        echo "  Error: $(echo "$RESPONSE" | jq -r '.error.message // "Unknown error"')"
        ((FAILED++))
    fi

    # Rate limiting: Small delay between uploads
    sleep 0.1
done

echo ""
echo "================================================================================"
echo "UPLOAD SUMMARY"
echo "================================================================================"
echo "Total files: ${TOTAL_FILES}"
echo "Uploaded: ${UPLOADED}"
echo "Failed: ${FAILED}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ All contexts uploaded successfully!"
else
    echo "⚠ ${FAILED} contexts failed to upload"
    exit 1
fi
