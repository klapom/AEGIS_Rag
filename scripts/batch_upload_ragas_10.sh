#!/bin/bash
# Batch upload first 10 RAGAS Phase 1 documents
# Sprint 127: vLLM-only mode with retry, optimal config (2 workers, gpu-mem 0.45)
# Usage: bash scripts/batch_upload_ragas_10.sh

RAGAS_DIR="/home/admin/projects/aegisrag/AEGIS_Rag/data/ragas_phase1_contexts"
API_URL="http://localhost:8000/api/v1/retrieval/upload"
RESULTS_FILE="/tmp/ragas_batch_10_results.jsonl"
NAMESPACE="ragas_phase1_sprint127"

echo "========================================="
echo "PRE-FLIGHT: Engine Mode & Cache Setup"
echo "========================================="

# Set engine mode to vllm (no Ollama fallback)
echo "Setting engine mode to vllm..."
docker exec aegis-redis redis-cli SET aegis:llm_engine_mode vllm
ENGINE_MODE=$(docker exec aegis-redis redis-cli GET aegis:llm_engine_mode)
echo "Engine mode: $ENGINE_MODE"

# Clear Redis prompt cache to ensure fresh extraction
echo "Clearing Redis prompt cache..."
CLEARED=$(docker exec aegis-redis redis-cli EVAL "local k=redis.call('keys','prompt_cache:*');for i,v in ipairs(k) do redis.call('del',v) end;return #k" 0)
echo "Cleared $CLEARED cached prompts"

# Verify vLLM is healthy
echo "Checking vLLM health..."
VLLM_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health --max-time 5)
if [ "$VLLM_HEALTH" != "200" ]; then
    echo "WARNING: vLLM health check returned HTTP $VLLM_HEALTH"
    echo "Make sure vLLM is running: docker compose -f docker-compose.dgx-spark.yml --profile ingestion up -d vllm"
    exit 1
fi
echo "vLLM healthy (HTTP 200)"
echo ""

# Get JWT token
echo "Authenticating..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/retrieval/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)  # pragma: allowlist secret

if [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to get JWT token"
    exit 1
fi
echo "Token acquired (${#TOKEN} chars)"
AUTH_HEADER="Authorization: Bearer $TOKEN"

# Clear previous results
> "$RESULTS_FILE"

echo ""
echo "========================================="
echo "RAGAS Phase 1 Batch Upload (10 docs)"
echo "Namespace: $NAMESPACE"
echo "Engine:    vLLM (with retry, no Ollama fallback)"
echo "Workers:   2 (AEGIS_EXTRACTION_WORKERS)"
echo "GPU Mem:   0.45 (gpu-memory-utilization)"
echo "Start:     $(date -Iseconds)"
echo "========================================="
echo ""

# Get first 10 files sorted
FILES=($(ls "$RAGAS_DIR" | sort | head -10))

TOTAL_START=$(date +%s)
SUCCESS=0
FAIL=0

for i in "${!FILES[@]}"; do
    FILE="${FILES[$i]}"
    NUM=$((i + 1))
    FILEPATH="$RAGAS_DIR/$FILE"
    FILESIZE=$(stat -c%s "$FILEPATH")

    echo "[$NUM/10] Uploading: $FILE (${FILESIZE} bytes)"

    # Re-authenticate before each upload (JWT expires after ~30min)
    TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/retrieval/auth/token" \
      -H "Content-Type: application/json" \
      -d '{"username": "admin", "password": "admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)  # pragma: allowlist secret
    AUTH_HEADER="Authorization: Bearer $TOKEN"

    START=$(date +%s%3N)

    # Upload via API (with JWT auth)
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_URL" \
        -H "$AUTH_HEADER" \
        -F "file=@$FILEPATH" \
        -F "namespace=$NAMESPACE" \
        -F "domain_id=auto" \
        --max-time 900)

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    END=$(date +%s%3N)
    DURATION_MS=$((END - START))
    DURATION_S=$(echo "scale=1; $DURATION_MS / 1000" | bc)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        DOC_ID=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('document_id','?'))" 2>/dev/null)
        STATUS=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null)

        echo "  -> HTTP $HTTP_CODE | doc_id=$DOC_ID | status=$STATUS | ${DURATION_S}s"

        # If background processing, wait for completion
        if [ "$STATUS" = "processing_background" ]; then
            echo "  -> Waiting for background processing..."
            POLL_START=$(date +%s)
            while true; do
                sleep 5
                POLL_RESP=$(curl -s "http://localhost:8000/api/v1/upload-status/$DOC_ID" --max-time 10)
                POLL_STATUS=$(echo "$POLL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null)

                if [ "$POLL_STATUS" = "completed" ] || [ "$POLL_STATUS" = "complete" ] || [ "$POLL_STATUS" = "indexed" ]; then
                    POLL_END=$(date +%s)
                    TOTAL_DOC_TIME=$((POLL_END - POLL_START + DURATION_MS/1000))

                    # Extract metrics from poll response
                    ENTITIES=$(echo "$POLL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('neo4j_entities', d.get('entities','-')))" 2>/dev/null)
                    RELATIONS=$(echo "$POLL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('neo4j_relationships', d.get('relationships','-')))" 2>/dev/null)
                    CHUNKS=$(echo "$POLL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('chunks_created', d.get('chunks','-')))" 2>/dev/null)
                    TOTAL_SECS=$(echo "$POLL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('duration_seconds','-'))" 2>/dev/null)

                    echo "  -> DONE: ${TOTAL_SECS}s total | entities=$ENTITIES | relations=$RELATIONS | chunks=$CHUNKS"
                    echo "{\"file\":\"$FILE\",\"doc_id\":\"$DOC_ID\",\"status\":\"completed\",\"duration_s\":$TOTAL_SECS,\"entities\":$ENTITIES,\"relations\":$RELATIONS,\"chunks\":$CHUNKS,\"filesize\":$FILESIZE}" >> "$RESULTS_FILE"
                    SUCCESS=$((SUCCESS + 1))
                    break
                elif [ "$POLL_STATUS" = "failed" ] || [ "$POLL_STATUS" = "error" ]; then
                    ERROR=$(echo "$POLL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error','unknown'))" 2>/dev/null)
                    echo "  -> FAILED: $ERROR"
                    echo "{\"file\":\"$FILE\",\"doc_id\":\"$DOC_ID\",\"status\":\"failed\",\"error\":\"$ERROR\"}" >> "$RESULTS_FILE"
                    FAIL=$((FAIL + 1))
                    break
                fi

                # Timeout after 15 minutes per document
                ELAPSED=$(($(date +%s) - POLL_START))
                if [ "$ELAPSED" -gt 900 ]; then
                    echo "  -> TIMEOUT (15 min)"
                    echo "{\"file\":\"$FILE\",\"doc_id\":\"$DOC_ID\",\"status\":\"timeout\"}" >> "$RESULTS_FILE"
                    FAIL=$((FAIL + 1))
                    break
                fi

                printf "  -> polling... (%ds, status=%s)\r" "$ELAPSED" "$POLL_STATUS"
            done
        else
            # Synchronous completion
            ENTITIES=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('neo4j_entities','-'))" 2>/dev/null)
            RELATIONS=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('neo4j_relationships','-'))" 2>/dev/null)
            CHUNKS=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('chunks_created','-'))" 2>/dev/null)
            echo "  -> SYNC: entities=$ENTITIES | relations=$RELATIONS | chunks=$CHUNKS"
            echo "{\"file\":\"$FILE\",\"doc_id\":\"$DOC_ID\",\"status\":\"completed\",\"duration_s\":$DURATION_S,\"entities\":$ENTITIES,\"relations\":$RELATIONS,\"chunks\":$CHUNKS,\"filesize\":$FILESIZE}" >> "$RESULTS_FILE"
            SUCCESS=$((SUCCESS + 1))
        fi
    else
        echo "  -> ERROR HTTP $HTTP_CODE: $(echo "$BODY" | head -c 200)"
        echo "{\"file\":\"$FILE\",\"status\":\"error\",\"http_code\":\"$HTTP_CODE\"}" >> "$RESULTS_FILE"
        FAIL=$((FAIL + 1))
    fi

    echo ""
