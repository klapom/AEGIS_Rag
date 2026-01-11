#!/bin/bash
# Upload files 3-5, skipping file 2

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

echo "🔐 Authenticated"
echo "Skipping file 2, uploading files 3-5..."

FILES=(
  "ragas_phase1_0032_hotpot_5ac061ab.txt"
  "ragas_phase1_0089_hotpot_5ac3e8c6.txt"
  "ragas_phase1_0102_hotpot_5ab6e84a.txt"
)

for i in "${!FILES[@]}"; do
  FILE="${FILES[$i]}"
  FILE_NUM=$((i+3))
  echo ""
  echo "[$FILE_NUM/5] Uploading: $FILE"
  echo "========================================"

  START=$(date +%s)

  RESULT=$(curl -s -X POST http://localhost:8000/api/v1/retrieval/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@data/ragas_phase1_contexts/$FILE" \
    -F "namespace=ragas_phase2_sprint83_v1" \
    -F "domain=factual" \
    --max-time 180)

  END=$(date +%s)
  DURATION=$((END - START))

  STATUS=$(echo "$RESULT" | jq -r '.status // "error"')
  CHUNKS=$(echo "$RESULT" | jq -r '.chunks_created // 0')
  ENTITIES=$(echo "$RESULT" | jq -r '.neo4j_entities // 0')
  RELATIONS=$(echo "$RESULT" | jq -r '.neo4j_relationships // 0')

  echo "Duration: ${DURATION}s"
  echo "Status: $STATUS"
  echo "Chunks: $CHUNKS"
  echo "Entities: $ENTITIES"
  echo "Relations: $RELATIONS"

  if [ "$CHUNKS" -gt 0 ]; then
    ENTITIES_PER_CHUNK=$(echo "scale=2; $ENTITIES / $CHUNKS" | bc)
    echo "Entities/Chunk: $ENTITIES_PER_CHUNK"

    if (( $(echo "$ENTITIES_PER_CHUNK < 1.0" | bc -l) )); then
      echo "🔴 CRITICAL: Entities per chunk below 1.0!"
      exit 1
    fi
  fi

  if [ "$STATUS" != "success" ]; then
    echo "🔴 Upload failed!"
    echo "Response: $RESULT"
    exit 1
  fi

  echo "✅ Success"
done

echo ""
echo "========================================"
echo "✅ Files 3-5 uploaded successfully!"
echo "NOTE: File 2 skipped due to timeout - requires investigation"
