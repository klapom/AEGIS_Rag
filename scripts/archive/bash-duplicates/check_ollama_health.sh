#!/bin/bash
# Ollama Health Check Script for AegisRAG
# Verifies Ollama is running and required models are loaded

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Ollama Health Check${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Required models
required_models=("llama3.2:3b" "llama3.1:8b" "nomic-embed-text")

# Check if Ollama is reachable
echo -e "${YELLOW}[1/3] Checking Ollama connectivity...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running on http://localhost:11434${NC}"
else
    echo -e "${RED}✗ Ollama is not reachable${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "  1. Check if Docker is running: docker ps"
    echo -e "  2. Start services: docker compose up -d"
    echo -e "  3. Check Ollama logs: docker compose logs ollama"
    exit 1
fi

echo ""

# Check installed models
echo -e "${YELLOW}[2/3] Checking installed models...${NC}"

installed_models=$(curl -s http://localhost:11434/api/tags | python -c "import sys, json; print('\n'.join([m['name'] for m in json.load(sys.stdin)['models']]))" 2>/dev/null || echo "")

all_models_present=true
for model in "${required_models[@]}"; do
    if echo "$installed_models" | grep -q "^${model}$"; then
        size=$(curl -s http://localhost:11434/api/tags | python -c "import sys, json; models = json.load(sys.stdin)['models']; m = next((x for x in models if x['name'] == '${model}'), None); print(f\"{m['size']/1e9:.2f}\" if m else '0')" 2>/dev/null)
        echo -e "  ${GREEN}✓ ${model} (${size} GB)${NC}"
    else
        echo -e "  ${RED}✗ ${model} (not found)${NC}"
        all_models_present=false
    fi
done

if [ "$all_models_present" = false ]; then
    echo ""
    echo -e "${YELLOW}Missing models detected!${NC}"
    echo -e "  Run: ./scripts/setup_ollama_models.sh"
    exit 1
fi

echo ""

# Test model inference
echo -e "${YELLOW}[3/3] Testing model inference...${NC}"

test_model="llama3.2:3b"
test_prompt="Hello! Respond with just 'OK' if you can read this."

response=$(curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"${test_model}\",
        \"prompt\": \"${test_prompt}\",
        \"stream\": false,
        \"options\": {
            \"temperature\": 0.1,
            \"num_predict\": 10
        }
    }")

if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓ Model inference successful${NC}"
    echo -e "${GRAY}    Model: ${test_model}${NC}"

    model_response=$(echo "$response" | python -c "import sys, json; print(json.load(sys.stdin)['response'].strip())" 2>/dev/null || echo "unknown")
    load_duration=$(echo "$response" | python -c "import sys, json; print(int(json.load(sys.stdin).get('load_duration', 0) / 1000000))" 2>/dev/null || echo "0")
    total_duration=$(echo "$response" | python -c "import sys, json; print(int(json.load(sys.stdin).get('total_duration', 0) / 1000000))" 2>/dev/null || echo "0")

    echo -e "${GRAY}    Response: ${model_response}${NC}"
    echo -e "${GRAY}    Load duration: ${load_duration}ms${NC}"
    echo -e "${GRAY}    Total duration: ${total_duration}ms${NC}"
else
    echo -e "  ${RED}✗ Model inference failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All checks passed! Ollama is healthy ✓${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Show system info
echo -e "${CYAN}System Information:${NC}"
echo -e "  Ollama URL: http://localhost:11434"

model_count=$(echo "$installed_models" | wc -l)
echo -e "  Installed models: $model_count"
echo -e "  Required models: ${#required_models[@]}"

total_size=$(curl -s http://localhost:11434/api/tags | python -c "import sys, json; print(f\"{sum(m['size'] for m in json.load(sys.stdin)['models'])/1e9:.2f}\")" 2>/dev/null || echo "0")
echo -e "  Total model size: ${total_size} GB"

echo ""
echo -e "${CYAN}Ready to use! Start the API server:${NC}"
echo -e "  uvicorn src.api.main:app --reload"
echo ""