done

TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_END - TOTAL_START))
TOTAL_MIN=$((TOTAL_ELAPSED / 60))
TOTAL_SEC=$((TOTAL_ELAPSED % 60))

echo "========================================="
echo "BATCH COMPLETE"
echo "========================================="
echo "Success: $SUCCESS / 10"
echo "Failed:  $FAIL / 10"
echo "Total:   ${TOTAL_MIN}m ${TOTAL_SEC}s"
echo "End:     $(date -Iseconds)"
echo ""
echo "Results: $RESULTS_FILE"
echo ""

# Summary table
echo "=== DETAILED RESULTS ==="
python3 -c "
import json
results = []
with open('$RESULTS_FILE') as f:
    for line in f:
        if line.strip():
            results.append(json.loads(line))

print(f\"{'File':<50} {'Time':>7} {'Ent':>5} {'Rel':>5} {'Chunks':>6} {'Size':>7}\")
print('-' * 85)
total_time = 0
total_ent = 0
total_rel = 0
total_chunks = 0
for r in results:
    fname = r.get('file','?')[:48]
    dur = r.get('duration_s', 0)
    ent = r.get('entities', 0)
    rel = r.get('relations', 0)
    chunks = r.get('chunks', 0)
    fsize = r.get('filesize', 0)
    status = r.get('status', '?')

    if status == 'completed':
        total_time += float(dur) if dur != '-' else 0
        total_ent += int(ent) if str(ent) != '-' else 0
        total_rel += int(rel) if str(rel) != '-' else 0
        total_chunks += int(chunks) if str(chunks) != '-' else 0
        print(f'{fname:<50} {dur:>6}s {ent:>5} {rel:>5} {chunks:>6} {fsize:>6}B')
    else:
        print(f'{fname:<50} {status:>7}')

completed = [r for r in results if r.get('status')=='completed']
print('-' * 85)
print(f\"{'TOTAL':<50} {total_time:>6.0f}s {total_ent:>5} {total_rel:>5} {total_chunks:>6}\")
print(f\"{'AVG per doc':<50} {total_time/max(len(completed),1):>6.1f}s\")
" 2>&1

# Check for vLLM retries in logs
echo ""
echo "=== vLLM RETRY STATS ==="
RETRY_COUNT=$(docker logs aegis-api --since=2h 2>&1 | grep -c "Retrying.*_call_vllm" || echo "0")
VLLM_FAILS=$(docker logs aegis-api --since=2h 2>&1 | grep -c "vllm_request_failed" || echo "0")
VLLM_OK=$(docker logs aegis-api --since=2h 2>&1 | grep -c "vllm_request_complete" || echo "0")
echo "vLLM successful calls: $VLLM_OK"
echo "vLLM retries:          $RETRY_COUNT"
echo "vLLM final failures:   $VLLM_FAILS"
