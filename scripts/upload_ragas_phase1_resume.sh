#!/bin/bash
#
# Iteration 1 Re-Run: Verify Feature 84.7 + 84.8 (Sprint 84)
#
# Purpose: Re-upload 5 HotpotQA files to verify:
# - Feature 84.7: Neo4j Cypher escaping (entities with spaces/colons/slashes persist correctly)
# - Feature 84.8: .txt section extraction skip (42s → <5s chunking performance)
#
# Expected Results:
# - Neo4j: 139 entities persisted (was 0 before Feature 84.7)
# - Chunking performance: <5s per .txt file (was 42s before Feature 84.8)
#

set -e

NAMESPACE="ragas_phase2_sprint84_iter1_rerun"
API_BASE="http://localhost:8000/api/v1"
DATA_DIR="/home/admin/projects/aegisrag/AEGIS_Rag/data/ragas_phase1_contexts"

# Files from original Iteration 1 (now with _hotpot_ suffix)
FILES=(
    "ragas_phase1_0003_hotpot_5a82171f.txt"  # 3.6KB, 17 entities, 8 relations (42.8s chunking before fix)
    "ragas_phase1_0015_hotpot_5ae0d91e.txt"  # 54 entities, 23-26 relations (1409s total)
    "ragas_phase1_0032_hotpot_5ac061ab.txt"  # 14 entities, 20 relations (172.5s total)
    "ragas_phase1_0089_hotpot_5ac3e8c6.txt"  # 20 entities, 17 relations (381.8s total)
    "ragas_phase1_0102_hotpot_5ab6e84a.txt"  # 34 entities, 7 relations (125.9s total)
)

echo "========================================="
echo "Iteration 1 Re-Run: Feature 84.7 + 84.8 Verification"
echo "========================================="
echo "Namespace: $NAMESPACE"
echo "Files: ${#FILES[@]}"
echo ""

# Step 1: Login
echo "[1/3] Authenticating..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ]; then
    echo "❌ Authentication failed!"
    echo "$TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authenticated as admin"
echo ""

# Step 2: Upload files
echo "[2/3] Uploading files..."
UPLOAD_COUNT=0
FAILED_COUNT=0
TOTAL_ENTITIES=0
TOTAL_RELATIONS=0

for FILE in "${FILES[@]}"; do
    FILE_PATH="$DATA_DIR/$FILE"

    if [ ! -f "$FILE_PATH" ]; then
        echo "⚠️  File not found: $FILE_PATH"
        continue
    fi

    echo "Uploading: $FILE"
    START_TIME=$(date +%s)

    RESPONSE=$(curl -s -X POST "$API_BASE/retrieval/upload" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -F "file=@$FILE_PATH" \
        -F "namespace_id=$NAMESPACE" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    if [ "$HTTP_CODE" -eq 200 ]; then
        ENTITIES=$(echo "$BODY" | jq -r '.extraction_stats.entities_count // 0')
        RELATIONS=$(echo "$BODY" | jq -r '.extraction_stats.relations_count // 0')

        echo "  ✅ Success (${DURATION}s)"
        echo "     Entities: $ENTITIES, Relations: $RELATIONS"

        TOTAL_ENTITIES=$((TOTAL_ENTITIES + ENTITIES))
        TOTAL_RELATIONS=$((TOTAL_RELATIONS + RELATIONS))
        ((UPLOAD_COUNT++))
    else
        echo "  ❌ Failed (HTTP $HTTP_CODE)"
        echo "     $BODY"
        ((FAILED_COUNT++))
    fi

    echo ""
done

echo "Upload Summary:"
echo "  ✅ Success: $UPLOAD_COUNT"
echo "  ❌ Failed: $FAILED_COUNT"
echo "  Total Entities (API): $TOTAL_ENTITIES"
echo "  Total Relations (API): $TOTAL_RELATIONS"
echo ""

# Step 3: Verify Neo4j persistence (Feature 84.7)
echo "[3/3] Verifying Neo4j persistence (Feature 84.7)..."

# Wait 5s for background processing
echo "Waiting 5s for background processing..."
sleep 5

NEO4J_STATS=$(curl -s -X GET "$API_BASE/admin/graph/stats" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

ENTITY_COUNT=$(echo "$NEO4J_STATS" | jq -r '.entity_count // 0')
REL_COUNT=$(echo "$NEO4J_STATS" | jq -r '.relationship_count // 0')

echo "Neo4j Database:"
echo "  Entities: $ENTITY_COUNT (expected: ~$TOTAL_ENTITIES)"
echo "  Relations: $REL_COUNT (expected: ~$TOTAL_RELATIONS)"
echo ""

# Verification results
echo "========================================="
echo "Verification Results"
echo "========================================="

if [ "$ENTITY_COUNT" -gt 100 ]; then
    echo "✅ Feature 84.7 VERIFIED: Neo4j entities persisted successfully"
    echo "   Before fix: 0 entities (Cypher syntax errors)"
    echo "   After fix: $ENTITY_COUNT entities"
else
    echo "❌ Feature 84.7 FAILED: Only $ENTITY_COUNT entities in Neo4j"
    echo "   Expected: ~$TOTAL_ENTITIES entities from API extraction"
fi

echo ""
echo "Feature 84.8 performance verification:"
echo "  Check backend logs for TIMING_chunking_section_extraction"
echo "  Expected: section_extraction_ms = 0 for .txt files"
echo "  Expected: chunking duration <5s per file (was 42s before fix)"
echo ""

echo "To check backend logs:"
echo "  docker logs aegis-rag-api-1 2>&1 | grep -A 5 'TIMING_chunking'"
echo ""
