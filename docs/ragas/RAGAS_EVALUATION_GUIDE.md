# RAGAS Evaluation Guide

**Last Updated:** 2026-02-04 (Sprint 124)
**Purpose:** Standardized process for RAGAS evaluation using production ingestion pipeline

> **Sprint 124 Updates:**
> - Removed BM25 references (replaced by BGE-M3 sparse vectors since Sprint 87)
> - Context window increased to 128K for accurate evaluation
> - Removed 500-char truncation in eval harness

---

## Overview

This guide describes the **correct** way to ingest RAGAS evaluation datasets into AegisRAG for evaluation purposes. Always use the **Frontend API endpoint** to ensure consistency with production behavior.

---

## ⚠️ CRITICAL: Use Frontend API Endpoint

**✅ CORRECT Endpoint:**
```
POST /api/v1/retrieval/upload
```

**❌ WRONG Endpoint (Admin):**
```
POST /api/v1/admin/indexing/upload + /add
```

### Why Frontend Endpoint?

| Aspect | Frontend Endpoint | Admin Endpoint |
|--------|-------------------|----------------|
| **Pipeline** | Full LangGraph (Sprint 21) | Manual 2-step process |
| **Docling** | Automatic | Manual trigger required |
| **Chunking** | Adaptive section-aware | Must configure manually |
| **Embedding** | BGE-M3 CUDA automatic | Must trigger separately |
| **Graph** | Neo4j extraction automatic | Must trigger separately |
| **Namespace** | Single parameter | Complex multi-step |
| **Production Match** | 100% identical | Different behavior |

**Rule:** RAGAS evaluation MUST use the same pipeline as production users!

---

## Dataset Structure

### ragas_eval_txt (Small Dataset)
```
data/ragas_eval_txt/
├── hotpot_000000.txt          # ~200 bytes
├── hotpot_000000_meta.json    # Question + ground truth
├── hotpot_000001.txt
├── hotpot_000001_meta.json
...
└── hotpot_000004_meta.json
```

- **Files:** 5 .txt files
- **Size:** ~200-450 bytes each
- **Namespace:** `ragas_eval_txt`
- **Purpose:** Quick smoke tests

### ragas_eval_txt_large (Large Dataset)
```
data/ragas_eval_txt_large/
├── sample_0000.txt            # ~5 KB
├── sample_0000_meta.json      # Question + ground truth
├── sample_0001.txt
├── sample_0001_meta.json
...
└── sample_0009_meta.json
```

- **Files:** 10 .txt files
- **Size:** ~3-14 KB each
- **Namespace:** `ragas_eval_txt_large`
- **Purpose:** Full RAGAS evaluation

---

## Step-by-Step Ingestion Process

### Prerequisites

1. **All containers running:**
   ```bash
   docker compose -f docker-compose.dgx-spark.yml up -d
   ```

2. **API healthy:**
   ```bash
   curl http://localhost:8000/health | jq .
   ```

3. **Docling container running:**
   ```bash
   docker ps | grep docling
   # Should show: aegis-docling (healthy)
   ```

4. **Databases empty (for clean eval):**
   ```bash
   # Stop containers
   docker compose -f docker-compose.dgx-spark.yml down

   # Clear data (Sprint 124: BM25 removed - lexical search now uses BGE-M3 sparse vectors)
   rm -rf data/qdrant_storage/* data/neo4j_data/* data/redis_data/* data/lightrag_storage/*.*

   # Restart
   docker compose -f docker-compose.dgx-spark.yml up -d
   ```

### Upload Script (Frontend Endpoint)

Use this script: `scripts/upload_ragas_frontend.sh`

```bash
#!/bin/bash
set -e

API="http://localhost:8000"
ENDPOINT="$API/api/v1/retrieval/upload"

echo "================================================"
echo "RAGAS Dataset Upload (Frontend Endpoint)"
echo "================================================"

# Function to upload via frontend endpoint
upload_file() {
    local file=$1
    local namespace=$2
    local filename=$(basename "$file")

    echo ""
    echo "=== Uploading: $filename (namespace: $namespace) ==="

    RESPONSE=$(curl -s -X POST "$ENDPOINT" \
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

# Upload small files
echo ""
echo "### SMALL FILES (ragas_eval_txt) ###"
TOTAL=0
SUCCESS=0
for file in data/ragas_eval_txt/hotpot_*.txt; do
    [ -f "$file" ] || continue
    TOTAL=$((TOTAL + 1))
    if upload_file "$file" "ragas_eval_txt"; then
        SUCCESS=$((SUCCESS + 1))
    fi
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
done

# Summary
echo ""
echo "================================================"
echo "UPLOAD SUMMARY"
echo "================================================"
echo "Total Files:      $TOTAL"
echo "Successful:       $SUCCESS"
echo "Failed:           $((TOTAL - SUCCESS))"
echo "================================================"
```

