#!/bin/bash
# Sprint 124: Comprehensive LLM Extraction Benchmark
# Tests gpt-oss:20b and gpt-oss:120b with thinking on/off
# Uses the actual Frontend API for realistic results

set -e

# Configuration
API="http://localhost:8000"
RESULTS_DIR="data/benchmark_results/sprint124_$(date +%Y%m%d_%H%M%S)"
SMALL_FILE="data/ragas_phase1_contexts/ragas_phase1_0985_logqa_emanual5.txt"  # 576 bytes
MEDIUM_FILE="data/ragas_phase1_contexts/ragas_phase1_0015_hotpot_5ae0d91e.txt"  # 6.1 KB
COMPOSE_FILE="docker-compose.dgx-spark.yml"

mkdir -p "$RESULTS_DIR"

echo "================================================================"
echo "Sprint 124: LLM Extraction Benchmark"
echo "================================================================"
echo "Results directory: $RESULTS_DIR"
echo "Small file: $SMALL_FILE ($(wc -c < "$SMALL_FILE") bytes)"
echo "Medium file: $MEDIUM_FILE ($(wc -c < "$MEDIUM_FILE") bytes)"
echo "================================================================"
echo ""

# Global token
TOKEN=""

# Function to authenticate
authenticate() {
    TOKEN=$(curl -s -X POST "$API/api/v1/retrieval/auth/token" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' | jq -r '.access_token')

    if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
        echo "ERROR: Authentication failed!"
        return 1
    fi
    echo "  ✓ Authenticated"
}

# Function to reconfigure and restart API with new settings
reconfigure_api() {
    local model=$1
    local thinking=$2

    echo ""
    echo "--- Reconfiguring API: model=$model, thinking=$thinking ---"

    # Export for docker compose
    export LIGHTRAG_LLM_MODEL="$model"
    export AEGIS_LLM_THINKING="$thinking"

    # Force recreate API container with new env
    docker compose -f "$COMPOSE_FILE" up -d --force-recreate api > /dev/null 2>&1

    # Wait for API to be healthy
    echo "  Waiting for API to be healthy..."
    for i in {1..60}; do
        if curl -s "$API/health" | grep -q "healthy"; then
            echo "  ✓ API healthy"
            break
        fi
        sleep 2
    done
}

# Function to restart Ollama and warm up model
restart_and_warmup() {
    local model=$1
    local thinking=$2

    echo "--- Restarting Ollama and warming up $model ---"

    # Unload any existing model
    curl -s http://localhost:11434/api/generate -d '{"model": "'"$model"'", "keep_alive": 0}' > /dev/null 2>&1 || true
    sleep 2

    # Restart Ollama container
    docker restart aegis-ollama > /dev/null 2>&1
    sleep 5

    # Wait for Ollama to be ready
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    # Warm up the model with correct thinking setting
    echo "  Warming up model (think=$thinking)..."
    curl -s http://localhost:11434/api/generate -d '{
        "model": "'"$model"'",
        "prompt": "Hello, respond with OK.",
        "stream": false,
        "think": '"$thinking"',
        "options": {"num_predict": 10}
    }' > /dev/null 2>&1

    # Verify model is loaded
    docker exec aegis-ollama ollama ps 2>/dev/null | grep -v "NAME"
    echo "  ✓ Model warmed up"
}

