#!/bin/bash
set -e

API="http://localhost:8000"
LOGIN_ENDPOINT="$API/api/v1/auth/login"
UPLOAD_ENDPOINT="$API/api/v1/retrieval/upload"

echo "================================================"
echo "RAGAS Dataset Upload (Frontend Endpoint)"
echo "Using: $UPLOAD_ENDPOINT"
echo "================================================"

# Step 1: Login and get JWT token
echo ""
echo "=== Step 1: Authenticating ==="
LOGIN_RESPONSE=$(curl -s -X POST "$LOGIN_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "  ✗ Login failed!"
    echo "$LOGIN_RESPONSE" | jq .
    exit 1
fi

echo "  ✓ Authenticated successfully"
echo "  Token: ${TOKEN:0:20}..."

# Function to upload via frontend endpoint
upload_file() {
    local file=$1
    local namespace=$2
    local filename=$(basename "$file")

    echo ""
    echo "=== Uploading: $filename (namespace: $namespace) ==="

    RESPONSE=$(curl -s -X POST "$UPLOAD_ENDPOINT" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$file" \
        -F "namespace_id=$namespace" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo "  ✓ Success"
        echo "$BODY" | jq -r '
            "  - Chunks: \(.chunks_created // 0)",
            "  - Entities: \(.entities_extracted // 0)",
            "  - Relations: \(.relations_extracted // 0)",
            "  - Duration: \(.processing_time_s // 0)s"
        ' 2>/dev/null || echo "$BODY"
        return 0
    else
        echo "  ✗ Failed (HTTP $HTTP_CODE)"
        echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
        return 1
    fi
}

# Track totals
TOTAL=0
SUCCESS=0

# Upload small files
echo ""
echo "### SMALL FILES (ragas_eval_txt) ###"
for file in data/ragas_eval_txt/hotpot_*.txt; do
    [ -f "$file" ] || continue
    TOTAL=$((TOTAL + 1))
    if upload_file "$file" "ragas_eval_txt"; then
        SUCCESS=$((SUCCESS + 1))
    fi
    sleep 2  # Rate limiting
done

# Upload large files
echo ""
echo "### LARGE FILES (ragas_eval_txt_large) ###"
for file in data/ragas_eval_txt_large/sample_*.txt; do
    [ -f "$file" ] || continue
    TOTAL=$((TOTAL + 1))
    if upload_file "$file" "ragas_eval_txt_large"; then
        SUCCESS=$((SUCCESS + 1))
    fi
    sleep 2  # Rate limiting
done

# Summary
echo ""
echo "================================================"
echo "UPLOAD SUMMARY"
echo "================================================"
echo "Total Files:      $TOTAL"
echo "Successful:       $SUCCESS"
echo "Failed:           $((TOTAL - SUCCESS))"
echo "Success Rate:     $((SUCCESS * 100 / TOTAL))%"
echo "================================================"

exit $((TOTAL - SUCCESS))