### Run Upload

```bash
# Make executable
chmod +x scripts/upload_ragas_frontend.sh

# Run
./scripts/upload_ragas_frontend.sh
```

**Expected Output:**
```
=== Uploading: hotpot_000000.txt (namespace: ragas_eval_txt) ===
  ✓ Success
  - Chunks: 1
  - Entities: 3
  - Relations: 2
  - Duration: 8.5s

...

UPLOAD SUMMARY
Total Files:      15
Successful:       15
Failed:           0
```

---

## Verification

### 1. Check Vector Database (Qdrant)

```bash
curl -s http://localhost:6333/collections/documents_v1 | jq '{
  points_count: .result.points_count,
  indexed_vectors_count: .result.indexed_vectors_count,
  status: .result.status
}'
```

**Expected:**
```json
{
  "points_count": 17,
  "indexed_vectors_count": 0,
  "status": "green"
}
```

### 2. Check Graph Database (Neo4j)

```bash
curl -s http://localhost:8000/api/v1/admin/graph/stats | jq '{
  chunks: .chunk_nodes,
  entities: .entity_nodes,
  relations: .relation_edges,
  communities: .communities
}'
```

**Expected:**
```json
{
  "chunks": 17,
  "entities": 150,
  "relations": 70,
  "communities": 95
}
```

### 3. Check Namespaces

```bash
# Qdrant namespace distribution
curl -s 'http://localhost:6333/collections/documents_v1/points/scroll?limit=100' | \
  jq '.result.points[].payload.namespace' | sort | uniq -c

# Expected:
#   5 "ragas_eval_txt"
#  10 "ragas_eval_txt_large"
```

---

## RAGAS Evaluation Execution

After successful ingestion, run RAGAS evaluation:

```bash
# Using existing RAGAS script
poetry run python scripts/run_ragas_evaluation.py \
    --dataset data/ragas_eval_txt \
    --namespace ragas_eval_txt \
    --output reports/ragas_eval_txt_results.json

poetry run python scripts/run_ragas_evaluation.py \
    --dataset data/ragas_eval_txt_large \
    --namespace ragas_eval_txt_large \
    --output reports/ragas_eval_txt_large_results.json
```

---

## Troubleshooting

### Issue: "File upload failed"

**Check:**
1. Docling container running: `docker ps | grep docling`
2. API logs: `docker logs aegis-api --tail 50`
3. File exists: `ls -lh data/ragas_eval_txt/`

### Issue: "No chunks created"

**Possible causes:**
- Docling parsing failed (check logs)
- File too small (< 50 chars)
- Unsupported format

**Fix:**
```bash
# Check Docling health
curl http://localhost:8080/health

# Restart Docling
docker restart aegis-docling
```

### Issue: "Namespace mismatch"

**Symptoms:** Files uploaded but queries return nothing

**Verify namespace:**
```bash
curl -s 'http://localhost:6333/collections/documents_v1/points/scroll?limit=1' | \
  jq '.result.points[0].payload.namespace'
```

**Expected:** `"ragas_eval_txt"` or `"ragas_eval_txt_large"`

---

## Best Practices

1. ✅ **Always use frontend endpoint** (`/api/v1/retrieval/upload`)
2. ✅ **Clear databases before RAGAS runs** (prevent contamination)
3. ✅ **Use separate namespaces** for different datasets
4. ✅ **Verify upload success** before running evaluation
5. ✅ **Check both databases** (Qdrant for vectors, Neo4j for graph)
6. ❌ **Never use admin endpoints** for evaluation ingestion
7. ❌ **Never mix RAGAS data** with production data

---

## References

- **Frontend Upload Endpoint:** `src/api/v1/retrieval.py:423`
- **LangGraph Pipeline:** `src/components/ingestion/langgraph_pipeline.py`
- **Docling Client:** `src/components/ingestion/docling_client.py`
- **RAGAS Evaluator:** `src/evaluation/ragas_evaluator.py`
- **Sprint 21 Feature 21.2:** Full ingestion pipeline implementation
- **Sprint 76-77:** RAGAS evaluation infrastructure
- **Sprint 87:** BGE-M3 hybrid search (replaces BM25)
- **Sprint 124:** Context window 128K, truncation fixes

---

**Document maintained by:** RAGAS Evaluation Team
**Review frequency:** Before each RAGAS evaluation run
**Last Update:** Sprint 124 (2026-02-04)