# Function to run a single test
run_test() {
    local model=$1
    local thinking=$2
    local file=$3
    local namespace=$4
    local test_name=$5

    echo ""
    echo "=== Test: $test_name ==="
    echo "  Model: $model"
    echo "  Thinking: $thinking"
    echo "  File: $(basename $file)"
    echo "  Namespace: $namespace"

    # Verify API config
    local api_model=$(docker exec aegis-api printenv LIGHTRAG_LLM_MODEL 2>/dev/null || echo "unknown")
    local api_thinking=$(docker exec aegis-api printenv AEGIS_LLM_THINKING 2>/dev/null || echo "unknown")
    echo "  API Config: model=$api_model, thinking=$api_thinking"

    # Start timer
    local start_time=$(date +%s.%N)

    # Upload file via API
    local response=$(curl -s -X POST "$API/api/v1/retrieval/upload" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$file" \
        -F "namespace_id=$namespace" \
        --max-time 1800 2>&1)

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    # Parse response
    local chunks=$(echo "$response" | jq -r '.chunks_created // 0' 2>/dev/null || echo "0")
    local entities=$(echo "$response" | jq -r '.neo4j_entities // 0' 2>/dev/null || echo "0")
    local relations=$(echo "$response" | jq -r '.neo4j_relationships // 0' 2>/dev/null || echo "0")
    local doc_id=$(echo "$response" | jq -r '.document_id // "unknown"' 2>/dev/null || echo "unknown")
    local proc_time=$(echo "$response" | jq -r '.processing_time_s // 0' 2>/dev/null || echo "0")

    echo "  Duration: ${duration}s (API reported: ${proc_time}s)"
    echo "  Chunks: $chunks, Entities: $entities, Relations: $relations"

    # Save detailed results
    local result_file="$RESULTS_DIR/${test_name}.json"
    cat > "$result_file" << EOF
{
    "test_name": "$test_name",
    "model": "$model",
    "thinking": $thinking,
    "file": "$(basename $file)",
    "file_size_bytes": $(wc -c < "$file"),
    "namespace": "$namespace",
    "duration_seconds": $duration,
    "api_processing_time_s": $proc_time,
    "chunks_created": $chunks,
    "entities_extracted": $entities,
    "relations_extracted": $relations,
    "document_id": "$doc_id",
    "timestamp": "$(date -Iseconds)",
    "raw_response": $(echo "$response" | jq '.' 2>/dev/null || echo '"parse_error"')
}
EOF

    echo "  ✓ Results saved to: $result_file"

    # Get extraction details from API logs - capture JSON extraction results
    echo "  Extracting detailed logs..."
    docker logs aegis-api --since 10m 2>&1 | grep -E "(entities_extracted|relationships_extracted|json_parse_success|TIMING_)" | tail -30 > "$RESULTS_DIR/${test_name}_logs.txt" 2>/dev/null || true

    # CSV summary line
    echo "$test_name,$model,$thinking,$duration,$proc_time,$chunks,$entities,$relations" >> "$RESULTS_DIR/summary.csv"
}

# Main test execution
echo ""
echo "=== Starting Benchmark ==="
echo ""

# Initialize CSV
echo "test_name,model,thinking,total_duration_s,api_time_s,chunks,entities,relations" > "$RESULTS_DIR/summary.csv"

#
# TEST SUITE 1: gpt-oss:20b
#

# Test 1.1: gpt-oss:20b, thinking=false
echo ""
echo "========================================"
echo "TEST SUITE 1: gpt-oss:20b"
echo "========================================"
reconfigure_api "gpt-oss:20b" "false"
restart_and_warmup "gpt-oss:20b" "false"
authenticate
run_test "gpt-oss:20b" "false" "$SMALL_FILE" "bench_20b_thinkOff_small" "20b_thinkOff_small"
run_test "gpt-oss:20b" "false" "$MEDIUM_FILE" "bench_20b_thinkOff_medium" "20b_thinkOff_medium"

# Test 1.2: gpt-oss:20b, thinking=true
reconfigure_api "gpt-oss:20b" "true"
restart_and_warmup "gpt-oss:20b" "true"
authenticate
run_test "gpt-oss:20b" "true" "$SMALL_FILE" "bench_20b_thinkOn_small" "20b_thinkOn_small"
run_test "gpt-oss:20b" "true" "$MEDIUM_FILE" "bench_20b_thinkOn_medium" "20b_thinkOn_medium"

#
# TEST SUITE 2: gpt-oss:120b
#

echo ""
echo "========================================"
echo "TEST SUITE 2: gpt-oss:120b"
echo "========================================"

# Test 2.1: gpt-oss:120b, thinking=false
reconfigure_api "gpt-oss:120b" "false"
restart_and_warmup "gpt-oss:120b" "false"
authenticate
run_test "gpt-oss:120b" "false" "$SMALL_FILE" "bench_120b_thinkOff_small" "120b_thinkOff_small"
run_test "gpt-oss:120b" "false" "$MEDIUM_FILE" "bench_120b_thinkOff_medium" "120b_thinkOff_medium"

# Test 2.2: gpt-oss:120b, thinking=true
reconfigure_api "gpt-oss:120b" "true"
restart_and_warmup "gpt-oss:120b" "true"
authenticate
run_test "gpt-oss:120b" "true" "$SMALL_FILE" "bench_120b_thinkOn_small" "120b_thinkOn_small"
run_test "gpt-oss:120b" "true" "$MEDIUM_FILE" "bench_120b_thinkOn_medium" "120b_thinkOn_medium"

#
# SUMMARY
#

echo ""
echo "================================================================"
echo "BENCHMARK COMPLETE"
echo "================================================================"
echo ""
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "Summary (sorted by duration):"
echo ""
cat "$RESULTS_DIR/summary.csv" | column -t -s','
echo ""

# Calculate averages
echo "Per-Model Averages:"
echo "-------------------"

for model in "gpt-oss:20b" "gpt-oss:120b"; do
    for think in "true" "false"; do
        avg=$(grep ",$model,$think," "$RESULTS_DIR/summary.csv" | awk -F',' '{sum+=$4; count++} END {if(count>0) print sum/count; else print "N/A"}')
        ent=$(grep ",$model,$think," "$RESULTS_DIR/summary.csv" | awk -F',' '{sum+=$7; count++} END {if(count>0) print sum/count; else print "N/A"}')
        rel=$(grep ",$model,$think," "$RESULTS_DIR/summary.csv" | awk -F',' '{sum+=$8; count++} END {if(count>0) print sum/count; else print "N/A"}')
        echo "$model (think=$think): Avg ${avg}s, ${ent} entities, ${rel} relations"
    done
done

echo ""
echo "To view detailed results:"
echo "  cat $RESULTS_DIR/<test_name>.json | jq"
echo "  cat $RESULTS_DIR/<test_name>_logs.txt"
echo ""
