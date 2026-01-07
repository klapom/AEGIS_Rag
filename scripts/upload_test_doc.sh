#!/bin/bash
# Upload test document to test_ragas namespace
# Sprint 75 - Namespace Isolation Verification

set -e

echo "🔐 Getting auth token..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

echo "Token: ${TOKEN:0:30}..."

echo ""
echo "📄 Uploading ADR-024 to test_ragas namespace..."
curl -X POST "http://localhost:8000/api/v1/retrieval/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@docs/adr/ADR-024-bge-m3-system-wide-standardization.md" \
  -F "namespace=test_ragas" \
  | python3 -m json.tool 2>/dev/null || echo "Upload completed (parsing response failed)"

echo ""
echo "⏳ Waiting 10 seconds for processing..."
sleep 10

echo ""
echo "📊 Checking namespaces..."
curl -s "http://localhost:8000/api/v1/admin/namespaces" | python3 -m json.tool 2>/dev/null
