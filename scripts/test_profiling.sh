#!/bin/bash
# Quick test runner for profiling scripts
# Sprint 68 Feature 68.2: Performance Profiling & Bottleneck Analysis

set -e

echo "=========================================="
echo "Testing Profiling Scripts (Sprint 68.2)"
echo "=========================================="
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo "[1/3] Testing Pipeline Profiling (single query)..."
echo "---"
python scripts/profile_pipeline.py \
    --query "What is the project architecture?" \
    --output /tmp/pipeline_test.json
echo ""

echo "[2/3] Testing Memory Profiling (single query)..."
echo "---"
python scripts/profile_memory.py \
    --query "How does authentication work?" \
    --output /tmp/memory_test.json
echo ""

echo "[3/3] Checking output files..."
echo "---"
ls -lh /tmp/pipeline_test.json
ls -lh /tmp/memory_test.json
echo ""

echo "=========================================="
echo "All profiling scripts validated!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run intensive profiling:"
echo "   python scripts/profile_pipeline.py --mode intensive"
echo ""
echo "2. Run memory leak detection:"
echo "   python scripts/profile_memory.py --iterations 50"
echo ""
echo "3. Generate full report:"
echo "   python scripts/profile_report.py"
echo ""
