#!/bin/bash
# Sprint 44 Part 3: Run all 7 model evaluations sequentially
# Created: 2025-12-11

set -e

OUTPUT_DIR="reports/sprint44_evaluation"
SAMPLES=10
LOG_DIR="/tmp/sprint44_logs"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

echo "=== Sprint 44 Part 3: Full Model Evaluation ==="
echo "Start: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Samples per model: $SAMPLES"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Array of models to evaluate
MODELS=(
    "qwen3:32b"
    "qwen3:8b"
    "qwen2.5:7b"
    "nuextract:3.8b"
    "gemma3:4b"
    "qwen2.5:3b"
)

# Run evaluations sequentially
for i in "${!MODELS[@]}"; do
    MODEL="${MODELS[$i]}"
    MODEL_NUM=$((i + 1))
    MODEL_SAFE="${MODEL//:/_}"
    LOG_FILE="$LOG_DIR/eval_${MODEL_SAFE}.log"

    echo ""
    echo "=========================================="
    echo "[$MODEL_NUM/${#MODELS[@]}] Evaluating: $MODEL"
    echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Log: $LOG_FILE"
    echo "=========================================="

    poetry run python scripts/pipeline_model_evaluation.py \
        --model "$MODEL" \
        --samples "$SAMPLES" \
        --output-dir "$OUTPUT_DIR" \
        2>&1 | tee "$LOG_FILE"

    echo "[$MODEL_NUM/${#MODELS[@]}] $MODEL completed: $(date '+%Y-%m-%d %H:%M:%S')"
done

echo ""
echo "=== All Evaluations Complete ==="
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Reports saved to: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/*.json 2>/dev/null || echo "No JSON reports found"
