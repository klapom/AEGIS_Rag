#!/bin/bash
# Upload AEGIS documentation to test_ragas namespace
# Sprint 75 - RAGAS Evaluation Setup

set -e

echo "🔐 Getting auth token..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

echo "✅ Token obtained"
echo ""

# Upload each document
for file in /tmp/aegis_docs_txt/*.txt; do
    filename=$(basename "$file")
    echo "📄 Uploading: $filename"

    curl -s -X POST "http://localhost:8000/api/v1/retrieval/upload" \
      -H "Authorization: Bearer $TOKEN" \
      -F "file=@$file" \
      -F "namespace=test_ragas" \
      > /tmp/upload_result.json

    if grep -q "error" /tmp/upload_result.json; then
        echo "   ❌ Upload failed:"
        cat /tmp/upload_result.json | python3 -m json.tool 2>/dev/null | head -10
    else
        doc_id=$(cat /tmp/upload_result.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('document_id', 'N/A'))" 2>/dev/null)
        chunks=$(cat /tmp/upload_result.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('chunk_count', 'N/A'))" 2>/dev/null)
        echo "   ✅ Uploaded: doc_id=$doc_id, chunks=$chunks"
    fi

    echo "   ⏳ Waiting 5s for processing..."
    sleep 5
    echo ""
done

echo "📊 Checking namespaces..."
curl -s "http://localhost:8000/api/v1/admin/namespaces" | python3 -m json.tool 2>/dev/null

echo ""
echo "✅ Upload complete!"
