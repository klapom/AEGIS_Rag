#!/bin/bash
# Setup Ollama Models for AegisRAG
# This script downloads all required Ollama models for development

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}AegisRAG - Ollama Model Setup${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if Ollama is running
echo -e "${YELLOW}Checking Ollama status...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running${NC}"
else
    echo -e "${RED}✗ Ollama is not running or not accessible${NC}"
    echo -e "${YELLOW}  Please start Docker services first: docker compose up -d${NC}"
    exit 1
fi

echo ""

# Models to download
declare -A models=(
    ["llama3.2:3b"]="Latest 3B model for fast query understanding|~2GB"
    ["llama3.1:8b"]="Latest 8B model for high-quality generation (128K context)|~4.7GB"
    ["nomic-embed-text"]="Embedding model (768-dim) for vector search|~274MB"
)

echo -e "${CYAN}Models to download:${NC}"
for model in "${!models[@]}"; do
    IFS='|' read -r desc size <<< "${models[$model]}"
    echo -e "  - ${model} (${size})"
    echo -e "${GRAY}    ${desc}${NC}"
done

echo ""
echo -e "${YELLOW}Total download size: ~7GB${NC}"
echo ""

# Download each model
total_models=${#models[@]}
current_model=0

for model in "${!models[@]}"; do
    ((current_model++))
    IFS='|' read -r desc size <<< "${models[$model]}"

    echo -e "${CYAN}[${current_model}/${total_models}] Pulling ${model}...${NC}"
    echo -e "${GRAY}  ${desc}${NC}"
    echo ""

    # Pull model using Ollama CLI
    start_time=$(date +%s)
    if ollama pull "$model"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo -e "${GREEN}✓ ${model} downloaded successfully (took ${duration}s)${NC}"
    else
        echo -e "${RED}✗ Failed to download ${model}${NC}"
        exit 1
    fi
    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All models downloaded successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verify models
echo -e "${YELLOW}Verifying installed models...${NC}"
echo ""

installed_models=$(curl -s http://localhost:11434/api/tags | python -c "import sys, json; print('\n'.join([m['name'] for m in json.load(sys.stdin)['models']]))" 2>/dev/null || echo "")

echo -e "${CYAN}Installed models:${NC}"
for model in "${!models[@]}"; do
    if echo "$installed_models" | grep -q "^${model}$"; then
        echo -e "  ${GREEN}✓ ${model}${NC}"
    else
        echo -e "  ${RED}✗ ${model} (not found)${NC}"
    fi
done

echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Update your .env file with these models:"
echo -e "${GRAY}     OLLAMA_MODEL_QUERY=llama3.2:3b${NC}"
echo -e "${GRAY}     OLLAMA_MODEL_GENERATION=llama3.1:8b${NC}"
echo -e "${GRAY}     OLLAMA_MODEL_EMBEDDING=nomic-embed-text${NC}"
echo -e "  2. Test the setup: ./scripts/check_ollama_health.sh"
echo -e "  3. Start the API server: uvicorn src.api.main:app --reload"
echo ""
